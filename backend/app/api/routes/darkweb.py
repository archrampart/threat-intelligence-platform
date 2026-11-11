"""Dark web / Telegram monitoring endpoints (all data is per user)."""

from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.api.routes.auth import get_current_user
from app.core.encryption import decrypt_value, encrypt_value
from app.db.base import get_db
from app.core.dependencies import require_role
from app.models.darkweb import DarkWebMention, DarkWebSource, MonitoredAsset, TelegramAccount, TelegramChannel
from app.models.user import UserRole
from app.services.darkweb import sources as source_registry
from app.schemas.auth import UserResponse
from app.services.darkweb import telegram
from app.services.darkweb.matcher import normalise, validate
from app.services.darkweb.service import DarkWebMonitor

router = APIRouter(prefix="/darkweb", tags=["darkweb"])

MAX_ASSETS = 50
MAX_CHANNELS = 50


# --------------------------------------------------------------------------- schemas


class AssetIn(BaseModel):
    kind: Literal["domain", "keyword", "email_domain", "email"]
    value: str = Field(..., min_length=1, max_length=255)


class ChannelIn(BaseModel):
    username: str = Field(..., min_length=1, max_length=128, description="@name, t.me link, or numeric id (account mode)")
    mode: Literal["public", "account"] = "public"


class TelegramStart(BaseModel):
    api_id: int = Field(..., gt=0)
    api_hash: str = Field(..., min_length=16, max_length=64)
    phone: str = Field(..., min_length=6, max_length=20, pattern=r"^\+?[0-9 ]+$")


class TelegramVerify(BaseModel):
    code: str = Field(..., min_length=3, max_length=10)
    password: Optional[str] = Field(None, max_length=256)


class MentionUpdate(BaseModel):
    is_read: bool


class FeedConfig(BaseModel):
    url: str = Field(..., max_length=1000)
    format: Literal["json", "rss"]
    items_path: Optional[str] = Field(None, max_length=200, description="JSONPath to the item list, e.g. $.data[*]")
    title_path: Optional[str] = Field(None, max_length=200)
    text_path: Optional[str] = Field(None, max_length=200)
    url_path: Optional[str] = Field(None, max_length=200)
    date_path: Optional[str] = Field(None, max_length=200)
    severity: Literal["critical", "high", "medium", "low"] = "high"


