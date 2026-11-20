"""Sensitivity check: does the opportunity gap survive a length x position baseline?

The published benchmark only conditions on how many products were shown. A critic can ask
"isn't the gap just because the good products sit lower?" This script rebuilds the expected
clicks from a two-way baseline (result-list length x list position) for the top candidates
and reports how much the gap moves.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".localdeps"))
import duckdb

DB = ROOT / "data" / "processed" / "kuaisearch.duckdb"
PUBLIC = ROOT / "outputs_public"

CELL_SQL = """
CREATE TEMP TABLE cells AS
WITH positioned AS (
  SELECT
    f.session_id, f.is_clicked, f.is_purchased,
    s.length_stratum,
    CASE
      WHEN f.position <= 5 THEN '1-5'
      WHEN f.position <= 10 THEN '6-10'
      WHEN f.position <= 20 THEN '11-20'
      WHEN f.position <= 40 THEN '21-40'
      ELSE '41+'
    END AS pos_bucket
  FROM fact AS f
  JOIN sessions AS s USING (session_id)
  WHERE f.split = 'train'
)
SELECT length_stratum, pos_bucket, count(*) AS exposures,
       sum(is_clicked) AS clicks, sum(is_clicked) * 1.0 / count(*) AS ctr
FROM positioned
GROUP BY length_stratum, pos_bucket;
"""

QUERY_SQL = """
CREATE TEMP TABLE query_cells AS
WITH positioned AS (
  SELECT
    s.query, f.is_clicked,
    s.length_stratum,
    CASE
      WHEN f.position <= 5 THEN '1-5'
      WHEN f.position <= 10 THEN '6-10'
      WHEN f.position <= 20 THEN '11-20'
      WHEN f.position <= 40 THEN '21-40'
      ELSE '41+'
    END AS pos_bucket
  FROM fact AS f
  JOIN sessions AS s USING (session_id)
  WHERE f.split = 'train'
)
SELECT query, length_stratum, pos_bucket, count(*) AS exposures, sum(is_clicked) AS clicks
FROM positioned
GROUP BY query, length_stratum, pos_bucket;
"""


def main() -> None:
    with (PUBLIC / "opportunities_top30.csv").open(encoding="utf-8-sig") as stream:
        candidates = list(csv.DictReader(stream))
    names = [row["query"] for row in candidates]

    conn = duckdb.connect(str(DB), read_only=True)
    try:
        conn.execute("SET memory_limit='3GB'")
        conn.execute("SET threads=4")
        conn.execute(CELL_SQL)
        conn.execute(QUERY_SQL)
        placeholders = ", ".join("?" for _ in names)
        rows = conn.execute(
            f"""
            SELECT
              qc.query,
              sum(qc.exposures) AS exposures,
              sum(qc.clicks) AS clicks,
              sum(qc.exposures * c.ctr) AS expected_clicks,
              sum(qc.exposures * c.ctr) / sum(qc.exposures) AS expected_ctr
            FROM query_cells AS qc
            JOIN cells AS c USING (length_stratum, pos_bucket)
            WHERE qc.query IN ({placeholders})
            GROUP BY qc.query
            """,
            names,
        ).fetchall()
    finally:
        conn.close()

    by_query = {row[0]: row for row in rows}
    results = []
    for candidate in candidates:
        query = candidate["query"]
        exposures, clicks, expected = by_query[query][1], by_query[query][2], by_query[query][3]
        expected_pos_ctr = by_query[query][4]
        observed = clicks / exposures
        gap_len = float(candidate["gap_pp"])
        gap_pos = (expected_pos_ctr - observed) * 100
        results.append(
            {
                "rank": candidate["rank"],
                "query": query,
                "requests": candidate["requests"],
                "exposures": exposures,
                "clicks": clicks,
                "item_ctr_pct": round(observed * 100, 3),
                "expected_ctr_length_pct": round(float(candidate["expected_ctr"]) * 100, 3),
                "expected_ctr_length_position_pct": round(expected_pos_ctr * 100, 3),
                "gap_pp_length": round(gap_len, 3),
                "gap_pp_length_position": round(gap_pos, 3),
                "delta_pp": round(gap_pos - gap_len, 3),
            }
        )

    out = PUBLIC / "sensitivity_position.csv"
    with out.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    deltas = [abs(row["delta_pp"]) for row in results]
    print(f"wrote {out.name} ({len(results)} rows)")
    print(f"max |delta| = {max(deltas):.3f} pp, mean |delta| = {sum(deltas) / len(deltas):.3f} pp")
    print(f"candidates whose gap shrinks below 0.5pp: {sum(1 for r in results if r['gap_pp_length_position'] < 0.5)}")
    for row in results[:5]:
        print(
            f"  #{row['rank']:<2} {row['query']:<8} length={row['gap_pp_length']:+.2f}pp "
            f"len+pos={row['gap_pp_length_position']:+.2f}pp delta={row['delta_pp']:+.2f}pp"
        )


if __name__ == "__main__":
    main()
