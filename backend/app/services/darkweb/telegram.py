"""Telegram collection.

Two modes per channel:

* ``public``  - the public web preview https://t.me/s/<username>. No account, no login,
  read only; works for public channels that have the preview enabled.
* ``account`` - the user's own Telegram account through MTProto (Telethon), for private
  channels / groups the user has joined. The session is stored encrypted and only used
  to read messages; it is never shared between users.

Only message text and metadata are stored. Attachments (often stolen data) are never
downloaded.
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from datetime import datetime
from html import unescape
from html.parser import HTMLParser
from typing import Optional

import requests

USERNAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{3,31}$")
_PREVIEW_URL = "https://t.me/s/{username}"
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ThreatIntelPlatform/2.1)", "Accept-Language": "en"}


@dataclass
class TelegramMessage:
    channel: str
    message_id: int
    text: str
    url: str
    published_at: Optional[datetime]


def normalise_username(value: str) -> str:
    value = value.strip()
    for prefix in ("https://t.me/s/", "https://t.me/", "http://t.me/", "t.me/", "@"):
        if value.lower().startswith(prefix):
            value = value[len(prefix):]
    return value.split("/", 1)[0].split("?", 1)[0]


class _PreviewParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title: Optional[str] = None
        self.messages: list[dict] = []
        self._current: Optional[dict] = None
        self._text_depth = 0
        self._title_depth = 0
        self._title_parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        classes = (a.get("class") or "").split()
        if tag == "div" and "tgme_widget_message" in classes and a.get("data-post"):
            self._current = {"post": a["data-post"], "text": [], "datetime": None}
            self.messages.append(self._current)
        if self._text_depth:
            if tag == "div":
                self._text_depth += 1
            elif tag == "br":
                self._current["text"].append("\n")
            return
        if tag == "div" and "tgme_widget_message_text" in classes and self._current is not None:
            self._text_depth = 1
        elif tag == "time" and self._current is not None and a.get("datetime"):
            self._current["datetime"] = a["datetime"]
        elif tag == "div" and "tgme_channel_info_header_title" in classes:
            self._title_depth = 1

    def handle_endtag(self, tag):
        if self._text_depth and tag == "div":
            self._text_depth -= 1
        if self._title_depth and tag == "div":
            self._title_depth = 0
            self.title = "".join(self._title_parts).strip() or None

    def handle_data(self, data):
        if self._text_depth and self._current is not None:
            self._current["text"].append(data)
        elif self._title_depth:
            self._title_parts.append(data)


def parse_preview(html: str, username: str) -> tuple[Optional[str], list[TelegramMessage]]:
    parser = _PreviewParser()
    parser.feed(html)
    messages = []
    for item in parser.messages:
        try:
            message_id = int(item["post"].rsplit("/", 1)[1])
        except (IndexError, ValueError):
            continue
        published = None
        if item["datetime"]:
            try:
                published = datetime.fromisoformat(item["datetime"])
            except ValueError:
                pass
        text = unescape("".join(item["text"])).strip()
        messages.append(
            TelegramMessage(
                channel=username,
                message_id=message_id,
                text=text,
                url=f"https://t.me/{item['post']}",
                published_at=published,
            )
        )
    return parser.title, messages


def fetch_public(username: str, timeout: int = 20) -> tuple[Optional[str], list[TelegramMessage]]:
    """Latest ~20 messages of a public channel. Raises ValueError if the preview is unavailable."""
    if not USERNAME_RE.match(username):
        raise ValueError("Invalid channel username")
    response = requests.get(_PREVIEW_URL.format(username=username), headers=_HEADERS, timeout=timeout, allow_redirects=False)
    if response.status_code in (301, 302):
        raise ValueError("Channel has no public preview (private, a user/bot, or does not exist)")
    response.raise_for_status()
    title, messages = parse_preview(response.text, username)
    if not messages and "tgme_channel_info" not in response.text:
        raise ValueError("Channel has no public preview (private, a user/bot, or does not exist)")
    return title, messages


# --------------------------------------------------------------------------- MTProto (Telethon)


def _run(coro):
    """Run a coroutine from sync code (FastAPI sync endpoints / scheduler threads)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _client(api_id: int, api_hash: str, session: str = ""):
    from telethon import TelegramClient
    from telethon.sessions import StringSession

    return TelegramClient(StringSession(session), api_id, api_hash, device_model="ThreatIntelPlatform",
                          app_version="2.1", receive_updates=False)


def account_send_code(api_id: int, api_hash: str, phone: str) -> tuple[str, str]:
    """Start login. Returns (partial session, phone_code_hash)."""

    async def go():
        client = _client(api_id, api_hash)
        await client.connect()
        try:
            sent = await client.send_code_request(phone)
            return client.session.save(), sent.phone_code_hash
        finally:
            await client.disconnect()

    return _run(go())


def account_sign_in(
    api_id: int, api_hash: str, session: str, phone: str, code: str, code_hash: str, password: Optional[str] = None
) -> tuple[str, str]:
    """Finish login (code, plus 2FA password if enabled). Returns (session, display name)."""

    async def go():
        from telethon.errors import SessionPasswordNeededError

        client = _client(api_id, api_hash, session)
        await client.connect()
        try:
            try:
                await client.sign_in(phone=phone, code=code, phone_code_hash=code_hash)
            except SessionPasswordNeededError:
                if not password:
                    raise ValueError("This account has two-step verification: enter the password")
                await client.sign_in(password=password)
            me = await client.get_me()
            name = " ".join(filter(None, [getattr(me, "first_name", None), getattr(me, "last_name", None)]))
            return client.session.save(), name or (getattr(me, "username", None) or "Telegram user")
        finally:
            await client.disconnect()

    return _run(go())


def account_fetch(
    api_id: int, api_hash: str, session: str, channel: str, min_id: int, limit: int = 100
) -> tuple[Optional[str], list[TelegramMessage]]:
    """New messages (id > min_id) from a channel/group the account can read."""

    async def go():
        client = _client(api_id, api_hash, session)
        await client.connect()
        try:
            if not await client.is_user_authorized():
                raise ValueError("Telegram session expired - reconnect the account")
            entity = await client.get_entity(int(channel) if channel.lstrip("-").isdigit() else channel)
            title = getattr(entity, "title", None) or getattr(entity, "username", None)
            handle = getattr(entity, "username", None)
            out = []
            async for msg in client.iter_messages(entity, min_id=min_id, limit=limit):
                text = msg.message or ""
                if not text:
                    continue
                url = f"https://t.me/{handle}/{msg.id}" if handle else f"https://t.me/c/{str(entity.id)}/{msg.id}"
                out.append(TelegramMessage(channel=channel, message_id=msg.id, text=text, url=url, published_at=msg.date))
            return title, out
        finally:
            await client.disconnect()

    return _run(go())


def mask_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone)
    return f"+{digits[:2]}•••••{digits[-2:]}" if len(digits) > 4 else "•••"
