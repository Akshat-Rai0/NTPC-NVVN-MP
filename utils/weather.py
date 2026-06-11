"""
utils/weather.py

Fetches 15-min apparent temperature forecasts and returns population-weighted averages.
State-aware via cities dict in StateConfig.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

import numpy as np
import openmeteo_requests
import pandas as pd
import requests
import requests_cache
from retry_requests import retry

if TYPE_CHECKING:
    from predictions.services.registry import StateConfig

log = logging.getLogger(__name__)

FORECAST_POINTS = 96
OPENMETEO_URL = "https://api.open-meteo.com/v1/forecast"
TIMEZONE = "Asia/Kolkata"

_DEFAULT_CITIES = {
    "indore": {"lat": 22.7196, "lon": 75.8577, "weight": 0.292095},
    "bhopal": {"lat": 23.2599, "lon": 77.4126, "weight": 0.21238938},
    "jabalpur": {"lat": 23.1815, "lon": 79.9864, "weight": 0.15929204},
    "gwalior": {"lat": 26.2183, "lon": 78.1828, "weight": 0.12389381},
    "ujjain": {"lat": 23.1765, "lon": 75.7885, "weight": 0.09734513},
    "singrauli": {"lat": 24.1998, "lon": 82.6754, "weight": 0.11504425},
}

_openmeteo = None
_retry_session = None

def _get_openmeteo_client():
    global _openmeteo, _retry_session
    if _openmeteo is None:
        from django.conf import settings
        cache_path = str(settings.BASE_DIR / ".cache")
        _cache_session = requests_cache.CachedSession(cache_path, expire_after=3600)
        _retry_session = retry(_cache_session, retries=5, backoff_factor=0.2)
        _openmeteo = openmeteo_requests.Client(session=_retry_session)
    return _openmeteo, _retry_session


def _cities(config: StateConfig | None) -> dict:
    if config and config.cities:
        return config.cities
    return _DEFAULT_CITIES


def _timezone(config: StateConfig | None) -> str:
    if config and config.timezone:
        return config.timezone
    return TIMEZONE


def _get_minutely_forecast(lat: float, lon: float, forecast_points: int, timezone: str):
    client, _ = _get_openmeteo_client()
    params = {
        "latitude": lat,
        "longitude": lon,
        "minutely_15": "apparent_temperature",
        "forecast_minutely_15": forecast_points,
        "timezone": timezone,
    }
    response = client.weather_api(OPENMETEO_URL, params=params)[0]
    m = response.Minutely15()
    values = m.Variables(0).ValuesAsNumpy()
    timestamps = pd.date_range(
        start=pd.to_datetime(m.Time(), unit="s", utc=True).tz_convert(timezone),
        periods=len(values),
        freq=pd.Timedelta(seconds=m.Interval()),
    )
    return timestamps, values


def _get_hourly_fallback(
    lat: float,
    lon: float,
    forecast_days: int,
    timezone: str,
    forecast_points: int,
):
    _, retry_session = _get_openmeteo_client()
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "apparent_temperature",
        "forecast_days": forecast_days,
        "timezone": timezone,
    }
    r = retry_session.get(OPENMETEO_URL, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    times = pd.to_datetime(data["hourly"]["time"]).tz_localize(timezone)
    temps = np.array(data["hourly"]["apparent_temperature"])
    hourly = pd.DataFrame({"temperature": temps}, index=times)
    minutely = hourly.resample("15min").interpolate(method="time")
    return minutely.index[:forecast_points], minutely["temperature"].values[:forecast_points]


def _get_city_forecast(
    city: str,
    lat: float,
    lon: float,
    forecast_points: int,
    forecast_days: int,
    timezone: str,
):
    try:
        return _get_minutely_forecast(lat, lon, forecast_points, timezone)
    except Exception as exc:
        log.warning("%s: minutely failed (%s) — trying hourly fallback", city, exc)
    try:
        return _get_hourly_fallback(lat, lon, forecast_days, timezone, forecast_points)
    except Exception as exc:
        log.error("%s: both sources failed (%s)", city, exc)
        return None


def get_weighted_temperature_forecast(
    config: StateConfig | None = None,
    forecast_days: int = 1,
) -> pd.DataFrame:
    cities = _cities(config)
    timezone = _timezone(config)
    forecast_points = min(FORECAST_POINTS * forecast_days, 96 * forecast_days)
    successful = []

    for city, info in cities.items():
        result = _get_city_forecast(
            city,
            info["lat"],
            info["lon"],
            forecast_points,
            forecast_days,
            timezone,
        )
        if result is not None:
            timestamps, temps = result
            successful.append({
                "city": city,
                "weight": info["weight"],
                "temps": temps,
                "timestamps": timestamps,
            })

    if not successful:
        raise RuntimeError("All city forecasts failed — cannot continue")

    total_weight = sum(item["weight"] for item in successful)
    weighted_temp = np.zeros(len(successful[0]["temps"]))
    for item in successful:
        weighted_temp += item["temps"] * (item["weight"] / total_weight)

    return pd.DataFrame({
        "datetime": successful[0]["timestamps"],
        "weighted_apparent_temperature": weighted_temp,
    })


def get_current_weighted_temp(config: StateConfig | None = None) -> float:
    return get_weighted_temp_at(datetime.now(), config=config)


def get_weighted_temp_at(
    dt: datetime,
    config: StateConfig | None = None,
    forecast_days: int = 16,
) -> float:
    timezone = _timezone(config)
    df = get_weighted_temperature_forecast(config=config, forecast_days=forecast_days)
    target = pd.Timestamp(dt)
    if target.tzinfo is None:
        target = target.tz_localize(timezone)
    else:
        target = target.tz_convert(timezone)
    idx = np.argmin(np.abs((df["datetime"] - target).dt.total_seconds()))
    return float(df["weighted_apparent_temperature"].iloc[idx])
