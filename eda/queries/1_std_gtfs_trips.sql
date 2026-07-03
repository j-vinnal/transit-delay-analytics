-- ===============================================================================================
-- Raw GTFS data standardization: RAW -> STANDARDIZED
-- trips.txt       ← trip IDs per route, calendar service IDs
-- Business question answered: "What individual journeys are scheduled?"
-- Standardizes, parses, and loads raw GTFS CSV files into a single table for a selected date.
-- ===============================================================================================

SET VARIABLE gtfs_date = '2026-06-21';
SET VARIABLE raw_dir = 'data/raw/source=gtfs/date=' || getvariable('gtfs_date') || '/trips.txt';

CREATE OR REPLACE TABLE standardized.gtfs_trips AS
SELECT
    route_id
  , service_id
  , trip_id
  , trip_headsign
  , direction_id
  , block_id
  , shape_id
  , wheelchair_accessible
  , block_code
  , vehicle_type
  , thoreb_id
  , trip_short_name
  , source
  , date AS snapshot_date
FROM read_csv(getvariable('raw_dir'));

-- Zoo stop (stop_id=822), coordinates: ~59.42621°N, 24.65889°E
SELECT
    route_id
  , service_id
  , trip_id
  , trip_headsign
  , direction_id
  , block_id
  , shape_id
  , wheelchair_accessible
  , block_code
  , vehicle_type
  , thoreb_id
  , trip_short_name
  , source
  , snapshot_date
FROM standardized.gtfs_trips
--WHERE stop_id = 822;
