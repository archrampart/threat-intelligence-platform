"""Extract IOCs from free text (reports, logs, e-mails, chat messages).

Handles common defanging (hxxp, [.], (.), [dot], [:]) and returns unique IOCs in the
order they first appear. File names such as ``invoice.pdf`` are not reported as domains.
"""

from __future__ import annotations

import ipaddress
import re

MAX_IOCS = 500

_REFANG = [
    (re.compile(r"h[xX]{2}p(s?)", re.I), r"http\1"),
    (re.compile(r"\[\s*\.\s*\]|\(\s*\.\s*\)|\{\s*\.\s*\}|\[dot\]|\(dot\)", re.I), "."),
    (re.compile(r"\[\s*:\s*\]"), ":"),
    (re.compile(r"\[\s*@\s*\]|\[at\]|\(at\)", re.I), "@"),
    (re.compile(r"\[(/{1,2})\]"), r"\1"),
]

_URL = re.compile(r"\b(?:https?|ftp)://[^\s<>\"'`]+", re.I)
_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,24}\b")
_IPV4 = re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b")
_HASH = re.compile(r"\b(?:[A-Fa-f0-9]{64}|[A-Fa-f0-9]{40}|[A-Fa-f0-9]{32})\b")
_CVE = re.compile(r"\bCVE-\d{4}-\d{4,7}\b", re.I)
_DOMAIN = re.compile(
    r"\b(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z][A-Za-z0-9-]{1,23}\b"
)

# Extensions that look like TLDs but almost always mean a file name in reports.
_FILE_EXTENSIONS = {
    "exe", "dll", "sys", "bat", "cmd", "ps1", "vbs", "js", "jar", "py", "sh", "bin", "elf",
    "doc", "docx", "docm", "xls", "xlsx", "xlsm", "ppt", "pptx", "pdf", "rtf", "txt", "csv", "log",
    "zip", "rar", "7z", "gz", "tar", "iso", "img", "lnk", "hta", "msi", "scr", "tmp", "dat",
    "png", "jpg", "jpeg", "gif", "svg", "html", "htm", "php", "asp", "aspx", "json", "xml", "yaml", "yml",
}


def refang(text: str) -> str:
    for pattern, replacement in _REFANG:
        text = pattern.sub(replacement, text)
    return text


def _clean_url(url: str) -> str:
    return url.rstrip(".,;:!?)]}>'\"")


def extract_iocs(text: str, limit: int = MAX_IOCS) -> tuple[list[dict[str, str]], bool]:
    """Return ([{"ioc_type": ..., "ioc_value": ...}], truncated)."""
    text = refang(text or "")
    found: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    consumed: list[tuple[int, int]] = []  # spans already reported (URLs, e-mails)

    def add(ioc_type: str, value: str) -> None:
        key = (ioc_type, value.lower())
        if key not in seen:
            seen.add(key)
            found.append({"ioc_type": ioc_type, "ioc_value": value})

    def inside_consumed(start: int, end: int) -> bool:
        return any(s <= start and end <= e for s, e in consumed)

    for m in _URL.finditer(text):
        add("url", _clean_url(m.group(0)))
        consumed.append(m.span())
    for m in _EMAIL.finditer(text):
        if not inside_consumed(*m.span()):
            add("email", m.group(0))
            consumed.append(m.span())
    for m in _CVE.finditer(text):
        add("cve", m.group(0).upper())
    for m in _HASH.finditer(text):
        add("hash", m.group(0).lower())
    for m in _IPV4.finditer(text):
        if inside_consumed(*m.span()):
            continue
        try:
            ip = ipaddress.ip_address(m.group(0))
        except ValueError:
            continue
        if not (ip.is_unspecified or ip.is_loopback):
            add("ip", m.group(0))
    for m in _DOMAIN.finditer(text):
        value = m.group(0).rstrip(".")
        if inside_consumed(*m.span()) or _IPV4.fullmatch(value):
            continue
        tld = value.rsplit(".", 1)[-1].lower()
        if tld in _FILE_EXTENSIONS or tld.isdigit():
            continue
        add("domain", value.lower())

    truncated = len(found) > limit
    return found[:limit], truncated
