"""Refresh-token lifecycle: issue, rotate, revoke.

Every refresh token is single-use. Refreshing revokes the presented token and issues a
new pair. Presenting an already revoked token means it was stolen or replayed, so all
of that user's sessions are revoked (OAuth 2.0 Security BCP, refresh token rotation).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from loguru import logger
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.models.refresh_token import RefreshToken
from app.models.user import User


class TokenError(Exception):
    """Invalid, expired, revoked or reused refresh token."""


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def issue_tokens(db: Session, user: User) -> tuple[str, str]:
    claims = {"sub": user.id, "username": user.username}
    access = create_access_token(claims)
    refresh = create_refresh_token(claims)
    payload = decode_token(refresh) or {}
    db.add(
        RefreshToken(
            jti=payload["jti"],
            user_id=user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=get_settings().refresh_token_expire_days),
        )
    )
    db.commit()
    return access, refresh


def rotate(db: Session, refresh_token: str) -> tuple[User, str, str]:
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh" or not payload.get("jti"):
        raise TokenError("Invalid refresh token")
    record = db.query(RefreshToken).filter(RefreshToken.jti == payload["jti"]).first()
    if record is None:
        raise TokenError("Unknown refresh token")
    if record.revoked_at is not None:
        revoke_all(db, record.user_id)
        logger.warning("Refresh token reuse detected for user {} - all sessions revoked", record.user_id)
        raise TokenError("Refresh token reuse detected")
    if _aware(record.expires_at) < datetime.now(timezone.utc):
        raise TokenError("Refresh token expired")
    user = db.query(User).filter(User.id == record.user_id).first()
    if not user or not user.is_active:
        raise TokenError("User not found or inactive")

    access, refresh = issue_tokens(db, user)
    record.revoked_at = datetime.now(timezone.utc)
    record.replaced_by = (decode_token(refresh) or {}).get("jti")
    db.commit()
    return user, access, refresh


def revoke(db: Session, refresh_token: Optional[str]) -> None:
    payload = decode_token(refresh_token) if refresh_token else None
    if not payload or not payload.get("jti"):
        return
    record = db.query(RefreshToken).filter(RefreshToken.jti == payload["jti"]).first()
    if record and record.revoked_at is None:
        record.revoked_at = datetime.now(timezone.utc)
        db.commit()


def revoke_all(db: Session, user_id: str) -> int:
    now = datetime.now(timezone.utc)
    count = (
        db.query(RefreshToken)
        .filter(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .update({RefreshToken.revoked_at: now}, synchronize_session=False)
    )
    # Housekeeping: drop tokens that expired more than a day ago
    db.query(RefreshToken).filter(RefreshToken.expires_at < now - timedelta(days=1)).delete(synchronize_session=False)
    db.commit()
    return count
