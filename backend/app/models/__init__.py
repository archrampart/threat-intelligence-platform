"""Database models package."""

from app.models.alert import Alert, AlertSeverity, AlertType
from app.models.api_source import APIKey, APISource, APIType, AuthenticationType, TestStatus, UpdateMode
from app.models.cve import CVECache
from app.models.ioc_query import IOCQuery, ThreatIntelligenceData
from app.models.report import Report, ReportFormat
from app.models.user import User, UserRole
from app.models.watchlist import (
    AssetCheckHistory,
    AssetWatchlist,
    AssetWatchlistItem,
    IOCStatus,
    RiskThreshold,
)

__all__ = [
    # User
    "User",
    "UserRole",
    # IOC
    "IOCQuery",
    "ThreatIntelligenceData",
    # API
    "APISource",
    "APIKey",
    "APIType",
    "AuthenticationType",
    "UpdateMode",
    "TestStatus",
    # CVE
    "CVECache",
    # Watchlist
    "AssetWatchlist",
    "AssetWatchlistItem",
    "AssetCheckHistory",
    "RiskThreshold",
    "IOCStatus",
    # Report
    "Report",
    "ReportFormat",
    # Alert
    "Alert",
    "AlertType",
    "AlertSeverity",
]

