"""
utils/lag_store.py

Persists every 15-min demand reading and provides lag lookups for model features.
State-aware via StateConfig.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from predictions.services.registry import StateConfig

log = logging.getLogger(__name__)

COLUMNS = ["timestamp", "demand_mw", "source"]
NEIGHBOUR_WINDOW = timedelta(minutes=30)

_DEFAULT_MERIT_URL = (
    "https://meritindia.in/StateWiseDetails/"
    "BindCurrentStateStatus?StateCode=MPD"
)
_DEFAULT_CSV_PATH = "data/demand_log.csv"
_DEFAULT_FALLBACK = 14_500.0


def _default_config() -> StateConfig:
    from predictions.services.registry import StateConfig

    return StateConfig(
        code="mp",
        name="Madhya Pradesh",
        merit_state_code="MPD",
        merit_url=_DEFAULT_MERIT_URL,
        model_path="models/mp/lgbm_final.txt",
        fallback_demand_mw=_DEFAULT_FALLBACK,
        timezone="Asia/Kolkata",
        cities={},
    )


def _normalize_ts(series_or_ts):
    if isinstance(series_or_ts, pd.Series):
        ts = pd.to_datetime(series_or_ts)
        if getattr(ts.dt, "tz", None) is not None:
            return ts.dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
        return ts
    ts = pd.Timestamp(series_or_ts)
    if ts.tzinfo is not None:
        return ts.tz_convert("Asia/Kolkata").tz_localize(None)
    return ts


def _align_15min(dt: datetime) -> pd.Timestamp:
    ts = _normalize_ts(dt)
    minutes = (ts.minute // 15) * 15
    return ts.replace(minute=minutes, second=0, microsecond=0)


def _csv_path(config: StateConfig | None) -> str:
    if config is not None:
        return str(config.demand_csv_path)
    return _DEFAULT_CSV_PATH


def _load(config: StateConfig | None = None) -> pd.DataFrame:
    path = _csv_path(config)
    if config is not None and config.state_id:
        try:
            from states.models import DemandReading

            rows = DemandReading.objects.filter(state_id=config.state_id).order_by("timestamp")
            if rows.exists():
                return pd.DataFrame([
                    {
                        "timestamp": _normalize_ts(r.timestamp),
                        "demand_mw": r.demand_mw,
                        "source": r.source,
                    }
                    for r in rows
                ])
        except Exception:
            pass

    if os.path.exists(path):
        df = pd.read_csv(path, parse_dates=["timestamp"])
        df["timestamp"] = _normalize_ts(df["timestamp"])
        return df
    return pd.DataFrame(columns=COLUMNS)


def _save(df: pd.DataFrame, config: StateConfig | None = None) -> None:
    path = _csv_path(config)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False)


def write_demand(
    timestamp: datetime,
    demand_mw: float,
    source: str = "api",
    config: StateConfig | None = None,
) -> None:
    df = _load(config)
    ts = _align_15min(timestamp)
    df = df[df["timestamp"] != ts]
    new_row = pd.DataFrame([{
        "timestamp": ts,
        "demand_mw": round(demand_mw, 2),
        "source": source,
    }])
    df = pd.concat([df, new_row], ignore_index=True)
    df.sort_values("timestamp", inplace=True)
    _save(df, config)


def _exact_lookup(df: pd.DataFrame, ts: pd.Timestamp) -> float | None:
    row = df[df["timestamp"] == ts]
    if not row.empty:
        return float(row.iloc[0]["demand_mw"])
    return None


def _nearest_neighbour(
    df: pd.DataFrame,
    ts: pd.Timestamp,
    window: timedelta = NEIGHBOUR_WINDOW,
) -> float | None:
    if df.empty:
        return None
    deltas = (df["timestamp"] - ts).abs()
    idx = deltas.idxmin()
    if deltas[idx] <= window:
        return float(df.loc[idx, "demand_mw"])
    return None


def _api_demand(config: StateConfig | None = None) -> float | None:
    from predictions.services.merit_client import fetch_current_demand

    cfg = config or _default_config()
    return fetch_current_demand(cfg)


def _most_recent_demand(df: pd.DataFrame) -> float | None:
    if df.empty:
        return None
    return float(df.sort_values("timestamp").iloc[-1]["demand_mw"])


def _resolve_lag(
    df: pd.DataFrame,
    target: datetime,
    decay: float,
    label: str,
    config: StateConfig | None = None,
    override_value: float | None = None,
    allow_api: bool = True,
) -> tuple[float, str]:
    cfg = config or _default_config()
    ts = _align_15min(target)

    val = _exact_lookup(df, ts)
    if val is not None:
        return val, "csv_exact"

    val = _nearest_neighbour(df, ts)
    if val is not None:
        return val, "csv_nearest"

    if override_value is not None:
        return override_value * decay, "chain"

    if allow_api:
        api_val = _api_demand(config)
        if api_val is not None:
            return api_val * decay, f"api×{decay}"

    recent = _most_recent_demand(df)
    if recent is not None:
        return recent * decay, f"recent×{decay}"

    return cfg.fallback_demand_mw * decay, "constant"


def get_lag_features(
    now: datetime | None = None,
    config: StateConfig | None = None,
    chain_values: dict[datetime, float] | None = None,
    allow_api: bool = True,
) -> dict:
    now = now or datetime.now()
    df = _load(config)
    chain_values = chain_values or {}

    def chain_override(target: datetime) -> float | None:
        aligned = _align_15min(target).to_pydatetime()
        if aligned.tzinfo is not None:
            aligned = aligned.replace(tzinfo=None)
        for key, value in chain_values.items():
            key_aligned = _align_15min(key).to_pydatetime()
            if key_aligned.tzinfo is not None:
                key_aligned = key_aligned.replace(tzinfo=None)
            if key_aligned == aligned:
                return value
        return None

    lag_1, _ = _resolve_lag(
        df,
        now - timedelta(minutes=15),
        1.00,
        "y_lag_1",
        config,
        override_value=chain_override(now - timedelta(minutes=15)),
        allow_api=allow_api,
    )
    lag_24h, _ = _resolve_lag(
        df,
        now - timedelta(hours=24),
        0.99,
        "y_lag_24h",
        config,
        override_value=chain_override(now - timedelta(hours=24)),
        allow_api=allow_api,
    )
    lag_7d, _ = _resolve_lag(
        df,
        now - timedelta(days=7),
        0.98,
        "y_lag_7d",
        config,
        override_value=chain_override(now - timedelta(days=7)),
        allow_api=allow_api,
    )

    fallback = cfg_fallback(config)
    if lag_24h >= fallback * 0.99 and lag_1:
        lag_24h = lag_1 * 0.99
    if lag_7d >= fallback * 0.98 and lag_1:
        lag_7d = lag_1 * 0.98

    return {
        "y_lag_1": round(lag_1, 2),
        "y_lag_24h": round(lag_24h, 2),
        "y_lag_7d": round(lag_7d, 2),
    }


def cfg_fallback(config: StateConfig | None) -> float:
    cfg = config or _default_config()
    return cfg.fallback_demand_mw


def get_current_actual_demand(config: StateConfig | None = None) -> float | None:
    val = _api_demand(config)
    if val is not None:
        write_demand(datetime.now(), val, source="api", config=config)
    return val


def lookup_demand_at(
    target: datetime,
    config: StateConfig | None = None,
) -> float | None:
    df = _load(config)
    ts = _align_15min(target)
    val = _exact_lookup(df, ts)
    if val is not None:
        return val
    return _nearest_neighbour(df, ts)
