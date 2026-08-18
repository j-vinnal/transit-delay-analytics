-- ===============================================================================================
-- Raw GTFS data standardization: RAW -> STANDARDIZED
-- calendar_dates.txt ← 
-- Tavasõiduplaani erandid (näiteks konkreetsed kuupäevad ja riigipühad, millal buss ei sõida või kehtib erigraafik)
-- Business question answered: "?"
-- Standardizes, parses, and loads raw GTFS CSV files into a single table for a selected date.
-- ===============================================================================================

SET VARIABLE extract_date =
    coalesce((
        SELECT extract_date FROM config.source_params
        WHERE source = 'gtfs' AND active
    ), current_date)::VARCHAR;

SET VARIABLE raw_dir = 'data/raw/extract_source=gtfs/extract_date=' || getvariable('extract_date') || '/extract_ts=*/calendar_dates.txt';

CREATE OR REPLACE TABLE standardized.gtfs_calendar_dates AS
SELECT
    service_id -- Unique ID, calendar.service_id, trips.service_id
  , date -- Date when service exception occurs
  , exception_type -- 1 - Service has been added, 2 - removed
  , try_strptime(extract_ts, '%Y%m%d_%H%M%S') AT TIME ZONE 'UTC' AS extract_ts
  , current_timestamp AS updated_ts
FROM read_csv(
    getvariable('raw_dir')
  , dateformat = '%Y%m%d'
);
