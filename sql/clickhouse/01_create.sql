-- ClickHouse DDL for the cross-engine check (server or `clickhouse-local --path`).
-- Load first:  clickhouse-client --multiquery < sql/clickhouse/02_load.sql

CREATE DATABASE IF NOT EXISTS kuaisearch;

CREATE TABLE IF NOT EXISTS kuaisearch.sessions
(
    session_id      UInt64,
    user_id         UInt64,
    split           LowCardinality(String),
    time_index      UInt64,
    length_stratum  LowCardinality(String),
    impressions     UInt32,
    clicks          UInt32,
    purchases       UInt32
)
ENGINE = MergeTree
ORDER BY (split, session_id);

CREATE TABLE IF NOT EXISTS kuaisearch.fact
(
    session_id   UInt64,
    item_id      UInt64,
    position     UInt32,
    is_clicked   UInt8,
    is_purchased UInt8,
    user_id      UInt64,
    split        LowCardinality(String),
    time_index   UInt64,
    length_stratum LowCardinality(String),
    category_id  Int64,
    category     LowCardinality(String),
    subcategory  LowCardinality(String)
)
ENGINE = MergeTree
ORDER BY (split, session_id, position);
