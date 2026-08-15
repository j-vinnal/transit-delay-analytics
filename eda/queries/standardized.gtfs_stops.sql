-- ===============================================================================================
-- Raw GTFS data standardization: RAW -> STANDARDIZED
-- standardized.gtfs_stops
-- Business question answered: "Where exactly is each stop?"
-- Standardizes, parses, and loads raw GTFS CSV files into a single table for a selected date.
-- ===============================================================================================

SET VARIABLE gtfs_date = '2026-08-15';
SET VARIABLE raw_dir = 'data/raw/extract_source=gtfs/extract_date=' || getvariable('gtfs_date') || '/extract_ts=*/stops.txt';

CREATE OR REPLACE TABLE standardized.gtfs_stops AS
SELECT
    stop_id
  , stop_code
  , stop_name
  , stop_desc
  , stop_lat
  , stop_lon
  , stop_url
  , location_type
  , parent_station
  , thoreb_id
  , try_strptime(extract_ts, '%Y%m%d_%H%M%S') AT TIME ZONE 'UTC' AS extract_ts
  , current_timestamp AS loaded_ts
FROM --data/raw/extract_source=gtfs/extract_date={gtfs_date}/extract_ts=*/stops.txt
    read_csv(getvariable('raw_dir'));
