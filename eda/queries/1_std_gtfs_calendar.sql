-- ===============================================================================================
-- Raw GTFS data standardization: RAW -> STANDARDIZED
-- calendar_dates.txt ← weekday service patterns
-- Business question answered: "?"
-- Standardizes, parses, and loads raw GTFS CSV files into a single table for a selected date.
-- ===============================================================================================

SET VARIABLE gtfs_date = '2026-06-21';
SET VARIABLE raw_dir = 'data/raw/source=gtfs/date=' || getvariable('gtfs_date') || '/calendar.txt';

CREATE OR REPLACE TABLE standardized.gtfs_calendar AS
SELECT
    service_id
  , monday
  , tuesday
  , wednesday
  , thursday
  , friday
  , saturday
  , sunday
  , start_date
  , end_date
  , source
  , date AS snapshot_date
FROM read_csv(getvariable('raw_dir'));


SELECT
    service_id
  , monday
  , tuesday
  , wednesday
  , thursday
  , friday
  , saturday
  , sunday
  , start_date
  , end_date
  , source
  , snapshot_date
FROM standardized.gtfs_calendar

