"""
utils/lag_store.py

Persists every 15-min demand reading to a CSV and provides
lag lookups for the model features (y_lag_1, y_lag_24h, y_lag_7d).

Fallback chain for each lag value:
    1. Exact match in CSV
    2. Nearest neighbour in CSV within ±30 min
    3. MERIT India live API (current demand)
    4. Decay from the most recent CSV entry  (×0.99 / ×0.98)
    5. Hard-coded constant (14 500 MW)

Public API:
    write_demand(timestamp, demand_mw, source)
    get_lag_features(now)           -> dict
    get_current_actual_demand()     -> float | None
"""

import logging
import os
from datetime import datetime, timedelta

import pandas as pd
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

log = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

CSV_PATH        = "data/demand_log.csv"
COLUMNS         = ["timestamp", "demand_mw", "source"]
MERIT_URL       = (
    "https://meritindia.in/StateWiseDetails/"
    "BindCurrentStateStatus?StateCode=MPD"
)
FALLBACK_DEMAND = 14_500.0          # MW — last-resort constant
NEIGHBOUR_WINDOW = timedelta(minutes=30)   # ± window for nearest-neighbour


# ── Internal helpers ──────────────────────────────────────────────────────────

def _align_15min(dt: datetime) -> pd.Timestamp:
    """Floor to the nearest 15-min boundary, strip seconds/microseconds."""
    minutes = (dt.minute // 15) * 15
    return pd.Timestamp(
        dt.replace(minute=minutes, second=0, microsecond=0)
    )


def _load() -> pd.DataFrame:
    if os.path.exists(CSV_PATH):
        df = pd.read_csv(CSV_PATH, parse_dates=["timestamp"])
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df
    return pd.DataFrame(columns=COLUMNS)


def _save(df: pd.DataFrame) -> None:
    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
    df.to_csv(CSV_PATH, index=False)


# ── Public: write ─────────────────────────────────────────────────────────────

def write_demand(
    timestamp: datetime,
    demand_mw: float,
    source: str = "api",
) -> None:
    """
    Persist one 15-min demand reading.
    If a row for the same aligned timestamp already exists it is overwritten.

    source values used in this project:
        "api"       – live pull from MERIT India
        "predicted" – model output (used as proxy when actual is unavailable)
    """
    df = _load()
    ts = _align_15min(timestamp)

    df = df[df["timestamp"] != ts]          # drop duplicate if present

    new_row = pd.DataFrame([{
        "timestamp": ts,
        "demand_mw": round(demand_mw, 2),
        "source":    source,
    }])

    df = pd.concat([df, new_row], ignore_index=True)
    df.sort_values("timestamp", inplace=True)
    _save(df)
    log.debug(f"Wrote demand {demand_mw:.0f} MW at {ts} (source={source})")


# ── Internal: lookup strategies ───────────────────────────────────────────────

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
    """Return demand from the closest timestamp within ±window."""
    if df.empty:
        return None
    deltas = (df["timestamp"] - ts).abs()
    idx    = deltas.idxmin()
    if deltas[idx] <= window:
        val = float(df.loc[idx, "demand_mw"])
        log.warning(
            f"Nearest-neighbour fallback: used {df.loc[idx, 'timestamp']} "
            f"for target {ts} (Δ={deltas[idx]})"
        )
        return val
    return None


def _api_demand() -> float | None:
    """Fetch current MP demand from MERIT India API."""
    try:
        r = requests.get(MERIT_URL, verify=False, timeout=10)
        r.raise_for_status()
        raw = r.json()[0]["Demand"].replace(",", "")
        val = float(raw)
        log.info(f"MERIT API demand: {val:.0f} MW")
        return val
    except Exception as e:
        log.warning(f"MERIT API failed: {e}")
        return None


def _most_recent_demand(df: pd.DataFrame) -> float | None:
    """Return the most recent demand value in the CSV."""
    if df.empty:
        return None
    return float(df.sort_values("timestamp").iloc[-1]["demand_mw"])


# ── Internal: resolve a single lag ────────────────────────────────────────────

def _resolve_lag(
    df: pd.DataFrame,
    target: datetime,
    decay: float,
    label: str,
) -> tuple[float, str]:
    """
    Try each strategy in order and return (value, strategy_used).

    decay is applied to the API / most-recent value when an older
    reading is missing from the CSV:
        y_lag_24h → decay ≈ 0.99
        y_lag_7d  → decay ≈ 0.98
    """
    ts = _align_15min(target)

    # 1. Exact match
    val = _exact_lookup(df, ts)
    if val is not None:
        return val, "csv_exact"

    # 2. Nearest neighbour
    val = _nearest_neighbour(df, ts)
    if val is not None:
        return val, "csv_nearest"

    # 3. Live API (then apply decay for older lags)
    api_val = _api_demand()
    if api_val is not None:
        result = api_val * decay
        log.warning(
            f"{label}: no CSV entry near {ts}, "
            f"using API×{decay} = {result:.0f} MW"
        )
        return result, f"api×{decay}"

    # 4. Decay from most recent CSV entry
    recent = _most_recent_demand(df)
    if recent is not None:
        result = recent * decay
        log.warning(
            f"{label}: API also failed, "
            f"using most-recent×{decay} = {result:.0f} MW"
        )
        return result, f"recent×{decay}"

    # 5. Hard-coded constant
    log.error(f"{label}: all strategies failed, using constant {FALLBACK_DEMAND}")
    return FALLBACK_DEMAND * decay, "constant"


# ── Public: lag features ──────────────────────────────────────────────────────

def get_lag_features(now: datetime | None = None) -> dict:
    """
    Returns the three lag features the model needs:

        y_lag_1   – demand 15 min ago
        y_lag_24h – demand 24 h ago
        y_lag_7d  – demand 7 days ago

    Each value is resolved through the fallback chain described above.
    """
    now = now or datetime.now()
    df  = _load()

    lag_1,   s1  = _resolve_lag(df, now - timedelta(minutes=15), 1.00, "y_lag_1")
    lag_24h, s24 = _resolve_lag(df, now - timedelta(hours=24),   0.99, "y_lag_24h")
    lag_7d,  s7  = _resolve_lag(df, now - timedelta(days=7),     0.98, "y_lag_7d")

    log.info(
        f"Lag features — "
        f"y_lag_1={lag_1:.0f}({s1})  "
        f"y_lag_24h={lag_24h:.0f}({s24})  "
        f"y_lag_7d={lag_7d:.0f}({s7})"
    )

    return {
        "y_lag_1":   round(lag_1,   2),
        "y_lag_24h": round(lag_24h, 2),
        "y_lag_7d":  round(lag_7d,  2),
    }


# ── Public: fetch and store current actual demand ─────────────────────────────

def get_current_actual_demand() -> float | None:
    """
    Pull current MP demand from MERIT India, persist it to the CSV,
    and return the value (or None if the API is down).
    """
    val = _api_demand()
    if val is not None:
        write_demand(datetime.now(), val, source="api")
    return val


# ── CLI smoke-test ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    actual = get_current_actual_demand()
    print(f"Current actual demand : {actual} MW")

    lags = get_lag_features()
    print(f"Lag features          : {lags}")