"""Authentication schemas."""

from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class Token(BaseModel):
    """Token response schema."""

    access_token: str
    refresh_token: str
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
    """Refresh token request schema."""

    refresh_token: str


class UserResponse(BaseModel):
    """User response schema."""

    id: str
    username: str
    email: str
    full_name: Optional[str] = None
    role: str
    is_active: bool
    language_preference: str

    class Config:
        from_attributes = True


class UserProfileUpdate(BaseModel):
    """User profile update request schema."""

    full_name: Optional[str] = Field(None, max_length=200)
    email: Optional[EmailStr] = None


class ChangePasswordRequest(BaseModel):
    """Change password request schema."""

    current_password: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=6)

