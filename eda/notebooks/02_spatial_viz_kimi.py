# %%
"""
Bus Fleet 35 — Distance to Zoo Stop: Symmetric Method Comparison
==================================================================
Interactive Plotly visualization reading directly from DuckDB.

Connects to ../../db.duckdb, runs the spatial distance query,
and produces a 3-panel interactive HTML report.

Compatible with: Jupyter, VS Code interactive, or `python script.py`
"""

import duckdb
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# %% ── Connect to DuckDB ─────────────────────────────────────────────────

DB_PATH = "../../db.duckdb"
con = duckdb.connect(DB_PATH)

# Ensure spatial extension is available
con.execute("INSTALL spatial; LOAD spatial;")

print(f"Connected to: {DB_PATH}")

# %% ── Run Query ──────────────────────────────────────────────────────────

query = """
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
        st_point(stop_lat, stop_lon) AS stop_geom4326,
        st_transform(
            st_point(stop_lat, stop_lon),
            'EPSG:4326',
            'EPSG:3301'
        ) AS stop_geom3301
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
ORDER BY p.snapshot_ts, p.vehicle_id
"""

# Fetch as list of tuples, then build columnar structures
result = con.execute(query).fetchall()
columns = [desc[0] for desc in con.execute(query).description]

print(f"Fetched {len(result)} rows, {len(columns)} columns")
print(f"Columns: {columns}")

# %% ── Prepare Data ───────────────────────────────────────────────────────

from datetime import datetime

# Columnar extraction for Plotly
snapshot_ts = [row[0] for row in result]
time_str = [t.strftime("%H:%M:%S") for t in snapshot_ts]
vehicle_id = [row[1] for row in result]
lat = [row[2] for row in result]
lon = [row[3] for row in result]

eucl_wgs84 = [row[4] for row in result]
projected = [row[5] for row in result]
haversine = [row[6] for row in result]
sphere = [row[7] for row in result]
spheroid = [row[8] for row in result]

METHODS = {
    "eucl_wgs84_manual_m": ("WGS84 Flat-Earth", eucl_wgs84),
    "projected_distance_m": ("EPSG:3301 LCC", projected),
    "haversine_manual_m": ("Haversine (manual)", haversine),
    "sphere_distance_m": ("ST_Distance_Sphere", sphere),
    "spheroid_distance_m": ("ST_Distance_Spheroid", spheroid),
}

COLORS = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7"]
DASHES = ["solid", "solid", "dash", "dash", "solid"]
DIFF_COLORS = [
    "#8884d8", "#82ca9d", "#ffc658", "#ff7300",
    "#00C49F", "#FFBB28", "#FF8042", "#a4de6c",
    "#d0ed57", "#8dd1e1",
]

# %% ── Build Figure ───────────────────────────────────────────────────────

fig = make_subplots(
    rows=3,
    cols=1,
    shared_xaxes=True,
    vertical_spacing=0.09,
    subplot_titles=(
        "Distance to Zoo Stop (m)",
        "Pairwise Differences Between Methods (m)",
        "Vehicle Trajectory (lat / lon)",
    ),
    specs=[[{"type": "scatter"}], [{"type": "scatter"}], [{"type": "scatter"}]],
)

# ── Row 1: Raw distances ──
for (col_key, (label, y_vals)), color, dash in zip(METHODS.items(), COLORS, DASHES):
    fig.add_trace(
        go.Scatter(
            x=snapshot_ts,
            y=y_vals,
            mode="lines",
            name=label,
            line=dict(color=color, width=2, dash=dash),
            hovertemplate="%{x|%H:%M:%S}<br>%{y:.2f} m<extra>" + label + "</extra>",
        ),
        row=1,
        col=1,
    )

# ── Row 2: Symmetric pairwise differences ──
method_keys = list(METHODS.keys())
method_names = [METHODS[k][0] for k in method_keys]
method_data = [METHODS[k][1] for k in method_keys]

