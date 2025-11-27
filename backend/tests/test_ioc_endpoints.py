"""Integration tests for IOC API endpoints."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from uuid import uuid4

from app.models.user import User, UserRole


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    from app.core.security import get_password_hash
    
    user = User(
        id=str(uuid4()),
        username="testuser",
        email="test@example.com",
        password_hash=get_password_hash("TestPassword123!"),
        role=UserRole.ANALYST,
        is_active=True,
        profile_json={"full_name": "Test User"},  # full_name is stored in profile_json
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_token(client, test_user):
    """Get authentication token for test user."""
    # Login with test user (user is already created by test_user fixture)
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": test_user.username,
            "password": "TestPassword123!",
        },
    )
    
    data = response.json()
    return data["access_token"]


@patch('app.api.routes.ioc.IOCService')
def test_query_ioc_endpoint_cached(mock_ioc_service, client, auth_token):
    """Test querying IOC from cache."""
    from app.schemas.ioc import IOCQueryResponse, IOCSourceResult
    
    # Create mock response
    cached_response = IOCQueryResponse(
        ioc_type="ip",
        ioc_value="1.2.3.4",
        overall_risk="high",
        queried_sources=[
            IOCSourceResult(
                source="test",
                status="success",
                risk_score=0.9,
                description="Test threat",
                raw=None
            )
        ],
        queried_at=datetime.now(timezone.utc),
    )
    
    # Mock the service instance
    mock_service_instance = mock_ioc_service.return_value
    mock_service_instance.query_ioc.return_value = cached_response
    
    response = client.post(
        "/api/v1/ioc/query",
        json={
            "ioc_type": "ip",
            "ioc_value": "1.2.3.4"
        },
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["ioc_type"] == "ip"
    assert data["ioc_value"] == "1.2.3.4"
    assert data["overall_risk"] == "high"


def test_query_ioc_endpoint_unauthorized(client):
    """Test querying IOC without authentication."""
    response = client.post(
        "/api/v1/ioc/query",
        json={
            "ioc_type": "ip",
            "ioc_value": "1.2.3.4"
        }
    )
    
    assert response.status_code == 401


def test_list_ioc_history_endpoint(client, auth_token, test_user):
    """Test listing IOC query history."""
    # Use real service but with empty database
    response = client.get(
        "/api/v1/ioc/history",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data


def test_list_ioc_history_endpoint_unauthorized(client):
    """Test listing IOC history without authentication."""
    response = client.get("/api/v1/ioc/history")
    
    assert response.status_code == 401

