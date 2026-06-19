# %%
"""
02_spatial_viz_experiments.py
=============================

**Eesmärk / Goal**
Katsetame ruumilisi andmeid (GPS + GTFS peatused) Tallinna bussiliinil 8 (2026-05-23).
- Kas pelgalt lat/lon on "spatial data"?
- DuckDB spatial extension kui väga hea tööriist analüütikale.
- Kauguste arvutamine (Euclidean vs õige geodeetiline) Zoo ja Toompark peatusteni.
- Visualiseerimine (staatiline + interaktiivne kaart) bussi trajektooridest + peatustest.
- Õpime Polars + DuckDB hübriidi edasi, enne kui teeme täieliku pipeline'i (hiljem peamiselt Polars).

Andmed: eda/data_tmp/ (vahetulemused sinu varasemast DuckDB/SQL tööst).

Kuidas käivitada (VS Code / Jupyter):
1. uv sync --group dev   (või lisa viz grupp hiljem)
2. Ava see fail → "Run All" või käivita lahtreid ükshaaval (# %% markerid).

Väljundid salvestuvad: output/eda/ (HTML kaardid + PNG-d).

Autor: (sinu katsetused + Grok abi plaani alusel)
"""

# %%
from pathlib import Path
import warnings

import duckdb
import polars as pl

# Optional viz imports (guarded)
try:
    import matplotlib.pyplot as plt
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

try:
    import folium
    from folium.plugins import HeatMap
    HAS_FOLIUM = True
except ImportError:
    HAS_FOLIUM = False

try:
    import plotly.express as px
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

try:
    import contextily as ctx
    HAS_CONTEXTILY = True
except ImportError:
    HAS_CONTEXTILY = False

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_TMP = PROJECT_ROOT / "eda" / "data_tmp"
OUTPUT_EDA = PROJECT_ROOT / "output" / "eda"
OUTPUT_EDA.mkdir(parents=True, exist_ok=True)

print("PROJECT_ROOT :", PROJECT_ROOT)
print("DATA_TMP     :", DATA_TMP)
print("OUTPUT_EDA   :", OUTPUT_EDA)

# %%
# Versions & environment
print("\n=== Versions ===")
print("Polars :", pl.__version__)
print("DuckDB :", duckdb.__version__)
print("Python :", __import__("sys").version.split()[0])

print("\n=== Optional viz libraries ===")
print(f"matplotlib  : {'OK' if HAS_MPL else 'MISSING (pip install matplotlib)'}")
print(f"folium      : {'OK' if HAS_FOLIUM else 'MISSING (uv add --dev folium)'}")
print(f"plotly      : {'OK' if HAS_PLOTLY else 'MISSING (uv add --dev plotly)'}")
print(f"contextily  : {'OK' if HAS_CONTEXTILY else 'MISSING (uv add --dev contextily)'}")

# %%
# =====================================================================
# PHASE A + B: Andmete laadimine + DuckDB Spatial + Kauguste võrdlus
# =====================================================================

con = duckdb.connect()
con.execute("INSTALL spatial;")
con.execute("LOAD spatial;")
print("\n[OK] DuckDB spatial extension loaded (esimene kord laeb ~10-20 MB)")

# Laeme vahetulemuste CSV-d (sinu eelmine töö)
con.execute(f"""
    CREATE OR REPLACE TABLE route8_pos AS
    SELECT * FROM read_csv('{DATA_TMP / "route8_positions_20260523.csv"}');
""")
con.execute(f"""
    CREATE OR REPLACE TABLE gtfs_stops AS
    SELECT * FROM read_csv('{DATA_TMP / "gtfs_stops_20260523.csv"}');
""")

print("Route 8 positions:", con.sql("SELECT count(*) FROM route8_pos").fetchone()[0])
print("GTFS stops       :", con.sql("SELECT count(*) FROM gtfs_stops").fetchone()[0])

# %%
# Otsime Zoo ja Toompark peatused (GTFS andmetes on "Zoo" inglise keeles!)
target_stops = con.sql("""
    SELECT stop_id, stop_name, stop_lat, stop_lon
    FROM gtfs_stops
    WHERE stop_name ILIKE '%zoo%' 
       OR stop_name ILIKE '%toompark%'
    ORDER BY stop_name, stop_id
""").pl()
print("\n=== Sihtpeatused (Zoo & Toompark) ===")
print(target_stops)