class CustomSourceIn(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    description: Optional[str] = Field(None, max_length=500)
    homepage: Optional[str] = Field(None, max_length=500)
    config: FeedConfig


class SourceUpdate(BaseModel):
    is_enabled: Optional[bool] = None
    name: Optional[str] = Field(None, min_length=2, max_length=120)
    description: Optional[str] = Field(None, max_length=500)
    config: Optional[FeedConfig] = None


class SourcePreference(BaseModel):
    enabled: bool


def _asset(a: MonitoredAsset) -> dict:
    return {"id": a.id, "kind": a.kind, "value": a.value, "is_active": a.is_active, "created_at": a.created_at}


def _channel(c: TelegramChannel) -> dict:
    return {
        "id": c.id, "username": c.username, "title": c.title, "mode": c.mode, "is_active": c.is_active,
        "last_checked_at": c.last_checked_at, "last_error": c.last_error, "last_message_id": c.last_message_id,
    }


def _mention(m: DarkWebMention) -> dict:
    return {
        "id": m.id, "source": m.source, "severity": m.severity, "matched_term": m.matched_term, "title": m.title,
        "snippet": m.snippet, "url": m.url, "actor": m.actor, "published_at": m.published_at,
        "details": m.details, "is_read": m.is_read, "created_at": m.created_at,
    }


# --------------------------------------------------------------------------- assets


@router.get("/assets")
def list_assets(user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.query(MonitoredAsset).filter_by(user_id=user.id).order_by(MonitoredAsset.created_at).all()
    return [_asset(a) for a in rows]


@router.post("/assets", status_code=status.HTTP_201_CREATED)
def add_asset(payload: AssetIn, user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    value = normalise(payload.kind, payload.value)
    error = validate(payload.kind, value)
    if error:
        raise HTTPException(status_code=400, detail=error)
    if db.query(MonitoredAsset).filter_by(user_id=user.id).count() >= MAX_ASSETS:
        raise HTTPException(status_code=400, detail=f"At most {MAX_ASSETS} monitored assets")
    if db.query(MonitoredAsset).filter_by(user_id=user.id, kind=payload.kind, value=value).first():
        raise HTTPException(status_code=409, detail="Already monitored")
    asset = MonitoredAsset(user_id=user.id, kind=payload.kind, value=value)
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return _asset(asset)


@router.delete("/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset(asset_id: str, user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)) -> None:
    asset = db.query(MonitoredAsset).filter_by(id=asset_id, user_id=user.id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    db.delete(asset)
    db.commit()


# --------------------------------------------------------------------------- telegram channels


@router.get("/channels")
def list_channels(user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.query(TelegramChannel).filter_by(user_id=user.id).order_by(TelegramChannel.created_at).all()
    return [_channel(c) for c in rows]


@router.post("/channels", status_code=status.HTTP_201_CREATED)
def add_channel(payload: ChannelIn, user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    username = telegram.normalise_username(payload.username)
    if payload.mode == "public" and not telegram.USERNAME_RE.match(username):
        raise HTTPException(status_code=400, detail="Use the channel's public @username or t.me link")
    if payload.mode == "account":
        if not db.query(TelegramAccount).filter_by(user_id=user.id, status="connected").first():
            raise HTTPException(status_code=400, detail="Connect your Telegram account first")
        if not (telegram.USERNAME_RE.match(username) or username.lstrip("-").isdigit()):
            raise HTTPException(status_code=400, detail="Use an @username or numeric chat id")
    if db.query(TelegramChannel).filter_by(user_id=user.id).count() >= MAX_CHANNELS:
        raise HTTPException(status_code=400, detail=f"At most {MAX_CHANNELS} channels")
    if db.query(TelegramChannel).filter_by(user_id=user.id, username=username).first():
        raise HTTPException(status_code=409, detail="Channel already added")

    title = None
    if payload.mode == "public":
        try:  # validate now so the user gets immediate feedback
            title, _ = telegram.fetch_public(username)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except Exception:
            raise HTTPException(status_code=502, detail="Telegram did not respond, try again")
    channel = TelegramChannel(user_id=user.id, username=username, title=title, mode=payload.mode)
    db.add(channel)
    db.commit()
    db.refresh(channel)
    return _channel(channel)


@router.get("/channels/suggested")
def suggested_channels(user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    """Curated public Telegram channels that repost leak / ransomware alerts."""
    added = {u for (u,) in db.query(TelegramChannel.username).filter_by(user_id=user.id).all()}
    return [dict(c, added=c["username"] in added) for c in source_registry.SUGGESTED_CHANNELS]


@router.delete("/channels/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_channel(channel_id: str, user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)) -> None:
    channel = db.query(TelegramChannel).filter_by(id=channel_id, user_id=user.id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    db.delete(channel)
    db.commit()


# --------------------------------------------------------------------------- telegram account (MTProto)


@router.get("/telegram-account")
def telegram_account_status(user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    account = db.get(TelegramAccount, user.id)
    if not account:
        return {"status": "not_connected"}
    return {"status": account.status, "phone": account.phone_masked, "display_name": account.display_name}


@router.post("/telegram-account/start")
def telegram_account_start(
    payload: TelegramStart, user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    """Step 1: Telegram sends a login code to the user's Telegram app."""
    phone = "+" + payload.phone.replace(" ", "").lstrip("+")
    try:
        session, code_hash = telegram.account_send_code(payload.api_id, payload.api_hash, phone)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Telegram rejected the request: {type(exc).__name__}")
    account = db.get(TelegramAccount, user.id) or TelegramAccount(user_id=user.id, api_id=payload.api_id, api_hash_enc="")
    account.api_id = payload.api_id
    account.api_hash_enc = encrypt_value(payload.api_hash)
    account.session_enc = encrypt_value(session)
    account.pending_code_hash = code_hash
    account.pending_phone_enc = encrypt_value(phone)
    account.phone_masked = telegram.mask_phone(phone)
    account.status = "pending"
    db.merge(account)
    db.commit()
    return {"status": "code_sent", "phone": account.phone_masked}


@router.post("/telegram-account/verify")
def telegram_account_verify(
    payload: TelegramVerify, user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    """Step 2: enter the code (and the 2FA password if the account has one)."""
    account = db.get(TelegramAccount, user.id)
    if not account or account.status != "pending" or not account.pending_code_hash:
        raise HTTPException(status_code=400, detail="Start the login first")
    try:
        session, name = telegram.account_sign_in(
            account.api_id, decrypt_value(account.api_hash_enc), decrypt_value(account.session_enc),
            decrypt_value(account.pending_phone_enc), payload.code.strip(), account.pending_code_hash, payload.password,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Login failed: {type(exc).__name__}")
    account.session_enc = encrypt_value(session)
    account.pending_code_hash = None
    account.pending_phone_enc = None
    account.status = "connected"
    account.display_name = name
    db.commit()
    return {"status": "connected", "display_name": name, "phone": account.phone_masked}


@router.delete("/telegram-account", status_code=status.HTTP_204_NO_CONTENT)
def telegram_account_disconnect(user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)) -> None:
    account = db.get(TelegramAccount, user.id)
    if account:
        db.delete(account)
    db.query(TelegramChannel).filter_by(user_id=user.id, mode="account").update({TelegramChannel.is_active: False})
    db.commit()


# --------------------------------------------------------------------------- mentions & scan


@router.get("/mentions")
def list_mentions(
    user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
    source: Optional[str] = Query(None, pattern="^(ransomware|infostealer|breach|telegram|forum|feed)$"),
    severity: Optional[str] = Query(None, pattern="^(critical|high|medium|low)$"),
    unread_only: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> dict:
    query = db.query(DarkWebMention).filter(DarkWebMention.user_id == user.id)
    if source:
        query = query.filter(DarkWebMention.source == source)
    if severity:
        query = query.filter(DarkWebMention.severity == severity)
    if unread_only:
        query = query.filter(DarkWebMention.is_read.is_(False))
    total = query.count()
    severity_rank = case(
        (DarkWebMention.severity == "critical", 0),
        (DarkWebMention.severity == "high", 1),
        (DarkWebMention.severity == "medium", 2),
        else_=3,
    )
    # unread first, then most severe, then newest
    items = query.order_by(
        DarkWebMention.is_read, severity_rank, DarkWebMention.created_at.desc(), DarkWebMention.published_at.desc()
    ).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    return {"items": [_mention(m) for m in items], "total": total, "page": page, "page_size": page_size}


@router.get("/summary")
def summary(user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    by_source = dict(
        db.query(DarkWebMention.source, func.count(DarkWebMention.id)).filter_by(user_id=user.id).group_by(DarkWebMention.source).all()
    )
    unread = db.query(DarkWebMention).filter_by(user_id=user.id, is_read=False).count()
    return {
        "by_source": by_source,
        "unread": unread,
        "assets": db.query(MonitoredAsset).filter_by(user_id=user.id).count(),
        "channels": db.query(TelegramChannel).filter_by(user_id=user.id).count(),
    }


@router.put("/mentions/{mention_id}")
def update_mention(
    mention_id: str, payload: MentionUpdate, user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    mention = db.query(DarkWebMention).filter_by(id=mention_id, user_id=user.id).first()
    if not mention:
        raise HTTPException(status_code=404, detail="Mention not found")
    mention.is_read = payload.is_read
    db.commit()
    return _mention(mention)


@router.post("/mentions/read-all")
def read_all(user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    count = db.query(DarkWebMention).filter_by(user_id=user.id, is_read=False).update({DarkWebMention.is_read: True})
    db.commit()
    return {"updated": count}


@router.post("/scan")
def scan_now(user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    """Run a scan for the current user now (also runs automatically every DARKWEB_SCAN_INTERVAL_MINUTES)."""
    result = DarkWebMonitor(db).scan_user(user.id)
    if result.get("status") == "busy":
        raise HTTPException(status_code=409, detail="A scan is already running")
    result["scanned_at"] = datetime.now(timezone.utc).isoformat()
    return result


# --------------------------------------------------------------------------- sources


def _source(row: DarkWebSource, disabled: set[str], is_admin: bool) -> dict:
    data = {
        "key": row.key, "name": row.name, "description": row.description, "category": row.category,
        "builtin": row.builtin, "homepage": row.homepage, "is_enabled": row.is_enabled,
        "user_enabled": row.key not in disabled, "last_fetch_at": row.last_fetch_at,
        "last_success_at": row.last_success_at, "last_item_count": row.last_item_count,
        "last_duration_ms": row.last_duration_ms, "last_error": row.last_error,
        "status": "disabled" if not row.is_enabled else "never" if not row.last_fetch_at
        else "error" if row.last_error and (not row.last_success_at or row.last_success_at < row.last_fetch_at)
        else "ok",
    }
    if is_admin and not row.builtin:
        data["config"] = row.config  # feed URLs are only shown to admins
    return data


def _profile(db: Session, user_id: str) -> dict:
    from app.models.user import User

    user = db.query(User).filter(User.id == user_id).first()
    return dict(user.profile_json or {}) if user else {}


@router.get("/sources")
def list_sources(user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    source_registry.ensure_seeded(db)
    disabled = source_registry.disabled_by_user(_profile(db, user.id))
    is_admin = str(getattr(user.role, "value", user.role)) == "admin"
    rows = db.query(DarkWebSource).order_by(DarkWebSource.builtin.desc(), DarkWebSource.category, DarkWebSource.name).all()
    return [_source(r, disabled, is_admin) for r in rows]


@router.put("/sources/{key}/preference")
def set_source_preference(
    key: str, payload: SourcePreference, user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    """Switch a source on/off for my own scans."""
    from sqlalchemy.orm.attributes import flag_modified

    from app.models.user import User

    source_registry.ensure_seeded(db)
    if not db.query(DarkWebSource).filter_by(key=key).first():
        raise HTTPException(status_code=404, detail="Source not found")
    row = db.query(User).filter(User.id == user.id).first()
    profile = dict(row.profile_json or {})
    disabled = set(profile.get("darkweb_disabled_sources") or [])
    disabled.discard(key) if payload.enabled else disabled.add(key)
    profile["darkweb_disabled_sources"] = sorted(disabled)
    row.profile_json = profile
    flag_modified(row, "profile_json")
    db.commit()
    return {"key": key, "user_enabled": payload.enabled}


def _check_config(config: FeedConfig) -> dict:
    data = config.model_dump()
    error = source_registry.validate_config(data)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return data


@router.post("/sources/preview")
def preview_source(
    payload: FeedConfig, user: UserResponse = Depends(require_role([UserRole.ADMIN])),
) -> dict:
    """Fetch a feed with the given mapping and return the first parsed items (nothing is saved)."""
    config = _check_config(payload)
    try:
        items = source_registry.fetch_custom(config)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not read the feed: {type(exc).__name__}: {str(exc)[:200]}")
    return {
        "count": len(items),
        "items": [
            {"title": i.title, "text": i.text[:300], "url": i.url, "published_at": i.published_at} for i in items[:5]
        ],
    }


@router.post("/sources", status_code=status.HTTP_201_CREATED)
def add_source(
    payload: CustomSourceIn, user: UserResponse = Depends(require_role([UserRole.ADMIN])), db: Session = Depends(get_db)
) -> dict:
    import re

    config = _check_config(payload.config)
    key = "custom_" + (re.sub(r"[^a-z0-9]+", "_", payload.name.lower()).strip("_") or "feed")[:40]
    if db.query(DarkWebSource).filter_by(key=key).first():
        raise HTTPException(status_code=409, detail="A source with this name already exists")
    row = DarkWebSource(
        key=key, name=payload.name, description=payload.description, homepage=payload.homepage,
        category="feed", builtin=False, is_enabled=True, config=config, created_by=user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _source(row, set(), True)


@router.put("/sources/{key}")
def update_source(
    key: str, payload: SourceUpdate, user: UserResponse = Depends(require_role([UserRole.ADMIN])),
    db: Session = Depends(get_db),
) -> dict:
    source_registry.ensure_seeded(db)
    row = db.query(DarkWebSource).filter_by(key=key).first()
    if not row:
        raise HTTPException(status_code=404, detail="Source not found")
    if payload.is_enabled is not None:
        row.is_enabled = payload.is_enabled
    if not row.builtin:
        if payload.name:
            row.name = payload.name
        if payload.description is not None:
            row.description = payload.description
        if payload.config is not None:
            row.config = _check_config(payload.config)
    elif payload.config is not None or payload.name:
        raise HTTPException(status_code=400, detail="Built-in sources can only be enabled or disabled")
    db.commit()
    return _source(row, set(), True)


@router.delete("/sources/{key}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source(
    key: str, user: UserResponse = Depends(require_role([UserRole.ADMIN])), db: Session = Depends(get_db)
) -> None:
    source_registry.ensure_seeded(db)
    row = db.query(DarkWebSource).filter_by(key=key).first()
    if not row:
        raise HTTPException(status_code=404, detail="Source not found")
    if row.builtin:
        raise HTTPException(status_code=400, detail="Built-in sources cannot be deleted (disable them instead)")
    db.delete(row)
    db.commit()
