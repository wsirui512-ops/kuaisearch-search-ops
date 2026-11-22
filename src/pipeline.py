"""Build the local KuaiSearch-Lite analysis database and export aggregate results.

Design notes
------------
* The database is built into ``.work/build.duckdb`` and only replaces the published
  file after every SQL step and quality assertion passes. A failed run never leaves
  the previous database deleted (the v1 pipeline removed it before connecting).
* Raw JSONL files stay outside git. Only reviewed aggregates are exported to
  ``outputs_public/``; the full query-level table stays in ``outputs/``.
* Two denominators are never mixed: item CTR (clicks / exposures) and request click
  rate (requests with a click / requests).
"""

from __future__ import annotations

import csv
import json
import os
import shutil
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "kuaisearch"
DB = ROOT / "data" / "processed" / "kuaisearch.duckdb"
BUILD_DB = ROOT / ".work" / "build.duckdb"
OUT = ROOT / "outputs"
PUBLIC = ROOT / "outputs_public"
SQL_DIR = ROOT / "sql"
INTENT_RULES = ROOT / "config" / "intent_rules.csv"

SOURCES = {
    "raw_search": RAW / "recall_lite" / "train.jsonl",
    "raw_items": RAW / "items_lite" / "train.jsonl",
    "raw_users": RAW / "users_lite" / "train.jsonl",
    "raw_relevance": RAW / "relevance" / "train.jsonl",
}

NUMERIC_CHECKS = {
    "requests": "distinct_sessions",
    "exposure_rows": "request_exposures",
    "exposure_clicks": "request_clicks",
    "exposure_purchases": "request_purchases",
    "item_rows": "distinct_items",
    "user_rows": "distinct_users",
}

ZERO_CHECKS = (
    "missing_item_exposures",
    "missing_user_requests",
    "bad_positions",
    "unclassified_requests",
    "zero_exposure_requests",
    "clicks_exceeding_exposures",
)

# (file name, SQL, publish?) - publish=False stays local because it may contain raw query text.
EXPORTS = [
    ("overview", "SELECT * FROM overview ORDER BY split", True),
    ("length_strata", "SELECT * FROM length_strata ORDER BY split, length_stratum", True),
    ("intent_metrics", "SELECT * FROM intent_metrics ORDER BY split, requests DESC, intent", True),
    (
        "intent_residuals",
        """
        SELECT
          m.intent, m.requests, m.users, m.exposures, m.clicks, m.purchases,
          m.avg_list_length, m.item_ctr,
          e.expected_clicks / e.exposures AS expected_ctr,
          (e.expected_clicks / e.exposures - m.item_ctr) * 100 AS gap_pp,
          (e.expected_clicks - m.clicks) AS gap_clicks,
          m.request_click_rate, m.request_purchase_rate
        FROM intent_metrics AS m
        JOIN intent_expected AS e USING (intent)
        WHERE m.split = 'train'
        ORDER BY gap_clicks DESC, m.intent
        """,
        True,
    ),
    ("category_metrics", "SELECT * FROM category_metrics ORDER BY split, exposures DESC, category_id", True),
    (
        "relative_time_metrics",
        "SELECT * FROM relative_time_metrics ORDER BY split, time_bucket",
        True,
    ),
    ("age_metrics", "SELECT * FROM age_metrics ORDER BY split, requests DESC, age_bucket", True),
    ("relevance_coverage", "SELECT * FROM relevance_coverage ORDER BY split, score", True),
    ("relevance_summary", "SELECT * FROM relevance_summary", True),
    ("stratum_baseline", "SELECT * FROM stratum_baseline ORDER BY length_stratum", True),
    (
        "category_residuals",
        """
        SELECT
          c.category_id, c.category, c.exposures, c.clicks, c.item_ctr,
          e.expected_clicks / e.exposures AS expected_ctr,
          (e.expected_clicks / e.exposures - c.item_ctr) * 100 AS gap_pp,
          (e.expected_clicks - c.clicks) AS gap_clicks
        FROM category_metrics AS c
        JOIN category_expected AS e USING (category)
        WHERE c.split = 'train'
        ORDER BY gap_clicks DESC, c.category_id
        """,
        True,
    ),
    ("query_metrics", "SELECT * FROM query_metrics ORDER BY split, exposures DESC, query_key", False),
    (
        "intent_review_sample",
        """
        SELECT query, intent AS auto_intent, '' AS reviewer_intent, '' AS note
        FROM query_intent
        USING SAMPLE 200 ROWS
        """,
        False,
    ),
]

