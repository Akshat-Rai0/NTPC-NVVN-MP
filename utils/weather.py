"""
utils/weather.py

Fetches 15-min apparent temperature forecasts for 6 MP cities
from Open-Meteo and returns a population-weighted average.

Public API:
    get_current_weighted_temp() -> float
    get_weighted_temperature_forecast() -> pd.DataFrame
"""

import logging
import numpy as np
import pandas as pd
import requests
import requests_cache
import openmeteo_requests
from retry_requests import retry

log = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

FORECAST_POINTS = 96          # 96 × 15 min = 24 h
OPENMETEO_URL   = "https://api.open-meteo.com/v1/forecast"
TIMEZONE        = "Asia/Kolkata"

CITIES = {
    "indore":    {"lat": 22.7196, "lon": 75.8577,  "weight": 0.292095},
    "bhopal":    {"lat": 23.2599, "lon": 77.4126,  "weight": 0.21238938},
    "jabalpur":  {"lat": 23.1815, "lon": 79.9864,  "weight": 0.15929204},
    "gwalior":   {"lat": 26.2183, "lon": 78.1828,  "weight": 0.12389381},
    "ujjain":    {"lat": 23.1765, "lon": 75.7885,  "weight": 0.09734513},
    "singrauli": {"lat": 24.1998, "lon": 82.6754,  "weight": 0.11504425},
}

# ── Shared HTTP session (cache + retry) ───────────────────────────────────────

_cache_session  = requests_cache.CachedSession(".cache", expire_after=3600)
_retry_session  = retry(_cache_session, retries=5, backoff_factor=0.2)
_openmeteo      = openmeteo_requests.Client(session=_retry_session)

# ── Primary source (minutely_15) ──────────────────────────────────────────────

def _get_minutely_forecast(lat: float, lon: float):
    params = {
        "latitude":              lat,
        "longitude":             lon,
        "minutely_15":           "apparent_temperature",
        "forecast_minutely_15":  FORECAST_POINTS,
        "timezone":              TIMEZONE,
    }
    response = _openmeteo.weather_api(OPENMETEO_URL, params=params)[0]
    m        = response.Minutely15()
    values   = m.Variables(0).ValuesAsNumpy()

    if len(values) != FORECAST_POINTS:
        raise ValueError(
            f"Expected {FORECAST_POINTS} points, got {len(values)}"
        )

    timestamps = pd.date_range(
        start   = pd.to_datetime(m.Time(), unit="s", utc=True)
                    .tz_convert(TIMEZONE),
        periods = len(values),
        freq    = pd.Timedelta(seconds=m.Interval()),
    )
    return timestamps, values


# ── Fallback source (hourly → interpolated to 15 min) ────────────────────────

def _get_hourly_fallback(lat: float, lon: float):
    params = {
        "latitude":     lat,
        "longitude":    lon,
        "hourly":       "apparent_temperature",
        "forecast_days": 1,
        "timezone":     TIMEZONE,
    }
    r = _retry_session.get(OPENMETEO_URL, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()

    times = pd.to_datetime(data["hourly"]["time"]).tz_localize(TIMEZONE)
    temps = np.array(data["hourly"]["apparent_temperature"])

    hourly  = pd.DataFrame({"temperature": temps}, index=times)
    minutely = hourly.resample("15min").interpolate(method="time")

    vals = minutely["temperature"].values[:FORECAST_POINTS]
    if len(vals) < FORECAST_POINTS:
        log.warning(f"Hourly fallback only returned {len(vals)} points")

    return minutely.index[:FORECAST_POINTS], vals


# ── Per-city safe wrapper ─────────────────────────────────────────────────────

def _get_city_forecast(city: str, lat: float, lon: float):
    try:
        log.info(f"{city}: trying minutely_15")
        return _get_minutely_forecast(lat, lon)
    except Exception as e:
        log.warning(f"{city}: minutely failed ({e}) — trying hourly fallback")

    try:
        return _get_hourly_fallback(lat, lon)
    except Exception as e:
        log.error(f"{city}: both sources failed ({e})")
        return None


# ── Public: full forecast DataFrame ──────────────────────────────────────────

def get_weighted_temperature_forecast() -> pd.DataFrame:
    """
    Returns a DataFrame with columns:
        datetime                        (IST, tz-aware)
        weighted_apparent_temperature   (°C)
    covering the next 24 h at 15-min resolution.
    """
    successful = []

    for city, info in CITIES.items():
        result = _get_city_forecast(city, info["lat"], info["lon"])
        if result is not None:
            timestamps, temps = result
            successful.append({
                "city":       city,
                "weight":     info["weight"],
                "temps":      temps,
                "timestamps": timestamps,
            })

    if not successful:
        raise RuntimeError("All city forecasts failed — cannot continue")

    total_weight  = sum(x["weight"] for x in successful)
    weighted_temp = np.zeros(len(successful[0]["temps"]))

    for item in successful:
        weighted_temp += item["temps"] * (item["weight"] / total_weight)

    return pd.DataFrame({
        "datetime":                     successful[0]["timestamps"],
        "weighted_apparent_temperature": weighted_temp,
    })


# ── Public: single number for the current slot ───────────────────────────────

def get_current_weighted_temp() -> float:
    """
    Returns the weighted apparent temperature (°C) for the
    15-min slot closest to right now.
    """
    df  = get_weighted_temperature_forecast()
    now = pd.Timestamp.now(tz=TIMEZONE)
    idx = np.argmin(np.abs((df["datetime"] - now).dt.total_seconds()))
    temp = float(df["weighted_apparent_temperature"].iloc[idx])
    log.info(f"Current weighted temp: {temp:.2f}°C")
    return temp


# ── CLI smoke-test ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    df = get_weighted_temperature_forecast()

    df.to_csv("weighted_temperature_forecast.csv", index=False)

    print(df.head(8).to_string(index=False))
    print(f"\nCurrent slot: {get_current_weighted_temp():.2f}°C")