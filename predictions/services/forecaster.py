"""96-slot day forecasting with autoregressive lag chaining."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pandas as pd
from django.utils import timezone as django_tz

from predictions.services.predictor import StatePredictor, _align_15min, _to_local_naive
from predictions.services.registry import StateRegistry
from states.models import DemandReading, PredictionRecord


def _day_start(target: date) -> datetime:
    return datetime.combine(target, datetime.min.time())


def _slot_timestamps(target: date) -> list[datetime]:
    start = _day_start(target)
    return [start + timedelta(minutes=15 * i) for i in range(96)]


def _slot_window_label(slot: datetime) -> str:
    start = _align_15min(slot)
    end = start + timedelta(minutes=15)
    return f"{start.strftime('%H:%M')} - {end.strftime('%H:%M')}"


def _format_time_label(iso_or_dt) -> str:
    if isinstance(iso_or_dt, str):
        dt = datetime.fromisoformat(iso_or_dt.replace("Z", "+00:00"))
        if dt.tzinfo:
            dt = django_tz.localtime(dt).replace(tzinfo=None)
    else:
        dt = iso_or_dt
    return dt.strftime("%H:%M")


def _compute_mape(pairs: list[tuple[float, float]]) -> float | None:
    if not pairs:
        return None
    errors = [abs(a - p) / a * 100 for a, p in pairs if a > 0]
    if not errors:
        return None
    return sum(errors) / len(errors)


class DayForecaster:
    def __init__(self, state_code: str):
        self.predictor = StatePredictor(state_code)
        self.config = StateRegistry.get(state_code)
        self.state = self.predictor.state
        self._actual_cache: dict[datetime, float] | None = None
        self._live_actual_cache: dict[datetime, float] | None = None
        self._predicted_cache: dict[datetime, float] | None = None
        self._temp_cache: dict[datetime, float] | None = None

    def _load_day_caches(self, target: date) -> None:
        if self._actual_cache is not None:
            return
        self._actual_cache = {}
        self._live_actual_cache = {}
        self._predicted_cache = {}
        self._temp_cache = {}

        for reading in DemandReading.objects.filter(state=self.state, timestamp__date=target):
            key = _align_15min(_to_local_naive(reading.timestamp))
            self._actual_cache[key] = reading.demand_mw
            if reading.source == "api":
                self._live_actual_cache[key] = reading.demand_mw

        for record in PredictionRecord.objects.filter(state=self.state, timestamp__date=target):
            key = _align_15min(_to_local_naive(record.timestamp))
            if record.actual_demand is not None:
                self._actual_cache.setdefault(key, record.actual_demand)
                self._live_actual_cache.setdefault(key, record.actual_demand)
            self._predicted_cache.setdefault(key, record.predicted_demand)
            self._temp_cache.setdefault(key, record.temp_weighted)

    def _live_actual_for_slot(self, slot: datetime, target: date) -> float | None:
        self._load_day_caches(target)
        return self._live_actual_cache.get(_align_15min(slot))

    def _predicted_for_slot(self, slot: datetime, target: date) -> float | None:
        self._load_day_caches(target)
        return self._predicted_cache.get(_align_15min(slot))

    def _live_actual_points(self, target: date, up_to: datetime | None = None) -> list[dict]:
        self._load_day_caches(target)
        limit = _align_15min(up_to) if up_to else None
        points = []
        for ts in sorted(self._live_actual_cache):
            if limit is not None and ts > limit:
                continue
            points.append({"t": ts.isoformat(), "mw": self._live_actual_cache[ts]})
        return points

    def _predicted_points_for_day(self, target: date) -> tuple[list[dict], dict[str, float]]:
        self._load_day_caches(target)
        now_naive = django_tz.localtime(django_tz.now()).replace(tzinfo=None)
        today = now_naive.date()
        days_ahead = (target - today).days + 1
        forecast_days = max(1, min(days_ahead + 1, 16))

        chain: dict[datetime, float] = {}
        points: list[dict] = []
        temps: dict[str, float] = {}

        for slot in _slot_timestamps(target):
            aligned = _align_15min(slot)
            live = self._live_actual_for_slot(aligned, target)
            if live is not None:
                chain[aligned] = live

            stored = self._predicted_for_slot(aligned, target)
            if stored is not None and (target < today or aligned <= _align_15min(now_naive)):
                chain[aligned] = stored
                points.append({"t": aligned.isoformat(), "mw": stored})
                if aligned in self._temp_cache:
                    temps[aligned.isoformat()] = self._temp_cache[aligned]
                continue

            result = self.predictor.predict_at(
                aligned,
                chain_values=chain,
                forecast_days=forecast_days,
            )
            predicted = result["predicted_demand"]
            temp = result["features"]["temp_weighted"]
            chain[aligned] = predicted
            points.append({"t": aligned.isoformat(), "mw": predicted})
            temps[aligned.isoformat()] = temp

        return points, temps

    def forecast(self, target: date) -> list[dict]:
        """Future-only forecast slots (from first slot after now for today)."""
        now_naive = django_tz.localtime(django_tz.now()).replace(tzinfo=None)
        today = now_naive.date()
        predicted_points, _ = self._predicted_points_for_day(target)

        if target > today:
            return [{"t": p["t"], "mw": p["mw"], "type": "forecast"} for p in predicted_points]

        now_slot = _align_15min(now_naive)
        return [
            {"t": p["t"], "mw": p["mw"], "type": "forecast"}
            for p in predicted_points
            if _align_15min(datetime.fromisoformat(p["t"])) > now_slot
        ]
    def forecast_day(self, target: date) -> list[dict]:
        """
        Public API for full 96-slot forecast for any future date.
        Returns list of {t, mw} dicts for all slots.
        Use this in API views instead of _predicted_points_for_day().
        """
        points, _ = self._predicted_points_for_day(target)
        return points

    def _build_metrics(
        self,
        target: date,
        actual_points: list[dict],
        predicted_points: list[dict],
        temps: dict[str, float],
    ) -> dict:
        now_naive = django_tz.localtime(django_tz.now()).replace(tzinfo=None)
        now_slot = _align_15min(now_naive)
        pred_map = {p["t"]: p["mw"] for p in predicted_points}

        latest_actual = actual_points[-1] if actual_points else None
        current_pred = pred_map.get(now_slot.isoformat())
        if current_pred is None:
            for p in reversed(predicted_points):
                if _align_15min(datetime.fromisoformat(p["t"])) <= now_slot:
                    current_pred = p["mw"]
                    break

        peak_pred = max(predicted_points, key=lambda p: p["mw"]) if predicted_points else None
        peak_temp = temps.get(peak_pred["t"]) if peak_pred else None
        current_temp = temps.get(now_slot.isoformat())

        mape_pairs = []
        for ap in actual_points:
            pred_mw = pred_map.get(ap["t"])
            if pred_mw is not None:
                mape_pairs.append((ap["mw"], pred_mw))

        avg_mape = _compute_mape(mape_pairs)

        active_mape = None
        active_window = None
        if latest_actual:
            slot_key = latest_actual["t"]
            pred_at_slot = pred_map.get(slot_key)
            if pred_at_slot is not None and latest_actual["mw"] > 0:
                active_mape = abs(latest_actual["mw"] - pred_at_slot) / latest_actual["mw"] * 100
            slot_dt = datetime.fromisoformat(slot_key)
            active_window = _slot_window_label(slot_dt)

        live_window = None
        if latest_actual:
            live_window = _slot_window_label(datetime.fromisoformat(latest_actual["t"]))

        return {
            "live_load_mw": latest_actual["mw"] if latest_actual else None,
            "live_window": live_window,
            "current_predicted_mw": current_pred,
            "current_temp_c": round(current_temp, 1) if current_temp is not None else None,
            "predicted_peak_mw": peak_pred["mw"] if peak_pred else None,
            "predicted_peak_time": _format_time_label(peak_pred["t"]) if peak_pred else None,
            "predicted_peak_temp_c": round(peak_temp, 1) if peak_temp is not None else None,
            "avg_mape_pct": round(avg_mape, 2) if avg_mape is not None else None,
            "active_mape_pct": round(active_mape, 2) if active_mape is not None else None,
            "active_window": active_window,
        }

    def today_view(self) -> dict:
        now = django_tz.localtime(django_tz.now())
        now_naive = now.replace(tzinfo=None)
        today = now_naive.date()

        actual_points = self._live_actual_points(today, up_to=now_naive)
        predicted_points, temps = self._predicted_points_for_day(today)
        forecast_points = [
            p for p in predicted_points
            if _align_15min(datetime.fromisoformat(p["t"])) > _align_15min(now_naive)
        ]

        metrics = self._build_metrics(today, actual_points, predicted_points, temps)

        if actual_points:
            peak_point = max(actual_points, key=lambda p: p["mw"])
            peak = {"value_mw": peak_point["mw"], "timestamp": peak_point["t"]}
        elif predicted_points:
            peak_point = max(predicted_points, key=lambda p: p["mw"])
            peak = {"value_mw": peak_point["mw"], "timestamp": peak_point["t"]}
        else:
            peak = None

        prior_7_days = []
        for offset in range(1, 8):
            day = today - timedelta(days=offset)
            readings = DemandReading.objects.filter(
                state=self.state,
                timestamp__date=day,
                source="api",
            ).order_by("timestamp")
            if not readings.exists():
                continue
            prior_7_days.append({
                "day_offset": offset,
                "label": day.strftime("%b %d").replace(" 0", " "),
                "points": [
                    {
                        "t": _to_local_naive(r.timestamp).isoformat(),
                        "mw": r.demand_mw,
                    }
                    for r in readings
                ],
            })

        return {
            "title": "Live vs Predicted Load",
            "subtitle": "Real-time comparison between actual demand and forecasted load",
            "unit": "MW",
            "now": now.isoformat(),
            "peak": peak,
            "actual": actual_points,
            "predicted": predicted_points,
            "forecast": [{"t": p["t"], "mw": p["mw"]} for p in forecast_points],
            "metrics": metrics,
            "prior_7_days": prior_7_days,
            "has_actual_data": len(actual_points) > 0,
        }

    def history_view(self, target: date) -> dict:
        self._load_day_caches(target)
        actual = []
        predicted = []
        for slot in _slot_timestamps(target):
            aligned = _align_15min(slot)
            if aligned in self._live_actual_cache:
                actual.append({"t": aligned.isoformat(), "mw": self._live_actual_cache[aligned]})
            elif aligned in self._actual_cache:
                actual.append({"t": aligned.isoformat(), "mw": self._actual_cache[aligned]})
            if aligned in self._predicted_cache:
                predicted.append({"t": aligned.isoformat(), "mw": self._predicted_cache[aligned]})

        return {
            "title": f"Demand on {target.isoformat()}",
            "unit": "MW",
            "date": target.isoformat(),
            "actual": actual,
            "predicted": predicted,
        }