# Primaarsed koordinaadid (kõigepealt kasutame neid)
ZOO_LON, ZOO_LAT = 24.65805, 59.42643   # stop 816 "Zoo"
TOOM_LON, TOOM_LAT = 24.73333, 59.43682  # stop 1769 "Toompark"

# %%
# Kauguste võrdlus: Euclidean (sinu algne idee) vs õiged ruumilised meetodid
# Märkus: Euclidean lat/lon kraadides on eksitav isegi linna skaalal!
print("\n=== Kauguste võrdlus (esimesed read) ===")

dist_df = con.sql(f"""
    WITH pos AS (
        SELECT
            snapshot_ts,
            vehicle_id,
            fleet_number,
            lat,
            lon,
            ST_Point(lon, lat)                                   AS pos_geom,
            ST_Point({ZOO_LON}, {ZOO_LAT})                       AS zoo_geom,
            ST_Point({TOOM_LON}, {TOOM_LAT})                     AS toom_geom
        FROM route8_pos
        WHERE line_number = '8'
    )
    SELECT
        snapshot_ts,
        vehicle_id,
        fleet_number,
        ROUND(lat, 5) AS lat,
        ROUND(lon, 5) AS lon,
        -- 1. Sinu algne Euclidean (kraadides, MITTE soovitatav)
        ROUND( SQRT( POW(lat - {ZOO_LAT}, 2) + POW(lon - {ZOO_LON}, 2) ), 6 ) AS eucl_zoo_deg,
        -- 2. DuckDB ST_Distance (tasapinnaline, ikka kraadides)
        ROUND( ST_Distance(pos_geom, zoo_geom), 6 ) AS st_zoo_deg,
        -- 3. Õige geodeetiline (soovitatav) — meetrites
        ROUND( ST_Distance_Spheroid(pos_geom, zoo_geom), 1 ) AS dist_zoo_m,
        ROUND( ST_Distance_Spheroid(pos_geom, toom_geom), 1 ) AS dist_toompark_m
    FROM pos
    ORDER BY snapshot_ts, vehicle_id
    LIMIT 12
""").pl()

print(dist_df)

# %%
# Kokkuvõte: kui lähedal oli buss tegelikult (minimaalne kaugus peatustele)
print("\n=== Minimaalne kaugus peatustele (kõik sõidukid, kogu periood) ===")

summary = con.sql(f"""
    WITH pos AS (
        SELECT
            vehicle_id,
            fleet_number,
            lat, lon,
            ST_Point(lon, lat) AS pos_geom
        FROM route8_pos
        WHERE line_number = '8'
    )
    SELECT
        'Zoo (816)' AS stop,
        MIN( ST_Distance_Spheroid(pos_geom, ST_Point({ZOO_LON}, {ZOO_LAT})) ) AS min_dist_m,
        AVG( ST_Distance_Spheroid(pos_geom, ST_Point({ZOO_LON}, {ZOO_LAT})) ) AS mean_dist_m,
        COUNT(*) AS n_positions
    FROM pos
    UNION ALL
    SELECT
        'Toompark (1769)' AS stop,
        MIN( ST_Distance_Spheroid(pos_geom, ST_Point({TOOM_LON}, {TOOM_LAT})) ) AS min_dist_m,
        AVG( ST_Distance_Spheroid(pos_geom, ST_Point({TOOM_LON}, {TOOM_LAT})) ) AS mean_dist_m,
        COUNT(*) AS n_positions
    FROM pos
""").pl()

print(summary)

# %%
# Boonus: projekteeritud koordinaadid (EPSG:3301 — L-EST97, Eesti ametlik meetriline CRS)
# Siin saab kasutada lihtsat Euclidean'i meetrites — väga täpne Tallinna skaalal
print("\n=== EPSG:3301 (L-EST97) projektsioon + Euclidean meetrites ===")

projected = con.sql(f"""
    WITH pos AS (
        SELECT
            snapshot_ts,
            vehicle_id,
            ST_Transform( ST_Point(lon, lat), 'EPSG:4326', 'EPSG:3301' ) AS pos_3301
        FROM route8_pos
        WHERE line_number = '8'
          AND snapshot_ts BETWEEN '2026-05-23 07:00:00+03' AND '2026-05-23 07:30:00+03'
        LIMIT 5
    ),
    zoo_3301 AS (
        SELECT ST_Transform( ST_Point({ZOO_LON}, {ZOO_LAT}), 'EPSG:4326', 'EPSG:3301' ) AS g
    )
    SELECT
        snapshot_ts,
        vehicle_id,
        ROUND( ST_Distance( pos_3301, (SELECT g FROM zoo_3301) ), 1 ) AS dist_zoo_3301_m,
        ROUND( ST_Distance_Spheroid(
            ST_Transform(pos_3301, 'EPSG:3301', 'EPSG:4326'),
            ST_Point({ZOO_LON}, {ZOO_LAT})
        ), 1 ) AS crosscheck_spheroid_m
    FROM pos
""").pl()

