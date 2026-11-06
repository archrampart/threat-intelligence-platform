"""Unit tests for CVE service."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from app.services.cve_service import CVEService
from app.schemas.cve import CVESearchRequest, CVE, CVSSv3


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return Mock()


@pytest.fixture
def cve_service(mock_db):
    """Create CVE service instance."""
    return CVEService(mock_db)


def test_cve_service_init(cve_service):
    """Test CVE service initialization."""
    assert cve_service.db is not None
    assert cve_service._last_request_time == 0.0


def test_rate_limit(cve_service):
    """Test rate limiting mechanism."""
    import time
    
    start_time = time.time()
    cve_service._rate_limit()
    end_time = time.time()
    
    # First call should not delay
    assert (end_time - start_time) < 0.1
    
    # Second call should respect rate limit
    start_time = time.time()
    cve_service._rate_limit()
    end_time = time.time()
    # Should have minimal delay (less than rate limit delay)
    assert (end_time - start_time) < 0.7


@patch('app.services.cve_service.redis_cache')
@patch('app.services.cve_service.requests')
def test_get_cve_from_redis_cache(mock_requests, mock_redis_cache, cve_service):
    """Test getting CVE from Redis cache."""
    # Mock Redis cache hit
    cached_cve_data = {
        "cve_id": "CVE-2024-1234",
        "description": "Test CVE",
        "published_date": "2024-01-01T00:00:00+00:00",
        "cvss_v3": {
            "version": "3.1",
            "base_score": 7.5,
            "base_severity": "HIGH"
        },
        "affected_products": [],
        "references": [],
        "nvd_url": "https://nvd.nist.gov/vuln/detail/CVE-2024-1234",
    }
    mock_redis_cache.get.return_value = cached_cve_data
    
    result = cve_service.get_cve("CVE-2024-1234")
    
    assert result is not None
    assert result.cve_id == "CVE-2024-1234"
    mock_redis_cache.get.assert_called_once_with("cve:CVE-2024-1234")
    # Should not make API call
    mock_requests.get.assert_not_called()


@patch('app.services.cve_service.redis_cache')
@patch('app.services.cve_service.requests')
def test_get_cve_from_api(mock_requests, mock_redis_cache, cve_service):
    """Test getting CVE from API when cache misses."""
    # Mock Redis cache miss
    mock_redis_cache.get.return_value = None
    
    # Mock database cache miss
    cve_service._check_cache = Mock(return_value=None)
    
    # Mock API response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "vulnerabilities": [{
            "cve": {
                "id": "CVE-2024-1234",
                "descriptions": [{"lang": "en", "value": "Test CVE"}],
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
        }]
    }
    mock_response.raise_for_status = Mock()
    mock_requests.get.return_value = mock_response
    
    # Mock save to cache
    cve_service._save_to_cache = Mock()
    mock_redis_cache.set.return_value = True
    
    result = cve_service.get_cve("CVE-2024-1234")
    
    assert result is not None
    assert result.cve_id == "CVE-2024-1234"
    mock_requests.get.assert_called_once()
    cve_service._save_to_cache.assert_called_once()


@patch('app.services.cve_service.redis_cache')
@patch('app.services.cve_service.requests')
def test_search_cves_from_redis_cache(mock_requests, mock_redis_cache, cve_service):
    """Test searching CVEs from Redis cache."""
    # Mock Redis cache hit
    cached_search_data = {
        "total": 1,
        "limit": 20,
        "offset": 0,
        "total_pages": 1,
        "cves": [{
            "cve_id": "CVE-2024-1234",
            "description": "Test CVE",
            "published_date": "2024-01-01T00:00:00+00:00",
            "affected_products": [],
            "references": [],
        }]
    }
    mock_redis_cache.get.return_value = cached_search_data
    
    request = CVESearchRequest(keyword="test", limit=20, offset=0)
    result = cve_service.search_cves(request)
    
    assert result.total == 1
    assert len(result.cves) == 1
    # Should not make API call
    mock_requests.get.assert_not_called()


def test_parse_nvd_response(cve_service):
    """Test parsing NVD API response."""
    nvd_data = {
        "cve": {
            "id": "CVE-2024-1234",
            "descriptions": [{"lang": "en", "value": "Test CVE description"}],
            "published": "2024-01-01T00:00:00Z",
            "lastModified": "2024-01-02T00:00:00Z",
            "metrics": {
                "cvssMetricV31": [{
                    "cvssData": {
                        "vectorString": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
                        "baseScore": 7.5,
                        "baseSeverity": "HIGH"
                    }
                }]
            },
            "weaknesses": [{
                "description": [{"value": "CWE-79"}]
            }],
            "configurations": [],
            "references": []
        }
    }
    
    cve = cve_service._parse_nvd_response(nvd_data)
    
    assert cve.cve_id == "CVE-2024-1234"
    assert cve.description == "Test CVE description"
    assert cve.cvss_v3 is not None
    assert cve.cvss_v3.base_score == 7.5
    assert cve.cvss_v3.base_severity == "HIGH"
    assert cve.cwe_id == "CWE-79"









