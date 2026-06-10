"""
utils/time_features.py

Returns calendar / time-of-day features for the current moment.

Public API:
    get_time_features() -> dict
"""

import logging
from datetime import datetime
import holidays

log = logging.getLogger(__name__)

_india_holidays = holidays.India()

# ── Minute quantisation ───────────────────────────────────────────────────────

def _quantise_minute(minute: int) -> int:
    """
    Round the current minute down to the nearest 15-min boundary.

        0–14  →  0
       15–29  → 15
       30–44  → 30
       45–59  → 45
    """
    return (minute // 15) * 15


# ── Public ────────────────────────────────────────────────────────────────────

def get_time_features(dt: datetime | None = None) -> dict:
    """
    Returns a dict with five model features:

        month       int   1–12
        holiday     int   0 / 1   (national Indian holidays)
        is_weekend  int   0 / 1   (Saturday or Sunday)
        hour        int   0–23
        minute      int   0, 15, 30, or 45

    Pass a datetime to get features for a specific time;
    leave as None to use the current local time.
    """
    now = dt or datetime.now()

    features = {
        "month":      now.month,
        "holiday":    int(now.date() in _india_holidays),
        "is_weekend": int(now.weekday() >= 5),
        "hour":       now.hour,
        "minute":     _quantise_minute(now.minute),
    }

    log.debug(f"Time features: {features}")
    return features


# ── CLI smoke-test ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import json
    print(json.dumps(get_time_features(), indent=2))