"""
utils/log_store.py

Appends one row per prediction run to prediction_log.csv at project root.

Schema:
    timestamp           – 15-min aligned IST datetime
    actual_demand       – MW from MERIT India API (NaN if unavailable)
    predicted_demand    – MW from model
    temp_weighted       – °C
    month               – 1–12
    holiday             – 0/1
    is_weekend          – 0/1
    hour                – 0–23
    minute              – 0, 15, 30, 45
    y_lag_1             – MW
    y_lag_24h           – MW
    y_lag_7d            – MW

Public API:
    append_run(record)
    load_log() -> pd.DataFrame
"""

import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)

# Project-root/prediction_log.csv
CSV_PATH = Path(__file__).resolve().parent.parent / "prediction_log.csv"

COLUMNS = [
    "timestamp",
    "actual_demand",
    "predicted_demand",
    "temp_weighted",
    "month",
    "holiday",
    "is_weekend",
    "hour",
    "minute",
    "y_lag_1",
    "y_lag_24h",
    "y_lag_7d",
]

REQUIRED_FIELDS = [
    "predicted_demand",
    "temp_weighted",
    "month",
    "holiday",
    "is_weekend",
    "hour",
    "minute",
    "y_lag_1",
    "y_lag_24h",
    "y_lag_7d",
]


# ── Internal ────────────────────────────────────────────────────────────────

def _align_15min(dt: datetime) -> pd.Timestamp:
    """
    Floor a datetime to the nearest 15-minute boundary.

    Examples:
        10:07 -> 10:00
        10:21 -> 10:15
        10:44 -> 10:30
        10:59 -> 10:45
    """
    return pd.Timestamp(dt).floor("15min")


# ── Public ─────────────────────────────────────────────────────────────────

def append_run(record: dict) -> None:
    """
    Append one prediction run to the log CSV.

    Required fields:
        predicted_demand
        temp_weighted
        month
        holiday
        is_weekend
        hour
        minute
        y_lag_1
        y_lag_24h
        y_lag_7d

    Optional fields:
        actual_demand
        timestamp
    """

    missing = [field for field in REQUIRED_FIELDS if field not in record]
    if missing:
        raise ValueError(
            f"Missing required fields: {', '.join(missing)}"
        )

    ts = _align_15min(
        record.get("timestamp", datetime.now())
    )

    row = {col: None for col in COLUMNS}
    row.update(record)
    row["timestamp"] = ts

    df_new = pd.DataFrame([row])[COLUMNS]

    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)

    if CSV_PATH.exists():
        df_new.to_csv(
            CSV_PATH,
            mode="a",
            header=False,
            index=False,
        )
    else:
        df_new.to_csv(
            CSV_PATH,
            index=False,
        )

    pred = record.get("predicted_demand")
    actual = record.get("actual_demand")

    pred_str = f"{float(pred):.1f}" if pred is not None else "N/A"
    actual_str = (
        f"{float(actual):.1f}"
        if actual is not None
        else "N/A"
    )

    log.info(
        "Logged run at %s | predicted=%s MW | actual=%s MW",
        ts,
        pred_str,
        actual_str,
    )


def load_log() -> pd.DataFrame:
    """
    Return the full prediction log as a DataFrame.
    """

    if not CSV_PATH.exists():
        return pd.DataFrame(columns=COLUMNS)

    return pd.read_csv(
        CSV_PATH,
        parse_dates=["timestamp"],
    )


# ── CLI Smoke Test ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    df = load_log()

    if df.empty:
        print("prediction_log.csv is empty")
    else:
        print("\nLast 3 logged predictions:\n")
        print(df.tail(3).to_string(index=False))