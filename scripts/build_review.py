"""Build the query x product review table for the top opportunities (P3 evidence chain).

For each of the top 10 search terms, sample the 10 most-exposed products and attach what a
human reviewer needs: title, brand, category, exposure/click counts, average list position,
and an automatic bigram-coverage pre-screen. The human columns stay empty on purpose.

This table contains item titles, so it is written to outputs/ (local) only. An aggregate
summary without titles is written to outputs_public/.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT / ".localdeps"))
import duckdb

DB = ROOT / "data" / "processed" / "kuaisearch.duckdb"
PUBLIC = ROOT / "outputs_public"
OUT = ROOT / "outputs"

CLEAN = re.compile(r"[\s，。！？、,.!?_-]+")


def bigrams(text: str) -> set[str]:
    text = CLEAN.sub("", text.lower())
    return {text[i : i + 2] for i in range(len(text) - 1)}


def main() -> None:
    with (PUBLIC / "opportunities_top30.csv").open(encoding="utf-8-sig") as stream:
        top = list(csv.DictReader(stream))[:10]

    conn = duckdb.connect(str(DB), read_only=True)
    rows: list[dict] = []
    summary: list[dict] = []
    try:
        for rank, opportunity in enumerate(top, start=1):
            query = opportunity["query"]
            products = conn.execute(
                """
                SELECT
                  f.item_id,
                  i.item_title,
                  coalesce(i.brand_name, '') AS brand_name,
                  coalesce(i.category_level1_name, '') AS category1,
                  coalesce(i.category_level2_name, '') AS category2,
                  count(*) AS exposures,
                  sum(f.is_clicked) AS clicks,
                  sum(f.is_purchased) AS purchases,
                  avg(f.position) AS avg_position
                FROM fact AS f
                JOIN items AS i USING (item_id)
                WHERE f.session_id IN (
                    SELECT session_id FROM sessions WHERE query = ? AND split = 'train'
                )
                GROUP BY 1, 2, 3, 4, 5
                ORDER BY exposures DESC, f.item_id
                LIMIT 10
                """,
                [query],
            ).fetchall()

            query_grams = bigrams(query)
            covered_grams = 0
            zero_coverage = 0
            reviewed_exposures = 0
            reviewed_clicks = 0
            for position, product in enumerate(products, start=1):
                item_id, title, brand, category1, category2, exposures, clicks, purchases, avg_position = product
                title_grams = bigrams(title or "")
                hit = len(query_grams & title_grams)
                coverage = hit / len(query_grams) if query_grams else 0.0
                if coverage == 0:
                    zero_coverage += 1
                covered_grams += coverage
                reviewed_exposures += exposures
                reviewed_clicks += clicks
                rows.append(
                    {
                        "rank": rank,
                        "query": query,
                        "gap_pp": opportunity["gap_pp"],
                        "gap_clicks": opportunity["gap_clicks"],
                        "item_rank": position,
                        "item_id": item_id,
                        "item_title": title,
                        "brand_name": brand,
                        "category_level1": category1,
                        "category_level2": category2,
                        "exposures": exposures,
                        "clicks": clicks,
                        "purchases": purchases,
                        "item_ctr": round(clicks / exposures, 6) if exposures else 0.0,
                        "avg_position": round(float(avg_position or 0), 2),
                        "bigram_coverage": round(coverage, 3),
                        "query_in_title": int(query in (title or "")),
                        "human_relevance": "",
                        "human_note": "",
                    }
                )

            summary.append(
                {
                    "rank": rank,
                    "query": query,
                    "gap_pp": opportunity["gap_pp"],
                    "gap_clicks": opportunity["gap_clicks"],
                    "items_reviewed": len(products),
                    "exposures_reviewed": reviewed_exposures,
                    "clicks_reviewed": reviewed_clicks,
                    "avg_bigram_coverage": round(covered_grams / len(products), 3) if products else 0.0,
                    "pct_items_zero_coverage": round(zero_coverage / len(products), 3) if products else 0.0,
                }
            )
    finally:
        conn.close()

    OUT.mkdir(exist_ok=True)
    with (OUT / "review_table.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    with (PUBLIC / "review_coverage_summary.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summary[0].keys()))
        writer.writeheader()
        writer.writerows(summary)

    print(f"review rows: {len(rows)} -> outputs/review_table.csv")
    for row in summary:
        print(
            f"{row['query']:<12} items={row['items_reviewed']:<3} "
            f"coverage={row['avg_bigram_coverage']:.2f} "
            f"zero_cov={row['pct_items_zero_coverage']:.0%} "
            f"ctr={row['clicks_reviewed']}/{row['exposures_reviewed']}"
        )


if __name__ == "__main__":
    main()
