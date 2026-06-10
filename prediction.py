"""CLI entrypoint — delegates to Django prediction service."""

import os
import sys

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "demand_predictor.settings")
django.setup()

from predictions.services.predictor import StatePredictor


def predict_current_demand(state_code: str = "mp") -> float:
    result = StatePredictor(state_code).predict_now()
    print(f"Predicted {state_code.upper()} demand: {result['predicted_demand']:,.1f} MW")
    if result.get("actual_demand") is not None:
        print(f"Actual demand: {result['actual_demand']:,.1f} MW")
    return result["predicted_demand"]


if __name__ == "__main__":
    code = sys.argv[1] if len(sys.argv) > 1 else "mp"
    predict_current_demand(code)
