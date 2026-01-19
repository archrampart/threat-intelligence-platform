"""API Source schemas."""

from typing import Any, Optional

from pydantic import BaseModel, Field

from app.models.api_source import APIType, AuthenticationType


class APISourceBase(BaseModel):
    """Base API Source schema."""

    name: str = Field(..., min_length=1, max_length=100, description="API name (unique identifier)")
    display_name: str = Field(..., min_length=1, max_length=200, description="Display name")
    description: Optional[str] = Field(None, description="API description")
    api_type: APIType = Field(default=APIType.PREDEFINED, description="API type: predefined or custom")
    base_url: str = Field(..., min_length=1, max_length=500, description="Base URL")
    documentation_url: Optional[str] = Field(None, max_length=500, description="Documentation URL")
    supported_ioc_types: list[str] = Field(default_factory=list, description="Supported IOC types: ip, domain, url, hash")
    authentication_type: AuthenticationType = Field(..., description="Authentication type")
    request_config: Optional[dict[str, Any]] = Field(None, description="Request configuration")
    response_config: Optional[dict[str, Any]] = Field(None, description="Response parsing configuration")
    rate_limit_config: Optional[dict[str, Any]] = Field(None, description="Rate limit configuration")
    is_active: bool = Field(default=True, description="Is API source active")


class APISourceCreate(APISourceBase):
    """API Source creation schema."""

    pass


class APISourceUpdate(BaseModel):
    """API Source update schema."""

    display_name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    base_url: Optional[str] = Field(None, min_length=1, max_length=500)
    documentation_url: Optional[str] = Field(None, max_length=500)
    supported_ioc_types: Optional[list[str]] = None
    authentication_type: Optional[AuthenticationType] = None
    request_config: Optional[dict[str, Any]] = None
    response_config: Optional[dict[str, Any]] = None
    rate_limit_config: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None


class APISourceResponse(BaseModel):
    """API Source response schema."""

    id: str
    name: str
    display_name: str
    description: Optional[str] = None
    api_type: APIType
    base_url: str
    documentation_url: Optional[str] = None
    supported_ioc_types: list[str]
    authentication_type: AuthenticationType
    request_config: Optional[dict[str, Any]] = None
    response_config: Optional[dict[str, Any]] = None
    rate_limit_config: Optional[dict[str, Any]] = None
    is_active: bool
    created_by: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class APISourceTestRequest(BaseModel):
    """API Source test request schema."""

    api_key: str = Field(..., description="API key to test")
    test_ioc_type: str = Field(default="ip", description="IOC type to test")
    test_ioc_value: str = Field(default="8.8.8.8", description="IOC value to test")
    username: Optional[str] = Field(None, description="Username (if required)")
    password: Optional[str] = Field(None, description="Password (if required)")
    api_url: Optional[str] = Field(None, description="Custom API URL override")


class APISourceTestResponse(BaseModel):
    """API Source test response schema."""

    success: bool
    message: str
    response_data: Optional[dict[str, Any]] = None
    error: Optional[str] = None











