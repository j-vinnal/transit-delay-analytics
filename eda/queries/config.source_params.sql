CREATE SCHEMA IF NOT EXISTS config;

CREATE OR REPLACE TABLE config.source_params (
    source TEXT PRIMARY KEY            -- 'gps' | 'gtfs'
  , extract_date DATE NOT NULL         -- which extract date to read
  , active BOOLEAN DEFAULT true
  , comment TEXT                       -- e.g. why this date was chosen
  , updated_ts TIMESTAMPTZ DEFAULT current_timestamp
);

INSERT INTO config.source_params (source, extract_date)
VALUES ('gps', '2026-08-17')
, ('gtfs', '2026-08-17')
ON CONFLICT (source) DO UPDATE SET
    extract_date = excluded.extract_date;
--  , updated_ts = current_timestamp;
