-- ===============================================================================================
-- Raw GTFS data standardization: RAW -> STANDARDIZED
-- standardized.gtfs_stops
-- Business question answered: "Where exactly is each stop?"
-- Standardizes, parses, and loads raw GTFS CSV files into a single table for a selected date.
-- ===============================================================================================

SET VARIABLE gtfs_date = '2026-06-21';
SET VARIABLE raw_dir = 'data/raw/source=gtfs/date=' || getvariable('gtfs_date') || '/stops.txt';


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
  , source
  , date AS snapshot_date
FROM read_csv(getvariable('raw_dir'));
