from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class IOCQueryRequest(BaseModel):
    ioc_type: str = Field(..., description="IOC tipi: ip | domain | url | hash")
    ioc_value: str = Field(..., description="IOC değeri")
    sources: Optional[List[str]] = Field(
        default=None,
        description="Sorgulanacak kaynak listesi. None ise tüm aktif kaynaklar kullanılır.",
    )


class IOCSourceResult(BaseModel):
    source: str
    status: str
    risk_score: Optional[float] = None
    description: Optional[str] = None
    raw: Optional[dict] = None


class IOCQueryResponse(BaseModel):
    ioc_type: str
    ioc_value: str
    overall_risk: Optional[str] = None
    queried_sources: List[IOCSourceResult]
    queried_at: datetime


class IOCQueryHistoryItem(BaseModel):
    """IOC query history item for list view."""

    id: str
    ioc_type: str
    ioc_value: str
    risk_score: Optional[float] = None
    status: Optional[str] = None
    query_date: datetime
    created_at: datetime
    queried_sources: Optional[List[IOCSourceResult]] = None  # Sources that reported this risk


class IOCQueryHistoryListResponse(BaseModel):
    """IOC query history list response with pagination."""

    items: List[IOCQueryHistoryItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class IOCQueryDetailResponse(BaseModel):
    """IOC query detail response with full results."""

    id: str
    ioc_type: str
    ioc_value: str
    risk_score: Optional[float] = None
    status: Optional[str] = None
    query_date: datetime
    results: dict  # Full results_json from database
    threat_intelligence_data: List[dict]  # Related threat intelligence data
    created_at: datetime
