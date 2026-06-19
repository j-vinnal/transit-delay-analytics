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
        st_transform(geom4326, 'EPSG:4326', 'EPSG:3301') AS geom3301
    FROM db.standardized.route8_positions
    WHERE fleet_number = 35
),

stop AS (
    SELECT
        stop_lat,
        stop_lon,
        st_point(stop_lat, stop_lon) AS stop_geom4326,
        st_transform(stop_geom4326, 'EPSG:4326', 'EPSG:3301') AS stop_geom3301
    FROM db.standardized.gtfs_stops
    WHERE stop_id = 822
)

SELECT 
    p.snapshot_ts,
    p.vehicle_id,
    p.lat,
    p.lon,

    -- =========================================================
	-- METHOD 1: Local Euclidean (flat-Earth) with WGS84 meridian correction
	-- Source: https://en.wikipedia.org/wiki/Latitude#Length_of_a_degree_of_latitude
  	--
	-- Δlat_m uses latitude-dependent WGS84 meridional arc length per degree:
	-- 1° lat ≈ 111132.954 - 559.822·cos(2φ) + 1.175·cos(4φ)   meters
	--
	-- Δlon_m uses parallel correction:
	-- 1° lon ≈ 111412.84·cos(φ) - 93.5·cos(3φ)                meters
	-- where φ = average latitude (in radians)
	--
	-- d = sqrt(Δlat_m² + Δlon_m²)
	--
	-- Suitable for short distances. No built-in DuckDB equivalent.
	-- =========================================================
    sqrt(
        pow((p.lat - s.stop_lat) * (
            111132.954 
            - 559.822 * cos(radians(p.lat + s.stop_lat)) -- 2φ
            + 1.175  * cos(radians(2 * (p.lat + s.stop_lat))) -- 4φ
        ), 2)
      + pow((p.lon - s.stop_lon) * (
            111412.84 * cos(radians((p.lat + s.stop_lat) / 2)) 
            - 93.5 * cos(radians(3 * (p.lat + s.stop_lat) / 2))
        ), 2)
    ) AS eucl_wgs84_manual_m,
    
    -- =========================================================
    -- METHOD 2: Projected Euclidean via EPSG:3301 (Estonia LCC)
    --
    -- Reproject WGS84 (lat,lon) → meters in Estonia-specific Lambert Conformal Conic
    -- (ETRS89 / EPSG:3301), then apply Pythagoras.
    -- Low distortion for regional use in Estonia.
    -- =========================================================
    st_distance(p.geom3301, s.stop_geom3301) AS projected_distance_m,

    -- =========================================================
    -- METHOD 3: Haversine (spherical great-circle)
    --
    -- d = 2R · arcsin(√[sin²(Δlat/2) + cos(lat1)·cos(lat2)·sin²(Δlon/2)])
    -- R = 6370986 m (matches DuckDB internal)
    -- Assumes Earth is a perfect sphere. Fast closed-form approximation.
    -- Matches: ST_Distance_Sphere
    -- =========================================================
    (2 * 6370986 * asin(sqrt(
        pow(sin(radians((p.lat - s.stop_lat) / 2)), 2)
      + cos(radians(s.stop_lat)) * cos(radians(p.lat))
      * pow(sin(radians((p.lon - s.stop_lon) / 2)), 2)
    ))) AS haversine_manual_m,

    -- =========================================================
    -- METHOD 3b: ST_Distance_Sphere (built-in Haversine)
    --
    -- Identical to manual haversine above (within FP precision).
    -- Input assumed EPSG:4326 with [latitude, longitude] order.
    -- =========================================================
    st_distance_sphere(p.geom4326, s.stop_geom4326) AS sphere_distance_m,

    -- =========================================================
    -- METHOD 4: ST_Distance_Spheroid (WGS84 ellipsoid via GeographicLib)
    --
    -- Solves inverse geodesic problem iteratively on WGS84 ellipsoid
    -- (a=6378137 m, f=1/298.257223563). Most accurate for any distance.
    -- Slowest of the built-in options.
    -- =========================================================
    st_distance_spheroid(p.geom4326, s.stop_geom4326) AS spheroid_distance_m

FROM pos p
CROSS JOIN stop s
ORDER BY p.snapshot_ts, p.vehicle_id;