"""Periodic dark web scan (independent of the watchlist scheduler)."""

from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

from app.core.config import get_settings

_scheduler: Optional[BackgroundScheduler] = None


def start() -> None:
    global _scheduler
    settings = get_settings()
    if not settings.darkweb_monitor_enabled or _scheduler is not None:
        return
    from app.services.darkweb.service import run_scheduled_scan

    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(
        run_scheduled_scan,
        trigger=IntervalTrigger(minutes=max(15, settings.darkweb_scan_interval_minutes)),
        id="darkweb_scan",
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
    logger.info("Dark web monitor started (every {} min)", max(15, settings.darkweb_scan_interval_minutes))


def stop() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
