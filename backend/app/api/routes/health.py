from datetime import datetime, timezone

from fastapi import APIRouter

from app.utils.monitoring import metrics_collector
from app.utils.error_tracker import error_tracker

router = APIRouter()


@router.get("/health", summary="Health check", tags=["health"])
def health_check() -> dict[str, str]:
    """Return simple health payload for uptime checks."""

    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
    }


@router.get("/metrics", summary="Application metrics", tags=["health"])
def get_metrics() -> dict:
    """Get application metrics."""
    return {
        **metrics_collector.get_metrics(),
        "error_stats": error_tracker.get_error_stats(),
        "recent_errors": error_tracker.get_recent_errors(limit=10),
    }
