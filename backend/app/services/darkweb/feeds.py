"""Shared dark web feeds (fetched once per scan for all users).

* Ransomware leak-site victims: ransomware.live (v2/recentvictims) and RansomLook (api/recent).
  Both aggregators monitor the groups' onion sites; we never connect to Tor ourselves.
* Have I Been Pwned public breach catalog (no key needed for the catalog itself).
* Hudson Rock Cavalier: free infostealer exposure statistics per domain.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import requests
from loguru import logger

HEADERS = {"User-Agent": "ThreatIntelPlatform/2.1 (dark web monitor)", "Accept": "application/json"}
RANSOMWARE_LIVE_URL = "https://api.ransomware.live/v2/recentvictims"
RANSOMLOOK_URL = "https://www.ransomlook.io/api/recent"
HIBP_BREACHES_URL = "https://haveibeenpwned.com/api/v3/breaches"
HUDSONROCK_URL = "https://cavalier.hudsonrock.com/api/json/v2/osint-tools/search-by-domain"

_cache: dict[str, tuple[float, Any]] = {}
_lock = threading.Lock()


def _cached_json(url: str, ttl: int, params: Optional[dict] = None, timeout: int = 30) -> Any:
    key = url + repr(sorted((params or {}).items()))
    now = time.time()
    with _lock:
        hit = _cache.get(key)
        if hit and now - hit[0] < ttl:
            return hit[1]
    response = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    with _lock:
        _cache[key] = (now, data)
    return data


def _dt(value: Any) -> Optional[datetime]:
    if not value or value == "None":
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00").replace(" ", "T", 1))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _clean(value: Any) -> str:
    return "" if value in (None, "None", "null") else str(value).strip()


@dataclass
class LeakPost:
    source: str  # ransomware.live | ransomlook
    group: str
    victim: str
    domain: str
    description: str
    url: str
    published_at: Optional[datetime]
    extra: dict = field(default_factory=dict)

    @property
    def key(self) -> str:
        return f"{self.group.lower()}|{self.victim.lower()}"


def _expect_list(data: Any, source: str) -> list:
    if isinstance(data, dict) and data.get("message"):
        raise ValueError(f"{source}: {data['message']}")  # e.g. rate limit "1 per 1 minute"
    if not isinstance(data, list):
        raise ValueError(f"{source}: unexpected response")
    return data


def ransomware_live_posts() -> list[LeakPost]:
    """Raises on failure (the caller records the source status)."""
    return [
        LeakPost(
            source="ransomware.live",
            group=_clean(item.get("group")),
            victim=_clean(item.get("victim")),
            domain=_clean(item.get("domain")).lower(),
            description=_clean(item.get("description")),
            url=_clean(item.get("url")),
            published_at=_dt(item.get("attackdate")) or _dt(item.get("discovered")),
            extra={"country": _clean(item.get("country")), "activity": _clean(item.get("activity"))},
        )
        for item in _expect_list(_cached_json(RANSOMWARE_LIVE_URL, ttl=600), "ransomware.live")
    ]


def ransomlook_posts() -> list[LeakPost]:
    """Raises on failure (the caller records the source status)."""
    return [
        LeakPost(
            source="ransomlook",
            group=_clean(item.get("group_name")),
            victim=_clean(item.get("post_title")),
            domain="",
            description=_clean(item.get("description")),
            url=f"https://www.ransomlook.io/group/{_clean(item.get('group_name'))}",
            published_at=_dt(item.get("discovered")),
        )
        for item in _expect_list(_cached_json(RANSOMLOOK_URL, ttl=600), "RansomLook")
    ]


def merge_posts(*groups: list[LeakPost]) -> list[LeakPost]:
    """Both aggregators often report the same post: keep the first (ransomware.live has more fields)."""
    unique: dict[str, LeakPost] = {}
    for group in groups:
        for post in group:
            unique.setdefault(post.key, post)
    return list(unique.values())


def ransomware_posts() -> list[LeakPost]:
    groups = []
    for fetch in (ransomware_live_posts, ransomlook_posts):
        try:
            groups.append(fetch())
        except Exception as exc:
            logger.warning("Leak-site feed failed: {}", exc)
    return merge_posts(*groups)


def hibp_catalog() -> list[dict]:
    """Raises on failure."""
    return _cached_json(HIBP_BREACHES_URL, ttl=6 * 3600) or []


def hibp_breaches() -> list[dict]:
    try:
        return _cached_json(HIBP_BREACHES_URL, ttl=6 * 3600) or []
    except Exception as exc:
        logger.warning("HIBP breach catalog failed: {}", exc)
        return []


def infostealer_exposure(domain: str, raise_errors: bool = False) -> Optional[dict]:
    """Return {employees, users, third_parties, last_employee_compromised, ...} or None on failure."""
    try:
        data = _cached_json(HUDSONROCK_URL, ttl=12 * 3600, params={"domain": domain}, timeout=30)
    except Exception as exc:
        logger.warning("Hudson Rock lookup failed for {}: {}", domain, exc)
        if raise_errors:
            raise
        return None
    if not isinstance(data, dict):
        return None
    return {
        "employees": int(data.get("employees") or 0),
        "users": int(data.get("users") or 0),
        "third_parties": int(data.get("third_parties") or 0),
        "last_employee_compromised": data.get("last_employee_compromised"),
        "last_user_compromised": data.get("last_user_compromised"),
        "stealer_families": {
            k: v for k, v in (data.get("stealerFamilies") or {}).items() if k not in ("total", "UNKNOWN") and v
        },
    }
