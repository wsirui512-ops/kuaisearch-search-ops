-- Load the Parquet exports produced by: python scripts/export_parquet.py
-- Paths are relative to the directory you run the client from.

INSERT INTO kuaisearch.sessions
SELECT * FROM file('exports/parquet/sessions.parquet', 'Parquet');

INSERT INTO kuaisearch.fact
SELECT * FROM file('exports/parquet/fact.parquet', 'Parquet');
