# Power Demand Predictor — Operations Guide

This document explains how to set up the application, create admin users, add new states, and understand where each piece of configuration lives in the codebase.

---

## Table of contents

1. [Prerequisites](#1-prerequisites)
2. [First-time setup](#2-first-time-setup)
3. [Admin user creation & login](#3-admin-user-creation--login)
4. [Project structure — where everything lives](#4-project-structure--where-everything-lives)
5. [How the system works (high level)](#5-how-the-system-works-high-level)
6. [Adding a new state (step-by-step)](#6-adding-a-new-state-step-by-step)
7. [State YAML configuration reference](#7-state-yaml-configuration-reference)
8. [ML model requirements](#8-ml-model-requirements)
9. [Management commands](#9-management-commands)
10. [Using the Django admin dashboard](#10-using-the-django-admin-dashboard)
11. [Data storage (database + CSV)](#11-data-storage-database--csv)
12. [Lag feature fallback (first 7 days)](#12-lag-feature-fallback-first-7-days)
13. [Frontend dashboard & API](#13-frontend-dashboard--api)
14. [Background refresh (5-minute polling)](#14-background-refresh-5-minute-polling)
15. [Updating or deactivating a state](#15-updating-or-deactivating-a-state)
16. [Troubleshooting](#16-troubleshooting)
17. [Quick reference checklist](#17-quick-reference-checklist)

---

## 1. Prerequisites

- Python 3.10+
- pip
- Internet access (MERIT India API, Open-Meteo weather API)

Install dependencies from the project root:

```bash
pip install -r requirements.txt
```

---

## 2. First-time setup

Run these commands from the **project root** (`NTPC-NVVN-MP/`):

```bash
# 1. Create database tables
python manage.py migrate

# 2. Register Madhya Pradesh (example state — already included)
python manage.py seed_state config/states/mp.yaml

# 3. (Optional) Import historical demand for lag features & prior-day charts
python manage.py import_historical_demand --state mp --limit 5000

# 4. (Optional) Create an admin user — see Section 3
python manage.py createsuperuser

# 5. Fetch first live prediction
python manage.py refresh_demand --state mp

# 6. Start the web server
python manage.py runserver
```

| URL | Purpose |
|-----|---------|
| http://127.0.0.1:8000/ | Public dashboard (charts) |
| http://127.0.0.1:8000/admin/ | Django admin (requires login) |
| http://127.0.0.1:8000/api/states/ | JSON API |

---

## 3. Admin user creation & login

There is **no default admin username or password**. You must create one yourself.

### Create a superuser (interactive)

```bash
python manage.py createsuperuser
```

You will be prompted for:

| Field | Description |
|-------|-------------|
| **Username** | Login ID for `/admin/` (e.g. `admin`) |
| **Email** | Optional |
| **Password** | Enter twice; not shown on screen |

Then open http://127.0.0.1:8000/admin/ and sign in with those credentials.

### Create a superuser (non-interactive)

Useful for scripts or CI:

```bash
DJANGO_SUPERUSER_PASSWORD=yourpassword python manage.py createsuperuser \
  --noinput \
  --username admin \
  --email admin@example.com
```

### Reset a forgotten password

```bash
python manage.py changepassword <username>
```

### Create additional staff users (optional)

Staff users can access the admin if `is_staff=True`. Create via admin UI (**Users → Add user**) or Django shell.

---

## 4. Project structure — where everything lives

```text
NTPC-NVVN-MP/
├── manage.py                          # Django entry point
├── prediction.py                      # CLI wrapper for single-state prediction
├── requirements.txt
├── db.sqlite3                         # SQLite database (created after migrate)
│
├── config/states/                     # ★ State YAML configs (one file per state)
│   └── mp.yaml                        # Example: Madhya Pradesh
│
├── models/{code}/                     # ★ Trained LightGBM model files
│   └── mp/lgbm_final.txt
│
├── data/states/{code}/                # Auto-synced CSV exports per state
│   ├── demand_log.csv                 # Actual demand history
│   └── prediction_log.csv             # Prediction runs + features
│
├── demand_predictor/                  # Django project settings
│   ├── settings.py                    # TIME_ZONE, INSTALLED_APPS, scheduler flag
│   └── urls.py                        # Routes: /, /admin/, /api/
│
├── states/                            # Core data models + admin
│   ├── models.py                      # State, DemandReading, PredictionRecord
│   └── admin.py                       # Admin list views & CSV export actions
│
├── predictions/                       # Prediction engine + API + scheduler
│   ├── services/
│   │   ├── registry.py                # Loads YAML → StateConfig
│   │   ├── predictor.py               # Single-slot live prediction
│   │   ├── forecaster.py              # 96-slot day forecast
│   │   ├── merit_client.py            # MERIT India API client
│   │   └── csv_sync.py                # ORM → CSV sync
│   ├── api/views.py                   # REST endpoints
│   ├── scheduler.py                   # 5-minute background job
│   └── management/commands/
│       ├── seed_state.py              # Register state from YAML
│       ├── refresh_demand.py          # Manual live refresh
│       └── import_historical_demand.py
│
├── dashboard/                         # Frontend
│   ├── templates/dashboard/index.html
│   └── static/dashboard/
│       ├── css/dashboard.css
│       └── js/chart.js                # Chart.js rendering
│
└── utils/                             # Shared feature engineering
    ├── weather.py                     # Open-Meteo weighted temperature
    ├── time_features.py               # month, holiday, is_weekend, hour, minute
    └── lag_store.py                   # y_lag_1, y_lag_24h, y_lag_7d
```

### What you change when adding a state

| Action | File / location | Code change needed? |
|--------|-----------------|---------------------|
| Add state config | `config/states/{code}.yaml` | No |
| Add model file | `models/{code}/lgbm_final.txt` | No |
| Register in database | `python manage.py seed_state ...` | No |
| Import history (optional) | Your CSV + `import_historical_demand` | No |
| Dashboard state list | Auto from database | No |
| API routes | Auto from `{code}` URL param | No |

**You do not need to edit Python code** to add a new state — only YAML, model file, and management commands.

---

## 5. How the system works (high level)

```text
MERIT India API  ──►  Actual demand (every 5 min)
Open-Meteo API   ──►  Weighted temperature
Demand history   ──►  Lag features (y_lag_1, y_lag_24h, y_lag_7d)
Time calendar    ──►  month, holiday, is_weekend, hour, minute
                              │
                              ▼
                    LightGBM model (per state)
                              │
                              ▼
              PredictionRecord + CSV sync
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
        Django Admin                     Dashboard chart
```

Each state has its own:

- MERIT URL (live demand)
- City weights (weather)
- LightGBM model file
- Data folder under `data/states/{code}/`

---

## 6. Adding a new state (step-by-step)

Example: adding **Gujarat** with code `gj`.

### Step 1 — Train the ML model

Train a LightGBM model using the **exact 9 features** (order matters — see [Section 8](#8-ml-model-requirements)):

- `temp_weighted`
- `month`
- `holiday`
- `is_weekend`
- `hour`
- `minute`
- `y_lag_24h`
- `y_lag_7d`
- `y_lag_1`

Save the booster as a text file:

```text
models/gj/lgbm_final.txt
```

You can follow the training notebook at `lightgbm/lightgbm_hypertuned.ipynb` (MP example) and export with LightGBM's `save_model()`.

### Step 2 — Find the MERIT India state code

Live demand is fetched from:

```text
https://meritindia.in/StateWiseDetails/BindCurrentStateStatus?StateCode=<CODE>
```

Response format:

```json
[{"Demand":"12,606","ISGS":"6,271","ImportData":"6,335"}]
```

Common MERIT state codes (verify on meritindia.in):

| State | Example code |
|-------|--------------|
| Madhya Pradesh | `MPD` |
| Gujarat | `GJD` |
| Maharashtra | `MHD` |
| Rajasthan | `RJD` |
| Uttar Pradesh | `UPD` |

### Step 3 — Define weather cities

Pick major cities in the state with latitude, longitude, and **population weights** (should sum to ~1.0). These feed `utils/weather.py` for `temp_weighted`.

### Step 4 — Create the YAML config

Create `config/states/gj.yaml`:

```yaml
code: gj
name: Gujarat
merit_state_code: GJD
merit_url: https://meritindia.in/StateWiseDetails/BindCurrentStateStatus?StateCode=GJD
model_path: models/gj/lgbm_final.txt
fallback_demand_mw: 18000
timezone: Asia/Kolkata
is_active: true
cities:
  ahmedabad:
    lat: 23.0225
    lon: 72.5714
    weight: 0.35
  surat:
    lat: 21.1702
    lon: 72.8311
    weight: 0.25
  vadodara:
    lat: 22.3072
    lon: 73.1812
    weight: 0.20
  rajkot:
    lat: 22.3039
    lon: 70.8022
    weight: 0.20
```

Use `config/states/mp.yaml` as the reference template.

### Step 5 — Register the state in the database

```bash
python manage.py seed_state config/states/gj.yaml
```

Expected output:

```text
State 'Gujarat' (gj) registered/updated.
```

The state will immediately appear in:

- Dashboard state dropdown
- `/api/states/`
- Django admin → **States**

### Step 6 — (Recommended) Import historical demand

For the first week, lag features use fallback logic unless history exists. Import past demand if you have it:

```bash
python manage.py import_historical_demand \
  --state gj \
  --csv path/to/gujarat_demand.csv \
  --limit 0
```

**CSV requirements for import command:**

| Column | Description |
|--------|-------------|
| `datetime` | Timestamp (any parseable format) |
| `hourly_demand_met_mw` | Demand in MW |

Rows are floored to 15-minute intervals automatically.

### Step 7 — Run first live prediction

```bash
python manage.py refresh_demand --state gj
```

### Step 8 — Verify

1. Open http://127.0.0.1:8000/ → select **Gujarat** from dropdown
2. Check admin → **Prediction records** filtered by state `gj`
3. Confirm CSV files created at `data/states/gj/demand_log.csv` and `prediction_log.csv`

---

## 7. State YAML configuration reference

| Field | Required | Description |
|-------|----------|-------------|
| `code` | Yes | Short slug, lowercase (e.g. `mp`, `gj`). Used in URLs and folder names. |
| `name` | Yes | Display name shown in dashboard dropdown. |
| `merit_state_code` | Yes | MERIT India API state code (e.g. `MPD`). |
| `merit_url` | Yes | Full MERIT API URL including `StateCode` query param. |
| `model_path` | Yes | Path to LightGBM `.txt` file, relative to project root. |
| `fallback_demand_mw` | No | Last-resort MW constant when all lag lookups fail (default: 14500). |
| `timezone` | No | IANA timezone for time features (default: `Asia/Kolkata`). |
| `is_active` | No | If `false`, state hidden from API/dashboard/scheduler (default: `true`). |
| `cities` | Yes | Dict of `{city_name: {lat, lon, weight}}` for weather weighting. |

City weights should reflect population or load share and ideally sum to **1.0**.

---

## 8. ML model requirements

### Feature vector (exact column order)

The predictor in `predictions/services/predictor.py` builds features in this order:

```python
FEATURE_COLS = [
    "temp_weighted",
    "month",
    "holiday",
    "is_weekend",
    "hour",
    "minute",
    "y_lag_24h",
    "y_lag_7d",
    "y_lag_1",
]
```

Your trained model **must** expect these 9 features in this order.

### Model file format

- LightGBM booster saved as text: `lgbm_booster.save_model("models/{code}/lgbm_final.txt")`
- Referenced in YAML as `model_path: models/{code}/lgbm_final.txt`

### Prediction interval

- Data is aligned to **15-minute** slots (00, 15, 30, 45)
- MERIT API updates every **5 minutes**; the scheduler runs every **5 minutes** and aligns to the nearest 15-min boundary

---

## 9. Management commands

All commands run from the project root.

### `seed_state`

Register or update a state from YAML.

```bash
python manage.py seed_state config/states/mp.yaml
```

**What it does:** Reads YAML → upserts row in `states_state` table via `StateRegistry.upsert_from_yaml()`.

**When to re-run:** After editing YAML (URL, cities, fallback, model path).

---

### `refresh_demand`

Fetch live MERIT demand and run prediction.

```bash
# Single state
python manage.py refresh_demand --state mp

# All active states
python manage.py refresh_demand
```

**What it does:**

1. Calls MERIT API → saves `DemandReading`
2. Fetches weather + time + lag features
3. Runs LightGBM inference → saves `PredictionRecord`
4. Syncs CSV files

---

### `import_historical_demand`

Bulk-import past demand for lag features and prior-day chart overlays.

```bash
python manage.py import_historical_demand \
  --state mp \
  --csv "data/Final dataset.csv" \
  --limit 5000
```

| Flag | Default | Description |
|------|---------|-------------|
| `--state` | `mp` | State code (must have matching YAML) |
| `--csv` | `data/Final dataset.csv` | Path to CSV file |
| `--limit` | `0` (all rows) | Max rows to import from end of file |

---

### Standard Django commands

```bash
python manage.py migrate              # Apply database migrations
python manage.py createsuperuser        # Create admin login
python manage.py changepassword <user>  # Reset password
python manage.py runserver              # Start dev server
python manage.py runserver 0.0.0.0:8000 # Expose on network
```

---

## 10. Using the Django admin dashboard

Login at http://127.0.0.1:8000/admin/

### States

**Path:** Admin → **States**

View and edit:

- Name, code, MERIT URL
- Model path
- Fallback demand
- Cities JSON (weather config)
- **Is active** toggle

Changes here take effect immediately (no restart needed).

### Demand readings

**Path:** Admin → **Demand readings**

| Column | Description |
|--------|-------------|
| `state` | Which state |
| `timestamp` | 15-min aligned time |
| `demand_mw` | Actual demand in MW |
| `source` | `api`, `import`, or `predicted` |

**Admin action:** Select rows → **Export selected to CSV**

### Prediction records

**Path:** Admin → **Prediction records**

Full feature log per prediction run:

| Column | Description |
|--------|-------------|
| `timestamp` | Prediction time slot |
| `actual_demand` | Live MERIT value (MW) |
| `predicted_demand` | Model output (MW) |
| `temp_weighted` | Weighted apparent temp (°C) |
| `month` | 1–12 |
| `holiday` | 0 or 1 (Indian national holidays) |
| `is_weekend` | 0 or 1 |
| `hour` | 0–23 |
| `minute` | 0, 15, 30, or 45 |
| `y_lag_1` | Demand 15 min ago (MW) |
| `y_lag_24h` | Demand 24 h ago (MW) |
| `y_lag_7d` | Demand 7 days ago (MW) |

**Filters:** By state, month, holiday, weekend  
**Admin action:** Export selected to CSV

---

## 11. Data storage (database + CSV)

### Primary storage — SQLite (Django ORM)

Database file: `db.sqlite3`

| Model | Table purpose |
|-------|---------------|
| `State` | Configuration registry |
| `DemandReading` | Actual demand snapshots |
| `PredictionRecord` | Predictions + full feature vector |

### Secondary storage — CSV (auto-synced)

On every save, `predictions/services/csv_sync.py` exports to:

```text
data/states/{code}/demand_log.csv
data/states/{code}/prediction_log.csv
```

These mirror the ORM data for external tools and portability.

### Lag lookups

`utils/lag_store.py` reads demand history from:

1. Django ORM (`DemandReading`) when `state_id` is available
2. Fallback: `data/states/{code}/demand_log.csv`

---

## 12. Lag feature fallback (first 7 days)

When historical demand is missing, lags are resolved in this order (`utils/lag_store.py`):

1. **Exact match** — same 15-min timestamp in history
2. **Nearest neighbour** — within ±30 minutes
3. **Live MERIT API** — current demand (live prediction only)
4. **Decay from most recent** — `y_lag_24h = y_lag_1 × 0.99`, `y_lag_7d = y_lag_1 × 0.98`
5. **Hardcoded fallback** — `fallback_demand_mw` from state config

Import historical data or wait ~7 days of live collection for accurate `y_lag_7d`.

---

## 13. Frontend dashboard & API

### Dashboard views

| Tab | Data source |
|-----|-------------|
| **Today** | Actual (blue) + forecast (orange) + prior 7 days overlay |
| **Tomorrow** | 96 × 15-min predicted slots |
| **Future date** | Forecast up to 16 days ahead |
| **Previous day** | Stored actual vs predicted |

Chart refreshes every **5 minutes** on the Today view.

### API endpoints

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/states/` | List active states |
| GET | `/api/states/{code}/today/` | Today actual + forecast |
| GET | `/api/states/{code}/tomorrow/` | Tomorrow forecast |
| GET | `/api/states/{code}/forecast/?date=YYYY-MM-DD` | Future date (≤16 days) |
| GET | `/api/states/{code}/history/?date=YYYY-MM-DD` | Past day (date < today) |

Example:

```bash
curl http://127.0.0.1:8000/api/states/mp/today/
```

---

## 14. Background refresh (5-minute polling)

When `runserver` is active, `predictions/scheduler.py` automatically calls `refresh_all_states()` every **5 minutes** for all states where `is_active=True`.

### Disable scheduler (e.g. during tests)

```bash
ENABLE_SCHEDULER=false python manage.py runserver
```

Or set in `demand_predictor/settings.py`:

```python
ENABLE_SCHEDULER = False
```

### Production alternative

Use cron instead of the built-in scheduler:

```cron
*/5 * * * * cd /path/to/NTPC-NVVN-MP && python manage.py refresh_demand
```

---

## 15. Updating or deactivating a state

### Update config

1. Edit `config/states/{code}.yaml`
2. Re-run: `python manage.py seed_state config/states/{code}.yaml`

Or edit directly in Django admin → **States**.

### Replace model

1. Save new file to `models/{code}/lgbm_final.txt`
2. No restart needed — model is loaded on next prediction (cached in memory until process restart)

### Deactivate (hide from dashboard)

Set `is_active: false` in YAML and re-seed, or uncheck **Is active** in admin.

Deactivated states are excluded from:

- Dashboard dropdown
- `/api/states/`
- Background scheduler

---

## 16. Troubleshooting

### State not appearing in dropdown

- Confirm `is_active: true` in YAML or admin
- Run `python manage.py seed_state config/states/{code}.yaml`
- Check database: admin → **States**

### Prediction fails / model error

- Verify model file exists at path in YAML
- Confirm model expects exactly 9 features in correct order
- Check logs in terminal when running `refresh_demand`

### MERIT API returns no data

- Verify `merit_url` and `merit_state_code` in browser or curl
- MERIT may be temporarily unavailable; fallback demand is used for lags

### Lag values look wrong in first week

- Expected — import historical demand or wait for history to accumulate
- Check **Demand readings** in admin for imported/API data

### Admin login fails

- No default credentials exist — run `createsuperuser` or `changepassword`
- Ensure you migrated: `python manage.py migrate`

### Chart shows no actual line

- Run `python manage.py refresh_demand --state {code}`
- MERIT API must be reachable
- Check **Demand readings** in admin for recent rows

### Timezone warnings

- App uses `Asia/Kolkata` (set in `demand_predictor/settings.py`)
- Historical CSV imports are converted to timezone-aware datetimes automatically

---

## 17. Quick reference checklist

### New state checklist

- [ ] Train LightGBM model with 9 required features
- [ ] Save model to `models/{code}/lgbm_final.txt`
- [ ] Create `config/states/{code}.yaml` with MERIT URL + cities
- [ ] Run `python manage.py seed_state config/states/{code}.yaml`
- [ ] (Optional) Import historical demand CSV
- [ ] Run `python manage.py refresh_demand --state {code}`
- [ ] Verify dashboard + admin + CSV files under `data/states/{code}/`

### Admin setup checklist

- [ ] `python manage.py migrate`
- [ ] `python manage.py createsuperuser`
- [ ] Login at http://127.0.0.1:8000/admin/

### Daily operations

- Server running: `python manage.py runserver`
- Auto-refresh: every 5 min via scheduler (or cron)
- Manual refresh: `python manage.py refresh_demand`
- Monitor: admin → **Prediction records** / **Demand readings**

---

## Related files

| Topic | File |
|-------|------|
| MP example config | `config/states/mp.yaml` |
| State registration logic | `predictions/services/registry.py` |
| Live prediction | `predictions/services/predictor.py` |
| Day forecast (96 slots) | `predictions/services/forecaster.py` |
| MERIT API client | `predictions/services/merit_client.py` |
| Weather features | `utils/weather.py` |
| Lag features | `utils/lag_store.py` |
| Admin registration | `states/admin.py` |
| Chart frontend | `dashboard/static/dashboard/js/chart.js` |

For a shorter overview, see the root [README.md](../README.md).
