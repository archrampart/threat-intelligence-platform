"""Dark web / Telegram monitoring models.

Everything is per user: monitored assets, Telegram channels and the optional Telegram
account are personal, like API keys.
"""

from enum import Enum as PyEnum
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.sql import func

from app.db.base import Base, JSONType


class AssetKind(str, PyEnum):
    DOMAIN = "domain"  # company domain: matched as host / domain in leak posts and messages
    KEYWORD = "keyword"  # brand / product / executive name: whole-word, case-insensitive
    EMAIL_DOMAIN = "email_domain"  # matched as "@domain" in messages


class MentionSource(str, PyEnum):
    RANSOMWARE = "ransomware"  # leak site victim post (ransomware.live, RansomLook)
    INFOSTEALER = "infostealer"  # Hudson Rock infostealer exposure
    BREACH = "breach"  # HIBP public breach catalog
    TELEGRAM = "telegram"
    FORUM = "forum"  # dark web forum / market / Telegram sale posts reported by monitoring sites
    FEED = "feed"  # news feeds and custom JSON / RSS feeds added by an admin


class MonitoredAsset(Base):
    __tablename__ = "darkweb_assets"
    __table_args__ = (UniqueConstraint("user_id", "kind", "value", name="uq_darkweb_asset"),)

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    kind = Column(String(20), nullable=False)
    value = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class TelegramChannel(Base):
    __tablename__ = "darkweb_telegram_channels"
    __table_args__ = (UniqueConstraint("user_id", "username", name="uq_darkweb_channel"),)

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    username = Column(String(64), nullable=False)  # public @username or numeric id (account mode)
    title = Column(String(255), nullable=True)
    # "public": t.me/s web preview, "account": read through the user's own Telegram account
    mode = Column(String(10), default="public", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_message_id = Column(Integer, default=0, nullable=False)
    last_checked_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class TelegramAccount(Base):
    """Optional MTProto login (Telethon StringSession), encrypted at rest."""

    __tablename__ = "darkweb_telegram_accounts"

    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    api_id = Column(Integer, nullable=False)
    api_hash_enc = Column(Text, nullable=False)
    phone_masked = Column(String(32), nullable=True)
    session_enc = Column(Text, nullable=True)  # set once the login is complete
    pending_code_hash = Column(String(255), nullable=True)
    pending_phone_enc = Column(Text, nullable=True)
    status = Column(String(20), default="pending", nullable=False)  # pending | connected
    display_name = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DarkWebMention(Base):
    __tablename__ = "darkweb_mentions"
    __table_args__ = (UniqueConstraint("user_id", "fingerprint", name="uq_darkweb_mention"),)

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_id = Column(String, ForeignKey("darkweb_assets.id", ondelete="SET NULL"), nullable=True)
    source = Column(String(20), nullable=False, index=True)
    severity = Column(String(10), nullable=False, default="medium")
    matched_term = Column(String(255), nullable=False)
    title = Column(String(500), nullable=False)
    snippet = Column(Text, nullable=True)
    url = Column(String(1000), nullable=True)
    actor = Column(String(255), nullable=True)  # ransomware group / Telegram channel
    published_at = Column(DateTime(timezone=True), nullable=True)
    details = Column(JSONType, nullable=True)
    fingerprint = Column(String(128), nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class DarkWebSource(Base):
    """A feed the dark web monitor reads. Built-in sources are seeded; admins can add custom feeds.

    Users can switch any source off for their own scans (User.profile_json["darkweb_disabled_sources"]).
    """

    __tablename__ = "darkweb_sources"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    key = Column(String(64), unique=True, nullable=False)  # stable identifier, e.g. "ransomware_live"
    name = Column(String(120), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(20), nullable=False)  # ransomware | infostealer | breach | telegram | forum | news | feed
    builtin = Column(Boolean, default=True, nullable=False)
    is_enabled = Column(Boolean, default=True, nullable=False)  # global switch (admin)
    homepage = Column(String(500), nullable=True)
    # custom feeds: {"url", "format": "json"|"rss", "items_path", "title_path", "text_path", "url_path",
    #                "date_path", "severity"}
    config = Column(JSONType, nullable=True)
    created_by = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    last_fetch_at = Column(DateTime(timezone=True), nullable=True)
    last_success_at = Column(DateTime(timezone=True), nullable=True)
    last_item_count = Column(Integer, nullable=True)
    last_duration_ms = Column(Integer, nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
