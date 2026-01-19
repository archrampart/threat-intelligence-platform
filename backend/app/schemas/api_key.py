"""API Key schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.api_source import TestStatus, UpdateMode


class APIKeyBase(BaseModel):
    """Base API Key schema."""

    api_source_id: str = Field(..., description="API Source ID")
    api_key: Optional[str] = Field(None, description="API Key (will be encrypted, optional for APIs that don't require authentication)")
    username: Optional[str] = Field(None, description="Username (for MISP, etc.)")
    password: Optional[str] = Field(None, description="Password (for MISP, etc.)")
    api_url: Optional[str] = Field(None, description="Custom API URL override")
    update_mode: UpdateMode = Field(default=UpdateMode.MANUAL, description="Update mode: manual or auto")
    is_active: bool = Field(default=True, description="Is API key active")


class APIKeyCreate(APIKeyBase):
    """API Key creation schema."""

    pass


class APIKeyUpdate(BaseModel):
    """API Key update schema."""

    api_key: Optional[str] = Field(None, min_length=1)
    username: Optional[str] = None
    password: Optional[str] = None
    api_url: Optional[str] = None
    update_mode: Optional[UpdateMode] = None
    is_active: Optional[bool] = None


class APIKeyResponse(BaseModel):
    """API Key response schema (without sensitive data)."""

    id: str
    user_id: str
    api_source_id: str
    api_source_name: Optional[str] = None
    username: Optional[str] = None  # Username gösterilebilir (encrypted değil)
    api_url: Optional[str] = None
    update_mode: UpdateMode
    is_active: bool
    test_status: TestStatus
    last_test_date: Optional[datetime] = None
    last_used: Optional[datetime] = None
    rate_limit: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class APIKeyTestRequest(BaseModel):
    """API Key test request schema."""

    test_ioc_type: str = Field(default="ip", description="IOC type to test")
    test_ioc_value: str = Field(default="8.8.8.8", description="IOC value to test")


class APIKeyTestResponse(BaseModel):
    """API Key test response schema."""

    success: bool
    message: str
    test_status: TestStatus
    response_data: Optional[dict] = None
    error: Optional[str] = None


class APIKeyUpdateNowResponse(BaseModel):
    """API Key update now response schema."""

    success: bool
    message: str
    updated_data: Optional[dict] = None
    error: Optional[str] = None


class APIKeyUpdateAllResponse(BaseModel):
    """API Key update all response schema."""

    total: int
    successful: int
    failed: int
    results: list[dict]  # List of update results




