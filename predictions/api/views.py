from __future__ import annotations

from datetime import date, datetime, timedelta

from django.http import JsonResponse
from django.views.decorators.http import require_GET

from predictions.services.forecaster import DayForecaster
from predictions.services.registry import StateRegistry
from states.models import State

import logging

log = logging.getLogger(__name__)


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


@require_GET
def list_states(request):
    states = StateRegistry.list_active()
    return JsonResponse({
        "states": [
            {"code": state.code, "name": state.name}
            for state in states
        ]
    })


def _get_state_or_404(code: str) -> State | None:
    try:
        return State.objects.get(code=code.lower(), is_active=True)
    except State.DoesNotExist:
        return None


def _make_forecaster(code: str) -> DayForecaster | None:
    try:
        return DayForecaster(code)
    except Exception as exc:
        log.error("Failed to build DayForecaster for %s: %s", code, exc)
        return None


@require_GET
def today_view(request, code: str):
    if not _get_state_or_404(code):
        return JsonResponse({"error": "State not found"}, status=404)
    forecaster = _make_forecaster(code)
    if forecaster is None:
        return JsonResponse({"error": "Failed to initialise forecaster"}, status=500)
    try:
        return JsonResponse(forecaster.today_view())
    except Exception as exc:
        log.error("today_view failed for %s: %s", code, exc)
        return JsonResponse({"error": "Forecast unavailable"}, status=500)


@require_GET
def tomorrow_view(request, code: str):
    if not _get_state_or_404(code):
        return JsonResponse({"error": "State not found"}, status=404)
    forecaster = _make_forecaster(code)
    if forecaster is None:
        return JsonResponse({"error": "Failed to initialise forecaster"}, status=500)
    target = date.today() + timedelta(days=1)
    try:
        predicted_points = forecaster.forecast_day(target)
    except Exception as exc:
        log.error("tomorrow_view failed for %s: %s", code, exc)
        return JsonResponse({"error": "Forecast unavailable"}, status=500)
    return JsonResponse({
        "title": f"Tomorrow's predicted demand — {target.isoformat()}",
        "unit": "MW",
        "date": target.isoformat(),
        "predicted": predicted_points,
    })


@require_GET
def forecast_view(request, code: str):
    if not _get_state_or_404(code):
        return JsonResponse({"error": "State not found"}, status=404)
    target = _parse_date(request.GET.get("date"))
    if target is None:
        return JsonResponse({"error": "date query param required (YYYY-MM-DD)"}, status=400)
    max_date = date.today() + timedelta(days=16)
    if target > max_date:
        return JsonResponse({"error": "date must be within 16 days"}, status=400)
    forecaster = _make_forecaster(code)
    if forecaster is None:
        return JsonResponse({"error": "Failed to initialise forecaster"}, status=500)
    try:
        predicted_points = forecaster.forecast_day(target)
    except Exception as exc:
        log.error("forecast_view failed for %s: %s", code, exc)
        return JsonResponse({"error": "Forecast unavailable"}, status=500)
    return JsonResponse({
        "title": f"Forecast demand — {target.isoformat()}",
        "unit": "MW",
        "date": target.isoformat(),
        "predicted": predicted_points,
    })

@require_GET
def history_view(request, code: str):
    if not _get_state_or_404(code):
        return JsonResponse({"error": "State not found"}, status=404)
    target = _parse_date(request.GET.get("date"))
    if target is None:
        return JsonResponse({"error": "date query param required (YYYY-MM-DD)"}, status=400)
    if target >= date.today():
        return JsonResponse({"error": "date must be in the past"}, status=400)
    forecaster = _make_forecaster(code)
    if forecaster is None:
        return JsonResponse({"error": "Failed to initialise forecaster"}, status=500)
    try:
        return JsonResponse(forecaster.history_view(target))
    except Exception as exc:
        log.error("history_view failed for %s: %s", code, exc)
        return JsonResponse({"error": "Forecast unavailable"}, status=500)