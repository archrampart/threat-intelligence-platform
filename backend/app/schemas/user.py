"""User management schemas."""

from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """Schema for creating a new user."""

    username: str = Field(..., min_length=3, max_length=50, description="Username")
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., min_length=6, description="Password")
    role: str = Field(default="viewer", description="User role (admin, analyst, viewer)")
    is_active: bool = Field(default=True, description="User active status")
    full_name: Optional[str] = Field(None, max_length=100, description="Full name")
    language_preference: str = Field(default="en", description="Language preference")


class UserUpdate(BaseModel):
    """Schema for updating a user."""

    username: Optional[str] = Field(None, min_length=3, max_length=50, description="Username")
    email: Optional[EmailStr] = Field(None, description="Email address")
    role: Optional[str] = Field(None, description="User role (admin, analyst, viewer)")
    is_active: Optional[bool] = Field(None, description="User active status")
    full_name: Optional[str] = Field(None, max_length=100, description="Full name")
    language_preference: Optional[str] = Field(None, description="Language preference")


class UserListResponse(BaseModel):
    """Schema for user list response."""

    items: list = Field(..., description="List of users")
    total: int = Field(..., description="Total number of users")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Page size")
    total_pages: int = Field(..., description="Total number of pages")


class ChangeRoleRequest(BaseModel):
    """Schema for changing user role."""

    role: str = Field(..., description="New role (admin, analyst, viewer)")











