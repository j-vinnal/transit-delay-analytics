-- ===============================================================================================
-- Raw GTFS data standardization: RAW -> STANDARDIZED
-- calendar_dates.txt ← weekday service patterns
-- Liinide käigusoleku perioodi andmed (sisuliselt sõiduplaani kehtivus)
-- Business question answered: "?"
-- Standardizes, parses, and loads raw GTFS CSV files into a single table for a selected date.
-- ===============================================================================================

SET VARIABLE extract_date =
    coalesce((
        SELECT extract_date FROM config.source_params
        WHERE source = 'gtfs' AND active
    ), current_date)::VARCHAR;

SET VARIABLE raw_dir = 'data/raw/extract_source=gtfs/extract_date=' || getvariable('extract_date') || '/extract_ts=*/calendar.txt';

CREATE OR REPLACE TABLE standardized.gtfs_calendar AS
SELECT
    service_id -- Unique ID, trips.service_id
  , monday
  , tuesday
  , wednesday
  , thursday
  , friday
  , saturday
  , sunday
  , start_date -- Start service day for the service interval.
  , end_date -- End service day for the service interval
  , try_strptime(extract_ts, '%Y%m%d_%H%M%S') AT TIME ZONE 'UTC' AS extract_ts
  , current_timestamp AS updated_ts
FROM read_csv(
    getvariable('raw_dir')
  , dateformat = '%Y%m%d'
);
