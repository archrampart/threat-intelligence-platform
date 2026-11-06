"""Pytest configuration and fixtures."""

import os
import tempfile

# Isolate the app's own engine (used by startup seeding) from any developer database.
_TMP_DIR = tempfile.mkdtemp(prefix="tip-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DIR}/app.db"
os.environ.setdefault("REDIS_ENABLED", "false")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("EXPLOIT_INTEL_PREFETCH", "false")
os.environ.setdefault("DARKWEB_MONITOR_ENABLED", "false")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

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
test_engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # single shared connection, otherwise each connection sees an empty DB
)
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



@pytest.fixture
def test_user(db_session):
    """Analyst user for authenticated endpoint tests."""
    from uuid import uuid4

    from app.core.security import get_password_hash
    from app.models.user import UserRole

    user = User(
        id=str(uuid4()),
        username="testuser",
        email="test@example.com",
        password_hash=get_password_hash("TestPassword123!"),
        role=UserRole.ANALYST,
        is_active=True,
        profile_json={"full_name": "Test User"},
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_token(client, test_user):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": test_user.username, "password": "TestPassword123!"},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.fixture
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture(autouse=True)
def _no_exploit_intel_network(monkeypatch, request):
    """Keep tests offline: KEV/EPSS enrichment is tested separately with mocks."""
    if request.node.get_closest_marker("exploit_intel_live") is None and "test_exploit_intel" not in request.node.nodeid:
        monkeypatch.setattr("app.services.exploit_intel.get_exploit_intel", lambda ids: {})


@pytest.fixture(autouse=True)
def _no_darkweb_feed_network(monkeypatch):
    """Built-in RSS feeds must never hit the network in tests (tests patch _download when needed)."""
    def offline(url, timeout=30):
        raise ConnectionError(f"network disabled in tests: {url}")

    monkeypatch.setattr("app.services.darkweb.sources._download", offline)
