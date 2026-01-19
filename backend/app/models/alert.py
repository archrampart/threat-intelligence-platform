"""Alert model - Security alerts and notifications."""

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, Enum as SQLEnum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class AlertType(str, Enum):
    """Alert type enum."""

    WATCHLIST = "watchlist"
    IOC_QUERY = "ioc_query"
    CVE = "cve"
    SYSTEM = "system"


class AlertSeverity(str, Enum):
    """Alert severity enum."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Alert(Base):
    """Alert model for security notifications."""

    __tablename__ = "alerts"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()), index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    watchlist_id = Column(String, ForeignKey("asset_watchlist.id"), nullable=True)
    asset_id = Column(String, ForeignKey("asset_watchlist_items.id"), nullable=True)
    alert_type = Column(SQLEnum(AlertType), nullable=False, index=True)
    severity = Column(SQLEnum(AlertSeverity), nullable=False, default=AlertSeverity.MEDIUM)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=True)
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    metadata_json = Column(Text, nullable=True)  # JSON string for additional data (renamed from metadata to avoid SQLAlchemy conflict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    user = relationship("User", back_populates="alerts")
    watchlist = relationship("AssetWatchlist", back_populates="alerts")
    asset = relationship("AssetWatchlistItem", back_populates="alerts")

