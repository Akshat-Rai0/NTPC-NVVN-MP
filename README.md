# NTPC-NVVN-MP Power Demand Predictor
Django application for real-time and short-horizon power demand prediction across Indian states using MERIT demand data, Open-Meteo weather data, and per-state LightGBM models.

## What this project does
- Ingests live state demand from MERIT India
- Builds model features from:
  - weighted weather (`temp_weighted`)
  - calendar/time (`month`, `holiday`, `is_weekend`, `hour`, `minute`)
  - autoregressive lags (`y_lag_1`, `y_lag_24h`, `y_lag_7d`)
- Runs inference via LightGBM model files mapped per state
- Stores readings and predictions in SQLite
- Mirrors records to CSV logs (`data/states/{code}/`)
- Serves:
  - interactive dashboard (`/`)
  - JSON APIs (`/api/...`)
  - admin back office (`/admin/`)
- Refreshes live predictions every 5 minutes via APScheduler

## Key features
- **Today view:** live vs predicted load, now-line, prior 7-day overlays, and MAPE cards
- **Tomorrow view:** full 96-slot (15-minute) forecast
- **Future date view:** forecast up to 16 days ahead
- **History view:** actual vs predicted for past dates
- **State-driven architecture:** onboard new states using YAML + model file (no core code changes)
- **Operational tooling:** management commands for state setup, refresh, and historical import

## Tech stack
- Python, Django
- LightGBM, pandas, numpy
- APScheduler (`django-apscheduler`)
- Open-Meteo API + request caching/retry
- SQLite (default)
- Chart.js frontend

## Repository structure
```text
NTPC-NVVN-MP/
├── manage.py
├── prediction.py
├── requirements.txt
├── demand_predictor/                 # project settings and URL routing
├── dashboard/                        # HTML/CSS/JS dashboard
├── states/                           # State, DemandReading, PredictionRecord models
├── predictions/                      # API views, services, scheduler, mgmt commands
├── utils/                            # lag, weather, time features
├── config/states/                    # state YAML configurations
├── models/{state_code}/              # LightGBM model text files
├── data/states/{state_code}/         # generated CSV logs (demand/predictions)
└── docs/OPERATIONS_GUIDE.md          # extended operational runbook
```

## Prerequisites
- Python 3.12+
- pip
- Internet access for:
  - MERIT India endpoint
  - Open-Meteo endpoint

## Setup (first run)
Run these from project root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `.env` file (required by `demand_predictor/settings.py`):

```env
DJANGO_SECRET_KEY=your-strong-secret-key
DEBUG=true
ALLOWED_HOSTS=localhost,127.0.0.1
ENABLE_SCHEDULER=true
LOG_LEVEL=INFO
```

Then initialize the app:

```bash
python manage.py migrate
python manage.py seed_state config/states/mp.yaml
python manage.py import_historical_demand --state mp --limit 5000
python manage.py refresh_demand --state mp
python manage.py runserver
```

Open:
- Dashboard: http://127.0.0.1:8000/
- Admin: http://127.0.0.1:8000/admin/
- States API: http://127.0.0.1:8000/api/states/

## Management commands
### Seed or update a state
```bash
python manage.py seed_state config/states/mp.yaml
```

### Refresh demand and predict
Single state:
```bash
python manage.py refresh_demand --state mp
```

All active states:
```bash
python manage.py refresh_demand
```

### Import historical demand
```bash
python manage.py import_historical_demand \
  --state mp \
  --csv "data/Final dataset.csv" \
  --limit 5000
```

### Admin user
```bash
python manage.py createsuperuser
```

## CLI prediction entrypoint
```bash
python prediction.py mp
```
This wraps the same prediction service used by `refresh_demand`.

## API reference
Base path: `/api`

- `GET /api/states/`
  - list active states
- `GET /api/states/{code}/today/`
  - live + predicted day series and metrics
- `GET /api/states/{code}/tomorrow/`
  - 96-slot forecast for tomorrow
- `GET /api/states/{code}/forecast/?date=YYYY-MM-DD`
  - future forecast (max 16 days ahead)
- `GET /api/states/{code}/history/?date=YYYY-MM-DD`
  - historical actual vs predicted for past date

Example:
```bash
curl "http://127.0.0.1:8000/api/states/mp/today/"
```

## Model requirements
Each state must have a LightGBM model at:
`models/{code}/lgbm_final.txt`

The model must match the feature order used in code:
1. `temp_weighted`
2. `month`
3. `holiday`
4. `is_weekend`
5. `hour`
6. `minute`
7. `y_lag_24h`
8. `y_lag_7d`
9. `y_lag_1`

## Adding a new state
1. Train and export LightGBM model to `models/{code}/lgbm_final.txt`
2. Create `config/states/{code}.yaml` (use `config/states/mp.yaml` as template)
3. Include state metadata:
   - `code`, `name`
   - `merit_state_code`, `merit_url`
   - `model_path`
   - `fallback_demand_mw`, `timezone`, `is_active` (optional)
   - `cities` with lat/lon/weight
4. Register it:
```bash
python manage.py seed_state config/states/{code}.yaml
```
5. (Optional) import history and run refresh

## Scheduler behavior
- Started from `predictions.apps.PredictionsConfig.ready()`
- Runs every 5 minutes
- Disabled when:
  - `ENABLE_SCHEDULER=false`
  - Django runserver parent process (guarded by `RUN_MAIN`)

If you want manual-only refresh in development:
```bash
ENABLE_SCHEDULER=false python manage.py runserver
```

## Data storage and logs
- Primary store: `db.sqlite3`
- Derived CSV logs:
  - `data/states/{code}/demand_log.csv`
  - `data/states/{code}/prediction_log.csv`
- App log file:
  - `logs/demand_predictor.log`

## Lag fallback logic
When historical lag values are missing, lag resolution proceeds by:
1. exact historical timestamp
2. nearest neighbor (±30 min)
3. live API fallback (when allowed)
4. most recent observed value (with decay for 24h/7d lags)
5. state fallback constant (`fallback_demand_mw`)

If 24h/7d lag resolves to constant, code derives better estimate from `y_lag_1`.

## Testing and quality checks
Pytest is included in dependencies. Run:
```bash
pytest
```

You can also run Django’s built-in checks:
```bash
python manage.py check
```

## Common issues
### `KeyError: 'DJANGO_SECRET_KEY'`
Add `DJANGO_SECRET_KEY` in `.env`.

### State missing in dashboard/API
- ensure `is_active: true`
- run `seed_state` again

### Forecast/API unavailable
- verify model path in YAML exists
- verify MERIT URL is reachable
- inspect `logs/demand_predictor.log`

### `make ...` command fails
This repo does not include a `Makefile`. Use `python manage.py ...` commands directly.

## Extended operations documentation
For a deeper operations runbook (admin workflows, full onboarding steps, troubleshooting), see:
- `docs/OPERATIONS_GUIDE.md`
