"""Authentication endpoints."""

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import get_user_id_from_token
from app.services import token_service
from app.db.base import get_db
from app.schemas.auth import (
    ChangePasswordRequest,
    RefreshTokenRequest,
    Token,
    UserLogin,
    UserProfileUpdate,
    UserResponse,
)
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

ACCESS_COOKIE = "tip_access"
REFRESH_COOKIE = "tip_refresh"
_REFRESH_COOKIE_PATH = "/api/v1/auth"
_UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _cookie_secure() -> bool:
    settings = get_settings()
    return settings.is_production if settings.cookie_secure is None else settings.cookie_secure


def set_auth_cookies(response: Response, access: str, refresh: str) -> None:
    settings = get_settings()
    common = {"httponly": True, "secure": _cookie_secure(), "samesite": "strict"}
    response.set_cookie(ACCESS_COOKIE, access, max_age=settings.access_token_expire_minutes * 60, path="/api", **common)
    response.set_cookie(
        REFRESH_COOKIE, refresh, max_age=settings.refresh_token_expire_days * 86400, path=_REFRESH_COOKIE_PATH, **common
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE, path="/api")
    response.delete_cookie(REFRESH_COOKIE, path=_REFRESH_COOKIE_PATH)


def get_current_user(
    request: Request,
    bearer: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> UserResponse:
    """Authenticate via ``Authorization: Bearer`` (API clients) or the httpOnly cookie (browser).

    Cookie-authenticated state-changing requests must carry ``X-Requested-With``: a
    cross-site page cannot add that header without a CORS preflight we would reject (CSRF).
    """
    token = bearer
    if not token:
        token = request.cookies.get(ACCESS_COOKIE)
        if token and request.method in _UNSAFE_METHODS and request.headers.get("X-Requested-With") != "XMLHttpRequest":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing CSRF header")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = get_user_id_from_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_service = UserService(db)
    user = user_service.get_user_by_id(user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_service.to_response(user)


@router.post("/login", response_model=Token)
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    """Login and get access token."""
    user_service = UserService(db)
    user = user_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update last login
    user_service.update_user_last_login(user.id)

    access_token, refresh_token = token_service.issue_tokens(db, user)
    set_auth_cookies(response, access_token, refresh_token)
    # Tokens are also returned for API clients / Swagger "Authorize"; the web UI ignores them.
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: Request,
    response: Response,
    refresh_request: Optional[RefreshTokenRequest] = None,
    db: Session = Depends(get_db),
) -> Token:
    """Rotate the refresh token (single use) and issue a new access token.

    Browser: uses the httpOnly refresh cookie; new tokens are set as cookies only.
    API client: send ``{"refresh_token": "..."}``; new tokens are returned in the body.
    """
    from_body = bool(refresh_request and refresh_request.refresh_token)
    presented = refresh_request.refresh_token if from_body else request.cookies.get(REFRESH_COOKIE)
    if not presented:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token")
    if not from_body and request.headers.get("X-Requested-With") != "XMLHttpRequest":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing CSRF header")
    try:
        _, access_token, new_refresh = token_service.rotate(db, presented)
    except token_service.TokenError as exc:
        clear_auth_cookies(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))

    set_auth_cookies(response, access_token, new_refresh)
    if from_body:
        return Token(access_token=access_token, refresh_token=new_refresh)
    return Token(token_type="cookie")


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    refresh_request: Optional[RefreshTokenRequest] = None,
    db: Session = Depends(get_db),
) -> Response:
    """Revoke the refresh token and clear session cookies."""
    presented = (refresh_request.refresh_token if refresh_request else None) or request.cookies.get(REFRESH_COOKIE)
    token_service.revoke(db, presented)
    response.status_code = status.HTTP_204_NO_CONTENT
    clear_auth_cookies(response)
    return response


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
    """Get current user information."""
    return current_user


