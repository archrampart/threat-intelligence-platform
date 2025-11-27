"""Pytest configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# IMPORTANT: Import Base BEFORE importing app to ensure models are registered
from app.db.base import Base, get_db

# Import models to ensure they're registered with Base BEFORE importing app
from app.models import (  # noqa: F401
    User,
    APISource,
    APIKey,
    IOCQuery,
    ThreatIntelligenceData,
    CVECache,
    AssetWatchlist,
    AssetWatchlistItem,
    AssetCheckHistory,
    Alert,
    Report,
)

# Now import app after models are registered
from app.main import app

# Test database URL (in-memory SQLite)
# IMPORTANT: This is a SEPARATE in-memory database, NOT the production database
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

# Create a SEPARATE engine for tests - this does NOT affect production database
test_engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test.
    
    IMPORTANT: This uses an in-memory SQLite database (sqlite:///:memory:)
    which is COMPLETELY SEPARATE from the production database.
    This fixture does NOT affect production data.
    """
    # Drop all tables first to ensure clean state (in test database only)
    try:
        Base.metadata.drop_all(bind=test_engine)
    except Exception:
        pass  # Ignore if tables don't exist
    
    # Create all tables before creating session (in test database only)
    Base.metadata.create_all(bind=test_engine)
    
    session = TestingSessionLocal()
    try:
        yield session
        session.commit()  # Commit any changes
    except Exception:
        session.rollback()
    finally:
        session.close()
        # Drop all tables after test (in test database only)
        try:
            Base.metadata.drop_all(bind=test_engine)
        except Exception:
            pass


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database dependency override.
    
    IMPORTANT: This overrides the get_db dependency to use the test database
    session instead of the production database. Production database is NEVER touched.
    """
    # Ensure tables are created (db_session fixture already does this)
    # Double-check tables exist (in test database only)
    if not Base.metadata.tables:
        Base.metadata.create_all(bind=test_engine)
    
    def override_get_db():
        """Override get_db to use test database session."""
        try:
            yield db_session
        finally:
            pass

    # Override the dependency to use test database
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    # Clear override after test
    app.dependency_overrides.clear()

