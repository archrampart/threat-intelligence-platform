from datetime import datetime, timedelta, timezone
from typing import Dict, Tuple

from app.schemas.ioc import IOCQueryResponse


class IOCResponseCache:
    def __init__(self, ttl_seconds: int = 300) -> None:
        self.ttl = timedelta(seconds=ttl_seconds)
        self._store: Dict[Tuple[str, str, str], Tuple[IOCQueryResponse, datetime]] = {}

    def _make_key(self, ioc_type: str, ioc_value: str, scope: str) -> Tuple[str, str, str]:
        # scope = user id: results depend on the caller's own API keys and must not leak across users
        return scope, ioc_type.lower(), ioc_value.lower()

    def get(self, ioc_type: str, ioc_value: str, scope: str = "") -> IOCQueryResponse | None:
        key = self._make_key(ioc_type, ioc_value, scope)
        cached = self._store.get(key)
        if not cached:
            return None

        response, stored_at = cached
        if datetime.now(timezone.utc) - stored_at > self.ttl:
            del self._store[key]
            return None
        return response

    def set(self, response: IOCQueryResponse, scope: str = "") -> None:
        key = self._make_key(response.ioc_type, response.ioc_value, scope)
        self._store[key] = (response, datetime.now(timezone.utc))


ioc_cache = IOCResponseCache()
