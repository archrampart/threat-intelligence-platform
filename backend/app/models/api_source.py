"""API Source model."""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base, JSONType


class APIType(str, PyEnum):
    """API type enum."""

    PREDEFINED = "predefined"
    CUSTOM = "custom"


class AuthenticationType(str, PyEnum):
    """Authentication type enum."""

    API_KEY = "api_key"
    BASIC_AUTH = "basic_auth"
    BEARER_TOKEN = "bearer_token"
    OAUTH = "oauth"
    NONE = "none"


class APISource(Base):
    """API Source model - Threat intelligence API kaynak tanımları."""

    __tablename__ = "api_sources"

    id = Column(String, primary_key=True, index=True)  # UUID string
    name = Column(String(100), unique=True, nullable=False, index=True)  # API adı (örn: "VirusTotal")
    display_name = Column(String(200), nullable=False)  # Görünen ad
    description = Column(Text, nullable=True)  # API açıklaması
    api_type = Column(Enum(APIType), default=APIType.PREDEFINED, nullable=False)  # predefined veya custom
    base_url = Column(String(500), nullable=False)  # API base URL'i
    documentation_url = Column(String(500), nullable=True)  # API dokümantasyon linki
    supported_ioc_types = Column(JSONType, nullable=True)  # ["ip", "domain", "url", "hash"]
    authentication_type = Column(Enum(AuthenticationType), nullable=False)
    request_config = Column(JSONType, nullable=True)  # Request yapılandırması
    response_config = Column(JSONType, nullable=True)  # Response parsing yapılandırması
    rate_limit_config = Column(JSONType, nullable=True)  # Rate limit yapılandırması
    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(String, ForeignKey("users.id"), nullable=True)  # Custom API ise kullanıcı ID
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    # api_keys = relationship("APIKey", back_populates="api_source")
    # created_by_user = relationship("User", foreign_keys=[created_by])


class UpdateMode(str, PyEnum):
    """Update mode enum."""

    MANUAL = "manual"
    AUTO = "auto"


class TestStatus(str, PyEnum):
    """Test status enum."""

    VALID = "valid"
    INVALID = "invalid"
    NOT_TESTED = "not_tested"


class APIKey(Base):
    """API Key model - Kullanıcı API key'leri."""

    __tablename__ = "api_keys"

    id = Column(String, primary_key=True, index=True)  # UUID string
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    api_source_id = Column(String, ForeignKey("api_sources.id"), nullable=False, index=True)
    api_key = Column(Text, nullable=False)  # Şifrelenmiş API key
    username = Column(Text, nullable=True)  # Şifrelenmiş username (MISP gibi)
    password = Column(Text, nullable=True)  # Şifrelenmiş password (MISP gibi)
    api_url = Column(String(500), nullable=True)  # Custom API URL override (MISP instance URL gibi)
    is_active = Column(Boolean, default=True, nullable=False)
    update_mode = Column(Enum(UpdateMode), default=UpdateMode.MANUAL, nullable=False)  # manual veya auto
    rate_limit = Column(String(100), nullable=True)  # Rate limit bilgisi
    last_used = Column(DateTime(timezone=True), nullable=True)
    test_status = Column(Enum(TestStatus), default=TestStatus.NOT_TESTED, nullable=False)
    last_test_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    # user = relationship("User", back_populates="api_keys")
    # api_source = relationship("APISource", back_populates="api_keys")

