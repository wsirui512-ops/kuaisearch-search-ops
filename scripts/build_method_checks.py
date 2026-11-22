"""Export aggregate checks for baseline choice and category comparison (no titles/users)."""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".localdeps"))
import duckdb

def main():
    conn = duckdb.connect(str(ROOT / "data/processed/kuaisearch.duckdb"), read_only=True)
    queries = {
        "category_comparison": """
          SELECT c.category,c.exposures,c.item_ctr,
                 (o.item_ctr-c.item_ctr)*100 AS raw_gap_pp,
                 e.expected_clicks/e.exposures AS expected_ctr,
                 (e.expected_clicks/e.exposures-c.item_ctr)*100 AS adjusted_gap_pp
          FROM category_metrics c JOIN category_expected e USING(category)
          CROSS JOIN overview o
          WHERE c.split='train' AND o.split='train' AND c.exposures>=100000
          ORDER BY c.exposures DESC,c.category_id""",
        "validation_baselines": """
          WITH frozen AS (
            SELECT q.query_key,sum(q.exposures*b.item_ctr)/sum(q.exposures) AS ctr
            FROM query_strata_test q JOIN stratum_baseline b USING(length_stratum)
            GROUP BY q.query_key
          ), candidates AS (
            SELECT o.*,f.ctr FROM opportunities_base o LEFT JOIN frozen f USING(query_key)
            WHERE o.gap_clicks>0
          )
          SELECT 'test_period' AS reference,count(*) AS candidates,
            count(*) FILTER(WHERE test_exposures>=100) AS eligible,
            count(*) FILTER(WHERE test_exposures>=100 AND test_item_ctr<test_expected_ctr) AS consistent
          FROM candidates
          UNION ALL
          SELECT 'frozen_train',count(*),count(*) FILTER(WHERE test_exposures>=100),
            count(*) FILTER(WHERE test_exposures>=100 AND test_item_ctr<ctr) FROM candidates
          ORDER BY reference"""
        ,"opportunity_triage_top30": """
          WITH frozen AS (
            SELECT q.query_key,sum(q.exposures*b.item_ctr)/sum(q.exposures) AS ctr
            FROM query_strata_test q JOIN stratum_baseline b USING(length_stratum)
            GROUP BY q.query_key
          ), ranked AS (
            SELECT row_number() OVER(ORDER BY o.gap_clicks DESC,o.query_key) AS rank,
                   o.*, f.ctr AS frozen_ctr
            FROM opportunities_base o LEFT JOIN frozen f USING(query_key)
            WHERE o.gap_clicks>0
          )
          SELECT rank,query,requests,users,exposures,gap_clicks,
                 test_exposures,test_item_ctr,test_expected_ctr,frozen_ctr,
                 CASE WHEN test_exposures IS NULL OR test_exposures<100 THEN 'insufficient'
                   WHEN test_item_ctr<test_expected_ctr AND test_item_ctr<frozen_ctr THEN 'both'
                   WHEN test_item_ctr>=test_expected_ctr AND test_item_ctr>=frozen_ctr THEN 'neither'
                   ELSE 'disagree' END AS review_tier
          FROM ranked WHERE rank<=30 ORDER BY rank"""
    }
    try:
        for name, sql in queries.items():
            result = conn.execute(sql)
            columns = [c[0] for c in result.description]
            records = result.fetchall()
            target = ROOT / f"outputs_public/{name}.csv"
            with target.open("w", encoding="utf-8-sig", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(columns)
                writer.writerows([format(x,".10g") if isinstance(x,float) else x for x in row] for row in records)
            print(f"{name}: {len(records)} aggregate rows")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
