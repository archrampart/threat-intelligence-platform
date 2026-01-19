"""API Source service - CRUD and management operations."""

from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.api_source import APISource
from app.models.user import User
from app.schemas.api_source import APISourceCreate, APISourceUpdate, APISourceTestRequest, APISourceTestResponse

from datetime import datetime, timezone


class APISourceService:
    """API Source service for CRUD and management operations."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_api_source(self, api_source_id: str) -> APISource | None:
        """Get API source by ID."""
        return self.db.query(APISource).filter(APISource.id == api_source_id).first()

    def get_api_source_by_name(self, name: str) -> APISource | None:
        """Get API source by name."""
        return self.db.query(APISource).filter(APISource.name == name).first()

    def list_api_sources(self, include_inactive: bool = False) -> list[APISource]:
        """List all API sources."""
        query = self.db.query(APISource)
        if not include_inactive:
            query = query.filter(APISource.is_active == True)
        return query.all()

    def create_api_source(self, user_id: str | None, api_source_data: APISourceCreate) -> APISource:
        """Create a new API source."""
        # Check if name already exists
        existing = self.get_api_source_by_name(api_source_data.name)
        if existing:
            raise ValueError(f"API source with name '{api_source_data.name}' already exists")

        api_source = APISource(
            id=str(uuid4()),
            name=api_source_data.name,
            display_name=api_source_data.display_name,
            description=api_source_data.description,
            api_type=api_source_data.api_type,
            base_url=api_source_data.base_url,
            documentation_url=api_source_data.documentation_url,
            supported_ioc_types=api_source_data.supported_ioc_types,
            authentication_type=api_source_data.authentication_type,
            request_config=api_source_data.request_config,
            response_config=api_source_data.response_config,
            rate_limit_config=api_source_data.rate_limit_config,
            is_active=api_source_data.is_active,
            created_by=user_id,
        )
        self.db.add(api_source)
        self.db.commit()
        self.db.refresh(api_source)
        return api_source

    def update_api_source(self, api_source_id: str, api_source_data: APISourceUpdate) -> APISource:
        """Update an API source."""
        api_source = self.get_api_source(api_source_id)
        if not api_source:
            raise ValueError("API source not found")

        # Update fields
        if api_source_data.display_name is not None:
            api_source.display_name = api_source_data.display_name
        if api_source_data.description is not None:
            api_source.description = api_source_data.description
        if api_source_data.base_url is not None:
            api_source.base_url = api_source_data.base_url
        if api_source_data.documentation_url is not None:
            api_source.documentation_url = api_source_data.documentation_url
        if api_source_data.supported_ioc_types is not None:
            api_source.supported_ioc_types = api_source_data.supported_ioc_types
        if api_source_data.authentication_type is not None:
            api_source.authentication_type = api_source_data.authentication_type
        if api_source_data.request_config is not None:
            api_source.request_config = api_source_data.request_config
        if api_source_data.response_config is not None:
            api_source.response_config = api_source_data.response_config
        if api_source_data.rate_limit_config is not None:
            api_source.rate_limit_config = api_source_data.rate_limit_config
        if api_source_data.is_active is not None:
            api_source.is_active = api_source_data.is_active

        self.db.commit()
        self.db.refresh(api_source)
        return api_source

    def delete_api_source(self, api_source_id: str) -> bool:
        """Delete an API source (only custom sources can be deleted)."""
        api_source = self.get_api_source(api_source_id)
        if not api_source:
            return False

        # Only allow deletion of custom API sources
        if api_source.api_type.value == "predefined":
            raise ValueError("Cannot delete predefined API sources")

        self.db.delete(api_source)
        self.db.commit()
        return True

    def test_api_source(self, api_source_id: str, test_request: APISourceTestRequest) -> APISourceTestResponse:
        """Test an API source configuration."""
        api_source = self.get_api_source(api_source_id)
        if not api_source:
            return APISourceTestResponse(
                success=False,
                message="API source not found",
                error="API source not found",
            )

        # Validate configuration
        if not api_source.request_config:
            return APISourceTestResponse(
                success=False,
                message="Request configuration is missing",
                error="Request configuration is required",
            )

        # Check if IOC type is supported
        if api_source.supported_ioc_types and test_request.test_ioc_type not in api_source.supported_ioc_types:
            return APISourceTestResponse(
                success=False,
                message=f"IOC type '{test_request.test_ioc_type}' is not supported",
                error=f"Supported types: {', '.join(api_source.supported_ioc_types)}",
            )

        try:
            # Use dynamic API client to make actual request
            from app.services.dynamic_api_client import DynamicAPIClient

            client = DynamicAPIClient(
                api_source=api_source,
                api_key=test_request.api_key,
                username=test_request.username,
                password=test_request.password,
                api_url_override=test_request.api_url,
            )

            result = client.query(
                ioc_type=test_request.test_ioc_type,
                ioc_value=test_request.test_ioc_value,
                timeout=10,  # Shorter timeout for tests
            )

            if result.get("status") == "success":
                return APISourceTestResponse(
                    success=True,
                    message="API source test successful",
                    response_data=result,
                )
            else:
                return APISourceTestResponse(
                    success=False,
                    message=f"API source test failed: {result.get('error', 'Unknown error')}",
                    error=result.get("error", "Unknown error"),
                    response_data=result,
                )

        except Exception as e:
            return APISourceTestResponse(
                success=False,
                message=f"API source test failed: {str(e)}",
                error=str(e),
            )

    def to_response(self, api_source: APISource) -> dict:
        """Convert APISource model to response dict."""
        return {
            "id": api_source.id,
            "name": api_source.name,
            "display_name": api_source.display_name,
            "description": api_source.description,
            "api_type": api_source.api_type.value,
            "base_url": api_source.base_url,
            "documentation_url": api_source.documentation_url,
            "supported_ioc_types": api_source.supported_ioc_types or [],
            "authentication_type": api_source.authentication_type.value,
            "request_config": api_source.request_config,
            "response_config": api_source.response_config,
            "rate_limit_config": api_source.rate_limit_config,
            "is_active": api_source.is_active,
            "created_by": api_source.created_by,
            "created_at": api_source.created_at.isoformat() if api_source.created_at else None,
            "updated_at": api_source.updated_at.isoformat() if api_source.updated_at else None,
        }

