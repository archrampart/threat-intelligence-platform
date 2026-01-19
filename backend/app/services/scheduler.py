"""Background job scheduler for watchlist monitoring."""

import threading
from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import uuid4

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.base import SessionLocal
from app.models.watchlist import AssetWatchlist, AssetWatchlistItem
from app.services.alert_service import AlertService
from app.services.ioc_service import IOCService
from app.schemas.ioc import IOCQueryRequest
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class WatchlistScheduler:
    """Scheduler for automatic watchlist checks."""

    def __init__(self) -> None:
        self.scheduler: Optional[BackgroundScheduler] = None
        self.is_running = False

    def start(self) -> None:
        """Start the scheduler."""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return

        # Check if scheduler is enabled in config
        if not settings.watchlist_scheduler_enabled:
            logger.info("Watchlist scheduler is disabled in configuration. Skipping start.")
            return

        self.scheduler = BackgroundScheduler()
        interval_minutes = settings.watchlist_scheduler_interval_minutes
        self.scheduler.add_job(
            self._check_all_watchlists,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id="check_watchlists",
            name="Check all active watchlists",
            replace_existing=True,
        )
        self.scheduler.start()
        self.is_running = True
        logger.info(f"Watchlist scheduler started (interval: {interval_minutes} minutes)")

    def stop(self) -> None:
        """Stop the scheduler."""
        if self.scheduler and self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("Watchlist scheduler stopped")

    def _check_all_watchlists(self) -> None:
        """Check all active watchlists that need checking."""
        db: Session = SessionLocal()
        try:
            # Get all active watchlists
            watchlists = (
                db.query(AssetWatchlist)
                .filter(AssetWatchlist.is_active == True)
                .filter(AssetWatchlist.notification_enabled == True)
                .all()
            )

            for watchlist in watchlists:
                try:
                    self._check_watchlist(watchlist, db)
                except Exception as e:
                    logger.error(f"Error checking watchlist {watchlist.id}: {e}")

        except Exception as e:
            logger.error(f"Error in watchlist scheduler: {e}")
        finally:
            db.close()

    def _check_watchlist(self, watchlist: AssetWatchlist, db: Session) -> None:
        """Check a single watchlist."""
        # Skip watchlists with check_interval less than minimum configured interval
        # This prevents excessive API usage for frequently checked watchlists
        min_interval = settings.watchlist_scheduler_min_check_interval
        if watchlist.check_interval < min_interval:
            logger.debug(
                f"Skipping watchlist {watchlist.id}: check_interval ({watchlist.check_interval}m) "
                f"is less than minimum ({min_interval}m). Use manual check instead."
            )
            return

        # Check if it's time to check this watchlist
        items = (
            db.query(AssetWatchlistItem)
            .filter(AssetWatchlistItem.watchlist_id == watchlist.id)
            .filter(AssetWatchlistItem.is_active == True)
            .all()
        )

        if not items:
            return

        # Calculate next check time based on check_interval
        current_time = datetime.now(timezone.utc)
        
        for item in items:
            # Check if item needs to be checked
            should_check = False
            if not item.last_check_date:
                # Never checked before
                should_check = True
            else:
                # Check if check_interval has passed
                time_since_last_check = current_time - item.last_check_date
                interval_minutes = timedelta(minutes=watchlist.check_interval)
                if time_since_last_check >= interval_minutes:
                    should_check = True

            if should_check:
                try:
                    self._check_watchlist_item(item, watchlist, db)
                except Exception as e:
                    logger.error(f"Error checking watchlist item {item.id}: {e}")

    def _check_watchlist_item(
        self, item: AssetWatchlistItem, watchlist: AssetWatchlist, db: Session
    ) -> None:
        """Check a single watchlist item."""
        from app.models.watchlist import AssetCheckHistory, IOCStatus, RiskThreshold

        logger.info(f"Checking watchlist item: {item.ioc_type} - {item.ioc_value}")

        # Query IOC using IOC service
        # Use auto_mode_only=True to only query API keys that have update_mode='auto'
        # This respects user preferences and prevents API quota exhaustion
        ioc_service = IOCService(db)
        ioc_request = IOCQueryRequest(ioc_type=item.ioc_type, ioc_value=item.ioc_value)
        ioc_response = ioc_service.query_ioc(watchlist.user_id, ioc_request, auto_mode_only=True)

        # Update watchlist item
        item.last_check_date = datetime.now(timezone.utc)
        item.last_risk_score = ioc_response.overall_risk
        item.last_status = self._convert_risk_to_status(ioc_response.overall_risk)
        db.flush()

        # Create check history
        check_history = AssetCheckHistory(
            id=str(uuid4()),
            watchlist_item_id=item.id,
            check_date=datetime.now(timezone.utc),
            risk_score=ioc_response.overall_risk,
            status=self._convert_risk_to_status(ioc_response.overall_risk),
            threat_intelligence_data={
                "overall_risk": ioc_response.overall_risk,
                "queried_sources": [r.dict() for r in ioc_response.queried_sources],
            },
            sources_checked=[r.source for r in ioc_response.queried_sources],
            alert_triggered=self._should_trigger_alert(item.risk_threshold, ioc_response.overall_risk),
        )
        db.add(check_history)
        db.flush()

        # Create alert if threshold is exceeded
        if check_history.alert_triggered:
            from app.models.alert import AlertSeverity, AlertType
            from app.schemas.alert import AlertCreate

            # Determine severity based on risk level
            severity_map = {
                "low": AlertSeverity.LOW,
                "medium": AlertSeverity.MEDIUM,
                "high": AlertSeverity.HIGH,
                "critical": AlertSeverity.HIGH,
            }
            risk_level_for_alert = (ioc_response.overall_risk or "unknown").lower()
            alert_severity = severity_map.get(risk_level_for_alert, AlertSeverity.MEDIUM)

            alert_service = AlertService(db)
            alert_data = AlertCreate(
                alert_type=AlertType.WATCHLIST,
                severity=alert_severity,
                title=f"High Risk Detected: {item.ioc_type.upper()} - {item.ioc_value}",
                message=f"Watchlist asset '{item.ioc_value}' detected with {ioc_response.overall_risk or 'unknown'} risk level.",
                watchlist_id=watchlist.id,
                asset_id=item.id,
                metadata={
                    "ioc_type": item.ioc_type,
                    "ioc_value": item.ioc_value,
                    "risk_score": ioc_response.overall_risk,
                    "status": item.last_status.value if item.last_status else None,
                },
            )
            alert_service.create_alert(watchlist.user_id, alert_data)

        db.commit()
        logger.info(f"Checked watchlist item {item.id}: {ioc_response.overall_risk}")

    def _convert_risk_to_status(self, risk_level: Optional[str]) -> Optional[IOCStatus]:
        """Convert risk level to IOC status."""
        from app.models.watchlist import IOCStatus

        if not risk_level:
            return None
        risk_map = {
            "high": IOCStatus.MALICIOUS,
            "medium": IOCStatus.SUSPICIOUS,
            "low": IOCStatus.SUSPICIOUS,
            "clean": IOCStatus.CLEAN,
        }
        return risk_map.get(risk_level.lower())

    def _should_trigger_alert(self, risk_threshold: Optional[RiskThreshold], risk_level: Optional[str]) -> bool:
        """Check if alert should be triggered based on risk threshold."""
        from app.models.watchlist import RiskThreshold

        if not risk_threshold or not risk_level:
            return False

        threshold_map = {
            RiskThreshold.LOW: ["low", "medium", "high"],
            RiskThreshold.MEDIUM: ["medium", "high"],
            RiskThreshold.HIGH: ["high"],
            RiskThreshold.CRITICAL: ["high"],
        }

        trigger_levels = threshold_map.get(risk_threshold, [])
        return risk_level.lower() in trigger_levels


# Global scheduler instance
_scheduler_instance: Optional[WatchlistScheduler] = None


def get_scheduler() -> WatchlistScheduler:
    """Get the global scheduler instance."""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = WatchlistScheduler()
    return _scheduler_instance


def start_scheduler() -> None:
    """Start the global scheduler."""
    scheduler = get_scheduler()
    scheduler.start()


def stop_scheduler() -> None:
    """Stop the global scheduler."""
    global _scheduler_instance
    if _scheduler_instance:
        _scheduler_instance.stop()


