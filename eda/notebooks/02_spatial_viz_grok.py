# %%
import duckdb
import polars as pl
import plotly.express as px
import plotly.graph_objects as go

# %%
# ====================== CONNECT TO DUCKDB ======================
con = duckdb.connect('../../db.duckdb')
con.execute("INSTALL spatial; LOAD spatial;")

print("Connected to DuckDB successfully.")

# %%
# ====================== SQL QUERY ======================
# Paste your final clean SQL query here
sql = """
WITH 
pos AS (
    SELECT
        snapshot_ts,
        vehicle_id,
        lat,
        lon,
        st_point(lat, lon) AS geom4326,
        st_transform(st_point(lat, lon), 'EPSG:4326', 'EPSG:3301') AS geom3301
    FROM db.standardized.route8_positions
    WHERE fleet_number = 35
),

stop AS (
    SELECT
        stop_lat,
        stop_lon,
        st_point(stop_lat, stop_lon) AS stop_geom4326,
        st_transform(st_point(stop_lat, stop_lon), 'EPSG:4326', 'EPSG:3301') AS stop_geom3301
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
            - 559.822 * cos(radians(2 * (p.lat + s.stop_lat) / 2))
            + 1.175  * cos(radians(4 * (p.lat + s.stop_lat) / 2))
        ), 2)
      + pow((p.lon - s.stop_lon) * (
            111412.84 * cos(radians((p.lat + s.stop_lat) / 2))
            - 93.5   * cos(radians(3 * (p.lat + s.stop_lat) / 2))
        ), 2)
    ) AS eucl_wgs84_manual_m,

    -- METHOD 2: EPSG:3301 (Estonia LCC)
    st_distance(p.geom3301, s.stop_geom3301) AS projected_distance_m,

    -- METHOD 3: Haversine (manual)
    (2 * 6370986 * asin(sqrt(
        pow(sin(radians((p.lat - s.stop_lat) / 2)), 2)
      + cos(radians(s.stop_lat)) * cos(radians(p.lat))
      * pow(sin(radians((p.lon - s.stop_lon) / 2)), 2)
    ))) AS haversine_manual_m,

    -- METHOD 3b: Built-in Haversine
    st_distance_sphere(p.geom4326, s.stop_geom4326) AS sphere_distance_m,

    -- METHOD 4: WGS84 Spheroid
    st_distance_spheroid(p.geom4326, s.stop_geom4326) AS spheroid_distance_m

FROM pos p
CROSS JOIN stop s
ORDER BY p.snapshot_ts, p.vehicle_id;
"""

# %%
# ====================== EXECUTE QUERY ======================
df = con.sql(sql).pl()

print(f"Query executed successfully. Rows: {len(df)}")
print("\nFirst 5 rows:")
print(df.head())

distance_cols = [
    "eucl_wgs84_manual_m",
    "projected_distance_m",
    "haversine_manual_m",
    "sphere_distance_m",
    "spheroid_distance_m"
]

# %%
# ====================== SUMMARY STATISTICS ======================
print("\n=== Summary Statistics ===")
print(df.select(distance_cols).describe())

# %%
# ====================== MAIN INTERACTIVE LINE CHART ======================
fig = px.line(
    df.to_pandas(),
    x="snapshot_ts",
    y=distance_cols,
    labels={
        "value": "Distance (meters)",
        "variable": "Distance Method",
        "snapshot_ts": "Timestamp"
    },
    title="Comparison of GPS Distance Calculation Methods<br><sup>Vehicle 1236 approaching Zoo stop</sup>"
)

fig.update_layout(
    hovermode="x unified",
    legend_title_text="Method",
    height=650,
    template="plotly_white"
)
fig.update_traces(mode="lines+markers", marker=dict(size=4))
fig.show()

# %%
# ====================== PAIRWISE SCATTER MATRIX ======================
fig_matrix = px.scatter_matrix(
    df.to_pandas(),
    dimensions=distance_cols,
    title="Pairwise Relationships Between Distance Methods",
    height=900
)
fig_matrix.update_traces(marker=dict(size=4, opacity=0.6))
fig_matrix.show()

# %%
# ====================== CORRELATION HEATMAP ======================
corr = df.select(distance_cols).to_pandas().corr()

fig_heatmap = go.Figure(data=go.Heatmap(
    z=corr.values,
    x=corr.columns,
    y=corr.columns,
    colorscale="RdBu_r",
    zmin=0.9995,
    zmax=1.0,
    text=corr.round(6).values,
    texttemplate="%{text}"
))

fig_heatmap.update_layout(
    title="Correlation Matrix of Distance Methods",
    height=600,
    width=700
)
fig_heatmap.show()