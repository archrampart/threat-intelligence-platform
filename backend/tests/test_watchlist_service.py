"""Unit tests for Watchlist service."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone
from uuid import uuid4

from app.services.watchlist_service import WatchlistService
from app.models.watchlist import AssetWatchlist, AssetWatchlistItem
from app.models.user import User, UserRole


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return Mock()


@pytest.fixture
def watchlist_service(mock_db):
    """Create Watchlist service instance."""
    return WatchlistService(mock_db)


def test_watchlist_service_init(watchlist_service):
    """Test Watchlist service initialization."""
    assert watchlist_service.db is not None


def test_create_watchlist_basic(watchlist_service):
    """Test basic watchlist creation."""
    user_id = str(uuid4())
    
    from app.schemas.watchlist import WatchlistCreate, WatchlistAsset, Watchlist
    
    payload = WatchlistCreate(
        name="Test Watchlist",
        description="Test description",
        assets=[],
        notification_enabled=False,
        check_interval=60
    )
    
    # Mock the return value of _to_watchlist_response
    mock_watchlist_response = Watchlist(
        id=str(uuid4()),
        name="Test Watchlist",
        description="Test description",
        user_id=user_id,
        assets=[],
        is_active=True,
        notification_enabled=False,
        check_interval=60,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    
    watchlist_service._to_watchlist_response = Mock(return_value=mock_watchlist_response)
    watchlist_service.db.add = Mock()
    watchlist_service.db.commit = Mock()
    watchlist_service.db.refresh = Mock()
    watchlist_service.db.flush = Mock()
    
    result = watchlist_service.create_watchlist(
        user_id=user_id,
        payload=payload
    )
    
    assert result is not None
    assert result.name == "Test Watchlist"
    watchlist_service.db.add.assert_called()
    watchlist_service.db.commit.assert_called_once()




def test_add_assets_to_watchlist(watchlist_service):
    """Test adding assets to watchlist."""
    watchlist_id = str(uuid4())
    user_id = str(uuid4())
    
    # Mock watchlist
    mock_watchlist = Mock(spec=AssetWatchlist)
    mock_watchlist.id = watchlist_id
    mock_watchlist.user_id = user_id
    
    watchlist_service.get_watchlist = Mock(return_value=mock_watchlist)
    watchlist_service.db.query.return_value.filter.return_value.first.return_value = mock_watchlist
    watchlist_service.db.add = Mock()
    watchlist_service.db.commit = Mock()
    watchlist_service.db.refresh = Mock()
    watchlist_service._to_watchlist_response = Mock(return_value=mock_watchlist)
    
    from app.schemas.watchlist import WatchlistAsset
    
    assets = [
        WatchlistAsset(
            ioc_type="ip",
            ioc_value="1.2.3.4",
            description="Test IP",
            is_active=True
        )
    ]
    
    result = watchlist_service.add_assets_to_watchlist(
        watchlist_id=watchlist_id,
        user_id=user_id,
        assets=assets
    )
    
    assert result is not None
    watchlist_service.db.add.assert_called()
    watchlist_service.db.commit.assert_called_once()