@router.put("/profile", response_model=UserResponse)
async def update_profile(
    profile_data: UserProfileUpdate,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    """Update current user's profile."""
    from loguru import logger
    from sqlalchemy.orm.attributes import flag_modified
    
    user_service = UserService(db)
    user = user_service.get_user_by_id(current_user.id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    logger.info(f"Updating profile for user {user.id}: full_name={profile_data.full_name}, email={profile_data.email}")

    # Check if email is being changed and if it's already taken
    if profile_data.email and profile_data.email != user.email:
        existing_user = user_service.get_user_by_email(profile_data.email)
        if existing_user and existing_user.id != user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists",
            )

    # Update user
    if profile_data.email:
        user.email = profile_data.email
    
    if profile_data.full_name is not None:
        # Store full_name in profile_json
        if user.profile_json is None:
            user.profile_json = {}
        else:
            # Create a new dict to ensure SQLAlchemy detects the change
            user.profile_json = dict(user.profile_json)
        
        # Trim whitespace and store, or remove if empty
        full_name_trimmed = profile_data.full_name.strip() if profile_data.full_name else ""
        logger.info(f"Full name trimmed: '{full_name_trimmed}'")
        
        if full_name_trimmed:
            user.profile_json["full_name"] = full_name_trimmed
            logger.info(f"Setting full_name in profile_json: {user.profile_json}")
        else:
            # Remove full_name if empty string
            if "full_name" in user.profile_json:
                del user.profile_json["full_name"]
                logger.info("Removed full_name from profile_json")
        
        # Mark profile_json as modified for SQLAlchemy
        flag_modified(user, "profile_json")

    db.commit()
    db.refresh(user)
    
    logger.info(f"Profile updated. profile_json after commit: {user.profile_json}")
    response = user_service.to_response(user)
    logger.info(f"Response full_name: {response.full_name}")
    
    return response


@router.put("/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Change user's password."""
    user_service = UserService(db)
    user = user_service.get_user_by_id(current_user.id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Verify current password
    from app.core.security import verify_password, get_password_hash

    if not verify_password(password_data.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Update password and end every other session
    user.password_hash = get_password_hash(password_data.new_password)
    db.commit()
    revoked = token_service.revoke_all(db, user.id)

    return {"message": "Password changed successfully", "revoked_sessions": revoked}



class NotificationSettingsUpdate(BaseModel):
    enabled: bool = False
    webhook_url: Optional[str] = Field(None, max_length=1000, description="Leave empty to keep the stored URL")
    format: str = Field("slack", pattern="^(slack|teams|generic)$")
    min_severity: str = Field("high", pattern="^(info|low|medium|high|critical)$")


def _public_settings(settings: dict) -> dict:
    from app.services.notifier import mask_url

    return {
        "enabled": settings["enabled"],
        "format": settings["format"],
        "min_severity": settings["min_severity"],
        "webhook_configured": bool(settings["webhook_url"]),
        "webhook_url_masked": mask_url(settings["webhook_url"]),
    }


@router.get("/notifications", summary="Get my alert notification settings")
def get_notification_settings(
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    from app.services.notifier import get_settings_for

    user = UserService(db).get_user_by_id(current_user.id)
    return _public_settings(get_settings_for(user.profile_json if user else None))


@router.put("/notifications", summary="Update my alert notification settings")
def update_notification_settings(
    payload: NotificationSettingsUpdate,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    from sqlalchemy.orm.attributes import flag_modified

    from app.core.encryption import encrypt_value
    from app.core.url_guard import UnsafeURLError, validate_outbound_url
    from app.services.notifier import get_settings_for

    user = UserService(db).get_user_by_id(current_user.id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    profile = dict(user.profile_json or {})
    stored = dict(profile.get("notifications") or {})
    if payload.webhook_url:
        url = payload.webhook_url.strip()
        if not url.lower().startswith("https://"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Webhook URL must use https")
        try:
            validate_outbound_url(url)
        except UnsafeURLError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid webhook URL: {exc}")
        stored["webhook_url_enc"] = encrypt_value(url)
    elif payload.webhook_url == "":
        stored.pop("webhook_url_enc", None)
    stored.update(enabled=payload.enabled, format=payload.format, min_severity=payload.min_severity)
    profile["notifications"] = stored
    user.profile_json = profile
    flag_modified(user, "profile_json")
    db.commit()
    return _public_settings(get_settings_for(user.profile_json))


@router.post("/notifications/test", summary="Send a test notification to my webhook")
def test_notification(
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    from app.services.notifier import build_payload, get_settings_for, send_webhook

    user = UserService(db).get_user_by_id(current_user.id)
    settings = get_settings_for(user.profile_json if user else None)
    if not settings["webhook_url"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No webhook URL configured")
    ok, detail = send_webhook(
        settings["webhook_url"],
        build_payload(settings["format"], "Test notification", "Threat Intelligence Platform webhook works.", "info"),
    )
    return {"success": ok, "detail": detail}
