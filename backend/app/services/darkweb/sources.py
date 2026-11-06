"""Dark web source registry: built-in feeds, admin-defined custom feeds, health status and
per-user preferences."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urljoin, urlsplit

import requests
from jsonpath_ng import parse as jsonpath
from sqlalchemy.orm import Session

from app.core.url_guard import UnsafeURLError, validate_outbound_url
from app.models.darkweb import DarkWebSource

BUILTIN_SOURCES: list[dict[str, str]] = [
    {
        "key": "ransomware_live",
        "name": "ransomware.live",
        "category": "ransomware",
        "homepage": "https://www.ransomware.live",
        "description": "Victim posts published on ransomware groups' leak sites (aggregated, ~100 most recent).",
    },
    {
        "key": "ransomlook",
        "name": "RansomLook",
        "category": "ransomware",
        "homepage": "https://www.ransomlook.io",
        "description": "Second leak-site aggregator; improves coverage of groups the first one misses.",
    },
    {
        "key": "hudsonrock",
        "name": "Hudson Rock (Cavalier)",
        "category": "infostealer",
        "homepage": "https://www.hudsonrock.com/free-tools",
        "description": "Counts of infostealer-infected employees/users with credentials for your domains (free API).",
    },
    {
        "key": "hibp",
        "name": "Have I Been Pwned - breach catalog",
        "category": "breach",
        "homepage": "https://haveibeenpwned.com/PwnedWebsites",
        "description": "Public catalog of known data breaches, matched by breached domain.",
    },
    {
        "key": "telegram",
        "name": "Telegram channels",
        "category": "telegram",
        "homepage": "https://telegram.org",
        "description": "The public channels (and optional account channels) each user adds on the Telegram tab.",
    },
]

# Built-in feeds use the custom-feed machinery with a fixed configuration. Checked live 2026-11-06.
# "forum": dark web forum / market / Telegram sale posts and leak claims reported by monitoring sites.
_RSS = {"format": "rss"}
BUILTIN_FEEDS: list[dict] = [
    {
        "key": "darkwebinformer", "name": "Dark Web Informer", "category": "forum", "enabled": True,
        "homepage": "https://darkwebinformer.com",
        "description": "Database sales, access listings and leak claims seen on dark web forums and Telegram.",
        "config": {**_RSS, "url": "https://darkwebinformer.com/rss/", "severity": "high"},
    },
    {
        "key": "dailydarkweb", "name": "Daily Dark Web", "category": "forum", "enabled": False,
        "homepage": "https://dailydarkweb.net",
        "description": "Reports of data leaks and access sales. Off by default: no new posts since April 2026.",
        "config": {**_RSS, "url": "https://dailydarkweb.net/feed/", "severity": "high"},
    },
    {
        "key": "dexpose", "name": "DeXpose", "category": "forum", "enabled": True,
        "homepage": "https://www.dexpose.io",
        "description": "Ransomware and data leak victim disclosures observed on the dark web.",
        "config": {**_RSS, "url": "https://www.dexpose.io/feed/", "severity": "high"},
    },
    {
        "key": "databreaches_net", "name": "DataBreaches.net", "category": "breach", "enabled": True,
        "homepage": "https://databreaches.net",
        "description": "Breach reporting, including leak-site and forum claims.",
        "config": {**_RSS, "url": "https://databreaches.net/feed/", "severity": "high"},
    },
    # General security news: useful for brand monitoring but noisier -> off until an admin enables them
    {
        "key": "news_thecyberexpress", "name": "The Cyber Express", "category": "news", "enabled": False,
        "homepage": "https://thecyberexpress.com",
        "description": "Security news with a dedicated dark web section.",
        "config": {**_RSS, "url": "https://thecyberexpress.com/feed/", "severity": "medium"},
    },
    {
        "key": "news_securityaffairs", "name": "Security Affairs", "category": "news", "enabled": False,
        "homepage": "https://securityaffairs.com",
        "description": "Security news (data breaches, ransomware, cybercrime).",
        "config": {**_RSS, "url": "https://securityaffairs.com/feed", "severity": "medium"},
    },
    {
        "key": "news_hackread", "name": "Hackread", "category": "news", "enabled": False,
        "homepage": "https://hackread.com",
        "description": "Security news (leaks, breaches, cybercrime).",
        "config": {**_RSS, "url": "https://hackread.com/feed/", "severity": "medium"},
    },
    {
        "key": "news_therecord", "name": "The Record (Recorded Future News)", "category": "news", "enabled": False,
        "homepage": "https://therecord.media",
        "description": "Cybersecurity news from Recorded Future.",
        "config": {**_RSS, "url": "https://therecord.media/feed", "severity": "medium"},
    },
]

# Public Telegram channels that repost leak / ransomware alerts (public preview verified 2026-11-06)
SUGGESTED_CHANNELS: list[dict[str, str]] = [
    {"username": "darkfeed", "title": "Dark Feed", "why": "Ransomware victim and data leak alerts"},
    {"username": "vxunderground", "title": "vx-underground", "why": "Malware research, leaks and threat actor news"},
]


MAX_FEED_BYTES = 5 * 1024 * 1024
MAX_FEED_ITEMS = 500
_HEADERS = {"User-Agent": "ThreatIntelPlatform/2.1 (dark web monitor)"}


def seed_sources(db: Session) -> None:
    """Create / refresh built-in sources. The admin's enabled flag is kept; name, description and feed
    configuration are refreshed so fixes in new releases reach existing installations."""
    existing = {s.key: s for s in db.query(DarkWebSource).filter(DarkWebSource.builtin.is_(True)).all()}
    specs = [dict(spec, enabled=True, config=None) for spec in BUILTIN_SOURCES] + BUILTIN_FEEDS
    for spec in specs:
        row = existing.get(spec["key"])
        fields = {k: spec[k] for k in ("name", "category", "homepage", "description", "config")}
        if row is None:
            db.add(DarkWebSource(key=spec["key"], builtin=True, is_enabled=spec["enabled"], **fields))
        else:
            for field, value in fields.items():
                setattr(row, field, value)
    db.commit()


def ensure_seeded(db: Session) -> None:
    """Seed built-ins if missing (startup normally does this; custom rows may already exist)."""
    expected = len(BUILTIN_SOURCES) + len(BUILTIN_FEEDS)
    if db.query(DarkWebSource).filter(DarkWebSource.builtin.is_(True)).count() < expected:
        seed_sources(db)


def record(db: Session, key: str, *, ok: bool, items: Optional[int] = None, started: Optional[float] = None,
           error: Optional[str] = None) -> None:
    row = db.query(DarkWebSource).filter_by(key=key).first()
    if row is None:
        return
    now = datetime.now(timezone.utc)
    row.last_fetch_at = now
    if started is not None:
        row.last_duration_ms = int((time.monotonic() - started) * 1000)
    if ok:
        row.last_success_at = now
        row.last_error = None
        row.last_item_count = items
    else:
        row.last_error = (error or "failed")[:500]


def disabled_by_user(profile_json: Optional[dict]) -> set[str]:
    return set((profile_json or {}).get("darkweb_disabled_sources") or [])


def active_keys(db: Session, profile_json: Optional[dict]) -> set[str]:
    """Sources that are globally enabled and not switched off by this user."""
    enabled = {k for (k,) in db.query(DarkWebSource.key).filter(DarkWebSource.is_enabled.is_(True)).all()}
    return enabled - disabled_by_user(profile_json)


# --------------------------------------------------------------------------- custom feeds


@dataclass
class FeedItem:
    title: str
    text: str
    url: str
    published_at: Optional[datetime]


def validate_config(config: dict) -> Optional[str]:
    url = str(config.get("url") or "")
    if not url.lower().startswith(("https://", "http://")):
        return "Feed URL must start with http:// or https://"
    try:
        validate_outbound_url(url)
    except UnsafeURLError as exc:
        return f"Feed URL not allowed: {exc}"
    fmt = config.get("format")
    if fmt not in ("json", "rss"):
        return "Format must be json or rss"
    if fmt == "json":
        for key in ("items_path", "title_path", "text_path", "url_path", "date_path"):
            path = config.get(key)
            if path:
                try:
                    jsonpath(path)
                except Exception:
                    return f"Invalid JSONPath in {key}: {path}"
        if not config.get("title_path"):
            return "title_path is required for JSON feeds"
    if config.get("severity", "high") not in ("critical", "high", "medium", "low"):
        return "Invalid severity"
    return None


def _download(url: str, timeout: int = 30) -> bytes:
    """GET with SSRF checks on every hop, same-host redirects only and a size cap."""
    for _ in range(4):
        validate_outbound_url(url)
        response = requests.get(url, headers=_HEADERS, timeout=timeout, allow_redirects=False, stream=True)
        if response.is_redirect and response.headers.get("Location"):
            nxt = urljoin(url, response.headers["Location"])
            response.close()
            if urlsplit(nxt).netloc != urlsplit(url).netloc:
                raise UnsafeURLError("Cross-host redirect refused")
            url = nxt
            continue
        response.raise_for_status()
        data = response.raw.read(MAX_FEED_BYTES + 1, decode_content=True)
        if len(data) > MAX_FEED_BYTES:
            raise ValueError("Feed larger than 5 MB")
        return data
    raise ValueError("Too many redirects")


def _first(node: Any, path: Optional[str]) -> str:
    if not path:
        return ""
    matches = [m.value for m in jsonpath(path).find(node)]
    if not matches or matches[0] is None:
        return ""
    value = matches[0]
    return " ".join(map(str, value)) if isinstance(value, list) else str(value)


def _date(value: str) -> Optional[datetime]:
    if not value:
        return None
    from email.utils import parsedate_to_datetime

    for parser in (lambda v: datetime.fromisoformat(v.replace("Z", "+00:00")), parsedate_to_datetime):
        try:
            dt = parser(value.strip())
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue
    return None


def parse_json_feed(data: bytes, config: dict) -> list[FeedItem]:
    import json

    doc = json.loads(data)
    items = [m.value for m in jsonpath(config.get("items_path") or "$[*]").find(doc)]
    if len(items) == 1 and isinstance(items[0], list):
        items = items[0]
    out = []
    for item in items[:MAX_FEED_ITEMS]:
        title = _first(item, config.get("title_path"))
        if not title:
            continue
        out.append(
            FeedItem(
                title=title[:500],
                text=_first(item, config.get("text_path"))[:5000],
                url=_first(item, config.get("url_path"))[:1000],
                published_at=_date(_first(item, config.get("date_path"))),
            )
        )
    return out


def parse_rss_feed(data: bytes) -> list[FeedItem]:
    """RSS 2.0 and Atom. defusedxml blocks entity expansion / external entities."""
    import re

    from defusedxml import ElementTree

    root = ElementTree.fromstring(data)

    def local(tag: str) -> str:
        return tag.rsplit("}", 1)[-1]

    out = []
    for node in root.iter():
        if local(node.tag) not in ("item", "entry"):
            continue
        fields: dict[str, str] = {}
        for child in node:
            name = local(child.tag)
            if name == "link" and child.get("href"):
                fields.setdefault("link", child.get("href"))
            elif child.text:
                fields.setdefault(name, child.text.strip())
        title = fields.get("title", "")
        if not title:
            continue
        text = re.sub(r"<[^>]+>", " ", fields.get("description") or fields.get("summary") or fields.get("content") or "")
        out.append(
            FeedItem(
                title=title[:500],
                text=re.sub(r"\s+", " ", text).strip()[:5000],
                url=(fields.get("link") or "")[:1000],
                published_at=_date(fields.get("pubDate") or fields.get("published") or fields.get("updated") or ""),
            )
        )
        if len(out) >= MAX_FEED_ITEMS:
            break
    return out


def fetch_custom(config: dict) -> list[FeedItem]:
    data = _download(config["url"])
    return parse_json_feed(data, config) if config.get("format") == "json" else parse_rss_feed(data)