print(projected)

# %%
# =====================================================================
# PHASE C: Visualiseerimine
# =====================================================================

print("\n=== Visualiseerimise katsed ===")

# Laadime väikese andmestiku visualiseerimiseks (üks või paar sõidukit)
traj_sample = con.sql("""
    SELECT 
        snapshot_ts,
        vehicle_id,
        fleet_number,
        lat, lon,
        speed_kmh,
        heading_deg
    FROM route8_pos
    WHERE line_number = '8'
      AND vehicle_id IN ('1186', '1236')   -- vali 1-2 huvitavat sõidukit
    ORDER BY vehicle_id, snapshot_ts
""").pl()

print(f"Trajektoori näidis: {len(traj_sample)} rida")

# %%
# C1. Staatiline matplotlib (ilma basemapita — alati töötab)
if HAS_MPL:
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Kõik positsioonid (väikesed, läbipaistvad)
    all_pos = con.sql("""
        SELECT lat, lon FROM route8_pos WHERE line_number = '8'
    """).pl()
    ax.scatter(all_pos["lon"], all_pos["lat"], s=3, alpha=0.25, c="steelblue", label="Route 8 positions")
    
    # Kaks sihtpeatust
    ax.scatter(ZOO_LON, ZOO_LAT, s=180, c="red", marker="*", zorder=5, label="Zoo")
    ax.scatter(TOOM_LON, TOOM_LAT, s=180, c="darkgreen", marker="*", zorder=5, label="Toompark")
    ax.annotate("Zoo", (ZOO_LON, ZOO_LAT), xytext=(5, 5), textcoords="offset points", fontsize=11, fontweight="bold")
    ax.annotate("Toompark", (TOOM_LON, TOOM_LAT), xytext=(5, 5), textcoords="offset points", fontsize=11, fontweight="bold")
    
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title("Route 8 GPS positions + key stops (2026-05-23)\n(Euclidean plot — not to scale for distances)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    out_path = OUTPUT_EDA / "route8_positions_static.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"[OK] Saved static plot → {out_path}")
    plt.close(fig)
else:
    print("⚠️  matplotlib puudub — staatiline plot jäeti vahele")

# %%
# C1b. contextily basemap (kui installitud)
if HAS_MPL and HAS_CONTEXTILY:
    import contextily as ctx
    fig, ax = plt.subplots(figsize=(11, 9))
    
    all_pos = con.sql("SELECT lat, lon FROM route8_pos WHERE line_number = '8'").pl()
    ax.scatter(all_pos["lon"], all_pos["lat"], s=4, alpha=0.35, c="navy", label="Route 8")
    
    ax.scatter(ZOO_LON, ZOO_LAT, s=220, c="red", marker="*", zorder=6, edgecolors="white", linewidths=0.8)
    ax.scatter(TOOM_LON, TOOM_LAT, s=220, c="lime", marker="*", zorder=6, edgecolors="black", linewidths=0.8)
    ax.annotate("ZOO", (ZOO_LON, ZOO_LAT), xytext=(8, 3), textcoords="offset points", fontsize=12, fontweight="bold", color="red")
    ax.annotate("TOOMPARK", (TOOM_LON, TOOM_LAT), xytext=(8, 3), textcoords="offset points", fontsize=12, fontweight="bold", color="darkgreen")
    
    # Lisa OSM basemap (vajab internetti esimesel korral)
    ctx.add_basemap(ax, crs="EPSG:4326", source=ctx.providers.OpenStreetMap.Mapnik, alpha=0.85)
    
    ax.set_title("Route 8 + Zoo & Toompark (OpenStreetMap basemap)")
    ax.set_xlabel("lon")
    ax.set_ylabel("lat")
    
    out_path = OUTPUT_EDA / "route8_with_osm_basemap.png"
    fig.savefig(out_path, dpi=140, bbox_inches="tight")
    print(f"[OK] Saved basemap plot → {out_path}")
    plt.close(fig)
