# NTPC-NVVN-MP Power Demand Predictor

Full-stack Django application for live and forecasted power demand across Indian states.

## Features

- **Today**: live actual demand (MERIT India) vs model forecast, with prior 7-day overlay
- **Tomorrow**: full-day 96-slot prediction
- **Future dates**: forecast up to 16 days ahead
- **Previous days**: historical actual vs predicted from stored records
- **Admin dashboard**: view all prediction fields in Django admin
- **Modular states**: add a new state with YAML config + trained model file
- **Auto-refresh**: live data polled every 5 minutes

## Quick start

```bash
pip install -r requirements.txt

python manage.py migrate
python manage.py seed_state config/states/mp.yaml
python manage.py import_historical_demand --state mp --limit 5000  # optional, for lag history
python manage.py refresh_demand --state mp
python manage.py createsuperuser  # optional, for admin access

python manage.py runserver
```

Open http://127.0.0.1:8000/ for the dashboard and http://127.0.0.1:8000/admin/ for admin.

For detailed setup, admin user creation, and adding new states, see **[docs/OPERATIONS_GUIDE.md](docs/OPERATIONS_GUIDE.md)**.

## Adding a new state

1. Train a LightGBM model with features: `temp_weighted`, `month`, `holiday`, `is_weekend`, `hour`, `minute`, `y_lag_1`, `y_lag_24h`, `y_lag_7d`
2. Save model to `models/{code}/lgbm_final.txt`
3. Create `config/states/{code}.yaml` (see `config/states/mp.yaml` for template)
4. Run: `python manage.py seed_state config/states/{code}.yaml`

## API endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/states/` | List active states |
| `GET /api/states/{code}/today/` | Today's actual + forecast |
| `GET /api/states/{code}/tomorrow/` | Tomorrow's forecast |
| `GET /api/states/{code}/forecast/?date=YYYY-MM-DD` | Future date forecast |
| `GET /api/states/{code}/history/?date=YYYY-MM-DD` | Past day actual vs predicted |

## CLI prediction

```bash
python prediction.py mp
# or
python manage.py refresh_demand --state mp
```

## Project structure

```text
demand_predictor/     Django project settings
states/               State, DemandReading, PredictionRecord models + admin
predictions/          Services, API, scheduler, management commands
dashboard/            Frontend templates and Chart.js dashboard
config/states/        Per-state YAML configs
models/{code}/        Trained LightGBM model files
data/states/{code}/   Auto-synced CSV exports
utils/                Weather, time features, lag store
```

## Lag fallback (first 7 days)

When historical lag data is unavailable:

1. Exact 15-min match in demand history
2. Nearest neighbour within ±30 min
3. Live MERIT API value
4. Decay from most recent: `y_lag_24h = y_lag_1 × 0.99`, `y_lag_7d = y_lag_1 × 0.98`
5. Hardcoded fallback demand constant per state

## Data storage

- Primary: SQLite via Django ORM
- Secondary: per-state CSV files in `data/states/{code}/` (auto-synced on each write)
