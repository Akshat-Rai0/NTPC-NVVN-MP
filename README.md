# NTPC-NVVN-MP Power Demand Predictor

A Django-based machine learning system for real-time and short-horizon power demand prediction across Indian states. The system integrates live demand data from MERIT India, weather data from Open-Meteo, and state-specific LightGBM models to provide accurate 15-minute interval forecasts.

## Overview

This project addresses the critical need for accurate power demand forecasting in India's electricity grid. By combining real-time demand data, weather patterns, and historical trends, it enables grid operators to:

- **Optimize power generation scheduling** - Reduce costs by aligning generation with predicted demand
- **Improve grid stability** - Anticipate demand surges and prevent outages
- **Enable renewable integration** - Better match variable renewable output with demand patterns
- **Support planning decisions** - Provide data-driven insights for capacity planning

### System Architecture

The system follows a modular, state-driven architecture:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  MERIT India    │    │  Open-Meteo     │    │  Historical DB  │
│  (Live Demand)  │    │  (Weather API)  │    │  (Lag Features) │
└────────┬────────┘    └────────┬────────┘    └────────┬────────┘
         │                      │                      │
         └──────────────────────┼──────────────────────┘
                                │
                    ┌───────────▼───────────┐
                    │  Feature Engineering  │
                    │  - temp_weighted      │
                    │  - time features      │
                    │  - lag features       │
                    └───────────┬───────────┘
                                │
                    ┌───────────▼───────────┐
                    │  LightGBM Inference   │
                    │  (Per-State Models)   │
                    └───────────┬───────────┘
                                │
         ┌──────────────────────┼──────────────────────┐
         │                      │                      │