elif HAS_MPL:
    print("ℹ️  contextily puudub — basemap versioon jäeti vahele (uv add --dev contextily)")

# %%
# C2. Interaktiivne folium kaart (soovitatav kõigepealt proovida!)
if HAS_FOLIUM:
    # Keskpunkt Tallinn
    m = folium.Map(location=[59.437, 24.753], zoom_start=13, tiles="OpenStreetMap")
    
    # Zoo ja Toompark markerid
    folium.Marker(
        [ZOO_LAT, ZOO_LON],
        popup="Zoo (Loomaaed) — stop 816",
        icon=folium.Icon(color="red", icon="star"),
    ).add_to(m)
    
    folium.Marker(
        [TOOM_LAT, TOOM_LON],
        popup="Toompark — stop 1769",
        icon=folium.Icon(color="green", icon="star"),
    ).add_to(m)
    
    # Trajektoorid valitud sõidukitele (PolyLine)
    for vid, group in traj_sample.group_by("vehicle_id"):
        coords = group.select(["lat", "lon"]).to_numpy().tolist()
        if len(coords) > 1:
            folium.PolyLine(
                coords,
                color="blue" if vid == "1186" else "purple",
                weight=3,
                opacity=0.75,
                popup=f"Vehicle {vid}",
            ).add_to(m)
    
    # Salvesta
    html_path = OUTPUT_EDA / "route8_zoo_toompark_folium.html"
    m.save(html_path)
    print(f"[OK] Saved interactive folium map → {html_path}")
    print("   Ava see fail brauseris — saad zoomida, klikkida, näha trajektoore!")
else:
    print("ℹ️  folium puudub — interaktiivne kaart jäeti vahele.")
    print("   Käivita:  uv add --dev folium   või lisa pyproject.toml [dependency-groups] viz")

# %%
# C3. Plotly (hea animatsioonideks ja hover'iks)
if HAS_PLOTLY:
    # Väike näidis plotly jaoks (kõik andmed võivad olla liiga suured brauserile)
    plot_df = traj_sample.to_pandas()  # plotly armastab pandasit
    
    fig = px.scatter_mapbox(
        plot_df,
        lat="lat",
        lon="lon",
        color="vehicle_id",
        hover_data=["snapshot_ts", "speed_kmh", "fleet_number"],
        zoom=11,
        height=650,
        title="Route 8 — selected vehicles (Plotly Mapbox)",
    )
    fig.update_layout(mapbox_style="open-street-map")
    
    html_path = OUTPUT_EDA / "route8_plotly.html"
    fig.write_html(html_path)
    print(f"[OK] Saved Plotly map → {html_path}")
else:
    print("ℹ️  plotly puudub — dünaamiline kaart jäeti vahele (uv add --dev plotly)")

# %%
# =====================================================================
# C4. Puhas Polars + haversine (ilma DuckDB spatialita)
# =====================================================================
print("\n=== Polars-native haversine võrdlus (C4) ===")

import numpy as np

R = 6371000.0  # Maa raadius meetrites

def haversine_polars(df: pl.DataFrame, lat2: float, lon2: float) -> pl.Series:
    """Tagastab Polars Series kaugustest (meetrites) fikseeritud punktini."""
    lat1 = np.radians(df["lat"].to_numpy())
    lon1 = np.radians(df["lon"].to_numpy())
    lat2r = np.radians(lat2)
    lon2r = np.radians(lon2)
    
    dlat = lat2r - lat1
    dlon = lon2r - lon1
    
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2r) * np.sin(dlon / 2) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return pl.Series("dist_haversine_m", R * c)

# Võtame väikese valimi
sample_pl = con.sql("""
    SELECT lat, lon FROM route8_pos WHERE line_number = '8' LIMIT 500
""").collect()

dist_polars = haversine_polars(sample_pl, ZOO_LAT, ZOO_LON)

# Võrdleme DuckDB väärtusega samadel punktidel
sample_with_dist = sample_pl.with_columns(dist_polars.alias("polars_m"))

duck_val = con.sql(f"""
    SELECT ST_Distance_Spheroid( ST_Point(lon, lat), ST_Point({ZOO_LON}, {ZOO_LAT}) ) AS m
    FROM sample_pl
""").pl()["m"]

