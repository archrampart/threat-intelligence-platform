"""Database base configuration."""

from sqlalchemy import JSON, create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# Database URL (şimdilik SQLite, ileride PostgreSQL'e geçilecek)
# SQLite kullanarak hızlı geliştirme yapabiliriz, production'da PostgreSQL kullanılacak
DATABASE_URL = getattr(settings, "database_url", "sqlite:///./threat_intel.db")

# JSON type - SQLite için JSON, PostgreSQL için JSONB
# SQLAlchemy otomatik olarak uygun tipi seçecek
JSONType = JSONB if "postgresql" in DATABASE_URL else JSON

# SQLAlchemy 2.0 style base class
class Base(DeclarativeBase):
    """Base class for all database models."""
    pass

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False,  # SQL sorgularını logla (development için True yapılabilir)
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency injection için database session getter."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

