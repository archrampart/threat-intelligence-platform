"""Unit tests for IOC service."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from uuid import uuid4

from app.services.ioc_service import IOCService
from app.schemas.ioc import IOCQueryRequest, IOCQueryResponse, IOCSourceResult
from app.models.api_source import APISource, APIKey, UpdateMode
from app.models.user import User


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return Mock()


@pytest.fixture
def ioc_service(mock_db):
    """Create IOC service instance."""
    return IOCService(mock_db)


def test_ioc_service_init(ioc_service):
    """Test IOC service initialization."""
    assert ioc_service.db is not None


def test_get_risk_score_from_level(ioc_service):
    """Test risk level to score conversion."""
    assert ioc_service._get_risk_score_from_level("high") == 0.9
    assert ioc_service._get_risk_score_from_level("medium") == 0.6
    assert ioc_service._get_risk_score_from_level("low") == 0.3
    assert ioc_service._get_risk_score_from_level("clean") == 0.1
    assert ioc_service._get_risk_score_from_level("unknown") == 0.5
    assert ioc_service._get_risk_score_from_level(None) is None
    assert ioc_service._get_risk_score_from_level("invalid") is None


def test_calculate_overall_risk(ioc_service):
    """Test overall risk calculation."""
    # High risk
    results = [
        IOCSourceResult(source="test1", status="success", risk_score=0.9, description="", raw=None),
        IOCSourceResult(source="test2", status="success", risk_score=0.8, description="", raw=None),
    ]
    assert ioc_service._calculate_overall_risk(results) == "high"
    
    # Medium risk
    results = [
        IOCSourceResult(source="test1", status="success", risk_score=0.5, description="", raw=None),
        IOCSourceResult(source="test2", status="success", risk_score=0.6, description="", raw=None),
    ]
    assert ioc_service._calculate_overall_risk(results) == "medium"
    
    # Low risk
    results = [
        IOCSourceResult(source="test1", status="success", risk_score=0.2, description="", raw=None),
        IOCSourceResult(source="test2", status="success", risk_score=0.3, description="", raw=None),
    ]
    assert ioc_service._calculate_overall_risk(results) == "low"
    
    # Clean
    results = [
        IOCSourceResult(source="test1", status="success", risk_score=0.1, description="", raw=None),
    ]
    assert ioc_service._calculate_overall_risk(results) == "clean"
    
    # Unknown (errors)
    results = [
        IOCSourceResult(source="test1", status="error", risk_score=None, description="", raw=None),
    ]
    assert ioc_service._calculate_overall_risk(results) == "unknown"
    
    # None (no valid results)
    results = [
        IOCSourceResult(source="test1", status="skipped", risk_score=None, description="", raw=None),
    ]
    assert ioc_service._calculate_overall_risk(results) is None


@patch('app.services.ioc_service.redis_cache')
@patch('app.services.ioc_service.ioc_cache')
def test_query_ioc_from_redis_cache(mock_ioc_cache, mock_redis_cache, ioc_service):
    """Test querying IOC from Redis cache."""
    # Mock Redis cache hit
    cached_response_data = {
        "ioc_type": "ip",
        "ioc_value": "1.2.3.4",
        "overall_risk": "high",
        "queried_sources": [
            {
                "source": "test",
                "status": "success",
                "risk_score": 0.9,
                "description": "Test",
                "raw": None
            }
        ],
        "queried_at": datetime.now(timezone.utc).isoformat(),
    }
    mock_redis_cache.get.return_value = cached_response_data
    
    payload = IOCQueryRequest(ioc_type="ip", ioc_value="1.2.3.4")
    user_id = str(uuid4())
    
    result = ioc_service.query_ioc(user_id, payload)
    
    assert result is not None
    assert result.ioc_type == "ip"
    assert result.ioc_value == "1.2.3.4"
    assert result.overall_risk == "high"
    mock_redis_cache.get.assert_called_once()


@patch('app.services.ioc_service.redis_cache')
@patch('app.services.ioc_service.ioc_cache')
@patch('app.services.ioc_service.DynamicAPIClient')
def test_query_ioc_from_api(mock_dynamic_client, mock_ioc_cache, mock_redis_cache, ioc_service):
    """Test querying IOC from API when cache misses."""
    # Mock Redis cache miss
    mock_redis_cache.get.return_value = None
    # Mock in-memory cache miss
    mock_ioc_cache.get.return_value = None
    
    # Mock API source and key
    api_source = Mock(spec=APISource)
    api_source.id = str(uuid4())
    api_source.name = "test_source"
    api_source.display_name = "Test Source"
    api_source.supported_ioc_types = ["ip", "domain"]
    api_source.is_active = True
    
    api_key = Mock(spec=APIKey)
    api_key.id = str(uuid4())
    api_key.api_source_id = api_source.id
    api_key.is_active = True
    api_key.update_mode = UpdateMode.MANUAL
    
    # Mock database query
    ioc_service._get_active_api_keys = Mock(return_value=[(api_key, api_source)])
    
    # Mock dynamic client
    mock_client_instance = Mock()
    mock_client_instance.query.return_value = {
        "status": "success",
        "risk_score": 0.9,
        "raw": {"test": "data"},
        "data": {"description": "Test threat"}
    }
    mock_dynamic_client.return_value = mock_client_instance
    
    # Mock encryption
    with patch('app.services.ioc_service.decrypt_value', return_value="decrypted_key"):
        payload = IOCQueryRequest(ioc_type="ip", ioc_value="1.2.3.4")
        user_id = str(uuid4())
        
        result = ioc_service.query_ioc(user_id, payload)
        
        assert result is not None
        assert result.ioc_type == "ip"
        assert result.ioc_value == "1.2.3.4"
        assert result.overall_risk is not None
        assert len(result.queried_sources) > 0
        mock_redis_cache.set.assert_called_once()


def test_list_query_history(ioc_service):
    """Test listing IOC query history."""
    user_id = str(uuid4())
    
    # Use a simpler approach - mock the final result instead of the entire chain
    # This avoids issues with SQLAlchemy query comparisons
    from app.models.ioc_query import IOCQuery
    
    # Mock the final query result
    mock_queries = []
    
    # Create a mock that returns empty list for .all() and 0 for .count()
    mock_query_result = Mock()
    mock_query_result.all.return_value = mock_queries
    mock_query_result.count.return_value = 0
    
    # Mock order_by().offset().limit() chain
    mock_limit = Mock()
    mock_limit.all.return_value = mock_queries
    
    mock_offset = Mock()
    mock_offset.limit.return_value = mock_limit
    
    mock_order_by = Mock()
    mock_order_by.offset.return_value = mock_offset
    
    # Mock filter() - it should return itself for chaining, but also support order_by()
    mock_filter = Mock()
    mock_filter.filter.return_value = mock_filter  # Chainable
    mock_filter.order_by.return_value = mock_order_by
    mock_filter.count.return_value = 0
    
    # Mock query() to return our filter mock
    def query_side_effect(model):
        if model == IOCQuery:
            return mock_filter
        return Mock()
    
    ioc_service.db.query = Mock(side_effect=query_side_effect)
    
    result = ioc_service.list_query_history(
        user_id=user_id,
        page=1,
        page_size=20
    )
    
    assert result["total"] == 0
    assert result["page"] == 1
    assert result["page_size"] == 20
    assert result["items"] == []

