from functools import lru_cache
from typing import Optional

from loguru import logger
from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from typing_extensions import Annotated

# Values shipped in example files / old defaults. Never acceptable in production.
_INSECURE_SECRETS = {
    "",
    "your-secret-key",
    "your-secret-key-change-in-production",
    "your-super-secret-key-change-in-production",
    "your-32-byte-encryption-key!!",
    "your-32-byte-encryption-key-change-in-production!!",
    "change-me",
    "changeme",
}

# Legacy development defaults. Kept identical to previous releases so API keys that
# were encrypted in existing local databases remain decryptable. Rejected in production.
_DEV_SECRET_KEY = "your-secret-key-change-in-production"
_DEV_ENCRYPTION_KEY = "your-32-byte-encryption-key-change-in-production!!"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Threat Intelligence Platform API"
    app_version: str = "2.1.0"
    environment: str = "development"
    api_v1_str: str = "/api/v1"
    docs_url: Optional[str] = "/docs"
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=list,
        validation_alias=AliasChoices("CORS_ORIGINS", "BACKEND_CORS_ORIGINS"),
    )
    log_level: str = "INFO"

    # Database
    database_url: str = "sqlite:///./threat_intel.db"

    # Redis Cache
    redis_url: Optional[str] = "redis://localhost:6379/0"
    redis_enabled: bool = False

    # Watchlist Scheduler
    watchlist_scheduler_enabled: bool = False
    watchlist_scheduler_interval_minutes: int = 30
    watchlist_scheduler_min_check_interval: int = 60

    # JWT Authentication
    secret_key: str = _DEV_SECRET_KEY
    algorithm: str = "HS256"
    jwt_issuer: str = "threat-intel-platform"
    access_token_expire_minutes: int = 15
    # Session cookies (browser auth). None = Secure flag only in production.
    cookie_secure: Optional[bool] = None
    refresh_token_expire_days: int = 7

    # API Key Encryption
    encryption_key: str = _DEV_ENCRYPTION_KEY

    # Default users: only seeded when explicitly enabled (always in development).
    seed_default_users: Optional[bool] = None
    default_admin_password: Optional[str] = None

    # Optional API keys
    virustotal_api_key: Optional[str] = None
    abuseipdb_api_key: Optional[str] = None
    otx_api_key: Optional[str] = None

    # Outbound HTTP (threat intel sources)
    # Allow custom API sources / test URLs that resolve to private, loopback or
    # link-local addresses. Off by default to prevent SSRF.
    allow_private_api_targets: bool = False
    # Parallel outbound requests per IOC query
    ioc_query_concurrency: int = 8
    # Dark web / Telegram monitoring (public aggregators, no Tor). Minimum interval 15 min.
    darkweb_monitor_enabled: bool = True
    darkweb_scan_interval_minutes: int = 60
    # Download Exploit-DB / Nuclei / Metasploit catalogs in the background at startup
    exploit_intel_prefetch: bool = True

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 60
    rate_limit_per_hour: int = 1000
    login_rate_limit_per_minute: int = 10
    # Only trust X-Forwarded-For when the app runs behind a known reverse proxy.
    trust_proxy_headers: bool = False

    # Security
    security_headers_enabled: bool = True
    metrics_public: bool = False

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors(cls, v):
        if v is None or v == "":
            return []
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                import json

                return json.loads(v)
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @field_validator("environment")
    @classmethod
    def _normalise_env(cls, v: str) -> str:
        return (v or "development").strip().lower()

    @field_validator("algorithm")
    @classmethod
    def _check_alg(cls, v: str) -> str:
        if v not in {"HS256", "HS384", "HS512"}:
            raise ValueError("Only HMAC JWT algorithms (HS256/HS384/HS512) are supported")
        return v

    @model_validator(mode="after")
    def _check_secrets(self) -> "Settings":
        weak = []
        if not self.secret_key and not self.is_production:
            self.secret_key = _DEV_SECRET_KEY
        if not self.encryption_key and not self.is_production:
            self.encryption_key = _DEV_ENCRYPTION_KEY
        for name in ("secret_key", "encryption_key"):
            value = getattr(self, name)
            if value in _INSECURE_SECRETS or len(value) < 32:
                weak.append(name.upper())
        if weak:
            if self.is_production:
                raise ValueError(
                    f"Insecure {', '.join(weak)} for production. Generate strong values, e.g. "
                    "`python -c \"import secrets;print(secrets.token_urlsafe(48))\"`"
                )
            logger.warning("Using insecure development {}. Do NOT expose this instance.", ", ".join(weak))
        if "*" in self.cors_origins:
            raise ValueError("CORS_ORIGINS='*' is not allowed together with credentialed requests")
        return self

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def should_seed_default_users(self) -> bool:
        if self.seed_default_users is not None:
            return self.seed_default_users
        return not self.is_production


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
