-- Marts: business-facing metrics. Two denominators stay separate on purpose:
-- item CTR = clicks / product exposures, request click rate = requests with >=1 click / requests.

CREATE TABLE overview AS
SELECT
  split,
  count(*) AS requests,
  count(DISTINCT user_id) AS users,
  sum(impressions) AS exposures,
  sum(clicks) AS clicks,
  sum(purchases) AS purchases,
  count(*) FILTER (WHERE clicks > 0) AS clicked_requests,
  count(*) FILTER (WHERE purchases > 0) AS purchased_requests,
  count(*) FILTER (WHERE impressions < 5) AS low_exposure_requests,
  sum(clicks)::DOUBLE / nullif(sum(impressions), 0) AS item_ctr,
  count(*) FILTER (WHERE clicks > 0)::DOUBLE / count(*) AS request_click_rate,
  count(*) FILTER (WHERE purchases > 0)::DOUBLE / count(*) AS request_purchase_rate,
  avg(impressions) AS avg_list_length,
  min(time_index) AS min_time_index,
  max(time_index) AS max_time_index
FROM sessions
GROUP BY split;

-- Result-list length drives item CTR mechanically: more shown items means fewer clicks per item.
CREATE TABLE length_strata AS
SELECT
  split,
  length_stratum,
  count(*) AS requests,
  count(DISTINCT user_id) AS users,
  sum(impressions) AS exposures,
  sum(clicks) AS clicks,
  sum(purchases) AS purchases,
  avg(impressions) AS avg_list_length,
  sum(clicks)::DOUBLE / nullif(sum(impressions), 0) AS item_ctr,
  count(*) FILTER (WHERE clicks > 0)::DOUBLE / count(*) AS request_click_rate
FROM sessions
GROUP BY split, length_stratum;

-- Length baseline is estimated on train only and reused as the expected rate.
CREATE TABLE stratum_baseline AS
SELECT
  length_stratum,
  sum(impressions) AS exposures,
  sum(clicks) AS clicks,
  sum(clicks)::DOUBLE / nullif(sum(impressions), 0) AS item_ctr
FROM sessions
WHERE split = 'train'
GROUP BY length_stratum;

CREATE TABLE category_metrics AS
SELECT
  f.split,
  f.category_id,
  f.category,
  count(*) AS exposures,
  sum(f.is_clicked) AS clicks,
  sum(f.is_purchased) AS purchases,
  count(DISTINCT f.user_id) AS users,
  count(DISTINCT f.session_id) AS requests,
  avg(f.is_clicked) AS item_ctr,
  avg(f.is_purchased) AS item_purchase_rate
FROM fact AS f
GROUP BY f.split, f.category_id, f.category;

CREATE TABLE category_strata AS
SELECT
  f.split,
  f.category,
  f.length_stratum,
  count(*) AS exposures,
  sum(f.is_clicked) AS clicks
FROM fact AS f
GROUP BY f.split, f.category, f.length_stratum;

-- Category CTR adjusted for the result-list length mix, train only.
CREATE TABLE category_expected AS
SELECT
  c.category,
  sum(c.exposures * b.item_ctr) AS expected_clicks,
  sum(c.exposures) AS exposures
FROM category_strata AS c
JOIN stratum_baseline AS b USING (length_stratum)
WHERE c.split = 'train'
GROUP BY c.category;

CREATE TABLE query_metrics AS
SELECT
  d.query_key,
  d.query,
  qi.intent,
  s.split,
  count(*) AS requests,
  count(DISTINCT s.user_id) AS users,
  sum(s.impressions) AS exposures,
  sum(s.clicks) AS clicks,
  sum(s.purchases) AS purchases,
  avg(s.impressions) AS avg_list_length,
  sum(s.clicks)::DOUBLE / nullif(sum(s.impressions), 0) AS item_ctr,
  count(*) FILTER (WHERE s.clicks > 0)::DOUBLE / count(*) AS request_click_rate,
  count(*) FILTER (WHERE s.purchases > 0)::DOUBLE / count(*) AS request_purchase_rate,
  min(s.time_index) AS first_time_index,
  max(s.time_index) AS last_time_index
FROM sessions AS s
JOIN query_dictionary AS d USING (query)
JOIN query_intent AS qi USING (query)
GROUP BY d.query_key, d.query, qi.intent, s.split;

CREATE TABLE query_strata AS
SELECT
  d.query_key,
  s.length_stratum,
  sum(s.impressions) AS exposures,
  sum(s.clicks) AS clicks,
  count(*) AS requests
FROM sessions AS s
JOIN query_dictionary AS d USING (query)
WHERE s.split = 'train'
GROUP BY d.query_key, s.length_stratum;

CREATE TABLE query_expected AS
SELECT
  qs.query_key,
  sum(qs.exposures * b.item_ctr) AS expected_clicks,
  sum(qs.exposures) AS exposures
FROM query_strata AS qs
JOIN stratum_baseline AS b USING (length_stratum)
GROUP BY qs.query_key;

