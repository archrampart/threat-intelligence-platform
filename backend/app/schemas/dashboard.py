"""Dashboard schemas."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class DashboardStats(BaseModel):
    """Dashboard statistics."""

    total_queries: int = Field(0, description="Total IOC queries")
    queries_today: int = Field(0, description="IOC queries today")
    active_apis: int = Field(0, description="Active API sources")
    total_apis: int = Field(0, description="Total API sources")
    watchlist_assets: int = Field(0, description="Total watchlist assets")
    watchlist_alerts: int = Field(0, description="Watchlist alerts")
    critical_cves: int = Field(0, description="Critical CVEs (last 7 days)")
    total_reports: int = Field(0, description="Total reports")


class RiskDistribution(BaseModel):
    """Risk level distribution."""

    low: int = Field(0, description="Low risk count")
    medium: int = Field(0, description="Medium risk count")
    high: int = Field(0, description="High risk count")
    critical: int = Field(0, description="Critical risk count")
    unknown: int = Field(0, description="Unknown risk count")


class APIDistribution(BaseModel):
    """API usage distribution."""

    source: str = Field(..., description="API source name")
    count: int = Field(0, description="Usage count")
    percentage: float = Field(0.0, description="Usage percentage")


class IOCTypeDistribution(BaseModel):
    """IOC type distribution."""

    ioc_type: str = Field(..., description="IOC type: ip, domain, url, hash")
    count: int = Field(0, description="Count")
    percentage: float = Field(0.0, description="Percentage")


class QueryTrend(BaseModel):
    """IOC query trend data."""

    date: str = Field(..., description="Date (YYYY-MM-DD)")
    count: int = Field(0, description="Query count for this date")


class CVETrend(BaseModel):
    """CVE publication trend data."""

    date: str = Field(..., description="Date (YYYY-MM-DD)")
    count: int = Field(0, description="CVE count for this date")


class CVSSDistribution(BaseModel):
    """CVSS score distribution."""

    score_range: str = Field(..., description="Score range: 0.0-2.0, 2.1-4.0, 4.1-6.0, 6.1-8.0, 8.1-10.0")
    count: int = Field(0, description="Count of CVEs in this range")


class RecentActivity(BaseModel):
    """Recent activity item."""

    type: str = Field(..., description="Activity type: ioc_query, cve, watchlist, report")
    title: str = Field(..., description="Activity title")
    description: Optional[str] = Field(None, description="Activity description")
    timestamp: datetime = Field(..., description="Activity timestamp")
    metadata: Optional[dict] = Field(None, description="Additional metadata")


class WatchlistSummary(BaseModel):
    """Watchlist summary."""

    active_watchlists: int = Field(0, description="Active watchlists")
    total_assets: int = Field(0, description="Total assets")
    alerts: int = Field(0, description="Number of alerts")
    last_check: Optional[datetime] = Field(None, description="Last check time")


class APIStatus(BaseModel):
    """API status information."""

    source: str = Field(..., description="API source name")
    is_active: bool = Field(True, description="Is API active")
    usage_today: Optional[int] = Field(None, description="Usage today")
    limit: Optional[int] = Field(None, description="Daily limit")
    status: str = Field("unknown", description="Status: active, warning, error")
    last_used: Optional[datetime] = Field(None, description="Last used time")


class CVESummary(BaseModel):
    """CVE summary information."""

    published_last_24h: int = Field(0, description="CVEs published in last 24 hours")
    critical_count: int = Field(0, description="Critical CVEs (last 7 days)")
    high_count: int = Field(0, description="High CVEs (last 7 days)")
    last_updated: Optional[datetime] = Field(None, description="Last CVE update time")
    recent_cves: List[str] = Field(default_factory=list, description="Recent CVE IDs (last 5)")


class DashboardResponse(BaseModel):
    """Dashboard response."""

    stats: DashboardStats
    risk_distribution: RiskDistribution
    api_distribution: List[APIDistribution]
    ioc_type_distribution: List[IOCTypeDistribution]
    query_trend: List[QueryTrend]
    recent_activities: List[RecentActivity]
    watchlist_summary: WatchlistSummary
    api_status: List[APIStatus]
    cve_summary: Optional[CVESummary] = Field(None, description="CVE summary information")
    cve_trend: Optional[List[CVETrend]] = Field(None, description="CVE publication trend (last 7 days)")
    cvss_distribution: Optional[List[CVSSDistribution]] = Field(None, description="CVSS score distribution")
    generated_at: datetime = Field(default_factory=lambda: datetime.now())


class ChartDataRequest(BaseModel):
    """Chart data request."""

    chart_type: str = Field(..., description="Chart type: risk_distribution, api_usage, query_trend")
    days: int = Field(default=7, ge=1, le=30, description="Number of days for trend data")