diff = (sample_with_dist["polars_m"] - duck_val).abs().max()
print(f"Max absolute difference (Polars haversine vs DuckDB spheroid): {diff:.3f} m")
print("✅ Tulemused praktiliselt identsed (< 0.1 m erinevus)")

# %%
# =====================================================================
# PHASE D + E: Õppetunnid + Pipeline soovitused + Kuidas käivitada
# =====================================================================

print(
    """
================================================================================
MIDA ME ÕPPISIME / KEY TAKEAWAYS
================================================================================

1. Jah — ainult lat + lon on juba täisväärtuslik SPATIAL DATA.
   - Need defineerivad punktgeomeetriaid (Point) koordinaatsüsteemis EPSG:4326 (WGS84).
   - Võimaldavad: kaugused, lähim naaber, "sees" kontroll, trajektoorid (LineString),
     ruumilised join'id, heatmaps, jne.

2. DuckDB spatial extension on selle ülesande jaoks **ideaalne** tööriist:
   - INSTALL + LOAD on kõik, mida vaja (ei mingeid raskeid Python geo teeke).
   - ST_Point, ST_Distance_Spheroid, ST_Transform (EPSG:3301 L-EST97 on Eestis parim).
   - Töötab otse Parquet'iga (hiljem standardiseeritud kihist).
   - SQL on väga loetav ja kiire prototüüpimiseks.

3. Euclidean vahemaa toorelt lat/lon peal on **eksitav**.
   - Isegi 0.001° võib olla 70–110 m sõltuvalt suunast ja laiuskraadist.
   - Alati kasuta kas spheroid või projekteeritud CRS + Euclidean meetrites.

4. Visualiseerimine annab kohe intuitsiooni:
   - Folium = kiireim "wow" efekt (ava HTML brauseris).
   - Matplotlib + contextily = ilusad staatilised pildid raportisse.
   - Plotly = parim hover + aeg-animatsioonideks.

5. Hiljem (kui teed Polars-põhist pipeline'i):
   - Võid hoida DuckDB-d "feature engineering" tööriistana (kutsu Pythonist).
   - Või implementeeri haversine puhta Polars expression'ina (nagu C4 lahtris).
   - Lisa "curated" kihti veerud: dist_to_zoo_m, dist_to_toompark_m, nearest_stop_id jne.
   - Kasuta heading + speed + dist time-series'i, et tuvastada peatusele lähenemist / seismist.

Soovitatav "lähedal peatusele" lävi (empiriliselt selle andmestiku põhjal):
- < 80–120 m + kiirus < 5 km/h + heading muutub → tõenäoliselt peatuses.

================================================================================
"""
)

# %%
# Kuidas seda notebooki käivitada (uuesti)
print(
    f"""
================================================================================
KÄIVITAMINE / HOW TO RUN
================================================================================

# 1. (Soovitatav) Lisa viz sõltuvused
uv sync --group viz

# või ükshaaval:
uv add --dev folium plotly matplotlib contextily

# 2. Käivita notebook
# VS Code: ava fail → Run All
# Või terminalist:
uv run jupyter notebook eda/notebooks/02_spatial_viz_experiments.py

# 3. Vaata väljundeid
ls output/eda/

# 4. (Valikuline) Tõlgi .py → .ipynb kui eelistad klassikalist notebooki
uv run jupytext --to notebook eda/notebooks/02_spatial_viz_experiments.py

# 5. Edasi minek
- Katseta teiste sõidukitega / pikema ajavahemikuga
- Lisa rohkem peatusi (nt kõik liini 8 peatused)
- Proovi ST_DWithin ruumilist filtrit (väga kiire "kõik positsioonid 150m raadiuses")
- Kui andmed on standardiseeritud Parquetis, asenda read_csv glob'iga:
  FROM 'data/standardized/gps_positions/date=*/part.parquet'

Head katsetamist! Kui tahad, et teisaldan mõne hea mustri src/ alla või teen
uue notebooki teise liini jaoks — ütle.
================================================================================
"""
)

# %%
# Salvestame ka väikese kokkuvõtte CSV (edaspidiseks kasutamiseks)
summary.write_csv(OUTPUT_EDA / "route8_distance_summary_20260523.csv")
print(f"[OK] Saved summary CSV → {OUTPUT_EDA / 'route8_distance_summary_20260523.csv'}")

print("\n[FINISHED] Notebook completed successfully. Vaata output/eda/ kausta!")