OPPORTUNITY_COLUMNS = [
    "rank",
    "query_key",
    "query",
    "requests",
    "users",
    "exposures",
    "clicks",
    "purchases",
    "item_ctr",
    "expected_ctr",
    "gap_pp",
    "gap_clicks",
    "avg_list_length",
    "request_click_rate",
    "request_purchase_rate",
    "wilson_low",
    "wilson_high",
    "p_value",
    "q_value",
    "test_exposures",
    "test_requests",
    "test_item_ctr",
    "test_request_click_rate",
    "test_expected_ctr",
    "validation",
]


def _sql_path(path: Path) -> str:
    return str(path).replace("'", "''").replace("\\", "/")


def _stable(value):
    """Collapse parallel-aggregation float noise so exports diff cleanly.

    Ten significant digits keeps small p-values (1e-52) intact while removing the
    last-bit differences that change between runs with different thread scheduling.
    """
    if isinstance(value, float):
        return float(f"{value:.10g}")
    return value


def _write_rows(path: Path, columns: list[str], rows: list[tuple]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(columns)
        writer.writerows(tuple(_stable(value) for value in row) for row in rows)


def _write_query(conn: duckdb.DuckDBPyConnection, sql: str, path: Path) -> int:
    result = conn.execute(sql)
    columns = [description[0] for description in result.description]
    rows = result.fetchall()
    _write_rows(path, columns, rows)
    return len(rows)


def _build_opportunities(conn: duckdb.DuckDBPyConnection) -> list[tuple]:
    from stats import benjamini_hochberg, compare_rate, wilson_interval

    test_baseline = conn.execute(
        "SELECT item_ctr FROM overview WHERE split = 'test'"
    ).fetchone()[0]
    rows = conn.execute(
        "SELECT * FROM opportunities_base WHERE gap_clicks > 0 ORDER BY gap_clicks DESC, query_key"
    ).fetchall()
    columns = [description[0] for description in conn.description]
    index = {name: position for position, name in enumerate(columns)}

    candidates = []
    for row in rows:
        exposures = row[index["exposures"]]
        clicks = row[index["clicks"]]
        expected_ctr = row[index["expected_ctr"]]
        observed_rate = clicks / exposures if exposures else 0.0
        low, high = wilson_interval(clicks, exposures)
        candidates.append(
            {
                "row": row,
                "observed_rate": observed_rate,
                "expected_ctr": expected_ctr,
                "gap_clicks": row[index["gap_clicks"]],
                "p_value": compare_rate(clicks, exposures, expected_ctr),
                "wilson_low": low,
                "wilson_high": high,
            }
        )

    q_values = benjamini_hochberg([candidate["p_value"] for candidate in candidates])
    results = []
    for rank, (candidate, q_value) in enumerate(zip(candidates, q_values), start=1):
        row = candidate["row"]
        test_exposures = row[index["test_exposures"]]
        test_item_ctr = row[index["test_item_ctr"]]
        test_expected_ctr = row[index["test_expected_ctr"]]
        reference = test_expected_ctr if test_expected_ctr else test_baseline
        if test_exposures is None or test_exposures < 100:
            validation = "验证样本不足"
        elif test_item_ctr < reference:
            validation = "后段方向一致"
        else:
            validation = "后段方向未复现"
        results.append(
            (
                rank,
                row[index["query_key"]],
                row[index["query"]],
                row[index["requests"]],
                row[index["users"]],
                row[index["exposures"]],
                row[index["clicks"]],
                row[index["purchases"]],
                candidate["observed_rate"],
                candidate["expected_ctr"],
                (candidate["expected_ctr"] - candidate["observed_rate"]) * 100,
                candidate["gap_clicks"],
                row[index["avg_list_length"]],
                row[index["request_click_rate"]],
                row[index["request_purchase_rate"]],
                candidate["wilson_low"],
                candidate["wilson_high"],
                candidate["p_value"],
                q_value,
                test_exposures,
                row[index["test_requests"]],
                test_item_ctr,
                row[index["test_request_click_rate"]],
                test_expected_ctr,
                validation,
            )
        )
    return results


def main() -> None:
    missing = [str(path) for path in SOURCES.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError("Download official data first:\n" + "\n".join(missing))

    DB.parent.mkdir(parents=True, exist_ok=True)
    BUILD_DB.parent.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(exist_ok=True)
    PUBLIC.mkdir(exist_ok=True)
    if BUILD_DB.exists():
        BUILD_DB.unlink()

    conn = duckdb.connect(str(BUILD_DB))
    conn.execute("SET memory_limit='3GB'")
    conn.execute("SET threads=4")
    conn.execute("SET preserve_insertion_order=false")
    conn.execute(f"SET temp_directory='{_sql_path(ROOT / '.work' / 'duckdb')}'")

    try:
        for view, path in SOURCES.items():
            conn.execute(
                f"CREATE VIEW {view} AS SELECT * FROM read_json_auto('{_sql_path(path)}')"
            )
        conn.execute(
            "CREATE VIEW raw_intent_rules AS "
            "SELECT flag, pattern "
            f"FROM read_csv_auto('{_sql_path(INTENT_RULES)}', header=true)"
        )

        for path in sorted(SQL_DIR.glob("*.sql")):
            print(f"Running {path.name}", flush=True)
            conn.execute(path.read_text(encoding="utf-8"))

        quality_row = conn.execute(
            (SQL_DIR / "04_quality.sql").read_text(encoding="utf-8")
        ).fetchone()
        quality_columns = [
            description[0]
            for description in conn.description
        ]
        checks = dict(zip(quality_columns, quality_row))
        source_row = conn.execute("SELECT * FROM source_quality").fetchone()
        source_columns = [description[0] for description in conn.description]
        checks.update(dict(zip(source_columns, source_row)))

        for left, right in NUMERIC_CHECKS.items():
            if checks[left] != checks[right]:
                raise ValueError(f"Quality check failed: {left} != {right}")
        for name in ZERO_CHECKS:
            if checks.get(name, 0):
                raise ValueError(f"Quality check failed: {name} = {checks[name]}")
        dictionary_rows = conn.execute("SELECT count(*) FROM query_dictionary").fetchone()[0]
        intent_rows = conn.execute("SELECT count(*) FROM query_intent").fetchone()[0]
        if dictionary_rows != intent_rows:
            raise ValueError("Quality check failed: intent tagging is not one row per query")
        checks["dictionary_rows"] = dictionary_rows
        checks["intent_rules"] = conn.execute("SELECT count(*) FROM raw_intent_rules").fetchone()[0]

        (OUT / "quality.json").write_text(
            json.dumps(checks, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (PUBLIC / "quality.json").write_text(
            json.dumps(checks, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        for name, sql, publish in EXPORTS:
            count = _write_query(conn, sql, OUT / f"{name}.csv")
            if publish:
                shutil.copyfile(OUT / f"{name}.csv", PUBLIC / f"{name}.csv")
            print(f"Exported {name}: {count} rows", flush=True)

        opportunities = _build_opportunities(conn)
        _write_rows(OUT / "opportunities.csv", OPPORTUNITY_COLUMNS, opportunities)
        _write_rows(
            PUBLIC / "opportunities_top30.csv",
            OPPORTUNITY_COLUMNS,
            opportunities[:30],
        )
        print(f"Exported opportunities: {len(opportunities)} candidates", flush=True)

        print(json.dumps(checks, ensure_ascii=False, indent=2), flush=True)
    finally:
        conn.close()

    os.replace(BUILD_DB, DB)
    print(f"Built {DB} and {len(EXPORTS) + 1} aggregate exports", flush=True)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