┌────────▼────────┐   ┌────────▼────────┐   ┌────────▼────────┐
│  SQLite DB      │   │  CSV Logs       │   │  Dashboard/API  │
│  (Primary)      │   │  (Export)       │   │  (Visualization)│
└─────────────────┘   └─────────────────┘   └─────────────────┘
```

## What This Project Does

### Data Ingestion
- **Live Demand**: Fetches real-time power demand data from MERIT India API every 5 minutes
- **Weather Data**: Retrieves weighted temperature data from Open-Meteo for multiple cities per state
- **Historical Data**: Imports and stores historical demand for lag feature computation

### Feature Engineering
The system builds a comprehensive feature set for each prediction:

**Weather Features:**
- `temp_weighted`: Population-weighted apparent temperature across major state cities

**Temporal Features:**
- `month`: Month of year (1-12) for seasonal patterns
- `holiday`: Binary indicator for Indian national holidays
- `is_weekend`: Binary indicator for weekends
- `hour`: Hour of day (0-23) for diurnal patterns
- `minute`: Minute within hour (0, 15, 30, 45) for 15-minute granularity

**Autoregressive Features:**
- `y_lag_1`: Demand from 15 minutes ago
- `y_lag_24h`: Demand from 24 hours ago (same time yesterday)
- `y_lag_7d`: Demand from 7 days ago (same time last week)

### Model Inference
- Runs LightGBM model inference using per-state trained models
- Supports both instant predictions and 96-slot day-ahead forecasts
- Handles missing data through sophisticated fallback mechanisms

### Data Storage & Export
- **Primary Storage**: SQLite database with Django ORM
- **Secondary Storage**: CSV logs for external analysis and backup
- **Admin Interface**: Django admin for data inspection and management

### User Interfaces
- **Interactive Dashboard**: Real-time visualization of actual vs predicted demand
- **REST API**: JSON endpoints for programmatic access
- **Admin Panel**: Back-office interface for configuration and data management

### Automation
- **Background Scheduler**: Automatic 5-minute refresh via APScheduler
- **CSV Sync**: Automatic mirroring of database to CSV files
- **Error Handling**: Robust fallback mechanisms for API failures

## Key Features

### Dashboard Capabilities
- **Today View**: Real-time comparison of actual vs predicted demand with live updates every 5 minutes
  - Now-line showing current demand position
  - Prior 7-day demand overlays for pattern comparison
  - MAPE (Mean Absolute Percentage Error) cards for accuracy tracking
  - Interactive zooming and panning

- **Tomorrow View**: Complete 96-slot (15-minute interval) forecast for the next day
  - Detailed demand curve prediction
  - Confidence intervals where available
  - Export capabilities for planning

- **Future Date View**: Extended forecasting up to 16 days ahead
  - Useful for medium-term planning
  - Holiday and weekend pattern recognition
  - Seasonal trend visualization

- **History View**: Historical actual vs predicted comparison
  - Post-hoc accuracy analysis
  - Model performance tracking over time
  - Anomaly detection

### Architecture Highlights
- **State-Driven Design**: Add new states without touching core code
  - YAML-based configuration
  - Per-state model files
  - Independent data pipelines
- **Scalable**: Support for unlimited states with minimal overhead
- **Fault-Tolerant**: Multiple fallback mechanisms for data failures
- **Production-Ready**: Built-in logging, error handling, and monitoring

### Operational Excellence
- **Management Commands**: CLI tools for all operational tasks
- **Automated Workflows**: Background scheduler for hands-off operation
- **Data Portability**: Automatic CSV exports for external analysis
- **Admin Interface**: Django admin for configuration and data management

## Tech Stack

### Core Framework
- **Python 3.12+**: Modern Python with type hints and performance improvements
- **Django 6.0.1**: Full-featured web framework with ORM, admin, and authentication
- **Django-APScheduler 0.7.0**: Background job scheduling for automated predictions

### Machine Learning
- **LightGBM 4.6.0**: Gradient boosting framework for efficient model training and inference
- **pandas 2.3.3**: Data manipulation and analysis
- **numpy 2.4.0**: Numerical computing for feature engineering

### Data Sources
- **Open-Meteo Requests 1.7.5**: Weather data API client with caching
- **Requests 2.32.5**: HTTP library for API calls
- **Requests-Cache 1.3.2**: Response caching to reduce API calls
- **Retry-Requests 2.0.0**: Automatic retry logic for resilient API calls
- **urllib3 2.6.3**: HTTP client with connection pooling

### Utilities
- **python-dotenv 1.1.0**: Environment variable management
- **PyYAML 6.0.2**: YAML configuration file parsing
- **holidays 0.88**: Indian holiday calendar integration

### Frontend
- **Chart.js**: Interactive JavaScript charting library for data visualization
- **Bootstrap**: Responsive CSS framework for modern UI
- **Custom CSS**: Tailored styling for power industry aesthetics

### Development
- **pytest 9.0.2**: Testing framework
- **pytest-django 4.11.0**: Django integration for pytest

### Database
- **SQLite 3**: Lightweight, serverless database (default)
  - Easy deployment and backup
  - Suitable for medium-scale deployments
  - Can be replaced with PostgreSQL for production

## Repository Structure

```text
NTPC-NVVN-MP/
├── manage.py                          # Django command-line entry point
├── prediction.py                      # CLI wrapper for single-state prediction
├── train_dd_model.py                  # Model training script (example for DD state)
├── requirements.txt                  # Python dependencies with versions
├── .env                               # Environment variables (not in git)
├── .gitignore                         # Git ignore patterns
├── db.sqlite3                         # SQLite database (created after migrate)
│
├── demand_predictor/                  # Django project configuration
│   ├── __init__.py
│   ├── settings.py                    # Django settings, database, logging config
│   ├── urls.py                        # Root URL routing
│   ├── wsgi.py                        # WSGI deployment interface
│   └── asgi.py                        # ASGI deployment interface
│
├── dashboard/                         # Frontend web application
│   ├── __init__.py
│   ├── admin.py                       # Django admin registration
│   ├── apps.py                        # Dashboard app configuration
│   ├── models.py                      # Dashboard-specific models
│   ├── views.py                       # View logic for dashboard
│   ├── tests.py                       # Dashboard tests
│   ├── templates/
│   │   └── dashboard/
│   │       └── index.html             # Main dashboard template
│   └── static/
│       └── dashboard/
│           ├── css/
│           │   └── dashboard.css      # Custom styling
│           └── js/
│               └── chart.js           # Chart.js visualization logic
│
├── states/                            # Core data models
│   ├── __init__.py
│   ├── admin.py                       # Admin interface for state management
│   ├── apps.py                        # States app configuration
│   ├── models.py                      # State, DemandReading, PredictionRecord models
│   └── tests.py                       # Model tests
│
├── predictions/                       # Prediction engine and API
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py                        # Prediction app config with scheduler startup
│   ├── models.py
│   ├── scheduler.py                   # APScheduler configuration
│   ├── urls.py                        # API URL routing
│   ├── views.py
│   ├── tests.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── views.py                   # REST API endpoint implementations
│   ├── services/
│   │   ├── __init__.py
│   │   ├── registry.py                # YAML config loader and state registration
│   │   ├── predictor.py               # Single-slot live prediction logic
│   │   ├── forecaster.py              # Multi-slot day-ahead forecasting
│   │   ├── merit_client.py            # MERIT India API client
│   │   └── csv_sync.py                # ORM to CSV synchronization
│   └── management/
│       └── commands/
│           ├── seed_state.py          # Register state from YAML
│           ├── refresh_demand.py      # Manual demand refresh
│           └── import_historical_demand.py
│
├── utils/                             # Shared utility modules
│   ├── __init__.py
│   ├── weather.py                     # Open-Meteo weather data fetching
│   ├── time_features.py               # Temporal feature extraction
│   └── lag_store.py                   # Lag feature computation with fallback
│
├── config/states/                     # State YAML configurations
│   ├── mp.yaml                        # Madhya Pradesh configuration
│   └── {state_code}.yaml              # Other state configurations
│
├── models/                            # Trained LightGBM models
│   ├── mp/
│   │   └── lgbm_final.txt             # MP state model
│   ├── dd/
│   │   └── lgbm_final.txt             # Dadra & Nagar Haveli model
│   └── {state_code}/
│       └── lgbm_final.txt             # Per-state model files
│
├── data/                              # Data storage and exports
│   ├── demand_log.csv                 # Global demand log
│   ├── states/
│   │   ├── mp/
│   │   │   ├── demand_log.csv         # MP demand history
│   │   │   └── prediction_log.csv     # MP prediction history
│   │   └── {state_code}/
│   │       ├── demand_log.csv
│   │       └── prediction_log.csv
│   └── helper data/                   # Additional reference data
│
├── logs/                              # Application logs
│   └── demand_predictor.log           # Main application log file
│
└── docs/                              # Documentation
    ├── OPERATIONS_GUIDE.md           # Detailed operational procedures
    └── add_state.md                   # State addition guide
