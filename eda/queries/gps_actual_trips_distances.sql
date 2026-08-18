-- =============================================================
-- intermediate/stop_distances
-- Business question answered: "How far was each route 8 bus from Zoo and Toompark at each moment?"
--
-- Comparison of spatial distance calculation methods
-- Dataset: bus route 8, vehicle fleet_number=35, Zoo stop (stop_id=822)
--
-- Three approaches:
--   A) PLANAR    — Euclidean / Pythagorean (flat surface)
--   B) SPHERE    — Haversine (perfect sphere, R = 6370986 m)
--   C) ELLIPSOID — geodesic on WGS84 ellipsoid (most accurate)
--
-- Two coordinate spaces:
--   EPSG:4326 (WGS84)   — native GPS, unit: degree
--   EPSG:3301 (L-EST97) — Estonian Lambert projection, unit: metre
--
-- Expected ordering at short distances in Estonia:
--   A1 ≈ C > B
--   A1 ≈ C because both use WGS84 ellipsoid constants, at short
--   distances the straight line (Pythagoras) ≈ geodesic arc.
--   B is lower because it uses a sphere (R=6370986 m) which
--   underestimates the meridional radius of curvature at ~59°N (~6399 km).
-- =============================================================

INSTALL spatial;
LOAD spatial;

--SUMMARIZE
WITH
    -- Bus GPS positions (fleet_number=35, route 8 vehicle)
    -- geom4326: WGS84 point in degrees | geom3301: reprojected to L-EST97 in metres
    pos AS (
        SELECT
            extract_ts
          , vehicle_id
          , fleet_number
          , lat
          , lon
          , st_point(lat, lon) AS geom4326
          , st_transform(geom4326, 'EPSG:4326', 'EPSG:3301') AS geom3301
        FROM standardized.gps_positions
        WHERE
            line_number = '8'
            AND lower(destination) = 'äigrumäe'
            AND fleet_number = 89
    )

    -- Zoo stop (stop_id=822), coordinates: ~59.42621°N, 24.65889°E
  , stop AS (
        SELECT
            stop_lat
          , stop_lon
          , st_point(stop_lat, stop_lon) AS stop_geom4326
          , st_transform(stop_geom4326, 'EPSG:4326', 'EPSG:3301') AS stop_geom3301
        FROM db.standardized.gtfs_stops
        WHERE stop_id = 822 -- zoo stop
    )

SELECT
    p.extract_ts
  , p.fleet_number
  , p.vehicle_id
  , p.geom4326
    -- =============================================================
    -- A1) PLANAR — WGS84 degrees → metres via meridional arc approximation
    --
    -- Converts degree differences to metres using Fourier-series coefficients
    -- derived from WGS84 (a=6378137 m, f=1/298.257223563), then applies Pythagoras.
    -- Not a projection — still a straight-line distance on a flat surface.
    -- Because the coefficients encode ellipsoid shape, A1 ≈ C at short distances.
    --
    -- Δlat: 1° ≈ 111132.954 - 559.822·cos(2φ) + 1.175·cos(4φ)  metres
    -- Δlon: 1° ≈ 111412.84·cos(φ) - 93.5·cos(3φ)               metres
    -- φ = mean latitude of the two points
    -- Ref: https://en.wikipedia.org/wiki/Latitude#Length_of_a_degree_of_latitude
    -- =============================================================
  , sqrt(
        pow(
            (p.lat - s.stop_lat) * (
                111132.954
                - 559.822 * cos(radians(p.lat + s.stop_lat))        -- 2φ term
                + 1.175 * cos(radians(2.0 * (p.lat + s.stop_lat)))  -- 4φ term
            )
          , 2
        )
        + pow(
            (p.lon - s.stop_lon) * (
                111412.84 * cos(radians((p.lat + s.stop_lat) / 2.0))
                - 93.5 * cos(radians(3.0 * (p.lat + s.stop_lat) / 2.0))
            )
          , 2
        )
    ) AS eucl_wgs84_manual_m
    -- =============================================================
    -- A2) PLANAR — L-EST97 (EPSG:3301), manual Pythagorean formula
    --
    -- st_transform reprojects WGS84 → L-EST97 (Lambert Conformal Conic,
    -- ETRS89 datum) via PROJ. Coordinates are then in metres, so Pythagoras
    -- gives metres directly with no approximation error.
    -- A2 = A3 exactly (same PROJ projection, different computation path).
    -- =============================================================
  , sqrt(
        pow(st_x(p.geom3301) - st_x(s.stop_geom3301), 2)
        + pow(st_y(p.geom3301) - st_y(s.stop_geom3301), 2)
    ) AS eucl_3301_manual_m
    -- =============================================================
    -- A3) PLANAR — L-EST97 (EPSG:3301), DuckDB built-in st_distance
    --
    -- Applies Pythagoras to projected metre coordinates.
    -- Identical to A2: included to confirm st_distance behaviour on GEOMETRY type.
    -- Ref: https://duckdb.org/docs/current/core_extensions/spatial/functions#st_distance
    -- =============================================================
  , st_distance(p.geom3301, s.stop_geom3301) AS eucl_3301_m
    -- =============================================================
    -- B1) SPHERE — Haversine, manual
    --
    -- Great-circle arc distance on a perfect sphere.
    -- d = 2R · arcsin(√[sin²(Δlat/2) + cos(lat₁)·cos(lat₂)·sin²(Δlon/2)])
    -- R = 6370986 m (mean Earth radius used by DuckDB / PostGIS).
    -- Ref: https://postgis.net/docs/manual-1.4/ST_Distance_Sphere.html
    --
    -- Difference from B2: ~0.03 m (IEEE 754 floating-point ordering). Not fixable in SQL.
    -- =============================================================
  , (2.0 * 6370986 * asin(sqrt(
        pow(sin(radians((p.lat - s.stop_lat) / 2.0)), 2)
        + cos(radians(s.stop_lat))
        * cos(radians(p.lat))
        * pow(sin(radians((p.lon - s.stop_lon) / 2.0)), 2)
    ))) AS havers_wgs84_manual_m
    -- =============================================================
    -- B2) SPHERE — DuckDB built-in st_distance_sphere
    --
    -- Haversine formula (B1) with R = 6370986 m. Input axis order: [lat, lon].
    -- Ref: https://duckdb.org/docs/current/core_extensions/spatial/functions#st_distance_sphere
    -- =============================================================
  , st_distance_sphere(p.geom4326, s.stop_geom4326) AS havers_wgs84_m
    -- =============================================================
    -- C) ELLIPSOID — st_distance_spheroid (WGS84)
    --
    -- Solves the inverse geodesic problem on the WGS84 ellipsoid
    -- via GeographicLib (iterative algorithm). Most accurate method.
    -- Ellipsoid: a = 6378137 m, f = 1/298.257223563. Input axis order: [lat, lon].
    -- Ref: https://duckdb.org/docs/current/core_extensions/spatial/functions#st_distance_spheroid
    --      https://geographiclib.sourceforge.io/
    -- =============================================================
  , st_distance_spheroid(p.geom4326, s.stop_geom4326) AS spheroid_m
FROM pos AS p
CROSS JOIN stop AS s
ORDER BY p.extract_ts, p.vehicle_id;
