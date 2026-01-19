from functools import lru_cache
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Threat Intelligence Platform API"
    app_version: str = "0.1.0"
    environment: str = "development"
    api_v1_str: str = "/api/v1"
    docs_url: str = "/docs"
    cors_origins: list[str] = ["*"]  # Geliştirme için tüm originlere izin ver
    log_level: str = "INFO"

    # Database
    database_url: str = "sqlite:///./threat_intel.db"  # Default SQLite, production'da PostgreSQL

    # Redis Cache
    redis_url: Optional[str] = "redis://localhost:6379/0"  # Redis connection URL
    redis_enabled: bool = False  # Enable Redis cache (set to True in production)
    
    @field_validator('redis_enabled', mode='before')
    @classmethod
    def parse_redis_enabled(cls, v):
        """Parse redis_enabled from string to boolean."""
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ('true', '1', 'yes', 'on')
        return False

    # Watchlist Scheduler
    watchlist_scheduler_enabled: bool = False  # Enable automatic watchlist checking (disabled by default to save API quotas)
    watchlist_scheduler_interval_minutes: int = 30  # How often scheduler runs to check watchlists (default: 30 minutes)
    watchlist_scheduler_min_check_interval: int = 60  # Minimum check_interval for watchlists to be automatically checked (default: 60 minutes)

    # JWT Authentication
    secret_key: str = "your-secret-key-change-in-production"  # Production'da environment variable'dan alınmalı
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # API Key Encryption
    encryption_key: str = "your-32-byte-encryption-key-change-in-production!!"  # 32 byte key for AES-256

    # API Keys (şimdilik opsiyonel, ileride UI'dan yönetilecek)
    virustotal_api_key: Optional[str] = None
    abuseipdb_api_key: Optional[str] = None
    otx_api_key: Optional[str] = None

    # Rate Limiting
    rate_limit_enabled: bool = True  # Enable rate limiting (set to False to disable)
    rate_limit_per_minute: int = 60  # Requests per minute per IP
    rate_limit_per_hour: int = 1000  # Requests per hour per IP

    # Security
    security_headers_enabled: bool = True  # Enable security headers

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False  # Allow case-insensitive env var reading from .env
        extra = "allow"  # Allow extra fields from .env file


def get_settings() -> Settings:
    """Return cached settings instance."""

    @lru_cache
    def _get_settings() -> Settings:
        return Settings()

    return _get_settings()
