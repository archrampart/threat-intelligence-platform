"""Match monitored assets (domains, keywords, e-mail domains, e-mail addresses) against free text."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Optional


@dataclass(frozen=True)
class Asset:
    id: str
    user_id: str
    kind: str  # domain | keyword | email_domain | email
    value: str


def normalise(kind: str, value: str) -> str:
    value = value.strip()
    if kind in ("domain", "email_domain"):
        value = value.lower().lstrip("@").removeprefix("https://").removeprefix("http://").removeprefix("www.")
        value = value.split("/", 1)[0]
    elif kind == "email":
        value = value.lower().removeprefix("mailto:").strip("<>")
    return value


_DOMAIN_RE = re.compile(r"^(?=.{4,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")
_EMAIL_RE = re.compile(r"^(?=.{6,254}$)[a-z0-9](?:[a-z0-9._%+-]{0,62}[a-z0-9_%+-])?@([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")

# Public mailbox providers: as a domain asset they match almost every leak and flood the
# user with unrelated alerts. A single mailbox on them is watched with the "email" kind.
FREE_MAIL_PROVIDERS = frozenset({
    "gmail.com", "googlemail.com", "hotmail.com", "hotmail.co.uk", "hotmail.fr", "hotmail.de", "outlook.com",
    "live.com", "msn.com", "yahoo.com", "yahoo.co.uk", "yahoo.fr", "yahoo.de", "ymail.com", "icloud.com",
    "me.com", "mac.com", "aol.com", "gmx.com", "gmx.de", "gmx.net", "web.de", "mail.com", "mail.ru",
    "yandex.com", "yandex.ru", "yandex.com.tr", "proton.me", "protonmail.com", "zoho.com", "mynet.com",
    "qq.com", "163.com", "126.com",
})


def validate(kind: str, value: str) -> Optional[str]:
    """Return an error message or None."""
    if kind in ("domain", "email_domain"):
        if "@" in value:
            return ("Enter only the domain part (e.g. acme.com). "
                    "Use the \"E-mail address\" type to watch a single mailbox.")
        if not _DOMAIN_RE.match(value):
            return "Not a valid domain name"
        if value in FREE_MAIL_PROVIDERS:
            return (f"{value} is a public mail provider: it appears in almost every leak and would flood you "
                    "with unrelated alerts. Use the \"E-mail address\" type to watch a single mailbox.")
    elif kind == "email":
        if not _EMAIL_RE.match(value):
            return "Not a valid e-mail address"
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
    if asset.kind == "email":
        # the exact address, not a longer local part (xceo@ / ceo.x@) or a longer domain (acme.com.tr)
        return re.compile(rf"(?<![A-Za-z0-9._%+-]){value}(?![A-Za-z0-9-]|\.[A-Za-z0-9])", re.I)
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
