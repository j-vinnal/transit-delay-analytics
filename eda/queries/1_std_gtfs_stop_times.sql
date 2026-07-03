-- ===============================================================================================
-- Raw GTFS data standardization: RAW -> STANDARDIZED
-- standardized.gtfs_stop_times
-- Business question answered: "When should each trip arrive at each stop?"
-- Standardizes, parses, and loads raw GTFS CSV files into a single table for a selected date.
-- ===============================================================================================

SET VARIABLE gtfs_date = '2026-06-21';
SET VARIABLE raw_dir = 'data/raw/source=gtfs/date=' || getvariable('gtfs_date') || '/stop_times.txt';


CREATE OR REPLACE TABLE standardized.gtfs_stops_times AS
SELECT
    trip_id
  , arrival_time
  , departure_time
  , stop_id
  , stop_sequence
  , pickup_type
  , drop_off_type
  , source
  , date AS snapshot_date
FROM read_csv(getvariable('raw_dir'));


-- Zoo stop (stop_id=822), coordinates: ~59.42621°N, 24.65889°E
SELECT
    trip_id
  , arrival_time
  , departure_time
  , stop_id
  , stop_sequence
  , pickup_type
  , drop_off_type
  , source
  , snapshot_date
FROM standardized.gtfs_stops_times
WHERE stop_id = 822;



