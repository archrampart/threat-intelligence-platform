"""IOC Query model."""

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base, JSONType


class IOCQuery(Base):
    """IOC Query model."""

    __tablename__ = "ioc_queries"

    id = Column(String, primary_key=True, index=True)  # UUID string
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    ioc_type = Column(String(50), nullable=False, index=True)  # ip, domain, url, hash
    ioc_value = Column(String(500), nullable=False, index=True)
    query_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    results_json = Column(JSONType, nullable=True)  # Sorgu sonuçları
    risk_score = Column(Float, nullable=True)  # Genel risk skoru
    status = Column(String(50), nullable=True)  # clean, suspicious, malicious, pending
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    # user = relationship("User", back_populates="ioc_queries")
    # threat_intelligence_data = relationship("ThreatIntelligenceData", back_populates="ioc_query")


class ThreatIntelligenceData(Base):
    """Threat Intelligence Data model."""

    __tablename__ = "threat_intelligence_data"

    id = Column(String, primary_key=True, index=True)  # UUID string
    ioc_query_id = Column(String, ForeignKey("ioc_queries.id"), nullable=False, index=True)
    source_api = Column(String(100), nullable=False, index=True)  # VirusTotal, AbuseIPDB, vb.
    raw_data_json = Column(JSONType, nullable=True)  # Ham API yanıtı
    processed_data_json = Column(JSONType, nullable=True)  # İşlenmiş veri
    confidence_score = Column(Float, nullable=True)
    tags = Column(JSONType, nullable=True)  # Etiketler listesi
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    # ioc_query = relationship("IOCQuery", back_populates="threat_intelligence_data")

