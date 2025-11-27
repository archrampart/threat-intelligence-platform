"""Dashboard service - statistics and metrics."""

from datetime import datetime, timedelta, timezone
from typing import List

from sqlalchemy import and_, case, cast, Date, func, or_
from sqlalchemy.orm import Session

from app.models.api_source import APISource, APIKey
from app.models.cve import CVECache
from app.models.ioc_query import IOCQuery, ThreatIntelligenceData
from app.models.report import Report
from app.models.watchlist import AssetWatchlist, AssetWatchlistItem, AssetCheckHistory, IOCStatus
from app.schemas.dashboard import (
    APIDistribution,
    APIStatus,
    CVESummary,
    CVETrend,
    CVSSDistribution,
    DashboardResponse,
    DashboardStats,
    IOCTypeDistribution,
    QueryTrend,
    RecentActivity,
    RiskDistribution,
    WatchlistSummary,
)
from loguru import logger


class DashboardService:
    """Dashboard service for statistics and metrics."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_dashboard(self, user_id: str, is_admin: bool = False) -> DashboardResponse:
        """Get complete dashboard data."""
        try:
            # Get statistics
            stats = self._get_stats(user_id, is_admin)
        except Exception as e:
            logger.error(f"Error getting stats: {e}", exc_info=True)
            stats = DashboardStats()

        try:
            # Get risk distribution
            risk_distribution = self._get_risk_distribution(user_id, is_admin)
        except Exception as e:
            logger.error(f"Error getting risk distribution: {e}", exc_info=True)
            risk_distribution = RiskDistribution()

        try:
            # Get API distribution
            api_distribution = self._get_api_distribution(user_id, is_admin)
        except Exception as e:
            logger.error(f"Error getting API distribution: {e}", exc_info=True)
            api_distribution = []

        try:
            # Get IOC type distribution
            ioc_type_distribution = self._get_ioc_type_distribution(user_id, is_admin)
        except Exception as e:
            logger.error(f"Error getting IOC type distribution: {e}", exc_info=True)
            ioc_type_distribution = []

        try:
            # Get query trend
            query_trend = self._get_query_trend(user_id, is_admin, days=7)
        except Exception as e:
            logger.error(f"Error getting query trend: {e}", exc_info=True)
            query_trend = []

        try:
            # Get recent activities
            recent_activities = self._get_recent_activities(user_id, is_admin)
        except Exception as e:
            logger.error(f"Error getting recent activities: {e}", exc_info=True)
            recent_activities = []

        try:
            # Get watchlist summary
            watchlist_summary = self._get_watchlist_summary(user_id, is_admin)
        except Exception as e:
            logger.error(f"Error getting watchlist summary: {e}", exc_info=True)
            watchlist_summary = WatchlistSummary()

        try:
            # Get API status
            api_status = self._get_api_status(user_id)
        except Exception as e:
            logger.error(f"Error getting API status: {e}", exc_info=True)
            api_status = []

        try:
            # Get CVE summary
            cve_summary = self._get_cve_summary()
        except Exception as e:
            logger.error(f"Error getting CVE summary: {e}", exc_info=True)
            cve_summary = None

        try:
            # Get CVE trend
            cve_trend = self._get_cve_trend()
        except Exception as e:
            logger.error(f"Error getting CVE trend: {e}", exc_info=True)
            cve_trend = None

        try:
            # Get CVSS distribution
            cvss_distribution = self._get_cvss_distribution()
        except Exception as e:
            logger.error(f"Error getting CVSS distribution: {e}", exc_info=True)
            cvss_distribution = None

        return DashboardResponse(
            stats=stats,
            risk_distribution=risk_distribution,
            api_distribution=api_distribution,
            ioc_type_distribution=ioc_type_distribution,
            query_trend=query_trend,
            recent_activities=recent_activities,
            watchlist_summary=watchlist_summary,
            api_status=api_status,
            cve_summary=cve_summary,
            cve_trend=cve_trend,
            cvss_distribution=cvss_distribution,
            generated_at=datetime.now(timezone.utc),
        )

    def _get_stats(self, user_id: str, is_admin: bool) -> DashboardStats:
        """Get dashboard statistics."""
        # Base query filter
        if is_admin:
            query_filter = True
        else:
            query_filter = IOCQuery.user_id == user_id

        # Total queries
        total_queries = self.db.query(func.count(IOCQuery.id)).filter(query_filter).scalar() or 0

        # Queries today
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        queries_today = (
            self.db.query(func.count(IOCQuery.id))
            .filter(and_(query_filter, IOCQuery.query_date >= today_start))
            .scalar()
            or 0
        )

        # Active APIs
        active_apis = (
            self.db.query(func.count(APIKey.id))
            .join(APISource, APIKey.api_source_id == APISource.id)
            .filter(APIKey.is_active == True)
            .filter(APISource.is_active == True)
            .filter(APIKey.user_id == user_id if not is_admin else True)
            .scalar()
            or 0
        )

        # Total APIs
        total_apis = (
            self.db.query(func.count(APISource.id))
            .filter(APISource.is_active == True)
            .scalar()
            or 0
        )

        # Watchlist assets
        watchlist_filter = AssetWatchlist.user_id == user_id if not is_admin else True
        watchlist_assets = (
            self.db.query(func.count(AssetWatchlistItem.id))
            .join(AssetWatchlist, AssetWatchlistItem.watchlist_id == AssetWatchlist.id)
            .filter(watchlist_filter)
            .filter(AssetWatchlistItem.is_active == True)
            .scalar()
            or 0
        )

        # Watchlist alerts (high risk items)
        # For now, return 0 as we don't have status tracking yet
        watchlist_alerts = 0

        # Critical CVEs (last 7 days) - This would require CVE cache query
        # For now, return 0
        critical_cves = 0

        # Total reports
        report_filter = Report.user_id == user_id if not is_admin else True
        total_reports = self.db.query(func.count(Report.id)).filter(report_filter).scalar() or 0

        return DashboardStats(
            total_queries=total_queries,
            queries_today=queries_today,
            active_apis=active_apis,
            total_apis=total_apis,
            watchlist_assets=watchlist_assets,
            watchlist_alerts=watchlist_alerts,
            critical_cves=critical_cves,
            total_reports=total_reports,
        )

    def _get_risk_distribution(self, user_id: str, is_admin: bool) -> RiskDistribution:
        """Get risk level distribution from both IOC queries and watchlist items."""
        from app.models.watchlist import AssetWatchlistItem, AssetWatchlist
        
        query_filter = IOCQuery.user_id == user_id if not is_admin else True

        # Count by risk score ranges from IOC queries
        low_ioc = (
            self.db.query(func.count(IOCQuery.id))
            .filter(query_filter)
            .filter(and_(IOCQuery.risk_score >= 0.0, IOCQuery.risk_score < 0.2))
            .scalar()
            or 0
        )

        medium_ioc = (
            self.db.query(func.count(IOCQuery.id))
            .filter(query_filter)
            .filter(and_(IOCQuery.risk_score >= 0.2, IOCQuery.risk_score < 0.5))
            .scalar()
            or 0
        )

        high_ioc = (
            self.db.query(func.count(IOCQuery.id))
            .filter(query_filter)
            .filter(and_(IOCQuery.risk_score >= 0.5, IOCQuery.risk_score < 0.8))
            .scalar()
            or 0
        )

        critical_ioc = (
            self.db.query(func.count(IOCQuery.id))
            .filter(query_filter)
            .filter(IOCQuery.risk_score >= 0.8)
            .scalar()
            or 0
        )

        unknown_ioc = (
            self.db.query(func.count(IOCQuery.id))
            .filter(query_filter)
            .filter(IOCQuery.risk_score.is_(None))
            .scalar()
            or 0
        )

        # Also count from watchlist items (for alert context)
        watchlist_filter = AssetWatchlist.user_id == user_id if not is_admin else True
        
        # Count watchlist items by risk level
        low_watchlist = (
            self.db.query(func.count(AssetWatchlistItem.id))
            .join(AssetWatchlist, AssetWatchlistItem.watchlist_id == AssetWatchlist.id)
            .filter(watchlist_filter)
            .filter(AssetWatchlistItem.is_active == True)
            .filter(
                or_(
                    AssetWatchlistItem.last_risk_score == "low",
                    AssetWatchlistItem.last_risk_score == "clean",
                )
            )
            .scalar()
            or 0
        )

        medium_watchlist = (
            self.db.query(func.count(AssetWatchlistItem.id))
            .join(AssetWatchlist, AssetWatchlistItem.watchlist_id == AssetWatchlist.id)
            .filter(watchlist_filter)
            .filter(AssetWatchlistItem.is_active == True)
            .filter(AssetWatchlistItem.last_risk_score == "medium")
            .scalar()
            or 0
        )

        high_watchlist = (
            self.db.query(func.count(AssetWatchlistItem.id))
            .join(AssetWatchlist, AssetWatchlistItem.watchlist_id == AssetWatchlist.id)
            .filter(watchlist_filter)
            .filter(AssetWatchlistItem.is_active == True)
            .filter(AssetWatchlistItem.last_risk_score == "high")
            .scalar()
            or 0
        )

        critical_watchlist = 0  # Watchlist items don't have "critical" risk level

        unknown_watchlist = (
            self.db.query(func.count(AssetWatchlistItem.id))
            .join(AssetWatchlist, AssetWatchlistItem.watchlist_id == AssetWatchlist.id)
            .filter(watchlist_filter)
            .filter(AssetWatchlistItem.is_active == True)
            .filter(
                or_(
                    AssetWatchlistItem.last_risk_score.is_(None),
                    AssetWatchlistItem.last_risk_score == "unknown",
                )
            )
            .scalar()
            or 0
        )

        # Combine both sources (IOC queries are the primary source, watchlist items are additional context)
        return RiskDistribution(
            low=low_ioc + low_watchlist,
            medium=medium_ioc + medium_watchlist,
            high=high_ioc + high_watchlist,
            critical=critical_ioc + critical_watchlist,
            unknown=unknown_ioc + unknown_watchlist
        )

    def _get_api_distribution(self, user_id: str, is_admin: bool) -> List[APIDistribution]:
        """Get API usage distribution."""
        # Get threat intelligence data grouped by source
        query = (
            self.db.query(
                ThreatIntelligenceData.source_api,
                func.count(ThreatIntelligenceData.id).label("count"),
            )
            .join(IOCQuery, ThreatIntelligenceData.ioc_query_id == IOCQuery.id)
            .group_by(ThreatIntelligenceData.source_api)
        )

        if not is_admin:
            query = query.filter(IOCQuery.user_id == user_id)

        results = query.all()

        # Calculate total for percentage
        total = sum(r.count for r in results) or 1

        return [
            APIDistribution(
                source=r.source_api,
                count=r.count,
                percentage=(r.count / total * 100) if total > 0 else 0.0,
            )
            for r in results
        ]

    def _get_ioc_type_distribution(self, user_id: str, is_admin: bool) -> List[IOCTypeDistribution]:
        """Get IOC type distribution."""
        query_filter = IOCQuery.user_id == user_id if not is_admin else True

        # Get IOC queries grouped by type
        results = (
            self.db.query(
                IOCQuery.ioc_type,
                func.count(IOCQuery.id).label("count"),
            )
            .filter(query_filter)
            .group_by(IOCQuery.ioc_type)
            .all()
        )

        # Calculate total for percentage
        total = sum(r.count for r in results) or 1

        return [
            IOCTypeDistribution(
                ioc_type=r.ioc_type,
                count=r.count,
                percentage=(r.count / total * 100) if total > 0 else 0.0,
            )
            for r in results
        ]

    def _get_query_trend(self, user_id: str, is_admin: bool, days: int = 7) -> List[QueryTrend]:
        """Get IOC query trend for last N days."""
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)

        query_filter = IOCQuery.user_id == user_id if not is_admin else True

        # Group by date - use created_at if query_date is None
        try:
            date_field = case(
                (IOCQuery.query_date.isnot(None), IOCQuery.query_date),
                else_=IOCQuery.created_at
            )
            results = (
                self.db.query(
                    cast(date_field, Date).label("date"),
                    func.count(IOCQuery.id).label("count"),
                )
                .filter(and_(query_filter, date_field >= start_date))
                .group_by(cast(date_field, Date))
                .order_by(cast(date_field, Date))
                .all()
            )
        except Exception as e:
            logger.warning(f"Error getting query trend: {e}")
            results = []

        # Create date range and fill missing dates with 0
        date_range = []
        for i in range(days):
            date = (datetime.now(timezone.utc) - timedelta(days=days - 1 - i)).date()
            date_range.append(date)

        trend_dict = {r.date: r.count for r in results}

        return [
            QueryTrend(
                date=date.strftime("%Y-%m-%d"),
                count=trend_dict.get(date, 0),
            )
            for date in date_range
        ]

    def _get_recent_activities(self, user_id: str, is_admin: bool, limit: int = 10) -> List[RecentActivity]:
        """Get recent activities."""
        activities = []

        try:
            # Recent IOC queries
            query_filter = IOCQuery.user_id == user_id if not is_admin else True
            recent_queries = (
                self.db.query(IOCQuery)
                .filter(query_filter)
                .order_by(IOCQuery.query_date.desc() if IOCQuery.query_date else IOCQuery.created_at.desc())
                .limit(limit)
                .all()
            )

            for query in recent_queries:
                timestamp = query.query_date if query.query_date else (query.created_at if query.created_at else datetime.now(timezone.utc))
                activities.append(
                    RecentActivity(
                        type="ioc_query",
                        title=f"IOC Query: {query.ioc_type} - {query.ioc_value}",
                        description=f"Risk: {query.status or 'Unknown'}",
                        timestamp=timestamp,
                    )
                )
        except Exception as e:
            logger.warning(f"Error getting recent queries: {e}")

        try:
            # Recent reports
            report_filter = Report.user_id == user_id if not is_admin else True
            recent_reports = (
                self.db.query(Report)
                .filter(report_filter)
                .order_by(Report.created_at.desc())
                .limit(5)
                .all()
            )

            for report in recent_reports:
                format_str = report.format.value if hasattr(report.format, 'value') else str(report.format)
                timestamp = report.created_at if report.created_at else datetime.now(timezone.utc)
                activities.append(
                    RecentActivity(
                        type="report",
                        title=f"Report: {report.title}",
                        description=f"Format: {format_str}",
                        timestamp=timestamp,
                    )
                )
        except Exception as e:
            logger.warning(f"Error getting recent reports: {e}")

        # Sort by timestamp and return top N
        activities.sort(key=lambda x: x.timestamp, reverse=True)
        return activities[:limit]

    def _get_watchlist_summary(self, user_id: str, is_admin: bool) -> WatchlistSummary:
        """Get watchlist summary."""
        watchlist_filter = AssetWatchlist.user_id == user_id if not is_admin else True

        # Active watchlists
        active_watchlists = (
            self.db.query(func.count(AssetWatchlist.id))
            .filter(watchlist_filter)
            .filter(AssetWatchlist.is_active == True)
            .scalar()
            or 0
        )

        # Total assets
        total_assets = (
            self.db.query(func.count(AssetWatchlistItem.id))
            .join(AssetWatchlist, AssetWatchlistItem.watchlist_id == AssetWatchlist.id)
            .filter(watchlist_filter)
            .filter(AssetWatchlistItem.is_active == True)
            .scalar()
            or 0
        )

        # Alerts
        alerts = (
            self.db.query(func.count(AssetWatchlistItem.id))
            .join(AssetWatchlist, AssetWatchlistItem.watchlist_id == AssetWatchlist.id)
            .filter(watchlist_filter)
            .filter(AssetWatchlistItem.is_active == True)
            .filter(
                or_(
                    AssetWatchlistItem.last_status == IOCStatus.MALICIOUS,
                    AssetWatchlistItem.last_status == IOCStatus.SUSPICIOUS,
                )
            )
            .scalar()
            or 0
        )

        # Last check
        last_check = (
            self.db.query(func.max(AssetWatchlistItem.last_check_date))
            .join(AssetWatchlist, AssetWatchlistItem.watchlist_id == AssetWatchlist.id)
            .filter(watchlist_filter)
            .scalar()
        )

        return WatchlistSummary(
            active_watchlists=active_watchlists,
            total_assets=total_assets,
            alerts=alerts,
            last_check=last_check,
        )

    def _get_api_status(self, user_id: str) -> List[APIStatus]:
        """Get API status information."""
        # Get user's API keys
        api_keys = (
            self.db.query(APIKey)
            .join(APISource, APIKey.api_source_id == APISource.id)
            .filter(APIKey.user_id == user_id)
            .filter(APIKey.is_active == True)
            .filter(APISource.is_active == True)
            .all()
        )

        api_status_list = []

        for api_key in api_keys:
            # Get API source - relationship is commented out, so query directly
            api_source = (
                self.db.query(APISource)
                .filter(APISource.id == api_key.api_source_id)
                .first()
            )
            
            if not api_source:
                continue  # Skip if API source not found

            # Get usage today
            today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            usage_today = (
                self.db.query(func.count(ThreatIntelligenceData.id))
                .join(IOCQuery, ThreatIntelligenceData.ioc_query_id == IOCQuery.id)
                .filter(IOCQuery.user_id == user_id)
                .filter(ThreatIntelligenceData.source_api == api_source.name)
                .filter(IOCQuery.query_date >= today_start)
                .scalar()
                or 0
            )

            # Determine status
            status = "active"
            if api_key.test_status.value == "invalid":
                status = "error"
            elif api_key.test_status.value == "not_tested":
                status = "warning"

            api_status_list.append(
                APIStatus(
                    source=api_source.display_name or api_source.name,
                    is_active=api_key.is_active,
                    usage_today=usage_today,
                    limit=None,  # Would need to get from rate_limit_config
                    status=status,
                    last_used=api_key.last_used,
                )
            )

        return api_status_list

    def _get_cve_summary(self) -> CVESummary:
        """Get CVE summary information."""
        from datetime import timedelta

        now = datetime.now(timezone.utc)
        last_24h = now - timedelta(hours=24)
        last_7_days = now - timedelta(days=7)

        # CVEs published in last 24 hours
        # Note: published_date is a Date column, so we compare with date() part
        published_last_24h = (
            self.db.query(func.count(CVECache.id))
            .filter(CVECache.published_date.isnot(None))
            .filter(CVECache.published_date >= last_24h.date())
            .scalar()
            or 0
        )

        # Critical CVEs (last 7 days)
        # Critical = CVSS v3 CRITICAL or CVSS v2 HIGH (which is the highest in v2)
        critical_count = (
            self.db.query(func.count(CVECache.id))
            .filter(CVECache.published_date.isnot(None))
            .filter(CVECache.published_date >= last_7_days.date())
            .filter(
                or_(
                    CVECache.cvss_v3_severity == "CRITICAL",
                    and_(
                        CVECache.cvss_v3_severity.is_(None),
                        CVECache.cvss_v2_severity == "HIGH",
                    ),
                )
            )
            .scalar()
            or 0
        )

        # High CVEs (last 7 days)
        # High = CVSS v3 HIGH (but not CRITICAL) or CVSS v2 MEDIUM (when v3 is None)
        high_count = (
            self.db.query(func.count(CVECache.id))
            .filter(CVECache.published_date.isnot(None))
            .filter(CVECache.published_date >= last_7_days.date())
            .filter(
                or_(
                    and_(
                        CVECache.cvss_v3_severity == "HIGH",
                        CVECache.cvss_v3_severity != "CRITICAL",
                    ),
                    and_(
                        CVECache.cvss_v3_severity.is_(None),
                        CVECache.cvss_v2_severity == "MEDIUM",
                    ),
                )
            )
            .scalar()
            or 0
        )

        # Last updated CVE
        last_updated_cve = (
            self.db.query(CVECache)
            .order_by(CVECache.modified_date.desc().nulls_last(), CVECache.published_date.desc().nulls_last())
            .first()
        )
        last_updated = None
        if last_updated_cve:
            if last_updated_cve.modified_date:
                last_updated = datetime.combine(
                    last_updated_cve.modified_date, datetime.min.time()
                ).replace(tzinfo=timezone.utc)
            elif last_updated_cve.published_date:
                last_updated = datetime.combine(
                    last_updated_cve.published_date, datetime.min.time()
                ).replace(tzinfo=timezone.utc)

        # Recent CVEs (last 5)
        recent_cves = (
            self.db.query(CVECache.cve_id)
            .order_by(CVECache.published_date.desc().nulls_last(), CVECache.cached_at.desc())
            .limit(5)
            .all()
        )
        recent_cve_ids = [cve[0] for cve in recent_cves]

        return CVESummary(
            published_last_24h=published_last_24h,
            critical_count=critical_count,
            high_count=high_count,
            last_updated=last_updated,
            recent_cves=recent_cve_ids,
        )

    def _get_cve_trend(self, days: int = 7) -> List[CVETrend]:
        """Get CVE publication trend for the last N days."""
        from datetime import timedelta

        now = datetime.now(timezone.utc)
        start_date = (now - timedelta(days=days)).date()

        # Get CVE counts by date
        trend_data = (
            self.db.query(
                cast(CVECache.published_date, Date).label("date"),
                func.count(CVECache.id).label("count"),
            )
            .filter(CVECache.published_date >= start_date)
            .filter(CVECache.published_date.isnot(None))
            .group_by(cast(CVECache.published_date, Date))
            .order_by(cast(CVECache.published_date, Date))
            .all()
        )

        # Create a dictionary for easy lookup
        trend_dict = {str(item.date): item.count for item in trend_data}

        # Fill in missing dates with 0
        trend_list = []
        for i in range(days):
            date = (now - timedelta(days=days - 1 - i)).date()
            date_str = str(date)
            count = trend_dict.get(date_str, 0)
            trend_list.append(CVETrend(date=date_str, count=count))

        return trend_list

    def _get_cvss_distribution(self) -> List[CVSSDistribution]:
        """Get CVSS score distribution."""
        # Define score ranges
        ranges = [
            ("0.0-2.0", 0.0, 2.0),
            ("2.1-4.0", 2.1, 4.0),
            ("4.1-6.0", 4.1, 6.0),
            ("6.1-8.0", 6.1, 8.0),
            ("8.1-10.0", 8.1, 10.0),
        ]

        distribution = []

        for range_name, min_score, max_score in ranges:
            # Count CVEs in this range (prefer CVSS v3, fallback to v2)
            count = (
                self.db.query(func.count(CVECache.id))
                .filter(
                    or_(
                        and_(
                            CVECache.cvss_v3_score.isnot(None),
                            CVECache.cvss_v3_score >= min_score,
                            CVECache.cvss_v3_score <= max_score,
                        ),
                        and_(
                            CVECache.cvss_v3_score.is_(None),
                            CVECache.cvss_v2_score.isnot(None),
                            CVECache.cvss_v2_score >= min_score,
                            CVECache.cvss_v2_score <= max_score,
                        ),
                    )
                )
                .scalar()
                or 0
            )

            distribution.append(CVSSDistribution(score_range=range_name, count=count))

        return distribution

