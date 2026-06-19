-- 1. Identify the key stops
SELECT
    stop_id
  , stop_name
  , stop_lat
  , stop_lon
FROM db.standardized.gtfs_stops
WHERE lower(stop_name) = 'zoo' OR lower(stop_name) ILIKE 'toompark'
ORDER BY stop_name;

INSTALL spatial;
LOAD spatial;

EXPLAIN ANALYZE
WITH
pos AS (
    SELECT
        snapshot_ts,
        vehicle_id,
        lat,
        lon,
        st_point(lat, lon) AS geom4326,
        st_transform(
            st_point(lat, lon),
            'EPSG:4326',
            'EPSG:3301'
        ) AS geom3301
    FROM db.standardized.route8_positions
    WHERE fleet_number = 35
),

stop AS (
    SELECT
        stop_lat,
        stop_lon,
        st_point(stop_lat, stop_lon) AS geom4326,
        st_transform(
            st_point(stop_lat, stop_lon),
            'EPSG:4326',
            'EPSG:3301'
        ) AS geom3301
    FROM db.standardized.gtfs_stops
    WHERE stop_id = 822
    )

SELECT
    snapshot_ts
  , vehicle_id
  , lat
  , lon
  , (SELECT stop_lat FROM stop) AS stop_lat
  , (SELECT stop_lon FROM stop) AS stop_lon
	-- METHOD 1: Local Euclidean (flat-Earth) with WGS84 meridian correction
  , sqrt(
        pow((lat - stop_lat) * (111132.95 - 559.82 * cos(radians(2 * ((lat + stop_lat) / 2))) + 1.175 * cos(radians(4 * ((lat + stop_lat) / 2)))), 2)
      + pow((lon - stop_lon) * 111319.5 * cos(radians((lat + stop_lat) / 2)), 2)
    ) AS eucl_wgs84_manual_m
    

    -- METHOD 2: Projected Euclidean via EPSG:3301 (Estonia LCC)
  , st_distance(
        st_transform(pos_geom, 'EPSG:4326', 'EPSG:3301')
      , st_transform((SELECT g FROM stop), 'EPSG:4326', 'EPSG:3301')
    ) AS st_transform_eucl_m
    

    -- METHOD 3: Haversine (spherical great-circle)
  , (2 * 6370986 * asin(sqrt(
        pow(sin(radians((lat - (SELECT stop_lat FROM stop)) / 2)), 2)
      + cos(radians((SELECT stop_lat FROM stop)))
      * cos(radians(lat))
      * pow(sin(radians((lon - (SELECT stop_lon FROM stop)) / 2)), 2)
    ))) AS haversine_manual_m
    

    -- METHOD 3b: ST_Distance_Sphere (built-in Haversine)
  , st_distance_sphere(
        st_point(lat, lon)
      , (SELECT g FROM stop)
    ) AS st_distance_sphere_m
    
    -- METHOD 4: ST_Distance_Spheroid (WGS84 ellipsoid via GeographicLib)
  , st_distance_spheroid(pos_geom, (SELECT g FROM stop)) AS st_distance_spheroid_m
FROM pos
ORDER BY snapshot_ts, vehicle_id;
