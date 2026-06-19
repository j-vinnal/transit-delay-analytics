# %% [markdown]
# # Geospatial Distance Calculation Methods: Symmetric Comparison
# This script executes the optimized DuckDB spatial query and uses Polars 
# for zero-copy data manipulation, visualized interactively with Plotly.

# %%
import duckdb
import polars as pl
import plotly.express as px

# %%
# 1. Initialize DuckDB connection and load spatial extension
con = duckdb.connect('../../db.duckdb')
con.execute("INSTALL spatial; LOAD spatial;")

# Note: If your tables are in an actual DuckDB file, 
# replace ':memory:' with 'your_database.duckdb'

# %%
# 2. Define the optimized SQL query
sql_query = """
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

    -- METHOD 1: WGS84 flat-Earth with meridian correction
    sqrt(
        pow((p.lat - s.stop_lat) * (
            111132.954 
            - 559.822 * cos(radians(p.lat + s.stop_lat))
            + 1.175  * cos(radians(2 * (p.lat + s.stop_lat)))
        ), 2)
      + pow((p.lon - s.stop_lon) * (
            111412.84 * cos(radians((p.lat + s.stop_lat) / 2)) 
            - 93.5 * cos(radians(3 * (p.lat + s.stop_lat) / 2))
        ), 2)
    ) AS eucl_wgs84_m,

    -- METHOD 2: EPSG:3301 (Estonia LCC)
    st_distance(p.geom3301, s.stop_geom3301) AS projected_3301_m,

    -- METHOD 3: Haversine (manual)
    (2 * 6370986 * asin(sqrt(
        pow(sin(radians((p.lat - s.stop_lat) / 2)), 2)
      + cos(radians(s.stop_lat)) * cos(radians(p.lat))
      * pow(sin(radians((p.lon - s.stop_lon) / 2)), 2)
    ))) AS haversine_manual_m,

    -- METHOD 3b: Built-in Haversine
    st_distance_sphere(p.geom4326, s.stop_geom4326) AS sphere_builtin_m,

    -- METHOD 4: WGS84 Spheroid
    st_distance_spheroid(p.geom4326, s.stop_geom4326) AS spheroid_m

FROM pos p
CROSS JOIN stop s
ORDER BY p.snapshot_ts, p.vehicle_id;
"""

# %%
# 3. Execute query and fetch results directly into a Polars DataFrame (Zero-copy)
df = con.execute(sql_query).pl()

# %%
# 4. Data Transformation: Symmetric Unpivoting
# Transform the wide dataframe into a long format for seamless Plotly integration.
# Polars 'unpivot' is the modern equivalent of Pandas 'melt'.
methods_columns = [
    "eucl_wgs84_m", 
    "projected_3301_m", 
    "haversine_manual_m", 
    "sphere_builtin_m", 
    "spheroid_m"
]

df_long = df.unpivot(
    index=["snapshot_ts", "vehicle_id", "lat", "lon"],
    on=methods_columns,
    variable_name="calculation_method",
    value_name="distance_meters"
)

# %%
# 5. Visualizations

# ---------------------------------------------------------
# VISUALIZATION A: Symmetric Line Chart over Time
# ---------------------------------------------------------
# This plots the absolute calculated distance for all methods.
# Since the differences are small, you can use Plotly's interactive zoom 
# to inspect the exact microscopic variations between methods at any given point.
fig_line = px.line(
    df_long,
    x="snapshot_ts",
    y="distance_meters",
    color="calculation_method",
    title="Symmetric Comparison: Distance to Stop Across Different Algorithms",
    labels={
        "snapshot_ts": "Timestamp",
        "distance_meters": "Calculated Distance (m)",
        "calculation_method": "Geospatial Method"
    },
    template="plotly_white"
)

# Render the interactive line chart
fig_line.show()

# %%
# ---------------------------------------------------------
# VISUALIZATION B: Statistical Distribution of Calculated Distances
# ---------------------------------------------------------
# A box plot is excellent for a symmetric comparison to observe the 
# median, quartiles, and overall variance between the algorithms' outputs.
fig_box = px.box(
    df_long,
    x="calculation_method",
    y="distance_meters",
    color="calculation_method",
    title="Variance and Distribution of Distance Calculations",
    labels={
        "calculation_method": "Method",
        "distance_meters": "Distance (m)"
    },
    template="plotly_white"
)

fig_box.show()

# %%
# ---------------------------------------------------------
# VISUALIZATION C: Geospatial Trajectory Map
# ---------------------------------------------------------
# Visualizing the vehicle's actual path using one of the metrics for color mapping.
# Using the built-in sphere method for color scaling purely as a reference point.
fig_map = px.scatter_mapbox(
    df,
    lat="lat",
    lon="lon",
    color="sphere_builtin_m",
    hover_data=["snapshot_ts", "vehicle_id"] + methods_columns,
    title="Vehicle Trajectory & Distance to Target Stop",
    color_continuous_scale=px.colors.sequential.Viridis,
    zoom=12
)

# Open-source mapbox style (no API key required)
fig_map.update_layout(mapbox_style="carto-positron")
fig_map.show()