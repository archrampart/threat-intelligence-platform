"""Outbound alert notifications (Slack, Microsoft Teams, generic JSON webhooks).

Settings are stored per user in ``User.profile_json["notifications"]``:

    {"webhook_url": "...", "format": "slack" | "teams" | "generic",
     "min_severity": "low" | "medium" | "high" | "critical", "enabled": true}

Delivery runs in a background thread and never blocks or breaks alert creation.
Webhook URLs go through the same SSRF guard as threat intelligence sources.
"""

from __future__ import annotations

import threading
from typing import Any, Optional

import requests
from loguru import logger

from app.core.url_guard import UnsafeURLError, validate_outbound_url

SEVERITY_ORDER = ["info", "low", "medium", "high", "critical"]
FORMATS = ("slack", "teams", "generic")
_COLORS = {"critical": "#dc2626", "high": "#ea580c", "medium": "#ca8a04", "low": "#2563eb", "info": "#64748b"}


def _rank(severity: str) -> int:
    try:
        return SEVERITY_ORDER.index(str(severity).lower())
    except ValueError:
        return 0


def build_payload(fmt: str, title: str, message: str, severity: str, extra: Optional[dict] = None) -> dict:
    severity = str(severity).lower()
    if fmt == "slack":
        return {
            "text": f"[{severity.upper()}] {title}",
            "attachments": [{"color": _COLORS.get(severity, "#64748b"), "text": message}],
        }
    if fmt == "teams":
        # Adaptive Card, accepted by Teams "Workflows" incoming webhooks
        return {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.4",
                        "body": [
                            {"type": "TextBlock", "weight": "Bolder", "size": "Medium", "text": f"[{severity.upper()}] {title}"},
                            {"type": "TextBlock", "wrap": True, "text": message},
                        ],
                    },
                }
            ],
        }
    return {"title": title, "message": message, "severity": severity, **(extra or {})}


def send_webhook(url: str, payload: dict, timeout: int = 10) -> tuple[bool, str]:
    """Synchronous delivery (used for the "send test" button). Returns (ok, detail)."""
    try:
        validate_outbound_url(url)
        response = requests.post(url, json=payload, timeout=timeout, allow_redirects=False)
        if 200 <= response.status_code < 300:
            return True, f"HTTP {response.status_code}"
        return False, f"HTTP {response.status_code}"
    except UnsafeURLError as exc:
        return False, f"Blocked destination: {exc}"
    except requests.RequestException as exc:
        return False, type(exc).__name__


def notify_user_async(settings: Optional[dict], title: str, message: str, severity: str, extra: Optional[dict] = None) -> None:
    """Fire-and-forget delivery if the user's settings ask for this severity."""
    if not settings or not settings.get("enabled") or not settings.get("webhook_url"):
        return
    if _rank(severity) < _rank(settings.get("min_severity", "high")):
        return
    fmt = settings.get("format", "generic")
    payload = build_payload(fmt if fmt in FORMATS else "generic", title, message, severity, extra)

    def _run() -> None:
        ok, detail = send_webhook(settings["webhook_url"], payload)
        if not ok:
            logger.warning("Alert webhook delivery failed: {}", detail)

    threading.Thread(target=_run, name="alert-webhook", daemon=True).start()


def get_settings_for(profile_json: Optional[dict]) -> dict[str, Any]:
    """Decrypted settings (server side only - never return webhook_url to clients)."""
    from app.core.encryption import decrypt_value

    stored = (profile_json or {}).get("notifications") or {}
    return {
        "enabled": bool(stored.get("enabled", False)),
        "webhook_url": decrypt_value(stored.get("webhook_url_enc", "")) if stored.get("webhook_url_enc") else "",
        "format": stored.get("format", "slack"),
        "min_severity": stored.get("min_severity", "high"),
    }


def mask_url(url: str) -> str:
    """https://hooks.slack.com/services/T000/B000/XXXX -> https://hooks.slack.com/…XXXX"""
    if not url:
        return ""
    from urllib.parse import urlsplit

    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.hostname}/…{url[-4:]}"
