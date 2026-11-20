"""Cross-engine verification: same five headline metrics, three independent paths.

1. DuckDB over the analysis database.
2. DuckDB over exported Parquet files.
3. Pure Python over the exported aggregates in outputs_public/.

The point is to prove the published numbers do not depend on one query engine or
one storage format. ClickHouse runs the same SQL as step 2 once a container is
available; see sql/clickhouse/ and docs/tech-stack.md.
"""

from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".localdeps"))
import duckdb

DB = ROOT / "data" / "processed" / "kuaisearch.duckdb"
PARQUET = ROOT / "exports" / "parquet"
PUBLIC = ROOT / "outputs_public"

# Every query is written against the same logical schema (sessions-like columns).
METRICS = {
    "exposures": "SELECT sum(impressions) FROM sessions",
    "clicks": "SELECT sum(clicks) FROM sessions",
    "item_ctr": "SELECT sum(clicks) * 1.0 / sum(impressions) FROM sessions",
    "request_click_rate": (
        "SELECT count(*) FILTER (WHERE clicks > 0) * 1.0 / count(*) FROM sessions"
    ),
    "long_list_exposure_share": (
        "SELECT sum(impressions) FILTER (WHERE length_stratum = '100+') * 1.0 "
        "/ sum(impressions) FROM sessions"
    ),
}


def time_query(conn: duckdb.DuckDBPyConnection, sql: str, repeats: int = 3) -> tuple[float, list]:
    best = float("inf")
    rows = []
    for _ in range(repeats):
        start = time.perf_counter()
        rows = conn.execute(sql).fetchall()
        best = min(best, time.perf_counter() - start)
    return best, rows


def main() -> None:
    print("== DuckDB over database ==")
    conn = duckdb.connect(str(DB), read_only=True)
    conn.execute("SET threads=4")
    db_times: dict[str, float] = {}
    db_values: dict[str, list] = {}
    for name, sql in METRICS.items():
        seconds, rows = time_query(conn, sql)
        db_times[name] = seconds
        db_values[name] = rows
        print(f"{name:26s} {rows[0][0]:>18,.6f}  {seconds * 1000:8.1f} ms")
    conn.close()

    print("\n== DuckDB over Parquet ==")
    parquet = duckdb.connect()
    parquet.execute("SET threads=4")
    parquet.execute(
        f"CREATE VIEW sessions AS SELECT * FROM read_parquet('{(PARQUET / 'sessions.parquet').as_posix()}')"
    )
    pq_times: dict[str, float] = {}
    pq_values: dict[str, list] = {}
    for name, sql in METRICS.items():
        seconds, rows = time_query(parquet, sql)
        pq_times[name] = seconds
        pq_values[name] = rows
        print(f"{name:26s} {rows[0][0]:>18,.6f}  {seconds * 1000:8.1f} ms")
    parquet.close()

    print("\n== Pure Python over outputs_public/ ==")
    with (PUBLIC / "overview.csv").open(encoding="utf-8-sig") as stream:
        overview = list(csv.DictReader(stream))
    exposures = sum(int(row["exposures"]) for row in overview)
    clicks = sum(int(row["clicks"]) for row in overview)
    requests = sum(int(row["requests"]) for row in overview)
    clicked = sum(int(row["clicked_requests"]) for row in overview)
    with (PUBLIC / "length_strata.csv").open(encoding="utf-8-sig") as stream:
        strata = list(csv.DictReader(stream))
    long_exposures = sum(
        int(row["exposures"]) for row in strata if row["length_stratum"] == "100+"
    )
    python_values = {
        "exposures": [exposures],
        "clicks": [clicks],
        "item_ctr": [clicks / exposures],
        "request_click_rate": [clicked / requests],
        "long_list_exposure_share": [long_exposures / exposures],
    }
    for name in METRICS:
        print(f"{name:26s} {python_values[name][0]:>18,.6f}")

    print("\n== reconciliation ==")
    failed = 0
    for name in METRICS:
        a = float(db_values[name][0][0])
        b = float(pq_values[name][0][0])
        c = float(python_values[name][0])
        if name == "item_ctr":
            ok = abs(a - b) < 1e-12 and abs(a - c) < 1e-9
        else:
            ok = a == b == c
        failed += 0 if ok else 1
        print(f"{name:26s} {'PASS' if ok else 'FAIL'}  db={a!r} parquet={b!r} python={c!r}")

    summary = {
        "verified_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "metrics": {
            name: {
                "value": float(db_values[name][0][0]),
                "duckdb_db_ms": round(db_times[name] * 1000, 1),
                "duckdb_parquet_ms": round(pq_times[name] * 1000, 1),
            }
            for name in METRICS
        },
        "failed_checks": failed,
    }
    (PUBLIC / "engine_check.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nfailed checks: {failed}; wrote outputs_public/engine_check.json")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
