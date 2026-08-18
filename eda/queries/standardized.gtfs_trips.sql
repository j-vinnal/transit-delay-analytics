-- ===============================================================================================
-- Raw GTFS data standardization: RAW -> STANDARDIZED
-- trips.txt       ← trip IDs per route, calendar service IDs
-- Info individuaalsete sõitude ehk väljumiste kohta igal liinil (iga kord, kui buss liini algusest lõppu sõidab, on see üks *trip*)
-- Business question answered: "What individual journeys are scheduled?"
-- Standardizes, parses, and loads raw GTFS CSV files into a single table for a selected date.
-- ===============================================================================================

SET VARIABLE extract_date =
    coalesce((
        SELECT extract_date FROM config.source_params
        WHERE source = 'gtfs' AND active
    ), current_date)::VARCHAR;

SET VARIABLE raw_dir = 'data/raw/extract_source=gtfs/extract_date=' || getvariable('extract_date') || '/extract_ts=*/trips.txt';

CREATE OR REPLACE TABLE standardized.gtfs_trips AS
SELECT
    route_id -- FK routes.route_id
  , service_id -- FK calendar_dates.service_id
  , trip_id -- Unique ID
  , trip_headsign -- trip's destination
  , direction_id -- direction of travel for a trip
  , block_id
  , shape_id -- FK shapes.shape_id, geospatial shape describing the vehicle travel path for a trip
  , wheelchair_accessible
  , block_code
  , vehicle_type
  , thoreb_id
  , trip_short_name
  , try_strptime(extract_ts, '%Y%m%d_%H%M%S') AT TIME ZONE 'UTC' AS extract_ts
  , current_timestamp AS updated_ts
FROM read_csv(getvariable('raw_dir'));
