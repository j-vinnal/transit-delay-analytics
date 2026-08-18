-- ===============================================================================================
-- Raw GTFS data standardization: RAW -> STANDARDIZED
-- standardized.gtfs_stop_times
-- Business question answered: "When should each trip arrive at each stop?"
-- Standardizes, parses, and loads raw GTFS CSV files into a single table for a selected date.
-- ===============================================================================================

SET VARIABLE extract_date =
    coalesce((
        SELECT extract_date FROM config.source_params
        WHERE source = 'gtfs' AND active
    ), current_date)::VARCHAR;

SET VARIABLE raw_dir = 'data/raw/extract_source=gtfs/extract_date=' || getvariable('extract_date') || '/extract_ts=*/stop_times.txt';

CREATE OR REPLACE TABLE standardized.gtfs_stops_times AS
SELECT
    trip_id -- FK trips.trip_id
  , arrival_time -- Arrival time at the stop
  , departure_time -- Departure time from the stop
  , stop_id -- FK stops.stop_id
  , stop_sequence -- Order of stops, values increase along the trip 
  , pickup_type
  , drop_off_type
  , try_strptime(extract_ts, '%Y%m%d_%H%M%S') AT TIME ZONE 'UTC' AS extract_ts
  , current_timestamp AS updated_ts
FROM read_csv(getvariable('raw_dir'));