```

### Key Directories Explained

**`demand_predictor/`**: Core Django project configuration containing settings, URL routing, and deployment interfaces. This is where the application is configured with database connections, installed apps, middleware, and logging.

**`dashboard/`**: Frontend application serving the web interface. Contains HTML templates for the dashboard, custom CSS for styling, and JavaScript for Chart.js visualizations. The dashboard provides real-time demand monitoring and forecasting visualization.

**`states/`**: Contains the core data models for the application. The `State` model stores configuration, `DemandReading` stores actual demand data, and `PredictionRecord` stores predictions with full feature vectors.

**`predictions/`**: The heart of the prediction engine. Contains the service layer for fetching data, engineering features, running model inference, and serving API endpoints. The scheduler here automates the 5-minute refresh cycle.

**`utils/`**: Shared utility modules for feature engineering. `weather.py` handles Open-Meteo API calls, `time_features.py` extracts temporal features, and `lag_store.py` computes autoregressive lag features with sophisticated fallback logic.

**`config/states/`**: YAML configuration files for each state. These files define state-specific settings like MERIT API endpoints, city coordinates for weather weighting, model paths, and fallback values.

**`models/`**: Directory containing trained LightGBM model files. Each state has its own subdirectory with a `lgbm_final.txt` file exported from LightGBM's `save_model()` function.

**`data/`**: Storage for CSV exports and historical data. The system automatically mirrors database records to CSV files for external analysis and backup purposes.

## Prerequisites

### System Requirements
- **Python 3.12+**: The application requires Python 3.12 or higher for modern syntax and performance improvements
- **pip**: Python package manager for dependency installation
- **Virtual Environment**: Recommended for isolation (venv, conda, or similar)
- **Disk Space**: Minimum 500 MB for database, logs, and model files
- **Memory**: Minimum 2 GB RAM (4 GB recommended for production)

### Network Requirements
- **Internet Access**: Required for:
  - MERIT India API endpoint (live demand data)
  - Open-Meteo API endpoint (weather data)
  - Package installation via pip

### API Access
- **MERIT India**: Publicly accessible, no authentication required
- **Open-Meteo**: Free API with rate limits, no authentication required
- Both APIs have built-in retry logic and caching in the application

## Setup (First Run)

### Step 1: Clone and Navigate
```bash
cd /path/to/NTPC-NVVN-MP
```

### Step 2: Create Virtual Environment
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

This will install all required packages including Django, LightGBM, pandas, and API clients.

### Step 4: Configure Environment Variables
Create a `.env` file in the project root (this file is git-ignored):

```env
# Django Configuration
DJANGO_SECRET_KEY=your-strong-secret-key-here
DEBUG=true
ALLOWED_HOSTS=localhost,127.0.0.1

# Scheduler Configuration
ENABLE_SCHEDULER=true

# Logging Configuration
LOG_LEVEL=INFO
```

**Environment Variable Reference:**

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DJANGO_SECRET_KEY` | Yes | None | Django secret key for cryptographic signing |
| `DEBUG` | No | `false` | Enable debug mode (set to `false` in production) |
| `ALLOWED_HOSTS` | No | `localhost,127.0.0.1` | Comma-separated list of allowed hostnames |
| `ENABLE_SCHEDULER` | No | `true` | Enable automatic 5-minute background refresh |
| `LOG_LEVEL` | No | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |

**Security Note**: In production, use a strong, randomly generated `DJANGO_SECRET_KEY` and set `DEBUG=false`.

### Step 5: Initialize Database
```bash
python manage.py migrate
```

This creates the SQLite database and all required tables for States, DemandReadings, and PredictionRecords.

### Step 6: Register Initial State
```bash
python manage.py seed_state config/states/mp.yaml
```

This loads the Madhya Pradesh configuration from YAML and creates the corresponding State record in the database.

### Step 7: Import Historical Data (Optional but Recommended)
```bash
python manage.py import_historical_demand --state mp --limit 5000
```

This imports historical demand data for better lag feature computation. Without historical data, the system uses fallback values for the first 7 days.

**CSV Format for Historical Import:**
```csv
datetime,hourly_demand_met_mw
2024-01-01 00:00:00,12500
2024-01-01 00:15:00,12450
2024-01-01 00:30:00,12400
```

### Step 8: Run Initial Prediction
```bash
python manage.py refresh_demand --state mp
```

This fetches the first live prediction from MERIT India and runs the model inference.

### Step 9: Start Development Server
```bash
python manage.py runserver
```

The server will start on `http://127.0.0.1:8000/`

### Step 10: Access the Application
Open your browser and navigate to:

| URL | Purpose | Authentication |
|-----|---------|-----------------|
| http://127.0.0.1:8000/ | Public Dashboard | None required |
| http://127.0.0.1:8000/admin/ | Django Admin | Requires superuser |
| http://127.0.0.1:8000/api/states/ | States API | None required |

### Step 11: Create Admin User (Optional)
```bash
python manage.py createsuperuser
```

Follow the prompts to create username, email (optional), and password. This user can access the Django admin interface.

## Verification Steps

After setup, verify the installation:

1. **Check Dashboard**: Open http://127.0.0.1:8000/ and select a state from the dropdown
2. **Check API**: Run `curl http://127.0.0.1:8000/api/states/` to see JSON response
3. **Check Admin**: Login at http://127.0.0.1:8000/admin/ and verify State records exist
4. **Check Logs**: Review `logs/demand_predictor.log` for any errors
5. **Check CSV Files**: Verify `data/states/mp/demand_log.csv` and `prediction_log.csv` exist

## Management Commands

The application provides several Django management commands for operational tasks. All commands should be run from the project root directory.

### seed_state
Register or update a state configuration from YAML file.

```bash
python manage.py seed_state config/states/mp.yaml
```

**What it does:**
- Reads the YAML configuration file
- Creates or updates the State record in the database
- Validates required fields (code, name, MERIT URL, model path, cities)
- Updates existing records if the state code already exists

**When to use:**
- Initial state registration
- Updating state configuration (MERIT URL, cities, model path)
- Re-activating a deactivated state

