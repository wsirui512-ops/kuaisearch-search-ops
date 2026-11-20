-- Staging layer: one source row = one search request, not one product exposure.
-- Raw JSONL files are exposed by the pipeline as views raw_search / raw_items / raw_users / raw_relevance.

CREATE TABLE source_quality AS
SELECT
  count(*) AS source_requests,
  count(DISTINCT session_id) AS source_distinct_sessions,
  count(DISTINCT user_id) AS source_users,
  count(*) FILTER (WHERE user_id IS NULL OR session_id IS NULL OR time_index IS NULL) AS missing_keys,
  count(*) FILTER (WHERE query IS NULL OR trim(query) = '') AS empty_queries,
  count(*) FILTER (WHERE impressed_item_ids IS NULL) AS null_impression_lists,
  coalesce(sum(len(impressed_item_ids) - len(list_distinct(impressed_item_ids))), 0) AS repeated_impression_ids,
  coalesce(sum(len(list_distinct(clicked_item_ids)) - len(list_intersect(clicked_item_ids, impressed_item_ids))), 0) AS clicked_outside_impressions,
  coalesce(sum(len(list_distinct(purchased_item_ids)) - len(list_intersect(purchased_item_ids, impressed_item_ids))), 0) AS purchased_outside_impressions,
  coalesce(sum(len(list_distinct(purchased_item_ids)) - len(list_intersect(purchased_item_ids, clicked_item_ids))), 0) AS purchased_outside_clicks,
  (SELECT count(*) FROM (SELECT unnest(impressed_item_ids) AS item_id FROM raw_search) WHERE item_id IS NULL) AS null_impression_ids,
  (SELECT count(*) FROM (SELECT unnest(clicked_item_ids) AS item_id FROM raw_search) WHERE item_id IS NULL) AS null_click_ids,
  (SELECT count(*) FROM (SELECT unnest(purchased_item_ids) AS item_id FROM raw_search) WHERE item_id IS NULL) AS null_purchase_ids
FROM raw_search;

-- Lists are de-duplicated after the audit above proves whether duplicates exist.
CREATE TABLE search_clean AS
SELECT
  user_id,
  session_id,
  time_index,
  coalesce(nullif(trim(query), ''), '[空搜索词]') AS query,
  split,
  list_distinct(coalesce(impressed_item_ids, []::BIGINT[])) AS impressed_item_ids,
  list_distinct(coalesce(clicked_item_ids, []::BIGINT[])) AS clicked_item_ids,
  list_distinct(coalesce(purchased_item_ids, []::BIGINT[])) AS purchased_item_ids
FROM raw_search;