CREATE VIEW opportunities_base AS
SELECT
  m.query_key,
  m.query,
  m.requests,
  m.users,
  m.exposures,
  m.clicks,
  m.purchases,
  m.avg_list_length,
  m.item_ctr,
  m.request_click_rate,
  m.request_purchase_rate,
  e.expected_clicks,
  e.expected_clicks / e.exposures AS expected_ctr,
  (e.expected_clicks - m.clicks) AS gap_clicks,
  t.exposures AS test_exposures,
  t.requests AS test_requests,
  t.item_ctr AS test_item_ctr,
  t.request_click_rate AS test_request_click_rate
FROM query_metrics AS m
JOIN query_expected AS e USING (query_key)
LEFT JOIN query_metrics AS t
  ON t.query_key = m.query_key AND t.split = 'test'
WHERE m.split = 'train'
  AND m.requests >= 100
  AND m.users >= 30
  AND m.exposures >= 1000;

CREATE TABLE intent_metrics AS
SELECT
  s.split,
  qi.intent,
  count(*) AS requests,
  count(DISTINCT s.user_id) AS users,
  sum(s.impressions) AS exposures,
  sum(s.clicks) AS clicks,
  sum(s.purchases) AS purchases,
  avg(s.impressions) AS avg_list_length,
  sum(s.clicks)::DOUBLE / nullif(sum(s.impressions), 0) AS item_ctr,
  count(*) FILTER (WHERE s.clicks > 0)::DOUBLE / count(*) AS request_click_rate,
  count(*) FILTER (WHERE s.purchases > 0)::DOUBLE / count(*) AS request_purchase_rate
FROM sessions AS s
JOIN query_intent AS qi USING (query)
GROUP BY s.split, qi.intent;

-- Same length adjustment applied to demand tags, so tag differences are not just list length.
CREATE TABLE intent_strata AS
SELECT
  qi.intent,
  s.length_stratum,
  sum(s.impressions) AS exposures,
  sum(s.clicks) AS clicks
FROM sessions AS s
JOIN query_intent AS qi USING (query)
WHERE s.split = 'train'
GROUP BY qi.intent, s.length_stratum;

CREATE TABLE intent_expected AS
SELECT
  i.intent,
  sum(i.exposures * b.item_ctr) AS expected_clicks,
  sum(i.exposures) AS exposures
FROM intent_strata AS i
JOIN stratum_baseline AS b USING (length_stratum)
GROUP BY i.intent;

-- time_index is a relative index. It cannot be decoded into dates, hours or weekdays.
CREATE TABLE relative_time_metrics AS
WITH limits AS (
  SELECT min(time_index) AS lo, max(time_index) AS hi FROM sessions
),
buckets AS (
  SELECT
    s.*,
    least(19, floor((s.time_index - limits.lo) * 20.0 / nullif(limits.hi - limits.lo + 1, 0)))::INTEGER AS time_bucket
  FROM sessions AS s CROSS JOIN limits
)
SELECT
  split,
  time_bucket,
  min(time_index) AS min_time_index,
  max(time_index) AS max_time_index,
  count(*) AS requests,
  sum(impressions) AS exposures,
  sum(clicks) AS clicks,
  sum(impressions)::DOUBLE / nullif(count(*), 0) AS avg_list_length,
  sum(clicks)::DOUBLE / nullif(sum(impressions), 0) AS item_ctr,
  count(*) FILTER (WHERE clicks > 0)::DOUBLE / count(*) AS request_click_rate
FROM buckets
GROUP BY split, time_bucket;

CREATE TABLE age_metrics AS
SELECT
  s.split,
  coalesce(u.age_bucket, '[未匹配]') AS age_bucket,
  count(*) AS requests,
  count(DISTINCT s.user_id) AS users,
  sum(s.impressions) AS exposures,
  sum(s.clicks) AS clicks,
  sum(s.purchases) AS purchases,
  sum(s.clicks)::DOUBLE / nullif(sum(s.impressions), 0) AS item_ctr,
  count(*) FILTER (WHERE s.clicks > 0)::DOUBLE / count(*) AS request_click_rate
FROM sessions AS s
LEFT JOIN users AS u ON s.user_id = u.user_id
GROUP BY s.split, u.age_bucket;

CREATE TABLE relevance_coverage AS
SELECT split, score, count(*) AS pairs
FROM raw_relevance
GROUP BY split, score;

CREATE TABLE relevance_summary AS
SELECT
  (SELECT count(*) FROM raw_relevance) AS pairs,
  (SELECT count(DISTINCT query) FROM raw_relevance) AS tagged_queries,
  (SELECT count(*) FROM (SELECT DISTINCT query FROM raw_relevance) AS r
     JOIN query_dictionary AS d USING (query)) AS matched_queries,
  (SELECT count(*) FROM (SELECT DISTINCT query FROM raw_relevance) AS r
     JOIN query_metrics AS q ON q.query = r.query AND q.split = 'train') AS matched_train_queries;
