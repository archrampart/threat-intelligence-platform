"""Report schemas."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ReportCreate(BaseModel):
    """Report creation request."""

    title: str = Field(..., description="Report title", max_length=200)
    description: Optional[str] = Field(None, description="Report description")
    ioc_query_ids: Optional[List[str]] = Field(
        None, description="List of IOC query IDs to include in the report"
    )
    format: str = Field(default="PDF", description="Report format: PDF, HTML, or JSON")
    # Filter options for IOC queries
    watchlist_id: Optional[str] = Field(None, description="Filter by watchlist ID")
    ioc_type: Optional[str] = Field(None, description="Filter by IOC type")
    risk_level: Optional[str] = Field(None, description="Filter by risk level (low, medium, high, critical, unknown)")
    start_date: Optional[datetime] = Field(None, description="Filter by start date (ISO format)")
    end_date: Optional[datetime] = Field(None, description="Filter by end date (ISO format)")
    source: Optional[str] = Field(None, description="Filter by API source")


class ReportUpdate(BaseModel):
    """Report update request."""

    title: Optional[str] = Field(None, description="Report title", max_length=200)
    description: Optional[str] = Field(None, description="Report description")
    format: Optional[str] = Field(None, description="Report format: PDF, HTML, or JSON")


class ReportResponse(BaseModel):
    """Report response model."""

    id: str
    user_id: str
    title: str
    description: Optional[str] = None
    content: Optional[str] = None
    format: str
    shared_link: Optional[str] = None
    ioc_query_ids: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime


class ReportListResponse(BaseModel):
    """Report list response with pagination."""

    items: List[ReportResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ReportShareRequest(BaseModel):
    """Request schema for sharing report with users."""
    user_ids: List[str] = Field(..., description="List of user IDs to share the report with")


class ReportExportRequest(BaseModel):
    """Report export request."""

    format: str = Field(default="PDF", description="Export format: PDF, HTML, JSON, or CSV")
    include_raw_data: bool = Field(default=False, description="Include raw IOC data in export")





