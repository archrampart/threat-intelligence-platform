from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api.router import api_router
from app.core.config import get_settings
from app.db.base import Base, engine
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.metrics import MetricsMiddleware
from app.middleware.error_handler import ErrorHandlerMiddleware

settings = get_settings()

def _startup() -> None:
    """Initialize database, seed data and background services."""
    logger.info("Starting {} in {} mode", settings.app_name, settings.environment)
    
    # Create database tables if they don't exist (always, regardless of environment)
    # In production, use Alembic migrations, but create_all() is safe for missing tables
    # IMPORTANT: NEVER use drop_all() in production - it will delete all data!
    # create_all() is safe - it only creates missing tables, doesn't delete data
    from app.models import (  # noqa: F401 - Import all models
        Alert,
        APIKey,
        APISource,
        AssetCheckHistory,
        AssetWatchlist,
        AssetWatchlistItem,
        CVECache,
        DarkWebMention,
        DarkWebSource,
        IOCQuery,
        RefreshToken,
        Report,
        ThreatIntelligenceData,
        User,
    )
    Base.metadata.create_all(bind=engine)
    try:
        from app.db.schema_sync import add_missing_columns

        add_missing_columns(engine)
    except Exception as e:
        logger.warning("Schema sync failed: {}", e)
    logger.info("Database tables initialized (existing data preserved)")

    # Seed predefined API sources (always, if they don't exist)
    try:
        from app.db.seed_predefined_apis import seed_predefined_apis
        seed_predefined_apis()
        logger.info("Predefined API sources seeded")
    except Exception as e:
        logger.warning("Failed to seed predefined APIs: {}", e)

    # Dark web source registry (built-in feeds)
    try:
        from app.db.base import SessionLocal
        from app.services.darkweb.sources import seed_sources

        db = SessionLocal()
        try:
            seed_sources(db)
        finally:
            db.close()
    except Exception as e:
        logger.warning("Failed to seed dark web sources: {}", e)

    # Seed default users for development/Docker (only if they don't exist)
    # This is safe to run in production - it only creates users if they don't exist
    try:
        from app.db.seed_default_user import seed_default_user
        seed_default_user()
        logger.info("Default users seeded")
    except Exception as e:
        logger.warning("Failed to seed default users: {}", e)

    # Initialize and test Redis connection
    try:
        if settings.redis_enabled:
            from app.services.redis_cache import get_redis_client
            
            redis_client = get_redis_client()
            if redis_client:
                redis_client.ping()
                logger.info("✓ Redis cache connection established and tested successfully")
                
            else:
                logger.warning("Redis is enabled but connection failed. Falling back to in-memory cache.")
        else:
            logger.info("Redis cache is disabled. Using in-memory cache. Enable via REDIS_ENABLED=true in .env")
    except Exception as e:
        logger.warning("Redis connection test failed: {}. Falling back to in-memory cache.", e)

    # Start background scheduler for watchlist monitoring (only if enabled in config)
    # DISABLED BY DEFAULT to prevent API quota exhaustion
    try:
        if settings.watchlist_scheduler_enabled:
            from app.services.scheduler import start_scheduler
            start_scheduler()
            logger.info("Background scheduler started (enabled via config)")
        else:
            logger.info("Background scheduler is disabled by default to prevent API quota exhaustion. Enable via WATCHLIST_SCHEDULER_ENABLED=true in .env")
    except Exception as e:
        logger.warning("Failed to start background scheduler: {}", e)




def _prefetch_exploit_catalogs() -> None:
    if not settings.exploit_intel_prefetch:
        return
    import threading

    from app.services.exploit_intel import prefetch_catalogs

    threading.Thread(target=prefetch_catalogs, name="exploit-catalog-prefetch", daemon=True).start()


def _shutdown() -> None:
    logger.info("Shutting down {}", settings.app_name)
    
    # Close Redis connection if enabled
    try:
        if settings.redis_enabled:
            from app.services.redis_cache import get_redis_client
            
            redis_client = get_redis_client()
            if redis_client:
                redis_client.close()
                logger.info("Redis connection closed")
    except Exception as e:
        logger.warning("Failed to close Redis connection: {}", e)
    
    # Stop background scheduler
    try:
        from app.services.scheduler import stop_scheduler

        stop_scheduler()
        logger.info("Background scheduler stopped")
    except Exception as e:
        logger.warning("Failed to stop background scheduler: {}", e)




@asynccontextmanager
async def lifespan(_app: FastAPI):
    _startup()
    _prefetch_exploit_catalogs()
    from app.services.darkweb import scheduler as darkweb_scheduler

    darkweb_scheduler.start()
    yield
    darkweb_scheduler.stop()
    _shutdown()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url=settings.docs_url,
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production and not settings.docs_url else "/openapi.json",
    lifespan=lifespan,
)

# Error handler middleware (outermost: catches everything)
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(MetricsMiddleware)

if settings.security_headers_enabled:
    app.add_middleware(SecurityHeadersMiddleware)

if settings.rate_limit_enabled:
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=settings.rate_limit_per_minute,
        requests_per_hour=settings.rate_limit_per_hour,
        login_requests_per_minute=settings.login_rate_limit_per_minute,
        trust_proxy_headers=settings.trust_proxy_headers,
    )


def get_cors_origins() -> list[str]:
    """Explicit allow-list. Dev servers are allowed automatically outside production."""
    origins = list(settings.cors_origins)
    if not settings.is_production:
        for host in ("localhost", "127.0.0.1"):
            for port in (5173, 5174, 3000, 4765, 8080):
                origins.append(f"http://{host}:{port}")
    return sorted(set(origins))


# CORS must be the outermost layer so that error responses also carry CORS headers.
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With"],
    expose_headers=["Content-Disposition", "X-RateLimit-Remaining-Minute", "Retry-After"],
    max_age=600,
)


app.include_router(api_router, prefix=settings.api_v1_str)
