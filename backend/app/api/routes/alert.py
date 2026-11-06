"""Alert endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.routes.auth import get_current_user
from app.db.base import get_db
from app.models.alert import AlertSeverity, AlertType
from app.schemas.alert import (
    AlertCreate,
    AlertListResponse,
    AlertResponse,
    AlertStatsResponse,
    AlertUpdate,
)
from app.schemas.auth import UserResponse
from app.services.alert_service import AlertService

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get(
    "/",
    response_model=AlertListResponse,
    status_code=status.HTTP_200_OK,
    summary="Alert listesi",
)
def list_alerts(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
    is_read: Optional[bool] = Query(None, description="Filter by read status"),
    alert_type: Optional[AlertType] = Query(None, description="Filter by alert type"),
    severity: Optional[AlertSeverity] = Query(None, description="Filter by severity"),
    page: int = Query(1, ge=1, description="Sayfa numarası"),
    page_size: int = Query(20, ge=1, le=100, description="Sayfa başına kayıt sayısı"),
) -> AlertListResponse:
    """List alerts for the current user."""
    alert_service = AlertService(db)
    return alert_service.list_alerts(
        user_id=current_user.id,
        is_read=is_read,
        alert_type=alert_type,
        severity=severity,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/stats",
    response_model=AlertStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Alert istatistikleri",
)
def get_alert_stats(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
) -> AlertStatsResponse:
    """Get alert statistics for the current user."""
    alert_service = AlertService(db)
    return alert_service.get_stats(current_user.id)


@router.get(
    "/{alert_id}",
    response_model=AlertResponse,
    status_code=status.HTTP_200_OK,
    summary="Alert detayı",
)
def get_alert(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
) -> AlertResponse:
    """Get alert details."""
    alert_service = AlertService(db)
    alert = alert_service.get_alert(alert_id, current_user.id)
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return alert


@router.put(
    "/{alert_id}",
    response_model=AlertResponse,
    status_code=status.HTTP_200_OK,
    summary="Alert güncelle",
)
def update_alert(
    alert_id: str,
    alert_data: AlertUpdate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
) -> AlertResponse:
    """Update an alert."""
    alert_service = AlertService(db)
    alert = alert_service.update_alert(alert_id, current_user.id, alert_data)
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return alert


@router.put(
    "/{alert_id}/read",
    response_model=AlertResponse,
    status_code=status.HTTP_200_OK,
    summary="Alert'i okundu olarak işaretle",
)
def mark_alert_as_read(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
) -> AlertResponse:
    """Mark an alert as read."""
    alert_service = AlertService(db)
    alert = alert_service.mark_as_read(alert_id, current_user.id)
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return alert


@router.put(
    "/{alert_id}/unread",
    response_model=AlertResponse,
    status_code=status.HTTP_200_OK,
    summary="Alert'i okunmadı olarak işaretle",
)
def mark_alert_as_unread(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
) -> AlertResponse:
    """Mark an alert as unread."""
    alert_service = AlertService(db)
    alert = alert_service.mark_as_unread(alert_id, current_user.id)
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return alert


@router.post(
    "/read-all",
    status_code=status.HTTP_200_OK,
    summary="Tüm alertleri okundu olarak işaretle",
)
def mark_all_alerts_as_read(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
) -> dict:
    """Mark all alerts as read for the current user."""
    alert_service = AlertService(db)
    count = alert_service.mark_all_as_read(current_user.id)
    return {"message": f"Marked {count} alerts as read", "count": count}


@router.delete(
    "/{alert_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Alert sil",
)
def delete_alert(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
) -> None:
    """Delete an alert."""
    alert_service = AlertService(db)
    deleted = alert_service.delete_alert(alert_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")





