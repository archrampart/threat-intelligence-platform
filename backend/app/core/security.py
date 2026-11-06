"""Security utilities - JWT and password hashing."""

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

import bcrypt
import jwt

from app.core.config import get_settings

settings = get_settings()

# bcrypt only uses the first 72 bytes of a password; bcrypt>=5 raises instead of
# silently truncating. Longer passwords are pre-truncated explicitly so behaviour
# stays identical to the hashes created by the previous passlib-based code.
_BCRYPT_MAX_BYTES = 72


def _encode_password(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a bcrypt hash (constant time)."""
    if not plain_password or not hashed_password:
        return False
    try:
        return bcrypt.checkpw(_encode_password(plain_password), hashed_password.encode("utf-8"))
    except ValueError:
        # Malformed hash in DB
        return False


def get_password_hash(password: str) -> str:
    """Hash a password with bcrypt."""
    return bcrypt.hashpw(_encode_password(password), bcrypt.gensalt(rounds=12)).decode("utf-8")


# Pre-computed hash used to equalise timing when a username does not exist.
DUMMY_PASSWORD_HASH = get_password_hash(uuid4().hex)


def _create_token(data: dict, token_type: str, expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    to_encode = data.copy()
    to_encode.update(
        {
            "exp": now + expires_delta,
            "iat": now,
            "nbf": now,
            "jti": uuid4().hex,
            "type": token_type,
            "iss": settings.jwt_issuer,
        }
    )
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    return _create_token(
        data,
        "access",
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token."""
    return _create_token(data, "refresh", timedelta(days=settings.refresh_token_expire_days))


def decode_token(token: str) -> Optional[dict]:
    """Decode and verify a JWT token. Only the configured algorithm is accepted."""
    try:
        return jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "iat", "sub", "type"]},
        )
    except jwt.PyJWTError:
        return None


def get_user_id_from_token(token: str) -> Optional[str]:
    """Extract user ID from a JWT access token."""
    payload = decode_token(token)
    if payload and payload.get("type") == "access":
        return payload.get("sub")
    return None
