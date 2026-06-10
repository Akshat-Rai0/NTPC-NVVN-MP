"""Background scheduler for 5-minute demand refresh."""

from __future__ import annotations

import logging
import os

from apscheduler.schedulers.background import BackgroundScheduler
from django.conf import settings

log = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> None:
    global _scheduler

    if not getattr(settings, "ENABLE_SCHEDULER", True):
        return

    import sys
    if "runserver" in sys.argv and os.environ.get("RUN_MAIN") != "true":
        return

    if _scheduler is not None:
        return

    from predictions.services.predictor import refresh_all_states

    _scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)
    _scheduler.add_job(
        refresh_all_states,
        trigger="interval",
        minutes=5,
        id="refresh_demand",
        replace_existing=True,
        max_instances=1,
    )
    _scheduler.start()
    log.info("Demand refresh scheduler started (every 5 minutes)")
