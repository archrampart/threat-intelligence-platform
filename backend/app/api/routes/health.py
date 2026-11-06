from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.core.config import get_settings
from app.core.dependencies import require_role
from app.models.user import UserRole

from app.utils.monitoring import metrics_collector
from app.utils.error_tracker import error_tracker

router = APIRouter()


@router.get("/health", summary="Health check", tags=["health"])
def health_check() -> dict[str, str]:
    """Return simple health payload for uptime checks."""

    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


_metrics_deps = [] if get_settings().metrics_public else [Depends(require_role([UserRole.ADMIN]))]


@router.get("/metrics", summary="Application metrics (admin)", tags=["health"], dependencies=_metrics_deps)
def get_metrics() -> dict:
    """Get application metrics."""
    return {
        **metrics_collector.get_metrics(),
        "error_stats": error_tracker.get_error_stats(),
        "recent_errors": error_tracker.get_recent_errors(limit=10),
    }