**Example output:**
```
State 'Madhya Pradesh' (mp) registered/updated successfully.
```

### refresh_demand
Fetch live demand data from MERIT India and run predictions.

```bash
# Single state
python manage.py refresh_demand --state mp

# All active states
python manage.py refresh_demand
```

**What it does:**
1. Fetches current demand from MERIT India API
2. Saves demand reading to database
3. Fetches weather data from Open-Meteo
4. Computes temporal and lag features
5. Runs LightGBM model inference
6. Saves prediction record to database
7. Syncs data to CSV files

**When to use:**
- Manual refresh (outside of scheduler)
- Testing prediction pipeline
- After configuration changes
- Debugging prediction issues

**Options:**
- `--state <code>`: Specific state code (optional, defaults to all active states)

### import_historical_demand
Import historical demand data from CSV file for lag features and historical analysis.

```bash
python manage.py import_historical_demand \
  --state mp \
  --csv "data/Final dataset.csv" \
  --limit 5000
```

**What it does:**
- Reads demand data from CSV file
- Parses timestamps and aligns to 15-minute intervals
- Stores demand readings in database
- Enables accurate lag feature computation
- Improves prediction accuracy for first 7 days

**When to use:**
- Initial setup with historical data
- Adding historical data for new states
- Backfilling missing data periods

**Options:**
- `--state <code>`: State code (required)
- `--csv <path>`: Path to CSV file (required)
- `--limit <number>`: Maximum rows to import from end of file (optional, 0 = all)

**CSV Format Requirements:**
```csv
datetime,hourly_demand_met_mw
2024-01-01 00:00:00,12500
2024-01-01 00:15:00,12450
```

### createsuperuser
Create an admin user for Django admin access.

```bash
python manage.py createsuperuser
```

**What it does:**
- Creates a superuser with admin privileges
- Prompts for username, email (optional), and password
- Enables access to `/admin/` interface

**Non-interactive mode:**
```bash
DJANGO_SUPERUSER_PASSWORD=yourpassword python manage.py createsuperuser \
  --noinput \
  --username admin \
  --email admin@example.com
```

### Standard Django Commands
```bash
python manage.py migrate              # Apply database migrations
python manage.py makemigrations       # Create new migrations
python manage.py runserver            # Start development server
python manage.py runserver 0.0.0.0:8000 # Expose on network
python manage.py shell                 # Django Python shell
python manage.py check                # Check for configuration issues
python manage.py collectstatic        # Collect static files for production
```

## CLI Prediction Entrypoint

A standalone Python script for quick single-state predictions without running the full Django server.

```bash
python prediction.py mp
```

**What it does:**
- Initializes Django environment
- Loads state configuration
- Fetches live demand and weather data
- Computes features and runs prediction
- Prints predicted and actual demand values

**Example output:**
```
Predicted MP demand: 14,234.5 MW
Actual demand: 14,198.2 MW
```

**When to use:**
- Quick testing without starting server
- Script-based predictions
- Integration with external systems

## API Reference

The application provides a RESTful JSON API for programmatic access to predictions and state data.

### Base URL
```
http://127.0.0.1:8000/api/
```

### Endpoints

#### GET /api/states/
List all active states.

**Response:**
```json
[
  {
    "code": "mp",
    "name": "Madhya Pradesh",
    "is_active": true
  },
  {
    "code": "dd",
    "name": "Dadra & Nagar Haveli",
    "is_active": true
  }
]
```

#### GET /api/states/{code}/today/
Get live demand and predicted values for today with metrics.

**Parameters:**
- `code`: State code (e.g., `mp`)

**Response:**
```json
{
  "state": "mp",
  "date": "2024-06-24",
  "actual": [
    {"timestamp": "2024-06-24T00:00:00", "demand_mw": 12500},
    {"timestamp": "2024-06-24T00:15:00", "demand_mw": 12450}
  ],
  "predicted": [
    {"timestamp": "2024-06-24T00:00:00", "demand_mw": 12520},
    {"timestamp": "2024-06-24T00:15:00", "demand_mw": 12460}
  ],
  "metrics": {
    "mape": 2.3,
    "mae": 285.5,
    "rmse": 320.1
  }
}
```

#### GET /api/states/{code}/tomorrow/
Get 96-slot (15-minute) forecast for tomorrow.

**Parameters:**
- `code`: State code (e.g., `mp`)

**Response:**
```json
{
  "state": "mp",
  "date": "2024-06-25",
  "forecast": [
    {"timestamp": "2024-06-25T00:00:00", "predicted_demand_mw": 12600},
    {"timestamp": "2024-06-25T00:15:00", "predicted_demand_mw": 12550}
  ]
}
```

#### GET /api/states/{code}/forecast/
Get forecast for a specific future date (up to 16 days ahead).

**Parameters:**
- `code`: State code (e.g., `mp`)
- `date`: Date in YYYY-MM-DD format (query parameter)

**Example:**
```bash
curl "http://127.0.0.1:8000/api/states/mp/forecast/?date=2024-06-26"
```

**Response:**
```json
{
  "state": "mp",
  "date": "2024-06-26",
  "forecast": [
    {"timestamp": "2024-06-26T00:00:00", "predicted_demand_mw": 12700},
    {"timestamp": "2024-06-26T00:15:00", "predicted_demand_mw": 12650}
  ]
}
```

#### GET /api/states/{code}/history/
Get historical actual vs predicted data for a past date.

**Parameters:**
- `code`: State code (e.g., `mp`)
- `date`: Date in YYYY-MM-DD format (query parameter)

**Example:**
```bash
curl "http://127.0.0.1:8000/api/states/mp/history/?date=2024-06-23"
```

