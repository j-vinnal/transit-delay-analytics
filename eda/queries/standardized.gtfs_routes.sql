-- ===============================================================================================
-- Raw GTFS data standardization: RAW -> STANDARDIZED
-- routes.txt       ← route IDs, names
-- Ühistranspordi liinide üldandmed (näiteks info, et tegu on bussiga number 8)
-- Business question answered: "What routes exist?"
-- Standardizes, parses, and loads raw GTFS CSV files into a single table for a selected date.
-- ===============================================================================================

SET VARIABLE extract_date =
    coalesce((
        SELECT extract_date FROM config.source_params
        WHERE source = 'gtfs' AND active
    ), current_date)::VARCHAR;

SET VARIABLE raw_dir = 'data/raw/extract_source=gtfs/extract_date=' || getvariable('extract_date') || '/extract_ts=*/routes.txt';

CREATE OR REPLACE TABLE standardized.gtfs_routes AS
SELECT
    route_id -- PK, trips.route_id
  , route_short_name
  , route_long_name
  , route_desc
  , route_type -- 3:bus, 800:trol, 900:tram
  , route_url
  , route_color
  , route_text_color
  , route_sort_order
  , try_strptime(extract_ts, '%Y%m%d_%H%M%S') AT TIME ZONE 'UTC' AS extract_ts
  , current_timestamp AS updated_ts
FROM read_csv(getvariable('raw_dir'));