diff_idx = 0
for i in range(len(method_keys)):
    for j in range(i + 1, len(method_keys)):
        name_a, name_b = method_names[i], method_names[j]
        data_a, data_b = method_data[i], method_data[j]
        diff_vals = [a - b for a, b in zip(data_a, data_b)]

        fig.add_trace(
            go.Scatter(
                x=snapshot_ts,
                y=diff_vals,
                mode="lines",
                name=f"{name_a} − {name_b}",
                line=dict(
                    color=DIFF_COLORS[diff_idx % len(DIFF_COLORS)], width=1.2
                ),
                opacity=0.85,
                showlegend=False,
                hovertemplate=(
                    "%{x|%H:%M:%S}<br>"
                    f"Δ = %{{y:.3f}} m<extra>{name_a} − {name_b}</extra>"
                ),
            ),
            row=2,
            col=1,
        )
        diff_idx += 1

fig.add_hline(y=0, line_dash="dot", line_color="gray", line_width=1, row=2, col=1)

# ── Row 3: Trajectory with distance as color ──
fig.add_trace(
    go.Scatter(
        x=lon,
        y=lat,
        mode="lines+markers",
        name="Trajectory",
        line=dict(color="#636EFA", width=2),
        marker=dict(
            size=7,
            color=spheroid,
            colorscale="RdYlGn_r",
            colorbar=dict(
                title="Distance (m)",
                len=0.35,
                y=0.12,
                thickness=14,
            ),
            showscale=True,
        ),
        text=time_str,
        hovertemplate="lon: %{x:.5f}<br>lat: %{y:.5f}<br>time: %{text}<extra></extra>",
        showlegend=False,
    ),
    row=3,
    col=1,
)

# Zoo stop marker (closest recorded point ≈ Zoo location)
min_idx = spheroid.index(min(spheroid))
fig.add_trace(
    go.Scatter(
        x=[lon[min_idx]],
        y=[lat[min_idx]],
        mode="markers",
        name="Zoo Stop",
        marker=dict(
            size=16,
            color="red",
            symbol="star",
            line=dict(color="darkred", width=1),
        ),
        hovertemplate="Zoo Stop<extra></extra>",
        showlegend=False,
    ),
    row=3,
    col=1,
)

# %% ── Layout ──────────────────────────────────────────────────────────────

fig.update_layout(
    title=dict(
        text=(
            "<b>Bus Fleet 35 — Distance to Zoo Stop</b><br>"
            "<sup>Symmetric comparison of 5 GPS distance methods (DuckDB spatial)</sup>"
        ),
        x=0.5,
        font_size=17,
    ),
    height=1000,
    width=1150,
    template="plotly_white",
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="center",
        x=0.5,
        bgcolor="rgba(255,255,255,0.85)",
        bordercolor="lightgray",
        borderwidth=1,
    ),
    hovermode="x unified",
)

fig.update_xaxes(title_text="Timestamp", row=3, col=1)
fig.update_yaxes(title_text="Distance (m)", row=1, col=1)
fig.update_yaxes(title_text="Δ (m)", row=2, col=1)
fig.update_yaxes(title_text="Latitude", row=3, col=1)
fig.update_xaxes(title_text="Longitude", row=3, col=1)

# %% ── Export ─────────────────────────────────────────────────────────────

OUTPUT_HTML = "bus_zoo_distance_comparison.html"
fig.write_html(OUTPUT_HTML, include_plotlyjs="cdn")
print(f"\nSaved interactive report: {OUTPUT_HTML}")

# %% ── Summary Statistics ──────────────────────────────────────────────────

print("\n" + "=" * 55)
print("SUMMARY STATISTICS")
print("=" * 55)

for col_key, (label, vals) in METHODS.items():
    print(f"\n{label}:")
    print(f"  min:  {min(vals):>10.2f} m")
    print(f"  max:  {max(vals):>10.2f} m")
    print(f"  mean: {sum(vals)/len(vals):>10.2f} m")

print("\n" + "-" * 55)
print("PAIRWISE MAX ABSOLUTE DIFFERENCES")
print("-" * 55)

for i in range(len(method_keys)):
    for j in range(i + 1, len(method_keys)):
        name_a, name_b = method_names[i], method_names[j]
        data_a, data_b = method_data[i], method_data[j]
        max_diff = max(abs(a - b) for a, b in zip(data_a, data_b))
        print(f"  {name_a:22s} vs {name_b:22s} : {max_diff:8.4f} m")

# %% ── Cleanup ────────────────────────────────────────────────────────────

con.close()
print("\nDuckDB connection closed.")