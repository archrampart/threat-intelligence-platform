"""Database safety utilities to prevent accidental data loss."""

from loguru import logger
from sqlalchemy import inspect
from sqlalchemy.engine import Engine

from app.core.config import get_settings

settings = get_settings()


def is_production_database(engine: Engine) -> bool:
    """Check if the engine is connected to a production database."""
    database_url = str(engine.url)
    
    # Production indicators
    production_indicators = [
        "postgresql://",
        "postgres://",
        "mysql://",
        "mariadb://",
    ]
    
    # Check if it's a file-based database (SQLite)
    if "sqlite" in database_url:
        # In-memory SQLite is safe (for tests)
        if ":memory:" in database_url:
            return False
        # File-based SQLite - check if it's the production file
        if "threat_intel.db" in database_url:
            # Only consider it production if environment is production
            return settings.environment == "production"
    
    # Check for production database URLs
    return any(indicator in database_url for indicator in production_indicators)


def safe_create_tables(engine: Engine) -> None:
    """Safely create database tables without dropping existing ones."""
    from app.db.base import Base
    
    # Check if tables already exist
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    if existing_tables:
        logger.info(f"Database already has {len(existing_tables)} tables. Skipping table creation.")
        return
    
    # Only create if no tables exist
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")


def prevent_drop_all_in_production(engine: Engine) -> None:
    """Prevent accidental drop_all() on production database."""
    if is_production_database(engine):
        raise RuntimeError(
            "CRITICAL: drop_all() is NOT allowed on production database! "
            "This would delete all data. Use Alembic migrations instead."
        )









