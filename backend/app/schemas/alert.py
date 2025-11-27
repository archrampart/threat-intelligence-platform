"""Alert schemas."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.alert import AlertSeverity, AlertType


class AlertBase(BaseModel):
    """Base alert schema."""

    alert_type: AlertType
    severity: AlertSeverity = AlertSeverity.MEDIUM
    title: str = Field(..., max_length=255)
    message: Optional[str] = None
    metadata: Optional[dict] = None


class AlertCreate(AlertBase):
    """Alert creation schema."""

    watchlist_id: Optional[str] = None
    asset_id: Optional[str] = None


class AlertUpdate(BaseModel):
    """Alert update schema."""

    is_read: Optional[bool] = None


class AlertResponse(AlertBase):
    """Alert response schema."""

    id: str
    user_id: str
    watchlist_id: Optional[str] = None
    asset_id: Optional[str] = None
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AlertListResponse(BaseModel):
    """Alert list response schema."""

    items: List[AlertResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class AlertStatsResponse(BaseModel):
    """Alert statistics response schema."""

    total: int
    unread: int
    by_severity: dict
    by_type: dict











