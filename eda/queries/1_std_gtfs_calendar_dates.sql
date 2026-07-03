-- ===============================================================================================
-- Raw GTFS data standardization: RAW -> STANDARDIZED
-- calendar_dates.txt ← 
-- Business question answered: "?"
-- Standardizes, parses, and loads raw GTFS CSV files into a single table for a selected date.
-- ===============================================================================================

SET VARIABLE gtfs_date = '2026-06-21';
SET VARIABLE raw_dir = 'data/raw/source=gtfs/date=' || getvariable('gtfs_date') || '/calendar_dates.txt';

CREATE OR REPLACE TABLE standardized.gtfs_calendar_dates AS
SELECT
*
FROM read_csv(getvariable('raw_dir'))
;




SELECT
*
FROM standardized.gtfs_calendar_dates;
