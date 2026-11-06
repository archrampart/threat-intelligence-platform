"""Authentication schemas."""

from typing import Optional

from pydantic import ConfigDict, BaseModel, EmailStr, Field


class Token(BaseModel):
    """Token response schema.

    Browsers authenticate with httpOnly cookies; when a refresh happens via cookie the
    tokens are not echoed in the body (so injected scripts cannot read them).
    """

    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token data schema."""

    user_id: Optional[str] = None
    username: Optional[str] = None


class UserLogin(BaseModel):
    """User login request schema."""

    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema (omit when using the refresh cookie)."""

    refresh_token: Optional[str] = None


class UserResponse(BaseModel):
    """User response schema."""

    id: str
    username: str
    email: str
    full_name: Optional[str] = None
    role: str
    is_active: bool
    language_preference: str

    model_config = ConfigDict(from_attributes=True)


class UserProfileUpdate(BaseModel):
    """User profile update request schema."""

    full_name: Optional[str] = Field(None, max_length=200)
    email: Optional[EmailStr] = None


class ChangePasswordRequest(BaseModel):
    """Change password request schema."""

    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=10, max_length=128)

