"""Integration tests for IOC API endpoints."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from uuid import uuid4

from app.models.user import User, UserRole


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

