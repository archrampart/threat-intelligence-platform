from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class WatchlistAsset(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    ioc_type: str
    ioc_value: str
    description: Optional[str] = None
    risk_threshold: Optional[str] = Field(
        default=None, description="low|medium|high|critical"
    )
    is_active: bool = True
    created_at: Optional[datetime] = None


class WatchlistBase(BaseModel):
    name: str
    description: Optional[str] = None
    check_interval: int = Field(default=60, ge=5, description="Kontrol aralığı (dk)")
    notification_enabled: bool = True


class WatchlistCreate(WatchlistBase):
    assets: List[WatchlistAsset] = Field(default_factory=list)


class Watchlist(WatchlistBase):
    id: UUID
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
    assets: List[WatchlistAsset] = Field(default_factory=list)
    shared_with_user_ids: Optional[List[str]] = None  # User IDs of viewers who can access this watchlist


class WatchlistListResponse(BaseModel):
    watchlists: List[Watchlist]


class AssetCheckHistory(BaseModel):
    """Asset check history response schema."""
    id: str
    check_date: datetime
    risk_score: Optional[str] = None
    status: Optional[str] = None
    threat_intelligence_data: Optional[dict] = None
    sources_checked: Optional[List[str]] = None
    alert_triggered: bool = False

    class Config:
        from_attributes = True


class WatchlistShareRequest(BaseModel):
    """Request schema for sharing watchlist with users."""
    user_ids: List[str] = Field(..., description="List of user IDs to share the watchlist with")


class AssetCheckHistoryListResponse(BaseModel):
    """Asset check history list response."""
    items: List[AssetCheckHistory]
    total: int
