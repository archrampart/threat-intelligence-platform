"""Integration tests for CVE API endpoints."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from app.schemas.cve import CVE, CVSSv3


@pytest.fixture
def mock_cve_data():
    """Mock CVE data for testing."""
    return CVE(
        cve_id="CVE-2024-1234",
        description="Test CVE description",
        published_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        last_modified_date=datetime(2024, 1, 2, tzinfo=timezone.utc),
        cvss_v3=CVSSv3(
            version="3.1",
            vector_string="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
            base_score=7.5,
            base_severity="HIGH"
        ),
        affected_products=[],
        references=[],
        nvd_url="https://nvd.nist.gov/vuln/detail/CVE-2024-1234",
    )


@patch('app.services.cve_service.requests')
@patch('app.services.cve_service.redis_cache')
def test_search_cves_endpoint(mock_redis_cache, mock_requests, client, mock_cve_data):
    """Test CVE search endpoint."""
    # Mock Redis cache miss
    mock_redis_cache.get.return_value = None
    
    # Mock API response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "vulnerabilities": [{
            "cve": {
                "id": "CVE-2024-1234",
                "descriptions": [{"lang": "en", "value": "Test CVE description"}],
                "published": "2024-01-01T00:00:00Z",
                "metrics": {
                    "cvssMetricV31": [{
                        "cvssData": {
                            "vectorString": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
                            "baseScore": 7.5,
                            "baseSeverity": "HIGH"
                        }
                    }]
                },
                "configurations": [],
                "references": []
            }
        }],
        "totalResults": 1
    }
    mock_response.raise_for_status = MagicMock()
    mock_requests.get.return_value = mock_response
    mock_redis_cache.set.return_value = True
    
    response = client.post(
        "/api/v1/cves/search",
        json={
            "keyword": "test",
            "limit": 20,
            "offset": 0
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "cves" in data
    assert len(data["cves"]) > 0


@patch('app.services.cve_service.redis_cache')
def test_get_cve_endpoint_cached(client, mock_redis_cache, mock_cve_data):
    """Test getting CVE from cache."""
    # Mock Redis cache hit
    cached_data = {
        "cve_id": "CVE-2024-1234",
        "description": "Test CVE description",
        "published_date": "2024-01-01T00:00:00+00:00",
        "last_modified_date": "2024-01-02T00:00:00+00:00",
        "cvss_v3": {
            "version": "3.1",
            "vector_string": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
            "base_score": 7.5,
            "base_severity": "HIGH"
        },
        "affected_products": [],
        "references": [],
        "nvd_url": "https://nvd.nist.gov/vuln/detail/CVE-2024-1234",
    }
    mock_redis_cache.get.return_value = cached_data
    
    response = client.get("/api/v1/cves/CVE-2024-1234")
    
    assert response.status_code == 200
    data = response.json()
    assert "cve" in data
    assert data["cve"]["cve_id"] == "CVE-2024-1234"


@patch('app.services.cve_service.requests')
@patch('app.services.cve_service.redis_cache')
def test_get_cve_endpoint_not_found(mock_redis_cache, mock_requests, client):
    """Test getting non-existent CVE."""
    # Mock Redis cache miss
    mock_redis_cache.get.return_value = None
    
    # Mock API response - no vulnerabilities
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"vulnerabilities": []}
    mock_response.raise_for_status = MagicMock()
    mock_requests.get.return_value = mock_response
    
    response = client.get("/api/v1/cves/CVE-9999-9999")
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

