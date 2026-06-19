-- ===============================================================================================
-- Raw GPS data standardization: RAW -> STANDARDIZED
-- Standardizes, parses, and loads raw GPS CSV files into a single table for a selected date.
-- ===============================================================================================

SET VARIABLE gps_date = '2026-06-07';
SET VARIABLE raw_dir = 'data/raw/source=gps/date=' || getvariable('gps_date') || '/*.csv';

CREATE OR REPLACE TABLE standardized.gps_positions AS
	SELECT
	    gp.transport_type
	  , gp.line_number
	  , gp.vehicle_id
	  , gp.fleet_number
	  , gp.latitude_raw / 1000000.0 AS lat
	  , gp.longitude_raw / 1000000.0 AS lon
	  --, gp.longitude_raw
	  --, gp.latitude_raw
	  , nullif(gp.heading_deg, 999) AS heading_deg
	  --, gp.heading_deg
	  , gp.speed_kmh
	  , gp.floor_type
	  , gp.destination
	  , gp.source
	  , try_strptime(
	        regexp_extract(parse_filename(gp.filename), 'gps_(\d{8}_\d{6})\.csv', 1), '%Y%m%d_%H%M%S'
	    ) AT TIME ZONE 'UTC' AS snapshot_ts
	    --, filename AS file_path
	  , getvariable('gps_date')::DATE AS snapshot_date
	FROM
	    --data/raw/source=gps/date={gps_date}/*.csv
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
	    ) AS gp;