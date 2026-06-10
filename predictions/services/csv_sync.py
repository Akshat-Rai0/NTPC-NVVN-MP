"""Sync ORM records to per-state CSV files."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from predictions.services.registry import StateConfig
from states.models import DemandReading, PredictionRecord


def _ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def sync_demand_reading(reading: DemandReading) -> None:
    config = StateConfig(
        code=reading.state.code,
        name=reading.state.name,
        merit_state_code=reading.state.merit_state_code,
        merit_url=reading.state.merit_url,
        model_path=reading.state.model_path,
        fallback_demand_mw=reading.state.fallback_demand_mw,
        timezone=reading.state.timezone,
        cities=reading.state.cities,
        state_id=reading.state_id,
    )
    path = config.demand_csv_path
    _ensure_dir(path)

    qs = DemandReading.objects.filter(state=reading.state).order_by("timestamp")
    df = pd.DataFrame(
        [
            {
                "timestamp": row.timestamp,
                "demand_mw": row.demand_mw,
                "source": row.source,
            }
            for row in qs
        ]
    )
    if df.empty:
        return
    df.to_csv(path, index=False)


def sync_prediction_record(record: PredictionRecord) -> None:
    config = StateConfig(
        code=record.state.code,
        name=record.state.name,
        merit_state_code=record.state.merit_state_code,
        merit_url=record.state.merit_url,
        model_path=record.state.model_path,
        fallback_demand_mw=record.state.fallback_demand_mw,
        timezone=record.state.timezone,
        cities=record.state.cities,
        state_id=record.state_id,
    )
    path = config.prediction_csv_path
    _ensure_dir(path)

    qs = PredictionRecord.objects.filter(state=record.state).order_by("timestamp")
    df = pd.DataFrame(
        [
            {
                "timestamp": row.timestamp,
                "actual_demand": row.actual_demand,
                "predicted_demand": row.predicted_demand,
                "temp_weighted": row.temp_weighted,
                "month": row.month,
                "holiday": row.holiday,
                "is_weekend": row.is_weekend,
                "hour": row.hour,
                "minute": row.minute,
                "y_lag_1": row.y_lag_1,
                "y_lag_24h": row.y_lag_24h,
                "y_lag_7d": row.y_lag_7d,
            }
            for row in qs
        ]
    )
    if df.empty:
        return
    df.to_csv(path, index=False)


def export_state_csvs(state_id: int) -> tuple[Path, Path]:
    from states.models import State

    state = State.objects.get(pk=state_id)
    latest_demand = DemandReading.objects.filter(state=state).order_by("-timestamp").first()
    latest_prediction = PredictionRecord.objects.filter(state=state).order_by("-timestamp").first()
    if latest_demand:
        sync_demand_reading(latest_demand)
    if latest_prediction:
        sync_prediction_record(latest_prediction)
    config = StateConfig(
        code=state.code,
        name=state.name,
        merit_state_code=state.merit_state_code,
        merit_url=state.merit_url,
        model_path=state.model_path,
        fallback_demand_mw=state.fallback_demand_mw,
        timezone=state.timezone,
        cities=state.cities,
        state_id=state.id,
    )
    return config.demand_csv_path, config.prediction_csv_path
