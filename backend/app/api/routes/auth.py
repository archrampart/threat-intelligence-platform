"""Authentication endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_user_id_from_token,
)
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

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> UserResponse:
    """Get current authenticated user from JWT token."""
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

    # Create tokens
    access_token = create_access_token(data={"sub": user.id, "username": user.username})
    refresh_token = create_refresh_token(data={"sub": user.id, "username": user.username})

    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_request: RefreshTokenRequest,
    db: Session = Depends(get_db),
) -> Token:
    """Refresh access token using refresh token."""
    payload = decode_token(refresh_request.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user_id = payload.get("sub")
    username = payload.get("username")

    # Verify user exists and is active
    user_service = UserService(db)
    user = user_service.get_user_by_id(user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Create new tokens
    access_token = create_access_token(data={"sub": user.id, "username": user.username})
    refresh_token = create_refresh_token(data={"sub": user.id, "username": user.username})

    return Token(access_token=access_token, refresh_token=refresh_token)


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

    # Update password
    user.password_hash = get_password_hash(password_data.new_password)
    db.commit()

    return {"message": "Password changed successfully"}