**Response:**
```json
{
  "state": "mp",
  "date": "2024-06-23",
  "actual": [
    {"timestamp": "2024-06-23T00:00:00", "demand_mw": 12400}
  ],
  "predicted": [
    {"timestamp": "2024-06-23T00:00:00", "predicted_demand_mw": 12420}
  ]
}
```

### Error Responses

All endpoints return standard HTTP status codes:

- `200 OK`: Successful request
- `404 Not Found`: State or data not found
- `400 Bad Request`: Invalid parameters
- `500 Internal Server Error`: Server error

**Error Response Format:**
```json
{
  "error": "State not found",
  "detail": "No active state with code 'xy' exists"
}
```

## Model Requirements

### Model File Location
Each state must have a trained LightGBM model saved as:
```
models/{state_code}/lgbm_final.txt
```

For example, for Madhya Pradesh:
```
models/mp/lgbm_final.txt
```

### Feature Vector Requirements
The model must expect exactly **9 features** in this specific order:

| Index | Feature | Type | Description |
|-------|---------|------|-------------|
| 1 | `temp_weighted` | float | Population-weighted apparent temperature (°C) |
| 2 | `month` | int | Month of year (1-12) |
| 3 | `holiday` | int | Binary indicator (0 or 1) for Indian national holidays |
| 4 | `is_weekend` | int | Binary indicator (0 or 1) for weekends |
| 5 | `hour` | int | Hour of day (0-23) |
| 6 | `minute` | int | Minute within hour (0, 15, 30, or 45) |
| 7 | `y_lag_24h` | float | Demand from 24 hours ago (MW) |
| 8 | `y_lag_7d` | float | Demand from 7 days ago (MW) |
| 9 | `y_lag_1` | float | Demand from 15 minutes ago (MW) |

### Model Training Guidelines

**Training Data Requirements:**
- Historical demand data with 15-minute intervals
- Weather data for the same time periods
- Holiday calendar for the region
- Minimum 6 months of data for reasonable accuracy
- 1-2 years of data recommended for robust performance

**Feature Engineering:**
- Use the same feature definitions as the production system
- Ensure temporal features are computed in the state's timezone
- Use population-weighted temperature for weather features
- Compute lag features with the same fallback logic

**Model Hyperparameters (Recommended Starting Point):**
```python
params = {
    'objective': 'regression',
    'metric': 'rmse',
    'boosting_type': 'gbdt',
    'num_leaves': 31,
    'learning_rate': 0.05,
    'feature_fraction': 0.9,
    'verbose': -1,
}
```

**Training Example:**
```python
import lightgbm as lgb
from sklearn.model_selection import train_test_split

# Prepare data
X = df[FEATURE_COLS]  # Use the 9 features in correct order
y = df['hourly_demand_met_mw']

# Split data
X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)

# Train model
train_data = lgb.Dataset(X_train, label=y_train)
val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)

model = lgb.train(
    params,
    train_data,
    num_boost_round=1000,
    valid_sets=[train_data, val_data],
    callbacks=[
        lgb.early_stopping(stopping_rounds=50, verbose=False),
        lgb.log_evaluation(period=100)
    ]
)

# Save model
model.save_model('models/mp/lgbm_final.txt')
```

### Model Validation
Before deploying a model, validate:
- Feature names match exactly (case-sensitive)
- Feature order matches the required sequence
- Model file is saved in text format (not binary)
- Model achieves acceptable RMSE/MAPE on validation set
- Model generalizes to recent time periods

### Model Versioning
- Maintain version history of model files
- Document training data date ranges
- Record model performance metrics
- Keep backup of previous working models

## Adding a New State

The system is designed to support unlimited states without modifying core code. Follow this step-by-step process to add a new state.

### Step 1: Train the ML Model

Train a LightGBM model using historical demand data for the new state. Ensure the model uses the exact 9 features in the correct order (see Model Requirements section).

**Save the model:**
```bash
models/{state_code}/lgbm_final.txt
```

For example, for Gujarat:
```bash
models/gj/lgbm_final.txt
```

### Step 2: Determine MERIT India State Code

Find the correct MERIT state code by visiting:
```
https://meritindia.in/StateWiseDetails/BindCurrentStateStatus?StateCode=XX
```

Common MERIT state codes (verify on meritindia.in):

| State | MERIT Code |
|-------|------------|
| Madhya Pradesh | MPD |
| Gujarat | GJD |
| Maharashtra | MHD |
| Rajasthan | RJD |
| Uttar Pradesh | UPD |
| Delhi | DLD |
| Karnataka | KND |
| Tamil Nadu | TND |

### Step 3: Define Weather Cities

Select major cities in the state with their coordinates and population weights. These weights should reflect the relative population or load share and ideally sum to 1.0.

**Example cities for Gujarat:**
- Ahmedabad (largest city)
- Surat (major industrial hub)
- Vadodara (third-largest city)
- Rajkot (major city in Saurashtra)

### Step 4: Create YAML Configuration

Create a new YAML file in `config/states/{code}.yaml` using `config/states/mp.yaml` as a template.

**Example: `config/states/gj.yaml`**
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

**YAML Field Reference:**

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `code` | Yes | string | Short slug, lowercase (e.g., `gj`). Used in URLs and folder names |
| `name` | Yes | string | Display name shown in dashboard dropdown |
| `merit_state_code` | Yes | string | MERIT India API state code (e.g., `GJD`) |
| `merit_url` | Yes | string | Full MERIT API URL including StateCode query param |
| `model_path` | Yes | string | Path to LightGBM `.txt` file, relative to project root |
| `fallback_demand_mw` | No | number | Last-resort MW constant when all lag lookups fail (default: 14500) |
| `timezone` | No | string | IANA timezone for time features (default: `Asia/Kolkata`) |
| `is_active` | No | boolean | If `false`, state hidden from API/dashboard/scheduler (default: `true`) |
| `cities` | Yes | dict | Dict of `{city_name: {lat, lon, weight}}` for weather weighting |

