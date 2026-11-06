"""Match monitored assets (domains, keywords, e-mail domains) against free text."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Optional


@dataclass(frozen=True)
class Asset:
    id: str
    user_id: str
    kind: str  # domain | keyword | email_domain
    value: str


def normalise(kind: str, value: str) -> str:
    value = value.strip()
    if kind in ("domain", "email_domain"):
        value = value.lower().lstrip("@").removeprefix("https://").removeprefix("http://").removeprefix("www.")
        value = value.split("/", 1)[0]
    return value


_DOMAIN_RE = re.compile(r"^(?=.{4,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")


def validate(kind: str, value: str) -> Optional[str]:
    """Return an error message or None."""
    if kind in ("domain", "email_domain"):
        if not _DOMAIN_RE.match(value):
            return "Not a valid domain name"
    elif kind == "keyword":
        if len(value) < 3:
            return "Keywords need at least 3 characters (short terms cause false positives)"
        if len(value) > 100:
            return "Keyword too long"
    else:
        return "Unknown asset type"
    return None


def _pattern(asset: Asset) -> re.Pattern:
    value = re.escape(asset.value)
    if asset.kind == "domain":
        # the domain itself or any subdomain, not part of a longer label (evil-acme.com != acme.com)
        # (acme.com.tr is a different domain; a sentence-ending "acme.com." still matches)
        return re.compile(rf"(?<![A-Za-z0-9-])(?:[A-Za-z0-9-]+\.)*{value}(?![A-Za-z0-9-]|\.[A-Za-z0-9])", re.I)
    if asset.kind == "email_domain":
        return re.compile(rf"@(?:[A-Za-z0-9-]+\.)*{value}(?![A-Za-z0-9-]|\.[A-Za-z0-9])", re.I)
    return re.compile(rf"(?<!\w){value}(?!\w)", re.I)


class Matcher:
    def __init__(self, assets: Iterable[Asset]):
        self.assets = list(assets)
        self._patterns = [(a, _pattern(a)) for a in self.assets]

    def find(self, *texts: Optional[str]) -> list[Asset]:
        blob = "\n".join(t for t in texts if t)
        if not blob:
            return []
        return [asset for asset, pattern in self._patterns if pattern.search(blob)]

    def snippet(self, text: str, asset: Asset, width: int = 160) -> str:
        """Short context around the first match."""
        m = _pattern(asset).search(text or "")
        if not m:
            return (text or "")[:width * 2]
        start, end = max(0, m.start() - width), min(len(text), m.end() + width)
        return ("…" if start else "") + text[start:end].strip() + ("…" if end < len(text) else "")
