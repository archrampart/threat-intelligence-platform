"""Dashboard endpoints."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.routes.auth import get_current_user
from app.db.base import get_db
from app.schemas.auth import UserResponse
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get(
    "/",
    response_model=DashboardResponse,
    status_code=status.HTTP_200_OK,
    summary="Dashboard verileri",
)
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
) -> DashboardResponse:
    """Get complete dashboard data including statistics, charts, and activities."""
    from loguru import logger
    try:
        dashboard_service = DashboardService(db)
        is_admin = current_user.role == "admin"
        return dashboard_service.get_dashboard(current_user.id, is_admin=is_admin)
    except Exception as e:
        logger.error(f"Dashboard error: {e}", exc_info=True)
        raise