### Step 5: Register the State

Run the seed command to register the state in the database:

```bash
python manage.py seed_state config/states/gj.yaml
```

**Expected output:**
```
State 'Gujarat' (gj) registered/updated successfully.
```

The state will immediately appear in:
- Dashboard state dropdown
- `/api/states/` endpoint
- Django admin → States section

### Step 6: Import Historical Data (Recommended)

Import historical demand data to enable accurate lag features from day one:

```bash
python manage.py import_historical_demand \
  --state gj \
  --csv path/to/gujarat_demand.csv \
  --limit 0
```

**CSV Format:**
```csv
datetime,hourly_demand_met_mw
2024-01-01 00:00:00,18000
2024-01-01 00:15:00,17950
```

Without historical data, the system uses fallback values for lag features during the first 7 days of operation.

### Step 7: Run Initial Prediction

Test the new state with a manual prediction:

```bash
python manage.py refresh_demand --state gj
```

### Step 8: Verify Deployment

Verify the new state is working correctly:

1. **Dashboard**: Open http://127.0.0.1:8000/ and select the new state from dropdown
2. **API**: Run `curl http://127.0.0.1:8000/api/states/gj/today/`
3. **Admin**: Login to http://127.0.0.1:8000/admin/ and check States section
4. **CSV Files**: Verify `data/states/gj/demand_log.csv` and `prediction_log.csv` exist
5. **Logs**: Check `logs/demand_predictor.log` for any errors

### Step 9: Monitor Performance

After deployment, monitor:
- Prediction accuracy (MAPE, RMSE)
- API response times
- Data freshness (last prediction timestamp)
- Error rates in logs

## State YAML Configuration Reference

### Complete Example

```yaml
code: mp
name: Madhya Pradesh
merit_state_code: MPD
merit_url: https://meritindia.in/StateWiseDetails/BindCurrentStateStatus?StateCode=MPD
model_path: models/mp/lgbm_final.txt
fallback_demand_mw: 14500
timezone: Asia/Kolkata
is_active: true
cities:
  indore:
    lat: 22.7196
    lon: 75.8577
    weight: 0.292095
  bhopal:
    lat: 23.2599
    lon: 77.4126
    weight: 0.21238938
  jabalpur:
    lat: 23.1815
    lon: 79.9864
    weight: 0.15929204
  gwalior:
    lat: 26.2183
    lon: 78.1828
    weight: 0.12389381
  ujjain:
    lat: 23.1765
    lon: 75.7885
    weight: 0.09734513
  singrauli:
    lat: 24.1998
    lon: 82.6754
    weight: 0.11504425
```

### Field Details

**code**: Short identifier used throughout the system
- Must be lowercase
- No spaces or special characters
- Used in URLs: `/api/states/{code}/today/`
- Used in folder names: `models/{code}/`, `data/states/{code}/`

**name**: Human-readable display name
- Shown in dashboard dropdown
- Can include spaces and special characters
- Example: "Madhya Pradesh", "Dadra & Nagar Haveli"

**merit_state_code**: MERIT India API code
- Usually 3 letters (e.g., MPD, GJD)
- Case-sensitive as per MERIT documentation
- Used to construct MERIT API URL

**merit_url**: Complete MERIT API endpoint
- Must include StateCode query parameter
- Should be tested in browser before use
- Example: `https://meritindia.in/StateWiseDetails/BindCurrentStateStatus?StateCode=MPD`

**model_path**: Path to trained model file
- Relative to project root
- Must point to existing `.txt` file
- Example: `models/mp/lgbm_final.txt`

**fallback_demand_mw**: Emergency fallback value
- Used when all lag lookups fail
- Should be near average demand for the state
- Prevents prediction failures during data gaps

**timezone**: IANA timezone identifier
- Default: `Asia/Kolkata`
- Must be valid IANA timezone
- Affects temporal feature computation

**is_active**: State activation flag
- Default: `true`
- Set to `false` to temporarily disable state
- Inactive states excluded from API, dashboard, and scheduler

**cities**: Weather station configuration
- Dictionary of city configurations
- Each city needs: lat, lon, weight
- Weights should sum to approximately 1.0
- Used for population-weighted temperature

## Scheduler Behavior

The system includes an automatic background scheduler that refreshes predictions for all active states without manual intervention.

### How It Works

**Initialization:**
- The scheduler starts automatically when Django loads the application
- Initialized in `predictions/apps.PredictionsConfig.ready()`
- Only runs in the main Django process (not during auto-reload)

**Schedule:**
- Runs every 5 minutes
- Aligns to 15-minute intervals (00, 15, 30, 45)
- Processes all states where `is_active=true`

**Process:**
For each active state, the scheduler:
1. Fetches current demand from MERIT India API
2. Retrieves weather data from Open-Meteo
3. Computes temporal and lag features
4. Runs LightGBM model inference
5. Saves prediction record to database
6. Syncs data to CSV files

### Disabling the Scheduler

**For Development:**
Set environment variable before starting the server:
```bash
ENABLE_SCHEDULER=false python manage.py runserver
```

**For Configuration:**
Set in `.env` file:
```env
ENABLE_SCHEDULER=false
```

