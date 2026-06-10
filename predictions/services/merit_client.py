"""Parameterized MERIT India API client."""

from __future__ import annotations

import logging

import requests
import urllib3

from predictions.services.registry import StateConfig

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

log = logging.getLogger(__name__)


def fetch_current_demand(config: StateConfig) -> float | None:
    try:
        response = requests.get(config.merit_url, verify=False, timeout=10)
        response.raise_for_status()
        raw = response.json()[0]["Demand"].replace(",", "")
        value = float(raw)
        log.info("%s MERIT demand: %.0f MW", config.code, value)
        return value
    except Exception as exc:
        log.warning("MERIT API failed for %s: %s", config.code, exc)
        return None
