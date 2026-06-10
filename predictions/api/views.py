from __future__ import annotations

import json
from datetime import date, datetime, timedelta

from django.http import JsonResponse
from django.views.decorators.http import require_GET

from predictions.services.forecaster import DayForecaster
from predictions.services.registry import StateRegistry
from states.models import State


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


@require_GET
def list_states(request):
    states = StateRegistry.list_active()
    return JsonResponse({
        "states": [
            {"code": state.code, "name": state.name}
            for state in states
        ]
    })


def _get_state_or_404(code: str):
    try:
        return State.objects.get(code=code.lower(), is_active=True)
    except State.DoesNotExist:
        return None


@require_GET
def today_view(request, code: str):
    if not _get_state_or_404(code):
        return JsonResponse({"error": "State not found"}, status=404)
    forecaster = DayForecaster(code)
    return JsonResponse(forecaster.today_view())


@require_GET
def tomorrow_view(request, code: str):
    if not _get_state_or_404(code):
        return JsonResponse({"error": "State not found"}, status=404)
    target = date.today() + timedelta(days=1)
    forecaster = DayForecaster(code)
    predicted_points, _ = forecaster._predicted_points_for_day(target)
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
    forecaster = DayForecaster(code)
    predicted_points, _ = forecaster._predicted_points_for_day(target)
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
    forecaster = DayForecaster(code)
    return JsonResponse(forecaster.history_view(target))