**When to Disable:**
- During development and testing
- When running manual predictions only
- To prevent duplicate predictions in multi-process deployments

### Production Alternative

For production deployments, consider using cron instead of the built-in scheduler:

```cron
*/5 * * * * cd /path/to/NTPC-NVVN-MP && /path/to/venv/bin/python manage.py refresh_demand
```

**Advantages of cron:**
- More reliable across server restarts
- Better logging and monitoring integration
- Easier to debug timing issues
- Standard system administration practice

## Data Storage and Logs

### Primary Storage: SQLite Database

**Location:** `db.sqlite3` (project root)

**Tables:**

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `states_state` | State configuration | code, name, merit_url, model_path, cities |
| `states_demandreading` | Actual demand snapshots | state, timestamp, demand_mw, source |
| `states_predictionrecord` | Predictions + features | state, timestamp, actual_demand, predicted_demand, all features |

**Advantages of SQLite:**
- Zero configuration required
- Single file for easy backup
- Suitable for medium-scale deployments
- Can be replaced with PostgreSQL for production

### Secondary Storage: CSV Logs

**Location:** `data/states/{code}/`

**Files:**
- `demand_log.csv`: Historical demand readings
- `prediction_log.csv`: Prediction records with full feature vectors

**Sync Behavior:**
- CSV files are updated automatically on every database write
- Handled by `predictions/services/csv_sync.py`
- Provides portability and external analysis access

**CSV Schema - demand_log.csv:**
```csv
timestamp,state,demand_mw,source
2024-06-24 00:00:00,mp,12500,api
2024-06-24 00:15:00,mp,12450,api
```

**CSV Schema - prediction_log.csv:**
```csv
timestamp,state,actual_demand,predicted_demand,temp_weighted,month,holiday,is_weekend,hour,minute,y_lag_1,y_lag_24h,y_lag_7d
2024-06-24 00:00:00,mp,12500,12520,28.5,6,0,0,0,0,12480,12400,12300
```

### Application Logs

**Location:** `logs/demand_predictor.log`

**Configuration:**
- Rotating file handler (5 MB max, 5 backup files)
- Configured in `demand_predictor/settings.py`
- Log level controlled by `LOG_LEVEL` environment variable

**Log Levels:**
- `DEBUG`: Detailed diagnostic information
- `INFO`: General informational messages (default)
- `WARNING`: Warning messages for potential issues
- `ERROR`: Error messages for failures
- `CRITICAL`: Critical errors requiring immediate attention

**What Gets Logged:**
- API fetch successes and failures
- Prediction run results
- Feature computation warnings
- Database operation errors
- Scheduler activity

## Lag Feature Fallback Logic

The system uses sophisticated fallback logic to handle missing historical data for lag features (`y_lag_1`, `y_lag_24h`, `y_lag_7d`).

### Fallback Hierarchy

When a lag value is requested, the system tries these methods in order:

1. **Exact Historical Match**
   - Looks for demand reading at the exact timestamp
   - Checks database first, then CSV files
   - Most accurate when available

2. **Nearest Neighbor (±30 minutes)**
   - Finds the closest demand reading within 30 minutes
   - Useful when timestamps don't align perfectly
   - Provides reasonable approximation

3. **Live API Fallback**
   - Fetches current demand from MERIT India API
   - Only used for live predictions (not historical forecasts)
   - Ensures predictions use the latest available data

4. **Decay from Most Recent**
   - Uses the most recent available demand value
   - Applies decay factors for longer lags:
     - `y_lag_24h = y_lag_1 × 0.99`
     - `y_lag_7d = y_lag_1 × 0.98`
   - Accounts for natural demand variation over time

5. **State Fallback Constant**
   - Uses `fallback_demand_mw` from state configuration
   - Last resort when all other methods fail
   - Prevents prediction failures

### Special Case: 24h/7d Lag Enhancement

If the 24h or 7d lag resolves to the fallback constant, the system derives a better estimate from `y_lag_1`:
- `y_lag_24h_derived = y_lag_1 × 0.99`
- `y_lag_7d_derived = y_lag_1 × 0.98`

This provides more realistic lag values even when historical data is limited.

### First 7 Days Behavior

During the first 7 days of operation (without historical import):
- `y_lag_1`: Uses live API or recent readings
- `y_lag_24h`: Uses decay from `y_lag_1` or fallback
- `y_lag_7d`: Uses decay from `y_lag_1` or fallback

Prediction accuracy improves gradually as historical data accumulates. Importing historical data is recommended for immediate optimal performance.

## Testing and Quality Checks

### Running Tests

The project includes pytest for automated testing:

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest predictions/tests.py

