"""Watchlist models."""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base, JSONType


class RiskThreshold(str, PyEnum):
    """Risk threshold enum."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IOCStatus(str, PyEnum):
    """IOC status enum."""

    CLEAN = "clean"
    SUSPICIOUS = "suspicious"
    MALICIOUS = "malicious"


class AssetWatchlist(Base):
    """Asset Watchlist model."""

    __tablename__ = "asset_watchlist"

    id = Column(String, primary_key=True, index=True)  # UUID string
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)  # Watchlist adı
    description = Column(Text, nullable=True)  # Açıklama
    is_active = Column(Boolean, default=True, nullable=False)  # İzleme aktif/pasif
    notification_enabled = Column(Boolean, default=True, nullable=False)  # Bildirim açık/kapalı
    check_interval = Column(Integer, default=60, nullable=False)  # Kontrol aralığı (dakika)
    shared_with_user_ids = Column(JSONType, nullable=True)  # Viewer kullanıcılarının ID'leri (JSON array)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    # user = relationship("User", back_populates="watchlists")
    # items = relationship("AssetWatchlistItem", back_populates="watchlist", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="watchlist", cascade="all, delete-orphan")


class AssetWatchlistItem(Base):
    """Asset Watchlist Item model."""

    __tablename__ = "asset_watchlist_items"

    id = Column(String, primary_key=True, index=True)  # UUID string
    watchlist_id = Column(String, ForeignKey("asset_watchlist.id"), nullable=False, index=True)
    ioc_type = Column(String(50), nullable=False, index=True)  # ip, domain, url, hash
    ioc_value = Column(String(500), nullable=False, index=True)  # Asset değeri
    description = Column(Text, nullable=True)  # Asset açıklaması
    risk_threshold = Column(Enum(RiskThreshold), nullable=True)  # Alert için risk seviyesi
    last_check_date = Column(DateTime(timezone=True), nullable=True)  # Son kontrol tarihi
    last_risk_score = Column(String(50), nullable=True)  # Son kontrol risk skoru
    last_status = Column(Enum(IOCStatus), nullable=True)  # clean, suspicious, malicious
    is_active = Column(Boolean, default=True, nullable=False)  # Bu asset izleniyor mu
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    # watchlist = relationship("AssetWatchlist", back_populates="items")
    # check_history = relationship("AssetCheckHistory", back_populates="watchlist_item")
    alerts = relationship("Alert", back_populates="asset", cascade="all, delete-orphan")


class AssetCheckHistory(Base):
    """Asset Check History model."""

    __tablename__ = "asset_check_history"

    id = Column(String, primary_key=True, index=True)  # UUID string
    watchlist_item_id = Column(String, ForeignKey("asset_watchlist_items.id"), nullable=False, index=True)
    check_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    risk_score = Column(String(50), nullable=True)  # Risk skoru
    status = Column(Enum(IOCStatus), nullable=True)  # clean, suspicious, malicious
    threat_intelligence_data = Column(JSONType, nullable=True)  # Toplanan tehdit istihbaratı verileri
    sources_checked = Column(JSONType, nullable=True)  # Kontrol edilen API kaynakları
    alert_triggered = Column(Boolean, default=False, nullable=False)  # Alert tetiklendi mi
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    # watchlist_item = relationship("AssetWatchlistItem", back_populates="check_history")

