"""CVE model."""

from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Float, String, Text
from sqlalchemy.sql import func

from app.db.base import Base, JSONType


class CVECache(Base):
    """CVE Cache model - NIST NVD CVE verileri cache."""

    __tablename__ = "cve_cache"

    id = Column(String, primary_key=True, index=True)  # UUID string
    cve_id = Column(String(50), unique=True, nullable=False, index=True)  # CVE-2024-1234
    description = Column(Text, nullable=True)  # CVE açıklaması
    cvss_v2_score = Column(Float, nullable=True)  # CVSS v2 skoru
    cvss_v2_severity = Column(String(20), nullable=True)  # LOW, MEDIUM, HIGH
    cvss_v3_score = Column(Float, nullable=True)  # CVSS v3 skoru
    cvss_v3_severity = Column(String(20), nullable=True)  # LOW, MEDIUM, HIGH, CRITICAL
    published_date = Column(Date, nullable=True)  # Yayınlanma tarihi
    modified_date = Column(Date, nullable=True)  # Son güncelleme tarihi
    affected_products = Column(JSONType, nullable=True)  # Etkilenen ürün listesi
    references = Column(JSONType, nullable=True)  # Referans linkleri
    cwe = Column(String(50), nullable=True)  # CWE ID
    raw_data = Column(JSONType, nullable=True)  # NIST NVD'den gelen ham veri
    cached_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Cache sona erme tarihi

