"""Single-slot and batch prediction for a state."""

from __future__ import annotations

from datetime import datetime
from functools import lru_cache
from pathlib import Path

import lightgbm as lgb
import pandas as pd
from django.utils import timezone as django_tz

from predictions.services.csv_sync import sync_demand_reading, sync_prediction_record
from predictions.services.merit_client import fetch_current_demand
from predictions.services.registry import StateConfig, StateRegistry
from states.models import DemandReading, PredictionRecord, State
from utils.lag_store import get_lag_features, write_demand
from utils.time_features import get_time_features
from utils.weather import get_weighted_temp_at

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


_model_mtime: dict[str, float] = {}

@lru_cache(maxsize=32)
def _load_model_cached(model_path: str) -> lgb.Booster:
    return lgb.Booster(model_file=model_path)

def _load_model(model_path: str) -> lgb.Booster:
    mtime = Path(model_path).stat().st_mtime
    if _model_mtime.get(model_path) != mtime:
        _model_mtime[model_path] = mtime
        _load_model_cached.cache_clear()
    return _load_model_cached(model_path)


def _to_local_naive(dt: datetime) -> datetime:
    if django_tz.is_aware(dt):
        return django_tz.localtime(dt).replace(tzinfo=None)
    return dt


def _align_15min(dt: datetime) -> datetime:
    ts = pd.Timestamp(_to_local_naive(dt)).floor("15min")
    return ts.to_pydatetime()


def _make_aware(dt: datetime) -> datetime:
    naive = _align_15min(dt)
    return django_tz.make_aware(naive, django_tz.get_current_timezone())


def _predict_row(row: dict, config: StateConfig) -> float:
    model = _load_model(str(config.absolute_model_path))
    frame = pd.DataFrame([row])[FEATURE_COLS]
    return float(model.predict(frame)[0])


class StatePredictor:
    def __init__(self, state_code: str):
        self.config = StateRegistry.get(state_code)
        self.state = State.objects.get(code=state_code.lower())
        self._warm_lag_store()

    def _warm_lag_store(self) -> None:
        """Pre-populate lag store from DB so lag lookups work at cold start."""
        latest = (
            DemandReading.objects
            .filter(state=self.state)
            .order_by("-timestamp")
            .first()
        )
        if latest is not None:
            write_demand(
                _to_local_naive(latest.timestamp),
                latest.demand_mw,
                source="db",
                config=self.config,
            )
    def predict_at(
        self,
        dt: datetime | None = None,
        chain_values: dict[datetime, float] | None = None,
        forecast_days: int = 16,
        allow_api: bool = False,
    ) -> dict:
        dt_naive = _to_local_naive(dt or django_tz.now())

        temp = get_weighted_temp_at(dt_naive, config=self.config, forecast_days=forecast_days)
        time_feats = get_time_features(dt_naive)
        lag_feats = get_lag_features(
            dt_naive,
            config=self.config,
            chain_values=chain_values,
            allow_api=allow_api,
        )

        row = {"temp_weighted": temp, **time_feats, **lag_feats}
        predicted = _predict_row(row, self.config)
        return {
            "timestamp": _align_15min(dt_naive),
            "predicted_demand": predicted,
            "features": row,
        }

    def predict_now(self) -> dict:
        fetch_time = django_tz.now()
        actual = fetch_current_demand(self.config)
        aligned_naive = _align_15min(fetch_time)
        aligned = _make_aware(fetch_time)

        if actual is not None:
            reading, _ = DemandReading.objects.update_or_create(
                state=self.state,
                timestamp=aligned,
                defaults={"demand_mw": actual, "source": "api"},
            )
            write_demand(aligned_naive, actual, source="api", config=self.config)
            sync_demand_reading(reading)

        result = self.predict_at(fetch_time, allow_api=True)
        record, _ = PredictionRecord.objects.update_or_create(
            state=self.state,
            timestamp=aligned,
            defaults={
                "actual_demand": actual,
                "predicted_demand": result["predicted_demand"],
                "temp_weighted": result["features"]["temp_weighted"],
                "month": result["features"]["month"],
                "holiday": result["features"]["holiday"],
                "is_weekend": result["features"]["is_weekend"],
                "hour": result["features"]["hour"],
                "minute": result["features"]["minute"],
                "y_lag_1": result["features"]["y_lag_1"],
                "y_lag_24h": result["features"]["y_lag_24h"],
                "y_lag_7d": result["features"]["y_lag_7d"],
            },
        )
        sync_prediction_record(record)

        return {
            "timestamp": aligned_naive,
            "actual_demand": actual,
            "predicted_demand": result["predicted_demand"],
            "features": result["features"],
        }


def refresh_all_states() -> list[dict]:
    results = []
    for config in StateRegistry.list_active():
        try:
            results.append(StatePredictor(config.code).predict_now())
        except Exception as exc:
            results.append({"state": config.code, "error": str(exc)})
    return results
