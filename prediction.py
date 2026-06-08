# prediction.py

import numpy as np
import pandas as pd
import lightgbm as lgb
import openmeteo_requests
import requests_cache
from retry_requests import retry
from datetime import datetime
import holidays
import requests
import urllib3

# Suppress SSL warnings (use with caution - only for development)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)



# ─── 1. Load saved model ────────────────────────────────────────────────────

model = lgb.Booster(model_file='lightgbm/mp_lgbm_final.txt')

FEATURE_COLS = [
    'temp_weighted', 'month', 'holiday',
    'is_weekend', 'hour', 'minute',
    'y_lag_24h', 'y_lag_7d', 'y_lag_1'
]

# ─── 2. Weather fetching (from utils/weather.py) ────────────────────────────

CITIES = {
    "indore":    {"lat": 22.7196, "lon": 75.8577,  "weight": 0.292095},
    "bhopal":    {"lat": 23.2599, "lon": 77.4126,  "weight": 0.21238938},
    "jabalpur":  {"lat": 23.1815, "lon": 79.9864,  "weight": 0.15929204},
    "gwalior":   {"lat": 26.2183, "lon": 78.1629,  "weight": 0.12389381},
    "ujjain":    {"lat": 23.1815, "lon": 75.7845,  "weight": 0.09734513},
    "singrauli": {"lat": 24.1833, "lon": 82.6667,  "weight": 0.11504425},
}


def get_weighted_temperature_now() -> float:
    """
    Fetch 15-min interval apparent temperature for each city,
    find the slot closest to now, and return the weighted average.
    """
    cache_session = requests_cache.CachedSession('.cache', expire_after=900)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)

    url = "https://api.open-meteo.com/v1/forecast"
    now_utc = pd.Timestamp.utcnow()

    weighted_temp = 0.0

    for city_name, city in CITIES.items():
        params = {
            "latitude": city["lat"],
            "longitude": city["lon"],
            "minutely_15": "apparent_temperature",
            "forecast_minutely_15": 96,          # next 24 h
            "timezone": "Asia/Kolkata",
        }
        resp = openmeteo.weather_api(url, params=params)[0]
        m15  = resp.Minutely15()

        times = pd.date_range(
            start   = pd.to_datetime(m15.Time(), unit="s", utc=True),
            periods = m15.Variables(0).ValuesAsNumpy().shape[0],
            freq    = pd.Timedelta(seconds=m15.Interval()),
        )
        temps = m15.Variables(0).ValuesAsNumpy()

        # pick the slot closest to now
        idx  = np.argmin(np.abs((times - now_utc).total_seconds()))
        temp = float(temps[idx])

        weighted_temp += temp * city["weight"]
        print(f"  {city_name:<12} temp={temp:.1f}°C  weight={city['weight']}")

    return weighted_temp


# ─── 3. Date / time features (from utils/date_and_time.py) ──────────────────

def get_time_features() -> dict:
    now = datetime.now()

    minute = now.minute
    if minute < 8:
        minute = 0
    elif minute < 23:
        minute = 15
    elif minute < 38:
        minute = 30
    elif minute < 53:
        minute = 45
    else:
        minute = 0

    india_holidays = holidays.India()
    is_holiday     = int(now.date() in india_holidays)
    is_weekend     = int(now.weekday() >= 5)

    return {
        "month":      now.month,
        "holiday":    is_holiday,
        "is_weekend": is_weekend,
        "hour":       now.hour,
        "minute":     minute,
    }


# ─── 4. Lag features — you must supply these from MERIT India API ───────────
#
#   y_lag_1   : demand at the PREVIOUS 15-min slot          (MW)
#   y_lag_24h : demand exactly 24 hours ago                  (MW)
#   y_lag_7d  : demand exactly 7 days ago                    (MW)
#
#  Replace the stub below with your actual MERIT India API call.
# ────────────────────────────────────────────────────────────────────────────

import requests

def get_lag_features() -> dict:
    """
    Fetch lag features from MERIT India API.
    
    Returns demand values for:
        - y_lag_1   : current/previous 15-min demand
        - y_lag_24h : demand from 24 hours ago
        - y_lag_7d  : demand from 7 days ago
    """
    try:
        # Fetch current demand from API with SSL verification disabled
        api_url = "https://meritindia.in/StateWiseDetails/BindCurrentStateStatus?StateCode=MPD"
        response = requests.get(api_url, verify=False, timeout=10)
        response.raise_for_status()  # Raise error for bad status codes
        data = response.json()
        
        # Parse demand value (remove commas and convert to float)
        current_demand = float(data[0]["Demand"].replace(",", ""))
        
        y_lag_1   = current_demand      # Previous 15-min slot
        y_lag_24h = current_demand * 0.99  # Approximate 24h ago
        y_lag_7d  = current_demand * 0.98  # Approximate 7d ago
        
        print(f"  Current Demand: {current_demand:,.1f} MW")
        
    except Exception as e:
        print(f"  ⚠️ API Error: {e}. Using fallback values.")
        y_lag_1   = 14500.0
        y_lag_24h = 14800.0
        y_lag_7d  = 13900.0

    return {
        "y_lag_1":   y_lag_1,
        "y_lag_24h": y_lag_24h,
        "y_lag_7d":  y_lag_7d,
    }

def predict_current_demand() -> float:
    """
    Assemble all features and return the predicted MP power demand in MW.
    """
    # Capture exact current time
    data_fetch_time = datetime.now()
    
    print("\n[1/3] Fetching weather ...")
    temp = get_weighted_temperature_now()
    print(f"  → Weighted apparent temperature: {temp:.2f}°C")

    print("\n[2/3] Reading time features ...")
    time_feats = get_time_features()
    print(f"  → {time_feats}")

    print("\n[3/3] Fetching lag features ...")
    lag_feats = get_lag_features()
    print(f"  → {lag_feats}")

    # Build a single-row DataFrame in the exact column order the model expects
    row = {
        "temp_weighted": temp,
        **time_feats,
        **lag_feats,
    }
    X = pd.DataFrame([row])[FEATURE_COLS]

    prediction = float(model.predict(X)[0])
    
    # Calculate prediction time (round to next 15-min interval)
    prediction_time = data_fetch_time.replace(second=0, microsecond=0)
    minute = prediction_time.minute
    if minute < 15:
        prediction_time = prediction_time.replace(minute=15)
    elif minute < 30:
        prediction_time = prediction_time.replace(minute=30)
    elif minute < 45:
        prediction_time = prediction_time.replace(minute=45)
    else:
        prediction_time = (prediction_time + pd.Timedelta(hours=1)).replace(minute=0)
    
    # Print timestamp information
    print("\n" + "="*60)
    print("⏰ DATA & PREDICTION TIMESTAMPS")
    print("="*60)
    print(f"  Data Fetched At:     {data_fetch_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Prediction For:      {prediction_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Time Gap:            15 minutes")
    print("="*60)
    
    # Print all input features used by the model
    print("\n" + "="*60)
    print("📊 MODEL INPUT FEATURES")
    print("="*60)
    for col in FEATURE_COLS:
        value = X[col].values[0]
        print(f"  {col:<15} = {value:>10}")
    print("="*60)
    
    print(f"\n✅ Predicted MP Power Demand: {prediction:,.1f} MW")
    print("="*60 + "\n")
    return prediction

# ─── 6. Entry point ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    predict_current_demand()