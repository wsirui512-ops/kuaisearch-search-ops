-- Intermediate layer: request grain, exposure grain (with list position), dimensions and intent tags.

CREATE TABLE sessions AS
SELECT
  user_id,
  session_id,
  time_index,
  query,
  split,
  impressed_item_ids,
  clicked_item_ids,
  purchased_item_ids,
  len(impressed_item_ids) AS impressions,
  len(list_intersect(impressed_item_ids, clicked_item_ids)) AS clicks,
  len(list_intersect(impressed_item_ids, purchased_item_ids)) AS purchases,
  CASE
    WHEN len(impressed_item_ids) <= 10 THEN '01-10'
    WHEN len(impressed_item_ids) <= 20 THEN '11-20'
    WHEN len(impressed_item_ids) <= 30 THEN '21-30'
    WHEN len(impressed_item_ids) <= 40 THEN '31-40'
    WHEN len(impressed_item_ids) <= 60 THEN '41-60'
    WHEN len(impressed_item_ids) <= 100 THEN '61-100'
    ELSE '100+'
  END AS length_stratum
FROM search_clean;

-- One row per distinct product inside a request. `position` is the order in the
-- recalled list, kept as evidence of display order rather than a certified rank.
CREATE TABLE exposures AS
SELECT
  s.session_id,
  e.item_id,
  e.pos AS position,
  list_contains(s.clicked_item_ids, e.item_id)::INTEGER AS is_clicked,
  list_contains(s.purchased_item_ids, e.item_id)::INTEGER AS is_purchased
FROM sessions AS s,
  unnest(s.impressed_item_ids) WITH ORDINALITY AS e(item_id, pos);

CREATE TABLE items AS
SELECT source.*
FROM raw_items AS source
SEMI JOIN (SELECT DISTINCT item_id FROM exposures) AS needed USING (item_id);

CREATE TABLE users AS
SELECT * FROM raw_users;

-- Stable key: md5 of the query text, so the same query gets the same id on any engine.
CREATE TABLE query_dictionary AS
SELECT
  md5(query) AS query_key,
  query
FROM (SELECT DISTINCT query FROM sessions);

-- Rule-based demand tags. Rules are data-driven (config/intent_rules.csv) and flag-based,
-- so one query can carry several signals; the label below only picks a primary story.
CREATE TABLE query_flags AS
SELECT
  d.query,
  coalesce(max((r.flag = 'brand')::INTEGER), 0) AS has_brand,
  coalesce(max((r.flag = 'attr')::INTEGER), 0) AS has_attr,
  coalesce(max((r.flag = 'scene')::INTEGER), 0) AS has_scene,
  coalesce(max((r.flag = 'category')::INTEGER), 0) AS has_category
FROM query_dictionary AS d
LEFT JOIN raw_intent_rules AS r ON regexp_matches(d.query, r.pattern)
GROUP BY d.query;

CREATE TABLE query_intent AS
SELECT
  query,
  CASE
    WHEN has_brand = 1 THEN '品牌/店铺词'
    WHEN has_category = 1 AND (has_attr = 1 OR has_scene = 1) THEN '品类+修饰词'
    WHEN has_category = 1 THEN '纯品类词'
    WHEN has_attr = 1 OR has_scene = 1 THEN '属性/场景词（无品类）'
    ELSE '无品类信号'
  END AS intent
FROM query_flags;

CREATE VIEW fact AS
SELECT
  e.session_id,
  e.item_id,
  e.position,
  e.is_clicked,
  e.is_purchased,
  s.user_id,
  s.split,
  s.time_index,
  s.length_stratum,
  i.category_level1_id AS category_id,
  coalesce(i.category_level1_name, '[商品未匹配]') AS category,
  coalesce(i.category_level2_name, '[未提供]') AS subcategory
FROM exposures AS e
JOIN sessions AS s USING (session_id)
LEFT JOIN items AS i USING (item_id);
