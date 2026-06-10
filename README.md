# NTPC-NVVN-MP Power Demand Prediction
This project predicts Madhya Pradesh (MP) power demand using a trained LightGBM model and live utility data sources.

The prediction pipeline now reads feature data from modules inside `utils/` and writes run outputs to `prediction_log.csv` at the project root.

## What the script does
Running `prediction.py` performs:
1. Weather feature fetch (`temp_weighted`) from `utils/weather.py`
2. Time feature extraction (`month`, `holiday`, `is_weekend`, `hour`, `minute`) from `utils/time_features.py`
3. Lag feature construction (`y_lag_1`, `y_lag_24h`, `y_lag_7d`) from `utils/lag_store.py`
4. Model inference using `lightgbm/mp_lgbm_final.txt`
5. Output logging via `utils/log_store.py` into `prediction_log.csv`

## Project structure
```text
.
├── prediction.py                 # Main entrypoint
├── lightgbm/
│   └── mp_lgbm_final.txt         # Trained LightGBM model
├── utils/
│   ├── weather.py                # Weighted weather feature fetch
│   ├── time_features.py          # Calendar/time feature generation
│   ├── lag_store.py              # Demand history + lag feature fallback chain
│   └── log_store.py              # Prediction run logger
├── prediction_log.csv            # Prediction output log (created/updated at runtime)
└── data/
    └── demand_log.csv            # Stored demand history used by lag logic
```

## Requirements
Install dependencies in your Python environment:

```bash
pip install lightgbm pandas numpy requests urllib3 holidays requests-cache retry-requests openmeteo-requests pytest
```

## How to run
From the project root:

```bash
python3 prediction.py
```

The script prints:
- fetched features
- prediction timestamp and value
- actual demand (if API is available)
- confirmation that the result was logged

## Output files
### `prediction_log.csv` (project root)
One row per prediction run with this schema:

- `timestamp`
- `actual_demand`
- `predicted_demand`
- `temp_weighted`
- `month`
- `holiday`
- `is_weekend`
- `hour`
- `minute`
- `y_lag_1`
- `y_lag_24h`
- `y_lag_7d`

### `data/demand_log.csv`
Stores demand readings that support lag feature construction and fallback behavior.

## Notes on lag fallback behavior
If exact lag values are not available in stored demand history, `utils/lag_store.py` uses this fallback chain:
1. Exact timestamp match in demand log
2. Nearest timestamp within ±30 minutes
3. Live MERIT India API value
4. Decayed most-recent stored value
5. Hardcoded constant fallback

## Quick verification
After running `prediction.py`, confirm log output:

```bash
head -n 5 prediction_log.csv
```

You should see the header and at least one data row.
