"""Parameterized MERIT India API client."""

from __future__ import annotations

import logging

import requests
import urllib3

from predictions.services.registry import StateConfig

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

log = logging.getLogger(__name__)


def fetch_current_demand(config: StateConfig) -> float | None:
    urls = getattr(config, 'merit_urls', None)
    if urls:
        # Multiple URLs - fetch from all and sum
        total = 0.0
        success_count = 0
        for url in urls:
            try:
                response = requests.get(url, verify=False, timeout=10)
                response.raise_for_status()
                raw = response.json()[0]["Demand"].replace(",", "")
                value = float(raw)
                total += value
                success_count += 1
                log.info("%s MERIT demand from %s: %.0f MW", config.code, url, value)
            except Exception as exc:
                log.warning("MERIT API failed for %s (%s): %s", config.code, url, exc)
        
        if success_count > 0:
            log.info("%s Total MERIT demand: %.0f MW (from %d sources)", config.code, total, success_count)
            return total
        else:
            log.warning("All MERIT API calls failed for %s", config.code)
            return None
    else:
        # Single URL - original behavior
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
