-- ===============================================================================================
-- Raw GPS data standardization: RAW -> STANDARDIZED
-- Standardizes, parses, and loads raw GPS CSV files into a single table for a selected date.
-- ===============================================================================================

SET VARIABLE extract_date =
    coalesce((
        SELECT extract_date FROM config.source_params
        WHERE source = 'gps' AND active
    ), current_date)::VARCHAR;

SET VARIABLE raw_dir = 'data/raw/extract_source=gps/extract_date=' || getvariable('extract_date') || '/*.csv';

CREATE OR REPLACE TABLE standardized.gps_positions AS
SELECT
    transport_type
  , line_number
  , speed_kmh
  , vehicle_id
  , floor_type
  , fleet_number
  , destination
  , latitude_raw / 1000000.0 AS lat
  , longitude_raw / 1000000.0 AS lon
  , nullif(heading_deg, 999) AS heading_deg
  , try_strptime(
        regexp_extract(parse_filename(filename), 'gps_(\d{8}_\d{6})\.csv', 1), '%Y%m%d_%H%M%S'
    ) AT TIME ZONE 'UTC' AS extract_ts
  , current_timestamp AS updated_ts
FROM --data/raw/extract_source=gps/extract_date={gps_date}/*.csv
    read_csv(
        getvariable('raw_dir')
      , header = false
      , names = [
            'transport_type'
          , 'line_number'
          , 'longitude_raw'
          , 'latitude_raw'
          , 'speed_kmh'
          , 'heading_deg'
          , 'vehicle_id'
          , 'floor_type'
          , 'fleet_number'
          , 'destination'
        ]
    );
