"""Report model."""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base, JSONType


class ReportFormat(str, PyEnum):
    """Report format enum."""

    PDF = "PDF"
    HTML = "HTML"
    JSON = "JSON"


class Report(Base):
    """Report model."""

    __tablename__ = "reports"

    id = Column(String, primary_key=True, index=True)  # UUID string
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)  # Rapor başlığı
    description = Column(Text, nullable=True)  # Rapor açıklaması
    content = Column(Text, nullable=True)  # Rapor içeriği (HTML/JSON)
    format = Column(Enum(ReportFormat), default=ReportFormat.PDF, nullable=False)  # PDF, HTML, JSON
    shared_link = Column(String(500), nullable=True)  # Paylaşım linki
    ioc_query_ids = Column(JSONType, nullable=True)  # Rapor içindeki IOC query ID'leri
    shared_with_user_ids = Column(JSONType, nullable=True)  # Viewer kullanıcılarının ID'leri (JSON array)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    # user = relationship("User", back_populates="reports")

