"""Export the fact and request tables to Parquet for cross-engine verification.

Parquet is the interchange format for cross-engine checks (Spark read, Python read)
and a cheaper way to re-query the data without rebuilding the DuckDB file.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".localdeps"))
import duckdb

DB = ROOT / "data" / "processed" / "kuaisearch.duckdb"
OUT = ROOT / "exports" / "parquet"

TABLES = {
    "fact": "SELECT * FROM fact",
    "sessions": """
        SELECT session_id, user_id, split, time_index, length_stratum,
               impressions, clicks, purchases
        FROM sessions
    """,
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(DB), read_only=True)
    try:
        conn.execute("SET threads=4")
        for name, sql in TABLES.items():
            target = (OUT / f"{name}.parquet").as_posix()
            conn.execute(
                f"COPY ({sql}) TO '{target}' (FORMAT PARQUET, COMPRESSION ZSTD)"
            )
            rows = conn.execute(f"SELECT count(*) FROM read_parquet('{target}')").fetchone()[0]
            size = (OUT / f"{name}.parquet").stat().st_size / 1e6
            print(f"{name}.parquet: {rows:,} rows, {size:.1f} MB", flush=True)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
