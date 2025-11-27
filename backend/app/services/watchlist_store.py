from datetime import datetime
from typing import Dict, List
from uuid import UUID, uuid4

from app.schemas.watchlist import Watchlist, WatchlistAsset, WatchlistCreate


class WatchlistStore:
    """Basit bellek içi watchlist deposu."""

    def __init__(self) -> None:
        self._watchlists: Dict[UUID, Watchlist] = {}

    def list_watchlists(self) -> List[Watchlist]:
        return list(self._watchlists.values())

    def get_watchlist(self, watchlist_id: UUID) -> Watchlist | None:
        return self._watchlists.get(watchlist_id)

    def create_watchlist(self, payload: WatchlistCreate) -> Watchlist:
        now = datetime.utcnow()
        watchlist_id = uuid4()
        assets = [self._prepare_asset(asset) for asset in payload.assets]
        watchlist = Watchlist(
            id=watchlist_id,
            name=payload.name,
            description=payload.description,
            check_interval=payload.check_interval,
            notification_enabled=payload.notification_enabled,
            is_active=True,
            created_at=now,
            updated_at=now,
            assets=assets,
        )
        self._watchlists[watchlist_id] = watchlist
        return watchlist

    def update_watchlist(self, watchlist_id: UUID, payload: WatchlistCreate) -> Watchlist | None:
        existing = self._watchlists.get(watchlist_id)
        if not existing:
            return None

        now = datetime.utcnow()
        assets = [self._prepare_asset(asset) for asset in payload.assets]
        updated = Watchlist(
            id=existing.id,
            name=payload.name,
            description=payload.description,
            check_interval=payload.check_interval,
            notification_enabled=payload.notification_enabled,
            is_active=existing.is_active,
            created_at=existing.created_at,
            updated_at=now,
            assets=assets,
        )
        self._watchlists[watchlist_id] = updated
        return updated

    def delete_watchlist(self, watchlist_id: UUID) -> bool:
        if watchlist_id in self._watchlists:
            del self._watchlists[watchlist_id]
            return True
        return False

    def _prepare_asset(self, asset: WatchlistAsset) -> WatchlistAsset:
        return WatchlistAsset(
            id=asset.id or uuid4(),
            ioc_type=asset.ioc_type,
            ioc_value=asset.ioc_value,
            description=asset.description,
            risk_threshold=asset.risk_threshold,
            is_active=asset.is_active,
            created_at=asset.created_at or datetime.utcnow(),
        )


def get_watchlist_store() -> WatchlistStore:
    global _WATCHLIST_STORE
    try:
        return _WATCHLIST_STORE
    except NameError:
        _WATCHLIST_STORE = WatchlistStore()
        return _WATCHLIST_STORE
