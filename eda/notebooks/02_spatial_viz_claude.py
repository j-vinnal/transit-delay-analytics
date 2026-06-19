# %% [markdown]
# # Distance method comparison – bus #8 stop 822
# Compares 5 distance calculation methods symmetrically.
# Stack: DuckDB (query) → Polars (transform) → Plotly (visualise)

# %% Imports & config
import duckdb
import polars as pl
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import itertools

DB_PATH = "../../db.duckdb"
FLEET_NUMBER = 35
STOP_ID = 822

METHODS = {
    "eucl_wgs84":    "WGS84 flat-earth",
    "projected_m":   "EPSG:3301 projected",
    "haversine_m":   "Haversine (manual)",
    "sphere_m":      "Haversine (built-in)",
    "spheroid_m":    "WGS84 spheroid",
}
METHOD_KEYS = list(METHODS.keys())
METHOD_LABELS = list(METHODS.values())

# Plotly-friendly palette – 5 visually distinct, print-safe colours
COLORS = {
    "eucl_wgs84":  "#3266AD",
    "projected_m": "#1D9E75",
    "haversine_m": "#D85A30",
    "sphere_m":    "#BA7517",
    "spheroid_m":  "#7F77DD",
}

TEMPLATE = "plotly_white"
FONT = dict(family="Inter, system-ui, sans-serif", size=12)

# %% Query → Polars
con = duckdb.connect(DB_PATH)
con.execute("INSTALL spatial; LOAD spatial;")

query = f"""
WITH
pos AS (
    SELECT
        snapshot_ts,
        vehicle_id,
        lat,
        lon,
        st_point(lat, lon)                                     AS geom4326,
        st_transform(geom4326, 'EPSG:4326', 'EPSG:3301')      AS geom3301
    FROM db.standardized.route8_positions
    WHERE fleet_number = {FLEET_NUMBER}
),
stop AS (
    SELECT
        stop_lat,
        stop_lon,
        st_point(stop_lat, stop_lon)                           AS stop_geom4326,
        st_transform(stop_geom4326, 'EPSG:4326', 'EPSG:3301') AS stop_geom3301
    FROM db.standardized.gtfs_stops
    WHERE stop_id = {STOP_ID}
)
SELECT
    p.snapshot_ts,
    p.vehicle_id,
    p.lat,
    p.lon,

    sqrt(
        pow((p.lat - s.stop_lat) * (
            111132.954
            - 559.822 * cos(radians(2 * (p.lat + s.stop_lat) / 2))
            +   1.175 * cos(radians(4 * (p.lat + s.stop_lat) / 2))
        ), 2)
      + pow((p.lon - s.stop_lon) * 111319.5 * cos(radians((p.lat + s.stop_lat) / 2)), 2)
    )                                                           AS eucl_wgs84,

    st_distance(p.geom3301, s.stop_geom3301)                   AS projected_m,

    (2 * 6370986 * asin(sqrt(
        pow(sin(radians((p.lat - s.stop_lat) / 2)), 2)
      + cos(radians(s.stop_lat)) * cos(radians(p.lat))
      * pow(sin(radians((p.lon - s.stop_lon) / 2)), 2)
    )))                                                         AS haversine_m,

    st_distance_sphere(p.geom4326, s.stop_geom4326)            AS sphere_m,
    st_distance_spheroid(p.geom4326, s.stop_geom4326)          AS spheroid_m

FROM pos p
CROSS JOIN stop s
ORDER BY p.snapshot_ts, p.vehicle_id
"""

df: pl.DataFrame = con.execute(query).pl()
print(f"Loaded {len(df)} rows")
print(df.select(METHOD_KEYS).describe())

# %% Figure 1 – Scatter matrix (all vs all, symmetric)
#
# Upper triangle: scatter of method A vs method B
# Diagonal:       histogram of that method's distribution
# Lower triangle: mirrors upper (Plotly splom handles this automatically)
#
# A perfect method pair lies on the y=x diagonal.
# Divergence = systematic bias; scatter = noise.

splom_dims = [
    dict(label=METHODS[k], values=df[k].to_list())
    for k in METHOD_KEYS
]

fig_splom = go.Figure(go.Splom(
    dimensions=splom_dims,
    showupperhalf=True,
    showlowerhalf=True,
    diagonal_visible=True,
    marker=dict(
        size=4,
        opacity=0.55,
        color=df["spheroid_m"].to_list(),   # colour by spheroid distance
        colorscale="Teal",
        showscale=True,
        colorbar=dict(
            title=dict(text="spheroid distance (m)", side="right"),
            thickness=12,
            len=0.7,
        ),
        line=dict(width=0),
    ),
    text=[f"ts={r}" for r in df["snapshot_ts"].to_list()],
    hovertemplate="x: %{x:.1f} m<br>y: %{y:.1f} m<br>%{text}<extra></extra>",
))

