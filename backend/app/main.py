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

app = FastAPI(title=settings.app_name, version=settings.app_version, docs_url=settings.docs_url)

# Error handler middleware (should be first to catch all errors)
app.add_middleware(ErrorHandlerMiddleware)

# Metrics middleware (should be early to capture all requests)
app.add_middleware(MetricsMiddleware)

# Security headers middleware
if settings.security_headers_enabled:
    app.add_middleware(SecurityHeadersMiddleware)

# Rate limiting middleware
if settings.rate_limit_enabled:
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=settings.rate_limit_per_minute,
        requests_per_hour=settings.rate_limit_per_hour,
    )

# CORS middleware - Allow all origins for development
# For development, we'll allow all localhost and 127.0.0.1 origins
def get_cors_origins():
    """Get CORS origins - allow all localhost/127.0.0.1 origins in development."""
    if settings.environment == "development":
        return [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8080",
            "http://127.0.0.1:8080",
            "http://localhost:5174",
            "http://127.0.0.1:5174",
        ]
    return settings.cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.on_event("startup")
async def startup_event() -> None:
    """Initialize database on startup."""
    logger.info("Starting %s in %s mode", settings.app_name, settings.environment)
    
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
        IOCQuery,
        Report,
        ThreatIntelligenceData,
        User,
    )
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized (existing data preserved)")

    # Seed predefined API sources (always, if they don't exist)
    try:
        from app.db.seed_predefined_apis import seed_predefined_apis
        seed_predefined_apis()
        logger.info("Predefined API sources seeded")
    except Exception as e:
        logger.warning("Failed to seed predefined APIs: %s", e)

    # Seed default users for development/Docker (only if they don't exist)
    # This is safe to run in production - it only creates users if they don't exist
    try:
        from app.db.seed_default_user import seed_default_user
        seed_default_user()
        logger.info("Default users seeded")
    except Exception as e:
        logger.warning("Failed to seed default users: %s", e)

    # Initialize and test Redis connection
    try:
        if settings.redis_enabled:
            from app.services.redis_cache import get_redis_client
            
            redis_client = get_redis_client()
            if redis_client:
                redis_client.ping()
                logger.info("✓ Redis cache connection established and tested successfully")
                logger.info("  Redis URL: %s", settings.redis_url)
            else:
                logger.warning("Redis is enabled but connection failed. Falling back to in-memory cache.")
        else:
            logger.info("Redis cache is disabled. Using in-memory cache. Enable via REDIS_ENABLED=true in .env")
    except Exception as e:
        logger.warning("Redis connection test failed: %s. Falling back to in-memory cache.", e)

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
        logger.warning("Failed to start background scheduler: %s", e)


@app.on_event("shutdown")
async def shutdown_event() -> None:
    logger.info("Shutting down %s", settings.app_name)
    
    # Close Redis connection if enabled
    try:
        if settings.redis_enabled:
            from app.services.redis_cache import get_redis_client
            
            redis_client = get_redis_client()
            if redis_client:
                redis_client.close()
                logger.info("Redis connection closed")
    except Exception as e:
        logger.warning("Failed to close Redis connection: %s", e)
    
    # Stop background scheduler
    try:
        from app.services.scheduler import stop_scheduler

        stop_scheduler()
        logger.info("Background scheduler stopped")
    except Exception as e:
        logger.warning("Failed to stop background scheduler: %s", e)


app.include_router(api_router, prefix=settings.api_v1_str)
