from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from django.conf import settings

from states.models import State


@dataclass(frozen=True)
class StateConfig:
    code: str
    name: str
    merit_state_code: str
    merit_url: str
    model_path: str
    fallback_demand_mw: float
    timezone: str
    cities: dict[str, dict[str, float]]
    state_id: int | None = None

    @property
    def absolute_model_path(self) -> Path:
        path = Path(self.model_path)
        if path.is_absolute():
            return path
        return settings.BASE_DIR / path

    @property
    def demand_csv_path(self) -> Path:
        return settings.BASE_DIR / "data" / "states" / self.code / "demand_log.csv"

    @property
    def prediction_csv_path(self) -> Path:
        return settings.BASE_DIR / "data" / "states" / self.code / "prediction_log.csv"


class StateRegistry:
    @staticmethod
    def from_model(state: State) -> StateConfig:
        return StateConfig(
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

    @staticmethod
    def get(code: str) -> StateConfig:
        state = State.objects.get(code=code.lower(), is_active=True)
        return StateRegistry.from_model(state)

    @staticmethod
    def list_active() -> list[StateConfig]:
        return [
            StateRegistry.from_model(state)
            for state in State.objects.filter(is_active=True).order_by("name")
        ]

    @staticmethod
    def load_yaml(path: Path | str) -> dict[str, Any]:
        with open(path, encoding="utf-8") as handle:
            return yaml.safe_load(handle)

    @staticmethod
    def upsert_from_yaml(path: Path | str) -> State:
        data = StateRegistry.load_yaml(path)
        state, _ = State.objects.update_or_create(
            code=data["code"].lower(),
            defaults={
                "name": data["name"],
                "merit_state_code": data["merit_state_code"],
                "merit_url": data["merit_url"],
                "model_path": data["model_path"],
                "fallback_demand_mw": data.get("fallback_demand_mw", 14500.0),
                "timezone": data.get("timezone", "Asia/Kolkata"),
                "cities": data.get("cities", {}),
                "is_active": data.get("is_active", True),
            },
        )
        return state
