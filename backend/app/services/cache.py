from datetime import datetime, timedelta, timezone
from typing import Dict, Tuple

from app.schemas.ioc import IOCQueryResponse


class IOCResponseCache:
    def __init__(self, ttl_seconds: int = 300) -> None:
        self.ttl = timedelta(seconds=ttl_seconds)
        self._store: Dict[Tuple[str, str], Tuple[IOCQueryResponse, datetime]] = {}

    def _make_key(self, ioc_type: str, ioc_value: str) -> Tuple[str, str]:
        return ioc_type.lower(), ioc_value.lower()

    def get(self, ioc_type: str, ioc_value: str) -> IOCQueryResponse | None:
        key = self._make_key(ioc_type, ioc_value)
        cached = self._store.get(key)
        if not cached:
            return None

        response, stored_at = cached
        if datetime.now(timezone.utc) - stored_at > self.ttl:
            del self._store[key]
            return None
        return response

    def set(self, response: IOCQueryResponse) -> None:
        key = self._make_key(response.ioc_type, response.ioc_value)
        self._store[key] = (response, datetime.now(timezone.utc))


ioc_cache = IOCResponseCache()
