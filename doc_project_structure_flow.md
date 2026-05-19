# Data Flow & Project Structure

**Author**: Jüri Vinnal  
**Status**: Living document — describes raw design ideas, may, not necessarily current implementation state.  
**Current mindset & fluidity:**
These are just the current working guidelines for a file-based Python setup. Nothing is rigidly decided. If the data scale grows to require DuckDB, PostgreSQL, or proper cloud object storage, the physical backend will change. If I find a cleaner structural approach tomorrow, I'll replace this one. The main goal is just keeping the execution boundaries clean so swapping things out later isn't a headache.  
[**Source: GPS notes:**](docs/gps_readme.md)  
[**Source: GTFS notes:**](docs/gtfs_readme.md)  

---

## Table of Contents

- [Data Flow \& Project Structure](#data-flow--project-structure)
  - [Table of Contents](#table-of-contents)
  - [Part 1 — Context](#part-1--context)
    - [1.1 Project purpose](#11-project-purpose)
    - [1.2 Use case](#12-use-case)
    - [1.3 Design goals](#13-design-goals)
    - [1.4 Evolution of Architectural Thinking](#14-evolution-of-architectural-thinking)
  - [2.Modules \& Storage Layers](#2modules--storage-layers)
    - [2.1. Modules](#21-modules)
    - [2.2. Storage Layers](#22-storage-layers)
  - [3. GPS Data Flow](#3-gps-data-flow)
    - [3.1. LANDING \& RAW → `data/raw/source=gps/date=YYYY-MM-DD/`](#31-landing--raw--datarawsourcegpsdateyyyy-mm-dd)
    - [3.2. STANDARDIZED → `data/standardized/gps_positions.parquet`](#32-standardized--datastandardizedgps_positionsparquet)
    - [3.3. INTERMEDIATE → `data/intermediate/route8_positions.parquet`](#33-intermediate--dataintermediateroute8_positionsparquet)
    - [3.4. INTERMEDIATE → `data/intermediate/stop_distances.parquet`](#34-intermediate--dataintermediatestop_distancesparquet)
    - [3.5. INTERMEDIATE → `data/intermediate/stop_events.parquet`](#35-intermediate--dataintermediatestop_eventsparquet)
  - [4. GTFS Data Flow](#4-gtfs-data-flow)
    - [4.1. LANDING → `data/landing/source=gtfs/date=YYYY-MM-DD/gtfs_YYYYMMDD.zip`](#41-landing--datalandingsourcegtfsdateyyyy-mm-ddgtfs_yyyymmddzip)
    - [4.2. RAW → `data/raw/source=gtfs/date=YYYY-MM-DD/`](#42-raw--datarawsourcegtfsdateyyyy-mm-dd)
    - [4.3. STANDARDIZED → `data/standardized/gtfs_*.parquet`](#43-standardized--datastandardizedgtfs_parquet)
    - [4.4. CURATED → `data/curated/schedule_baseline.parquet`](#44-curated--datacuratedschedule_baselineparquet)
  - [5. Convergence: GPS + GTFS → Curated](#5-convergence-gps--gtfs--curated)
    - [5.1. CURATED → `data/curated/observed_trips.parquet`](#51-curated--datacuratedobserved_tripsparquet)
  - [6. Analytics](#6-analytics)
  - [7. Complete Flow Summary](#7-complete-flow-summary)
  - [8. Code Structure](#8-code-structure)

## Part 1 — Context

### 1.1 Project purpose

The `transit-delay-analytics` project constitutes a scalable, configuration-driven data engineering pipeline and stochastic modelling framework to model commute delay probabilities. It has two explicit goals that coexist deliberately.

The **immediate goal** is a data product: a probability curve showing the likelihood of arriving late to a 09:05 meeting, depending on when Rita leaves home. This is the [RMK Data Team Internship 2025 challenge](docs/rmk_test_challenge_2025.md).

The **longer-term goal** is a reusable boilerplate for data engineering and analytics projects of this class. The architecture is intentionally more considered than the single use case requires — the extra setup cost is paid back when the second use case is added. It strikes the **best balance between rigorous data engineering standards and Python's flexibility**.

The system is designed around the principles of a **Data Lakehouse architecture** scaled for local or containerized execution. It strictly decouples data ingestion, deterministic transformations, and downstream analytical consumption into isolated computational modules. This separation of concerns ensures that the framework can be seamlessly extended without fundamentally altering the core pipeline.

While it borrows some best practices from enterprise systems and some good recommendations from the [RMK Data Team's](https://koodivaramu.eesti.ee/rmk/datateam/internship), it remains a **pragmatic, personal-scale project**, avoiding the trap of tempting over-engineering.

### 1.2 Use case

Rita works at the RMK Tallinn office. She takes bus 8 from Zoo to Toompark every weekday morning. She has a meeting at **09:05 sharp**.

| Stage                     | Duration    |
| ------------------------- | ----------- |
| Home → Zoo (walk)         | 300 s fixed |
| Zoo → Toompark (bus)      | varies      |
| Toompark → meeting (walk) | 240 s fixed |

The question is: **if Rita leaves home at time R, what is the probability she arrives after 09:05?**

Neither the bus arrival time at Zoo nor the drive duration to Toompark is fixed. Both must be inferred from observed GPS data. This is the core modelling problem.

The deliverable is a probability curve — probability of being late on the y-axis, leave-home time on the x-axis — published as a plot in the repository README.

Reference: [RMK Data Team Internship 2025 challenge](https://koodivaramu.eesti.ee/rmk/datateam/internship/-/blob/main/2025/test_challenge.md)
[Recommended reading:](docs/rmk_feedback_2025.md)

### 1.3 Design goals

- **Modular Separation of Concerns:** The system is strictly delineated into extraction (`src/transit_delay_analytics/ingestion/`), transformation (`src/transit_delay_analytics/models/`), and consumption (`src/transit_delay_analytics/analytics/`) modules. Downstream analytics must not influence upstream data collection.

- **Configuration-driven execution.** Runtime behaviour is controlled through configuration files, not code changes. Data source URLs, ingestion windows, and scheduled intervals live in `config/pipeline.toml`. Changing what the daemon collects and when does not require editing Python.

- **CLI-first design & Docker-friendly design.** Every pipeline stage is reachable by a named CLI command. This makes the system scriptable, composable, and easy to run in Docker scheduled with a cron job. There is no "run everything" notebook that must be executed in the right cell order.

- **Dependencies**: Arhitektuuri tuumakomponentide (nt konfiguratsioonide lugemine, logimine ja süsteemi interaktsioonid) jaoks on mõistlik hoida sõltuvused minimaalsed ja kasutada sisseehitatud. Kuigi Pythoni standardteek on rikkalik, on andmeteaduse ja andmeinseneeria kuldreegliks "ära leiuta jalgratast uuesti". Python on muutunud andmeinseneeria vaikekeeleks just tänu oma võimsatele kolmandate osapoolte teekidele (nagu Pandas, NumPy, SQLAlchemy jne), mis pakuvad optimeeritud ja testitud lahendusi andmetöötluseks. Kuna eesmärk on luua taaskasutatav arhitektuur (reusable boilerplate), mis oleks kooskõlas andmeinseneeria standarditega, on väga mõistlik kohe kaasata valdkonna standardteegid (näiteks `pandas` andmete töötlemiseks, failide lugemiseks/kirjutamiseks

- **Preserve raw data.** Raw input files are never modified after download. Transformation bugs are fixable by rerunning the transformation — not by re-querying a live API. Source systems routinely purge history; a local raw archive prevents permanent data loss.

- **Idempotency.** Running any pipeline stage twice produces the same result as running it once. Ingestion skips files that already exist. Transformation overwrites its output partition deterministically. Analysis uses a stored random seed when reproducibility is required.

- **Human-readable intuitive and testable codebase.** Code is optimised for the person reading it, not for the machine running it. Functions have single responsibilities, type hints are used consistently, and docstrings explain intent. The reviewer should be able to understand any function without reading the code that calls it.

- **Honest documentation.** Assumptions, limitations, and open questions are documented explicitly. This document states what is planned, what is implemented, and what is unknown.

### 1.4 Evolution of Architectural Thinking

**Inspirations and borrowed concepts:**

- **dbt / SQLMesh:** I borrowed the semantic layering concept and the strict rule that transformations are "dataset definitions" rather than "operations" (i.e., 1 script = 1 dataset). However, I dropped the SQL-centric terminology ("marts", "staging", "ephemeral") because it doesn't fit well in a local Python/Polars file ecosystem.
- **Medallion Architecture (Databricks):** Borrowed the data maturity lifecycle (Bronze/Silver/Gold), but expanded it to 7 layers (ingestion + transformation = 5 layers). A single "Silver" layer gets too messy in Python when handling extraction, type casting, and complex joins all at once.
- **Data Lakehouse:** Using Hive-style directory partitioning (`source=.../date=YYYY-MM-DD/`) even on the local filesystem. It makes datasets self-describing, allows query engines to infer partitions, and handles idempotent backfilling safely.

**Log:**

1. **The Analytics Boundary Problem**  
   Monte Carlo simulation (and any statistical inference) is not a data transformation step — it is a downstream mathematical consumer of curated business entities. Treating it as part of the main pipeline created an unnatural coupling and made experimentation cumbersome.

2. **Terminology Mismatch**  
   Terms like "marts" (Kimball dimensional modelling) or "staging" (often ephemeral in dbt) felt forced in a world where every layer is physically persisted for reproducibility and auditability. We needed terminology that better reflects the reality of persistent files and Polars-based transformations.

3. **The Unpacking Concern**  
   Handling GTFS `.zip` archives (download + unpack) is fundamentally different from semantic cleaning and business logic. Mixing these responsibilities blurred layer boundaries. ==Hetkel otsustatud, et GTFS `.zip` unpack toimub models/standardized kihis, mitte ingestion, et hoida pipeline lihtne.==

---

## 2.Modules & Storage Layers

### 2.1. Modules

| Domain           | Industry Inspiration    | Responsibility                                                                                                                            | Deployment      |
| :--------------- | :---------------------- | :---------------------------------------------------------------------------------------------------------------------------------------- | :-------------- |
| **`ingestion/`** | *Fivetran / Airbyte*    | **Extract & Load (EL).** Connects to external APIs, downloads payloads, and unpacks them. Strictly ignorant of business logic or schemas. | Daemon (Docker) |
| **`models/`**    | *dbt / SQLMesh*         | **Data Pipeline (Transform).** The engineering core. Casts types, standardizes, joins GPS to GTFS, and infers physical stop events.       | CLI Batch       |
| **`analytics/`** | *Jupyter / R / Tableau* | **Downstream Consumer.** Reads curated data to run stochastic simulations and produce visual artefacts.                                   | CLI Ad-hoc      |

**Analytics is a downstream consumer, not part of the pipeline.** If Monte Carlo were replaced by a parametric model or a spreadsheet, the pipeline (`ingestion/` + `models/`) would not change.

### 2.2. Storage Layers

```sh
data/
  raw/           ← ingestion    original downloaded files (immutable)
  ─────────────────────────────────────────────────────────────
  standardized/  ← models     typed, cleaned, one source at a time, no joins
  intermediate/  ← models     cross-source joins, distance calculations, event inference
  curated/       ← models     analysis-ready entities, stable downstream contract
  ─────────────────────────────────────────────────────────────
  analytics/   ← analytics    simulation intermediate results
  output/      ← analytics    final artefacts for humans (plots, CSV tables)
```

**Naming rule:** One script → one output file, same name.  
`models/intermediate/stop_events.py` → `data/intermediate/stop_events.parquet`

---

## 3. GPS Data Flow

**Business context:** GPS gives a fleet-wide snapshot every ~30 s. One file = ALL Tallinn vehicles at one moment. We must infer bus 8 stop events from these position snapshots.

---

### 3.1. LANDING & RAW → `data/raw/source=gps/date=YYYY-MM-DD/`

**Module:** `ingestion/gps.py`

```txt
API poll every 30 s  →  data/raw/gps/date=2026-05-15/gps_20260515_073000.txt
                         data/raw/gps/date=2026-05-15/gps_20260515_073030.txt
                         ...
```

**Why:** GPS has no historical endpoint. If we miss a collection window it is gone permanently. Raw files are immutable — reprocessing is always possible from here.

**Format:** Headerless CSV-like text, 10 columns, coordinates × 1,000,000.

| Property         | Value                                                    |
| ---------------- | -------------------------------------------------------- |
| URL              | `https://transport.tallinn.ee/readfile.php?name=gps.txt` |
| Format           | Headerless CSV-like text                                 |
| Update frequency | Every ~30 seconds                                        |
| Availability     | Only while vehicles are actively in service              |

One file contains a snapshot of **all Tallinn vehicles at one moment in time**. It is not a history. Each request returns the current state of the entire fleet.

**Verified schema** (official documentation is inaccurate; this table reflects actual payload analysis):

| # | Column           | Type  | Notes                                    |
| - | ---------------- | ----- | ---------------------------------------- |
| 1 | `transport_type` | int   | 1=trolleybus, 2=bus, 3=tram, 7=night bus |
| 2 | `line_number`    | str   | e.g. `"8"`, `"18A"`                      |
| 3 | `longitude_raw`  | int   | Longitude × 1,000,000 (WGS84)            |
| 4 | `latitude_raw`   | int   | Latitude × 1,000,000 (WGS84)             |
| 5 | `speed_kmh`      | int?  | Empty string when unavailable            |
| 6 | `heading_deg`    | int?  | `999` when unavailable                   |
| 7 | `vehicle_id`     | str   | Internal vehicle identifier              |
| 8 | `floor_type`     | str   | `"Z"` = low-floor, `"false"` = unknown   |
| 9 | `fleet_number`   | str   | Physical vehicle serial number           |
|10 | `destination`    | str   | Destination stop name                    |

**Limitations:**

- Timestamps reflect pipeline collection time, not device time. Clock skew between device and server is unknown.
- Coordinates require division by 1,000,000 before use.
- A snapshot captured just before or just after a stop means the arrival time is only known within a ±30 second window.
- No historical data is available. Missed collection windows cannot be backfilled.

---

### 3.2. STANDARDIZED → `data/standardized/gps_positions.parquet`

**Script:** `models/standardized/gps/gps_positions.py`  
**Business question answered:** *"Where was every vehicle in Tallinn at each recorded moment?"*

**What happens:** Concatenate all snapshots for a date into one table. Parse columns, assign correct types, divide coordinates by 1,000,000, replace sentinel values (empty speed → `None`, heading 999 → `None`). Add `snapshot_ts` from filename. No filtering.

**Why not filter here:** Standardized mirrors the source 1:1. Filtering to route 8 is a business decision, not a parsing decision.

| Column           | Type           | Notes                       |
| ---------------- | -------------- | --------------------------- |
| `snapshot_ts`    | datetime (UTC) | Parsed from filename        |
| `transport_type` | int            |                             |
| `line_number`    | str            |                             |
| `lon`            | float          | `longitude_raw / 1_000_000` |
| `lat`            | float          | `latitude_raw / 1_000_000`  |
| `speed_kmh`      | int?           | None when unavailable       |
| `heading_deg`    | int?           | None when unavailable       |
| `vehicle_id`     | str            |                             |
| `floor_type`     | str            |                             |
| `fleet_number`   | str            |                             |
| `destination`    | str            |                             |

---

### 3.3. INTERMEDIATE → `data/intermediate/route8_positions.parquet`

**Script:** `models/intermediate/route8_positions.py`  
**Input:** `data/standardized/gps_positions.parquet`  
**Business question answered:** *"Where was each route 8 bus at each moment during the collection window?"*

**What happens:** Filter `transport_type == 2` and `line_number == "8"`. Drop all other vehicles.

**Why intermediate, not standardized:** Filtering to route 8 reflects a business decision (we care about route 8), not a technical parsing step. Standardized should have no opinion about which route matters.

Schema: same as `gps_positions.parquet`, fewer rows.

---

### 3.4. INTERMEDIATE → `data/intermediate/stop_distances.parquet`

**Script:** `models/intermediate/stop_distances.py`  
**Input:** `route8_positions.parquet` + `data/standardized/gtfs_stops.parquet`  
**Business question answered:** *"How far was each route 8 bus from Zoo and Toompark at each moment?"*

**What happens:** For each route 8 position, compute Euclidean-approximation distance to Zoo and Toompark coordinates (from GTFS `stops.txt`). **This is the first cross-source join in the pipeline** — GPS and GTFS data meet here.

**Why Euclidean and not Haversine:** At distances of 30–75 m, the Euclidean flat-surface approximation introduces negligible error (confirmed by Syrjärinne 2016 and RMK 2025 feedback). Simpler code, equivalent precision.

$$d_{lat} = R \cdot (lat_{bus} - lat_{stop})$$
$$d_{lon} = R \cdot \cos(lat_{bus}) \cdot (lon_{bus} - lon_{stop})$$
$$d = \sqrt{d_{lat}^2 + d_{lon}^2}$$

| Column                | Type           | Notes                     |
| --------------------- | -------------- | ------------------------- |
| `snapshot_ts`         | datetime (UTC) |                           |
| `vehicle_id`          | str            |                           |
| `zoo_distance_m`      | float          | Distance to Zoo stop      |
| `toompark_distance_m` | float          | Distance to Toompark stop |

---

### 3.5. INTERMEDIATE → `data/intermediate/stop_events.parquet`

**Script:** `models/intermediate/stop_events.py`  
**Input:** `data/intermediate/stop_distances.parquet`  
**Business question answered:** *"At what time did bus 213 arrive at Zoo on 2026-05-15?"*

**What happens:** For each vehicle, scan distance time series. When distance drops below `STOP_RADIUS_M` (configured, default 40 m) → `arrived`. When it rises above again → `departed`. Arrival timestamp = first snapshot inside radius. Departure timestamp = last snapshot before leaving.

**Why curated would be wrong for this:** Stop events are inferred, not parsed. They contain business meaning ("arrived") that does not exist in raw GPS data. But they are not yet joined with GTFS — so they belong in intermediate, one step before the final curated entity.

| Column       | Type           | Notes                       |
| ------------ | -------------- | --------------------------- |
| `vehicle_id` | str            |                             |
| `stop_name`  | str            | `"Zoo"` or `"Toompark"`     |
| `event_ts`   | datetime (UTC) |                             |
| `event_type` | str            | `"arrived"` or `"departed"` |
| `quality`    | str            | See quality flags below     |

**Quality flags:**

| Flag                  | Meaning                                                     |
| --------------------- | ----------------------------------------------------------- |
| `ok`                  | Clean entry and exit within radius                          |
| `missing_origin`      | Toompark seen but no Zoo arrival found for same vehicle/day |
| `missing_destination` | Zoo seen but no Toompark arrival found                      |
| `large_gap`           | Consecutive snapshots > 120 s apart around the event        |
| `outside_window`      | Event outside 07:00–09:30 collection window                 |

---

## 4. GTFS Data Flow

**Business context:** GTFS is the official timetable. Updated daily at 04:00. Gives us stop coordinates and scheduled departure times — the planned baseline we compare against GPS reality.

| Property         | Value                                         |
| ---------------- | --------------------------------------------- |
| URL              | `https://transport.tallinn.ee/data/gtfs.zip`  |
| Format           | ZIP archive containing CSV files              |
| Update frequency | Daily, typically around 04:00                 |

GTFS provides stop coordinates and the scheduled timetable. It does not provide what buses actually did — that comes from GPS.

**Files relevant to this use case:**

| File                 | Purpose                                             |
| -------------------- | --------------------------------------------------- |
| `stops.txt`          | Stop names, IDs, and exact WGS84 coordinates        |
| `routes.txt`         | Route metadata — used to identify route 8           |
| `trips.txt`          | Individual scheduled journeys per route             |
| `stop_times.txt`     | Scheduled arrival and departure time per stop/trip  |
| `calendar.txt`       | Regular weekly service pattern                      |
| `calendar_dates.txt` | Service exceptions (holidays, special events)       |

**Limitations:**

- Scheduled times are rounded to the nearest minute. This is imprecise for statistical modelling.
- The schedule represents what was planned, not what happened. GPS data is the ground truth.

---

### 4.1. LANDING → `data/landing/source=gtfs/date=YYYY-MM-DD/gtfs_YYYYMMDD.zip`

**Module:** `ingestion/gtfs.py`  
**Why landing ≠ raw for GTFS:** GTFS arrives as a zip archive. The pipeline never works with zip files — that is ingestion's problem to solve. Unzipping is part of the load step.

---

### 4.2. RAW → `data/raw/source=gtfs/date=YYYY-MM-DD/`

**Module:** `ingestion/gtfs.py` (same script, second step)

```sh
stops.txt       ← stop IDs, names, WGS84 coordinates
routes.txt      ← route IDs, names
trips.txt       ← trip IDs per route, calendar service IDs
stop_times.txt  ← scheduled arrival/departure per stop per trip
calendar.txt    ← weekday service patterns
```

**Why preserve raw CSV:** GTFS parsing logic will evolve. Having the original CSV allows reprocessing without re-downloading.

---

### 4.3. STANDARDIZED → `data/standardized/gtfs_*.parquet`

One script per source file. Parses CSV, assigns types, standardises column names to `snake_case`. No joins. No filtering.

| Script               | Output                    | Business question                          |
| -------------------- | ------------------------- | ------------------------------------------ |
| `gtfs_stops.py`      | `gtfs_stops.parquet`      | Where exactly is each stop?                |
| `gtfs_routes.py`     | `gtfs_routes.parquet`     | What routes exist?                         |
| `gtfs_trips.py`      | `gtfs_trips.parquet`      | What individual journeys are scheduled?    |
| `gtfs_stop_times.py` | `gtfs_stop_times.parquet` | When should each trip arrive at each stop? |

Key columns in `gtfs_stops.parquet`:

| Column      | Type  | Notes                      |
| ----------- | ----- | -------------------------- |
| `stop_id`   | str   | Unique identifier          |
| `stop_name` | str   | e.g. `"Zoo"`, `"Toompark"` |
| `stop_lat`  | float | WGS84                      |
| `stop_lon`  | float | WGS84                      |

---

### 4.4. CURATED → `data/curated/schedule_baseline.parquet`

**Script:** `models/curated/schedule_baseline.py`  
**Input:** `gtfs_trips.parquet` + `gtfs_stop_times.parquet` + `gtfs_routes.parquet` + `gtfs_stops.parquet`  
**Business question answered:** *"According to the official timetable, when should bus 8 depart Zoo?"*

**What happens:** Join trips → stop_times → routes → stops. Filter to route 8 and target stops Zoo and Toompark. One row per scheduled trip × stop.

| Column                | Type | Notes                             |
| --------------------- | ---- | --------------------------------- |
| `trip_id`             | str  |                                   |
| `service_date`        | date | Weekday service based on calendar |
| `stop_name`           | str  | `"Zoo"` or `"Toompark"`           |
| `scheduled_arrival`   | time | From GTFS `stop_times.txt`        |
| `scheduled_departure` | time | From GTFS `stop_times.txt`        |

**Known limitation:** GTFS times are rounded to the nearest minute. Precise delay comparisons are only accurate to ±60 s.

---

## 5. Convergence: GPS + GTFS → Curated

### 5.1. CURATED → `data/curated/observed_trips.parquet`

**Script:** `models/curated/observed_trips.py`  
**Input:** `data/intermediate/stop_events.parquet` + `data/curated/schedule_baseline.parquet`  
**Business question answered:** *"How long did bus 8 actually take from Zoo to Toompark on each observed trip, and how late was it compared to schedule?"*

**What happens:** Match Zoo arrival events with Toompark arrival events for the same vehicle on the same day. Join with schedule to compute delay. Exclude trips with `missing_origin` or `missing_destination` quality flags.

**This is the primary analytics input.** Analytics reads this file and nothing upstream.

| Column                    | Type           | Notes                                        |
| ------------------------- | -------------- | -------------------------------------------- |
| `vehicle_id`              | str            |                                              |
| `service_date`            | date           | Local date (Europe/Tallinn)                  |
| `zoo_arrival_ts`          | datetime (UTC) | Inferred from GPS                            |
| `toompark_arrival_ts`     | datetime (UTC) | Inferred from GPS                            |
| `drive_duration_seconds`  | int            | `toompark_arrival_ts - zoo_arrival_ts`       |
| `scheduled_zoo_departure` | datetime (UTC) | From GTFS, converted to UTC                  |
| `delay_seconds`           | int            | Positive = late, negative = early            |
| `has_large_gap`           | bool           | True if quality flag `large_gap` was present |

---

## 6. Analytics

Analytics consumes `data/curated/` and writes to `data/analytics/` and `data/output/`. It does not write back to any pipeline layer.

| Script                   | Input                        | Output                                                                     | Purpose          |
| ------------------------ | ---------------------------- | -------------------------------------------------------------------------- | ---------------- |
| `lateness_simulation.py` | `observed_trips.parquet`     | `data/analytics/simulation_results.parquet`                                | Monte Carlo runs |
| `visualization.py`       | `simulation_results.parquet` | `data/output/probability_plot.svg`, `data/output/lateness_probability.csv` | Final artefacts  |

---

## 7. Complete Flow Summary

```txt
GPS API (every 30 s)             GTFS zip (daily 04:00)
       │                                │
       ▼                                ▼
data/raw/source=gps/date={date}   data/raw/source=gtfs/date={date}
  gps_TIMESTAMP.txt               gps_TIMESTAMP.zip
                                        │ 
                                        ▼
                       unzip in memory
                                  stops.txt
                                  stop_times.txt
                                  trips.txt ...
       │                                │  
       ▼                                ▼
data/standardized/              data/standardized/
  gps_positions.parquet           gtfs_stops.parquet
                                  gtfs_stop_times.parquet
                                  gtfs_trips.parquet
       │                                │
       ▼                                │
data/intermediate/                      │
  route8_positions.parquet              │
       │                                │
       ▼                      ◄─────────┘  (first GPS+GTFS join)
data/intermediate/
  stop_distances.parquet
       │
       ▼
data/intermediate/
  stop_events.parquet
       │                                │
       └────────────────────────────────┘
                     │ (second join: events + schedule)
                     ▼
             data/curated/
               observed_trips.parquet   ← analytics entry point
               schedule_baseline.parquet
                     │
                     ▼
             data/analytics/
               simulation_results.parquet
                     │
                     ▼
             data/output/
               probability_plot.svg
               lateness_probability.csv
```

---

## 8. Code Structure

```txt
src/transit_delay_analytics/
│
├── ingestion/
│   ├── base.py                    # Base
│   ├── gps.py                     # polls API → data/raw/source=gps/
│   └── gtfs.py                    # downloads zip → raw/
│
├── models/
│   ├── standardized/
│   │   ├── gps/
│   │   │   └── gps_positions.py           → data/standardized/gps_positions.parquet
│   │   └── gtfs/
│   │       ├── gtfs_stops.py              → data/standardized/gtfs_stops.parquet
│   │       ├── gtfs_routes.py             → data/standardized/gtfs_routes.parquet
│   │       ├── gtfs_trips.py              → data/standardized/gtfs_trips.parquet
│   │       └── gtfs_stop_times.py         → data/standardized/gtfs_stop_times.parquet
│   │
│   ├── intermediate/
│   │   ├── route8_positions.py            → data/intermediate/route8_positions.parquet
│   │   ├── stop_distances.py              → data/intermediate/stop_distances.parquet
│   │   └── stop_events.py                 → data/intermediate/stop_events.parquet
│   │
│   └── curated/
│       ├── schedule_baseline.py           → data/curated/schedule_baseline.parquet
│       └── observed_trips.py              → data/curated/observed_trips.parquet
│
└── analytics/
    ├── lateness_simulation.py             → data/analytics/simulation_results.parquet
    └── visualization.py                   → data/output/probability_plot.svg
```

**Naming rule:** `models/intermediate/stop_events.py` writes exactly `data/intermediate/stop_events.parquet`. Script name = output file name. No exceptions.

**Standardized sub-directories:** Only `models/standardized/` uses source-based subdirectories (`gps/`, `gtfs/`), following dbt's staging convention. From `intermediate/` onward, files are named by what they contain, not where they came from.
