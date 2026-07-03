-- ===============================================================================================
-- Raw GTFS data standardization: RAW -> STANDARDIZED
-- routes.txt       ← route IDs, names
-- Business question answered: "What routes exist?"
-- Standardizes, parses, and loads raw GTFS CSV files into a single table for a selected date.
-- ===============================================================================================

SET VARIABLE gtfs_date = '2026-06-21';
SET VARIABLE raw_dir = 'data/raw/source=gtfs/date=' || getvariable('gtfs_date') || '/routes.txt';

CREATE OR REPLACE TABLE standardized.gtfs_routes AS
SELECT
    route_id
  , route_short_name
  , route_long_name
  , route_desc
  , route_type
  , route_url
  , route_color
  , route_text_color
  , route_sort_order
  , source
  , date AS snapshot_date
FROM read_csv(getvariable('raw_dir'));


SELECT
    route_id
  , route_short_name
  , route_long_name
  , route_desc
  , route_type
  , route_url
  , route_color
  , route_text_color
  , route_sort_order
  , source
  , snapshot_date
FROM standardized.gtfs_routes
WHERE route_short_name = '8';
