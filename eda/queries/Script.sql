-- Defineeri muutujad
SET VARIABLE zoo_lat = (SELECT stop_lat FROM db.standardized.gtfs_stops WHERE stop_id = 822);
SET VARIABLE zoo_lon = (SELECT stop_lon FROM db.standardized.gtfs_stops WHERE stop_id = 822);
SET VARIABLE zoo_g = (SELECT st_point(stop_lat, stop_lon) FROM db.standardized.gtfs_stops WHERE stop_id = 822);

-- Päring ilma CROSS JOINita
EXPLAIN ANALYZE
WITH pos AS (
    SELECT
        snapshot_ts,
        vehicle_id,
        lat,
        lon,
        st_point(lat, lon) AS pos_geom
    FROM db.standardized.route8_positions
    WHERE fleet_number = 35
)
SELECT
    snapshot_ts,
    vehicle_id,
    lat,
    lon,
    -- Meetod 1
    sqrt(
        pow((lat - getvariable('zoo_lat')) * (111132.95 - 559.82 * cos(radians(2 * ((lat + getvariable('zoo_lat')) / 2))) + 1.175 * cos(radians(4 * ((lat + getvariable('zoo_lat')) / 2)))), 2)
      + pow((lon - getvariable('zoo_lon')) * 111319.5 * cos(radians((lat + getvariable('zoo_lat')) / 2)), 2)
    ) AS eucl_wgs84_manual_m,
    -- Meetod 2
    st_distance(
        st_transform(pos_geom, 'EPSG:4326', 'EPSG:3301'),
        st_transform(getvariable('zoo_g'), 'EPSG:4326', 'EPSG:3301')
    ) AS st_transform_eucl_m,
    -- Meetod 3
    st_distance_sphere(pos_geom, getvariable('zoo_g')) AS st_distance_sphere_m,
    -- Meetod 4
    st_distance_spheroid(pos_geom, getvariable('zoo_g')) AS st_distance_spheroid_m
FROM pos
ORDER BY snapshot_ts, vehicle_id;