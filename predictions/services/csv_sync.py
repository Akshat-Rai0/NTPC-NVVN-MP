"""Sync ORM records to per-state CSV files."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from predictions.services.registry import StateRegistry
from states.models import DemandReading, PredictionRecord


def _ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _append_row(path: Path, row: dict) -> None:
    """Append a single row to CSV, writing header only if file doesn't exist yet."""
    df = pd.DataFrame([row])
    _ensure_dir(path)
    df.to_csv(path, mode="a", header=not path.exists(), index=False)


def sync_demand_reading(reading: DemandReading) -> None:
    config = StateRegistry.from_model(reading.state)
    _append_row(config.demand_csv_path, {
        "timestamp": reading.timestamp,
        "demand_mw": reading.demand_mw,
        "source": reading.source,
    })


def sync_prediction_record(record: PredictionRecord) -> None:
    config = StateRegistry.from_model(record.state)
    _append_row(config.prediction_csv_path, {
        "timestamp": record.timestamp,
        "actual_demand": record.actual_demand,
        "predicted_demand": record.predicted_demand,
        "temp_weighted": record.temp_weighted,
        "month": record.month,
        "holiday": record.holiday,
        "is_weekend": record.is_weekend,
        "hour": record.hour,
        "minute": record.minute,
        "y_lag_1": record.y_lag_1,
        "y_lag_24h": record.y_lag_24h,
        "y_lag_7d": record.y_lag_7d,
    })


def export_state_csvs(state_id: int) -> tuple[Path, Path]:
    from states.models import State

    state = State.objects.get(pk=state_id)
    config = StateRegistry.from_model(state)

    latest_demand = DemandReading.objects.filter(state=state).order_by("-timestamp").first()
    latest_prediction = PredictionRecord.objects.filter(state=state).order_by("-timestamp").first()

    if latest_demand:
        sync_demand_reading(latest_demand)
    if latest_prediction:
        sync_prediction_record(latest_prediction)

    return config.demand_csv_path, config.prediction_csv_path