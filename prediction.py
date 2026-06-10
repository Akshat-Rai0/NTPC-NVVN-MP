import lightgbm as lgb
import pandas as pd
from datetime import datetime

from utils.lag_store import get_current_actual_demand, get_lag_features as _get_lag_features
from utils.log_store import append_run
from utils.time_features import get_time_features as _get_time_features
from utils.weather import get_current_weighted_temp


model = lgb.Booster(model_file="lightgbm/mp_lgbm_final.txt")

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


def get_weighted_temperature_now() -> float:
    """Backward-compatible wrapper for weather utility."""
    return get_current_weighted_temp()


def get_time_features() -> dict:
    """Backward-compatible wrapper for time utility."""
    return _get_time_features()


def get_lag_features() -> dict:
    """Backward-compatible wrapper for lag utility."""
    return _get_lag_features()

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
    actual_demand = get_current_actual_demand()
    
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
    
    append_run(
        {
            "timestamp": data_fetch_time,
            "actual_demand": actual_demand,
            "predicted_demand": prediction,
            "temp_weighted": row["temp_weighted"],
            "month": row["month"],
            "holiday": row["holiday"],
            "is_weekend": row["is_weekend"],
            "hour": row["hour"],
            "minute": row["minute"],
            "y_lag_1": row["y_lag_1"],
            "y_lag_24h": row["y_lag_24h"],
            "y_lag_7d": row["y_lag_7d"],
        }
    )

    print(f"\n✅ Predicted MP Power Demand: {prediction:,.1f} MW")
    if actual_demand is not None:
        print(f"📥 Actual MP Demand (API):    {actual_demand:,.1f} MW")
    print("📝 Logged to:                 prediction_log.csv")
    print("="*60 + "\n")
    return prediction

# ─── 6. Entry point ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    predict_current_demand()