# Run with coverage
pytest --cov=predictions --cov=states --cov=utils
```

### Django System Checks

Run Django's built-in configuration checks:

```bash
python manage.py check
```

This verifies:
- Model configuration
- URL routing
- Settings configuration
- App registration

### Manual Testing Checklist

**After Setup:**
- [ ] Dashboard loads without errors
- [ ] State dropdown shows configured states
- [ ] Today view displays actual and predicted data
- [ ] Tomorrow view shows 96-slot forecast
- [ ] API endpoints return valid JSON

**After Adding State:**
- [ ] State appears in dashboard dropdown
- [ ] State appears in `/api/states/` response
- [ ] State shows in Django admin
- [ ] Manual prediction succeeds
- [ ] CSV files are created

**Periodic Monitoring:**
- [ ] Predictions are updating every 5 minutes
- [ ] API response times are acceptable
- [ ] No errors in application logs
- [ ] Database file size is reasonable
- [ ] CSV files are syncing correctly

## Common Issues and Troubleshooting

### Configuration Issues

**Issue: `KeyError: 'DJANGO_SECRET_KEY'`**
- **Cause**: Missing or incorrect `.env` file
- **Solution**: Create `.env` file with `DJANGO_SECRET_KEY=your-secret-key`

**Issue: State not appearing in dashboard/API**
- **Cause**: State not registered or inactive
- **Solution**:
  1. Run `python manage.py seed_state config/states/{code}.yaml`
  2. Verify `is_active: true` in YAML or admin
  3. Check database in Django admin

**Issue: `ModuleNotFoundError` for dependencies**
- **Cause**: Virtual environment not activated or dependencies not installed
- **Solution**:
  ```bash
  source .venv/bin/activate
  pip install -r requirements.txt
  ```

### Data Issues

**Issue: No actual demand line in chart**
- **Cause**: MERIT API not reachable or no recent data
- **Solution**:
  1. Test MERIT URL in browser
  2. Run `python manage.py refresh_demand --state {code}`
  3. Check Demand readings in admin
  4. Verify internet connectivity

**Issue: Lag values look wrong in first week**
- **Cause**: No historical data for lag computation
- **Solution**: This is expected behavior. Import historical data or wait 7 days for accumulation.

**Issue: Predictions seem inaccurate**
- **Cause**: Model may need retraining or features are incorrect
- **Solution**:
  1. Verify model file exists and is valid
  2. Check feature values in admin → Prediction records
  3. Compare with similar time periods
  4. Consider retraining model with recent data

### API Issues

**Issue: API returns 404 for state endpoint**
- **Cause**: State code incorrect or state not active
- **Solution**:
  1. Verify state code in URL matches YAML
  2. Check state is active in admin
  3. Run `seed_state` command again

**Issue: API returns 500 error**
- **Cause**: Server error in prediction pipeline
- **Solution**:
  1. Check `logs/demand_predictor.log` for stack trace
  2. Verify model file exists and is readable
  3. Test with `python manage.py refresh_demand --state {code}`

### Scheduler Issues

**Issue: Predictions not updating automatically**
- **Cause**: Scheduler disabled or not running
- **Solution**:
  1. Check `ENABLE_SCHEDULER=true` in `.env`
  2. Restart server
  3. Check logs for scheduler startup message
  4. Consider using cron as alternative

**Issue: Duplicate predictions**
- **Cause**: Multiple scheduler instances running
- **Solution**:
  1. Ensure only one server instance is running
  2. Check for cron jobs also running refresh
  3. Disable built-in scheduler if using cron

### Admin Issues

**Issue: Can't login to admin**
- **Cause**: No superuser created or wrong credentials
- **Solution**:
  ```bash
  python manage.py createsuperuser
  # or reset password
  python manage.py changepassword <username>
  ```

**Issue: Admin shows no data**
- **Cause**: Database not migrated or no data imported
- **Solution**:
  1. Run `python manage.py migrate`
  2. Run `python manage.py refresh_demand --state {code}`
  3. Import historical data if needed

### Performance Issues

**Issue: Slow API response times**
- **Cause**: Large database or inefficient queries
- **Solution**:
  1. Consider database indexing
  2. Archive old data
  3. Upgrade to PostgreSQL for production

**Issue: High memory usage**
- **Cause**: Large model files or data in memory
- **Solution**:
  1. Monitor model file sizes
  2. Implement data archiving
  3. Consider server resources

## Production Deployment

### Deployment Checklist

**Before Deployment:**
- [ ] Set `DEBUG=false` in `.env`
- [ ] Use strong `DJANGO_SECRET_KEY`
- [ ] Configure appropriate `ALLOWED_HOSTS`
- [ ] Set up production database (PostgreSQL recommended)
- [ ] Configure static file serving
- [ ] Set up proper logging
- [ ] Configure monitoring and alerts
- [ ] Test backup and restore procedures

**Deployment Options:**

**Option 1: Gunicorn with Nginx**
```bash
# Install gunicorn
pip install gunicorn

# Run with gunicorn
gunicorn demand_predictor.wsgi:application --bind 0.0.0.0:8000
```

**Option 2: Docker**
```dockerfile
FROM python:3.12
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "demand_predictor.wsgi:application", "--bind", "0.0.0.0:8000"]
```

**Option 3: Systemd Service**
```ini
[Unit]
Description=Django Demand Predictor
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/NTPC-NVVN-MP
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/gunicorn demand_predictor.wsgi:application --bind 0.0.0.0:8000

[Install]
WantedBy=multi-user.target
```

### Security Considerations

- **Secret Key**: Use environment variable, never commit to git
- **Database**: Use strong password for PostgreSQL
- **HTTPS**: Enable SSL/TLS in production
- **Firewall**: Restrict access to admin interface
- **Updates**: Keep dependencies updated regularly

### Monitoring

Monitor these metrics in production:
- Prediction success rate
- API response times
- Error rates in logs
- Database size and performance
- Disk space usage
- Memory and CPU usage

## Extended Documentation

For detailed operational procedures, including:
- Complete admin workflows
- Full state onboarding procedures
- Advanced troubleshooting
- Performance optimization
- Backup and restore procedures

See: **[docs/OPERATIONS_GUIDE.md](docs/OPERATIONS_GUIDE.md)**

## Contributing

When contributing to this project:
1. Follow the existing code style
2. Add tests for new features
3. Update documentation
4. Test with multiple states
5. Verify backward compatibility



## Support

For technical support or questions:
- Check the troubleshooting section above
- Review `docs/OPERATIONS_GUIDE.md`
- Check application logs in `logs/demand_predictor.log`
- Contact the development team
