-- 5_spatial_demo.sql
-- ============================================================
-- DuckDB Spatial + distance demo for route 8 + Zoo / Toompark
-- Can be run directly against the exported CSVs in eda/data_tmp/
-- or adapted to read from standardized Parquet later.
-- ============================================================

SET VARIABLE data_dir = 'eda/data_tmp';

INSTALL spatial;
LOAD spatial;

CREATE OR REPLACE TABLE route8_pos AS
    SELECT * FROM read_csv(getvariable('data_dir') || '/route8_positions_20260523.csv');

CREATE OR REPLACE TABLE gtfs_stops AS
    SELECT * FROM read_csv(getvariable('data_dir') || '/gtfs_stops_20260523.csv');

-- 1. Identify the key stops
SELECT stop_id, stop_name, stop_lat, stop_lon
FROM gtfs_stops
WHERE stop_name ILIKE '%zoo%' OR stop_name ILIKE '%toompark%'
ORDER BY stop_name;

-- 2. Euclidean vs proper distances (first few rows)
WITH pos AS (
    SELECT
        snapshot_ts,
        vehicle_id,
        lat, lon,
        ST_Point(lon, lat) AS pos_geom
    FROM route8_pos
    WHERE line_number = '8'
),
zoo  AS (SELECT ST_Point(24.65805, 59.42643) AS g),
toom AS (SELECT ST_Point(24.73333, 59.43682) AS g)
SELECT
    snapshot_ts,
    vehicle_id,
    ROUND(lat,5) AS lat, ROUND(lon,5) AS lon,
    ROUND( SQRT(POW(lat-59.42643,2) + POW(lon-24.65805,2)), 6) AS eucl_zoo_deg,
    ROUND( ST_Distance(pos_geom, (SELECT g FROM zoo)), 6)      AS st_zoo_deg,
    ROUND( ST_Distance_Spheroid(pos_geom, (SELECT g FROM zoo)), 1)  AS dist_zoo_m,
    ROUND( ST_Distance_Spheroid(pos_geom, (SELECT g FROM toom)), 1) AS dist_toompark_m
FROM pos
ORDER BY snapshot_ts, vehicle_id
LIMIT 10;

-- 3. Min/mean distance per stop (whole dataset)
WITH pos AS (
    SELECT vehicle_id, lat, lon, ST_Point(lon, lat) AS pos_geom
    FROM route8_pos WHERE line_number = '8'
)
SELECT
    'Zoo' AS stop,
    MIN(ST_Distance_Spheroid(pos_geom, ST_Point(24.65805, 59.42643))) AS min_dist_m,
    ROUND(AVG(ST_Distance_Spheroid(pos_geom, ST_Point(24.65805, 59.42643))),1) AS mean_dist_m,
    COUNT(*) AS n
FROM pos
UNION ALL
SELECT
    'Toompark',
    MIN(ST_Distance_Spheroid(pos_geom, ST_Point(24.73333, 59.43682))),
    ROUND(AVG(ST_Distance_Spheroid(pos_geom, ST_Point(24.73333, 59.43682))),1),
    COUNT(*)
FROM pos;

-- 4. EPSG:3301 (L-EST97) example — local meter Euclidean is excellent for Tallinn
WITH sample AS (
    SELECT lat, lon,
           ST_Transform(ST_Point(lon, lat), 'EPSG:4326', 'EPSG:3301') AS p_3301
    FROM route8_pos
    WHERE line_number = '8'
    LIMIT 5
)
SELECT
    lat, lon,
    ROUND( ST_Distance( p_3301, ST_Transform(ST_Point(24.65805, 59.42643), 'EPSG:4326', 'EPSG:3301') ), 1) AS dist_zoo_3301_m
FROM sample;

-- Tip: later replace the two CREATE TABLEs with views over your standardized Parquet:
-- CREATE OR REPLACE VIEW route8_pos AS
-- SELECT * FROM 'data/standardized/gps_positions/date=*/part.parquet' WHERE line_number='8';
