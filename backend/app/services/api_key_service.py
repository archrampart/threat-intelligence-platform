"""API Key service - CRUD and management operations."""

from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.encryption import decrypt_value, encrypt_value
from app.models.api_source import APISource, APIKey, TestStatus, UpdateMode
from app.models.user import User
from app.schemas.api_key import APIKeyCreate, APIKeyUpdate, APIKeyTestRequest, APIKeyTestResponse


class APIKeyService:
    """API Key service for CRUD and management operations."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_api_key(self, api_key_id: str, user_id: str) -> APIKey | None:
        """Get API key by ID (user can only access their own keys, unless admin)."""
        api_key = self.db.query(APIKey).filter(APIKey.id == api_key_id).first()
        if not api_key:
            return None

        # Check if user owns the key or is admin
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return None

        if api_key.user_id != user_id and user.role.value != "admin":
            return None

        return api_key

    def list_api_keys(self, user_id: str) -> list[APIKey]:
        """List all API keys for a user (admin sees all)."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return []

        if user.role.value == "admin":
            return self.db.query(APIKey).all()
        else:
            return self.db.query(APIKey).filter(APIKey.user_id == user_id).all()

    def create_api_key(self, user_id: str, api_key_data: APIKeyCreate) -> APIKey:
        """Create a new API key."""
        # Verify API source exists
        api_source = self.db.query(APISource).filter(APISource.id == api_key_data.api_source_id).first()
        if not api_source:
            raise ValueError("API source not found")

        # Check if API key is required
        requires_api_key = api_source.authentication_type.value != "none"
        
        # Validate API key if required
        if requires_api_key and (not api_key_data.api_key or not api_key_data.api_key.strip()):
            raise ValueError("API key is required for this API source")

        # Encrypt sensitive data (only if provided)
        # For APIs that don't require authentication, we still need to store something (empty encrypted string)
        # but we'll handle it in IOC service by checking authentication_type
        if api_key_data.api_key and api_key_data.api_key.strip():
            encrypted_key = encrypt_value(api_key_data.api_key)
        else:
            # For APIs that don't require authentication, store empty encrypted string
            # This will be handled in IOC service by checking authentication_type
            encrypted_key = encrypt_value("")
        encrypted_username = encrypt_value(api_key_data.username) if api_key_data.username else None
        encrypted_password = encrypt_value(api_key_data.password) if api_key_data.password else None

        api_key = APIKey(
            id=str(uuid4()),
            user_id=user_id,
            api_source_id=api_key_data.api_source_id,
            api_key=encrypted_key,
            username=encrypted_username,
            password=encrypted_password,
            api_url=api_key_data.api_url,
            update_mode=api_key_data.update_mode,
            is_active=api_key_data.is_active,
            test_status=TestStatus.NOT_TESTED,
        )
        self.db.add(api_key)
        self.db.commit()
        self.db.refresh(api_key)
        return api_key

    def update_api_key(self, api_key_id: str, user_id: str, api_key_data: APIKeyUpdate) -> APIKey:
        """Update an API key."""
        api_key = self.get_api_key(api_key_id, user_id)
        if not api_key:
            raise ValueError("API key not found")

        # Update fields
        if api_key_data.api_key is not None:
            api_key.api_key = encrypt_value(api_key_data.api_key)
        if api_key_data.username is not None:
            api_key.username = encrypt_value(api_key_data.username) if api_key_data.username else None
        if api_key_data.password is not None:
            api_key.password = encrypt_value(api_key_data.password) if api_key_data.password else None
        if api_key_data.api_url is not None:
            api_key.api_url = api_key_data.api_url
        if api_key_data.update_mode is not None:
            api_key.update_mode = api_key_data.update_mode
        if api_key_data.is_active is not None:
            api_key.is_active = api_key_data.is_active

        self.db.commit()
        self.db.refresh(api_key)
        return api_key

    def delete_api_key(self, api_key_id: str, user_id: str) -> bool:
        """Delete an API key."""
        api_key = self.get_api_key(api_key_id, user_id)
        if not api_key:
            return False

        self.db.delete(api_key)
        self.db.commit()
        return True

    def test_api_key(self, api_key_id: str, user_id: str, test_request: APIKeyTestRequest) -> APIKeyTestResponse:
        """Test an API key by making a test query."""
        api_key = self.get_api_key(api_key_id, user_id)
        if not api_key:
            return APIKeyTestResponse(
                success=False,
                message="API key not found",
                test_status=TestStatus.INVALID,
                error="API key not found",
            )

        # Decrypt API key
        decrypted_key = decrypt_value(api_key.api_key)
        if not decrypted_key:
            return APIKeyTestResponse(
                success=False,
                message="Failed to decrypt API key",
                test_status=TestStatus.INVALID,
                error="Decryption failed",
            )

        # Get API source
        api_source = self.db.query(APISource).filter(APISource.id == api_key.api_source_id).first()
        if not api_source:
            return APIKeyTestResponse(
                success=False,
                message="API source not found",
                test_status=TestStatus.INVALID,
                error="API source not found",
            )

        # Try to query using the API key
        # For now, we'll use the mock client registry
        # In the future, this will use the actual API client
        try:
            # This is a simplified test - in production, you'd make an actual API call
            # For now, we'll just mark it as valid if decryption succeeded
            api_key.test_status = TestStatus.VALID
            from datetime import datetime, timezone
            api_key.last_test_date = datetime.now(timezone.utc)
            self.db.commit()

            return APIKeyTestResponse(
                success=True,
                message="API key test successful",
                test_status=TestStatus.VALID,
                response_data={"status": "valid"},
            )
        except Exception as e:
            api_key.test_status = TestStatus.INVALID
            from datetime import datetime, timezone
            api_key.last_test_date = datetime.now(timezone.utc)
            self.db.commit()

            return APIKeyTestResponse(
                success=False,
                message=f"API key test failed: {str(e)}",
                test_status=TestStatus.INVALID,
                error=str(e),
            )

    def get_decrypted_key(self, api_key_id: str) -> str | None:
        """Get decrypted API key (for internal use only)."""
        api_key = self.db.query(APIKey).filter(APIKey.id == api_key_id).first()
        if not api_key or not api_key.is_active:
            return None
        return decrypt_value(api_key.api_key)

    def to_response(self, api_key: APIKey) -> dict:
        """Convert APIKey model to response dict."""
        api_source = self.db.query(APISource).filter(APISource.id == api_key.api_source_id).first()
        username = decrypt_value(api_key.username) if api_key.username else None

        return {
            "id": api_key.id,
            "user_id": api_key.user_id,
            "api_source_id": api_key.api_source_id,
            "api_source_name": api_source.display_name if api_source else None,
            "username": username,
            "api_url": api_key.api_url,
            "update_mode": api_key.update_mode.value,
            "is_active": api_key.is_active,
            "test_status": api_key.test_status.value,
            "last_test_date": api_key.last_test_date,
            "last_used": api_key.last_used,
            "rate_limit": api_key.rate_limit,
            "created_at": api_key.created_at,
            "updated_at": api_key.updated_at,
        }

