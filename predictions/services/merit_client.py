"""Parameterized MERIT India API client."""

from __future__ import annotations

import logging

import requests
import urllib3

from predictions.services.registry import StateConfig

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

log = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://meritindia.in/",
}


def fetch_current_demand(config: StateConfig) -> float | None:
    # 1. Helper function to route any Merit URL through Vercel
    def proxy_url(original_url):
        # REPLACE THIS with your actual Vercel deployment URL
        PROXY = "https://vercel-proxy-deploy-xi.vercel.app/api/proxy?StateCode="
        return original_url.replace("https://meritindia.in/StateWiseDetails/BindCurrentStateStatus?StateCode=", PROXY)

    urls = getattr(config, 'merit_urls', None)
    
    if urls:
        # Multiple URLs (e.g., Daman & Diu) - fetch from all and sum
        total = 0.0
        success_count = 0
        for url in urls:
            safe_url = proxy_url(url)
            try:
                # Removed verify=False since Vercel has a valid SSL!
                response = requests.get(safe_url, headers=_HEADERS, timeout=10)
                response.raise_for_status()
                value = float(response.json()[0]["Demand"].replace(",", ""))
                total += value
                success_count += 1
                log.info("%s MERIT demand from %s: %.0f MW", config.code, safe_url, value)
            except Exception as exc:
                log.warning("MERIT API failed for %s (%s): %s", config.code, safe_url, exc)
        
        if success_count > 0:
            return total
        else:
            return None
    else:
        # Single URL - standard behavior
        safe_url = proxy_url(config.merit_url)
        try:
            # Removed verify=False since Vercel has a valid SSL!
            response = requests.get(safe_url, headers=_HEADERS, timeout=10)
            response.raise_for_status()
            value = float(response.json()[0]["Demand"].replace(",", ""))
            log.info("%s MERIT demand: %.0f MW", config.code, value)
            return value
        except Exception as exc:
            log.warning("MERIT API failed for %s: %s", config.code, exc)
            return None