fig_splom.update_layout(
    title=dict(
        text="Scatter matrix – all distance methods vs all",
        subtitle=dict(text="Points on the diagonal = methods agree. Colour = spheroid distance."),
        font=dict(size=15),
    ),
    width=820,
    height=780,
    template=TEMPLATE,
    font=FONT,
    dragmode="select",
)

fig_splom.show()

# %% Figure 2 – Time series (all methods, one plot)
#
# Shows how each method tracks the bus moving toward / away from the stop.
# If lines are visually indistinguishable → methods are equivalent in practice.

fig_ts = go.Figure()

DASH = {
    "eucl_wgs84":  "solid",
    "projected_m": "dash",
    "haversine_m": "dot",
    "sphere_m":    "dashdot",
    "spheroid_m":  "solid",
}
WIDTH = {k: (2.5 if k == "spheroid_m" else 1.5) for k in METHOD_KEYS}

for key in METHOD_KEYS:
    fig_ts.add_trace(go.Scatter(
        x=df["snapshot_ts"].to_list(),
        y=df[key].to_list(),
        mode="lines",
        name=METHODS[key],
        line=dict(color=COLORS[key], width=WIDTH[key], dash=DASH[key]),
        hovertemplate=f"<b>{METHODS[key]}</b><br>%{{x}}<br>%{{y:.1f}} m<extra></extra>",
    ))

fig_ts.update_layout(
    title=dict(
        text="Distance to stop 822 over time – all methods",
        subtitle=dict(text="Overlapping lines = methods agree. Thick solid = WGS84 spheroid (most accurate)."),
        font=dict(size=15),
    ),
    xaxis=dict(title="snapshot_ts", showgrid=True, gridcolor="#e8e8e8"),
    yaxis=dict(title="distance (m)", showgrid=True, gridcolor="#e8e8e8"),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    template=TEMPLATE,
    font=FONT,
    hovermode="x unified",
    width=900,
    height=440,
)

fig_ts.show()

# %% Figure 3 – Pairwise delta heatmap + stats table
#
# Cell (A, B) = mean(A − B) in metres.
# Diagonal = 0 by definition.
# Symmetric: upper triangle = negative of lower.
# Colour diverges around 0: red = A overestimates vs B, blue = underestimates.

n = len(METHOD_KEYS)
mean_delta = [[0.0] * n for _ in range(n)]
max_delta   = [[0.0] * n for _ in range(n)]

for i, ka in enumerate(METHOD_KEYS):
    for j, kb in enumerate(METHOD_KEYS):
        diff = df[ka] - df[kb]
        mean_delta[i][j] = round(diff.mean(), 4)
        max_delta[i][j]  = round(diff.abs().max(), 4)

# Sub-figure: heatmap (mean) + heatmap (max abs)
fig_delta = make_subplots(
    rows=1, cols=2,
    subplot_titles=["Mean delta (m)  A − B", "Max |delta| (m)  |A − B|"],
    horizontal_spacing=0.14,
)

shared_kw = dict(
    x=METHOD_LABELS, y=METHOD_LABELS,
    colorscale="RdBu", zmid=0,
    text=[[f"{v:.3f}" for v in row] for row in mean_delta],
    texttemplate="%{text}",
    hovertemplate="A: %{y}<br>B: %{x}<br>mean(A−B): %{z:.4f} m<extra></extra>",
)

fig_delta.add_trace(
    go.Heatmap(z=mean_delta, showscale=True, colorbar=dict(x=0.44, thickness=10), **shared_kw),
    row=1, col=1,
)
fig_delta.add_trace(
    go.Heatmap(
        z=max_delta,
        x=METHOD_LABELS, y=METHOD_LABELS,
        colorscale="Oranges",
        text=[[f"{v:.3f}" for v in row] for row in max_delta],
        texttemplate="%{text}",
        hovertemplate="A: %{y}<br>B: %{x}<br>max|A−B|: %{z:.4f} m<extra></extra>",
        showscale=True,
        colorbar=dict(x=1.01, thickness=10),
    ),
    row=1, col=2,
)

fig_delta.update_layout(
    title=dict(
        text="Pairwise method deltas",
        subtitle=dict(text="Left: mean(A − B). Right: max absolute difference. Diagonal = 0."),
        font=dict(size=15),
    ),
    width=900,
    height=460,
    template=TEMPLATE,
    font=FONT,
)
fig_delta.update_xaxes(tickangle=25, tickfont=dict(size=10))
fig_delta.update_yaxes(tickfont=dict(size=10))

fig_delta.show()

# %% Summary stats (Polars)
summary = (
    df.select(METHOD_KEYS)
    .unpivot(variable_name="method", value_name="distance_m")
    .group_by("method")
    .agg(
        pl.col("distance_m").mean().round(2).alias("mean"),
        pl.col("distance_m").std().round(2).alias("std"),
        pl.col("distance_m").min().round(2).alias("min"),
        pl.col("distance_m").max().round(2).alias("max"),
    )
    .sort("mean")
)
print(summary)