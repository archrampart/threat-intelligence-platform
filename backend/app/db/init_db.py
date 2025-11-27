"""Database initialization script."""

from app.db.base import Base, engine
from app.models import (  # noqa: F401 - Import all models to register them
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


def init_db() -> None:
    """Create all database tables."""
    # Import all models first to ensure they're registered with Base
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")


if __name__ == "__main__":
    init_db()











