-- Same five headline metrics as scripts/verify_engines.py, expressed in ClickHouse SQL.
-- Run after loading sql/clickhouse/02_load.sql.

-- 1) exposures
SELECT 'exposures' AS metric, sum(impressions) AS value FROM kuaisearch.sessions;

-- 2) clicks
SELECT 'clicks' AS metric, sum(clicks) AS value FROM kuaisearch.sessions;

-- 3) item CTR
SELECT 'item_ctr' AS metric, sum(clicks) / sum(impressions) AS value FROM kuaisearch.sessions;

-- 4) request click rate
SELECT 'request_click_rate' AS metric,
       countIf(clicks > 0) / count() AS value
FROM kuaisearch.sessions;

-- 5) share of exposures coming from 100+ item lists
SELECT 'long_list_exposure_share' AS metric,
       sumIf(impressions, length_stratum = '100+') / sum(impressions) AS value
FROM kuaisearch.sessions;

-- 6) category gap (train, length-adjusted) — mirrors outputs_public/category_residuals.csv
WITH baseline AS (
    SELECT length_stratum, sum(clicks) / sum(impressions) AS ctr
    FROM kuaisearch.sessions
    WHERE split = 'train'
    GROUP BY length_stratum
)
SELECT f.category,
       count() AS exposures,
       sum(f.is_clicked) AS clicks,
       sum(f.is_clicked) / count() AS item_ctr,
       sum(b.ctr) / count() AS expected_ctr_placeholder
FROM kuaisearch.fact AS f
JOIN baseline AS b USING (length_stratum)
WHERE f.split = 'train'
GROUP BY f.category
ORDER BY exposures DESC
LIMIT 10;

-- Expected values (DuckDB, 2026-11-20):
--   exposures                17,800,904
--   clicks                      680,790
--   item_ctr                    0.0382399…
--   request_click_rate          0.5307205…
--   long_list_exposure_share    0.4016075…
