"""User model."""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Boolean, Column, DateTime, Enum, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base, JSONType


class UserRole(str, PyEnum):
    """User role enum."""

    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


class User(Base):
    """User model."""

    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)  # UUID string olarak saklanacak
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.VIEWER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    language_preference = Column(String(10), default="en", nullable=False)  # en, tr, vb.
    last_login = Column(DateTime(timezone=True), nullable=True)
    profile_json = Column(JSONType, nullable=True)  # Ek kullanıcı bilgileri
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    # ioc_queries = relationship("IOCQuery", back_populates="user")
    # reports = relationship("Report", back_populates="user")
    # api_keys = relationship("APIKey", back_populates="user")
    # watchlists = relationship("AssetWatchlist", back_populates="user")
    alerts = relationship("Alert", back_populates="user", cascade="all, delete-orphan")

