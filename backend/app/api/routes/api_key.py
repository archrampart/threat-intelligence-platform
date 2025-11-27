"""API Key management endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.routes.auth import get_current_user
from app.core.dependencies import require_role
from app.db.base import get_db
from app.models.user import UserRole
from app.schemas.api_key import (
    APIKeyCreate,
    APIKeyResponse,
    APIKeyTestRequest,
    APIKeyTestResponse,
    APIKeyUpdate,
    APIKeyUpdateAllResponse,
    APIKeyUpdateNowResponse,
)
from app.schemas.auth import UserResponse
from app.services.api_key_service import APIKeyService

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@router.get("/", response_model=List[APIKeyResponse], summary="List API keys")
async def list_api_keys(
    current_user: UserResponse = Depends(require_role([UserRole.ADMIN, UserRole.ANALYST])),
    db: Session = Depends(get_db),
) -> List[APIKeyResponse]:
    """List all API keys (user's own keys, or all if admin)."""
    service = APIKeyService(db)
    api_keys = service.list_api_keys(current_user.id)
    return [APIKeyResponse(**service.to_response(key)) for key in api_keys]


@router.post(
    "/",
    response_model=APIKeyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create API key",
)
async def create_api_key(
    api_key_data: APIKeyCreate,
    current_user: UserResponse = Depends(require_role([UserRole.ADMIN, UserRole.ANALYST])),
    db: Session = Depends(get_db),
) -> APIKeyResponse:
    """Create a new API key."""
    service = APIKeyService(db)
    try:
        api_key = service.create_api_key(current_user.id, api_key_data)
        return APIKeyResponse(**service.to_response(api_key))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{api_key_id}", response_model=APIKeyResponse, summary="Get API key")
async def get_api_key(
    api_key_id: str,
    current_user: UserResponse = Depends(require_role([UserRole.ADMIN, UserRole.ANALYST])),
    db: Session = Depends(get_db),
) -> APIKeyResponse:
    """Get API key by ID."""
    service = APIKeyService(db)
    api_key = service.get_api_key(api_key_id, current_user.id)
    if not api_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    return APIKeyResponse(**service.to_response(api_key))


@router.put("/{api_key_id}", response_model=APIKeyResponse, summary="Update API key")
async def update_api_key(
    api_key_id: str,
    api_key_data: APIKeyUpdate,
    current_user: UserResponse = Depends(require_role([UserRole.ADMIN, UserRole.ANALYST])),
    db: Session = Depends(get_db),
) -> APIKeyResponse:
    """Update an API key."""
    service = APIKeyService(db)
    try:
        api_key = service.update_api_key(api_key_id, current_user.id, api_key_data)
        return APIKeyResponse(**service.to_response(api_key))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete(
    "/{api_key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete API key",
)
async def delete_api_key(
    api_key_id: str,
    current_user: UserResponse = Depends(require_role([UserRole.ADMIN, UserRole.ANALYST])),
    db: Session = Depends(get_db),
) -> None:
    """Delete an API key."""
    service = APIKeyService(db)
    deleted = service.delete_api_key(api_key_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")


@router.post(
    "/{api_key_id}/test",
    response_model=APIKeyTestResponse,
    summary="Test API key",
)
async def test_api_key(
    api_key_id: str,
    test_request: APIKeyTestRequest,
    current_user: UserResponse = Depends(require_role([UserRole.ADMIN, UserRole.ANALYST])),
    db: Session = Depends(get_db),
) -> APIKeyTestResponse:
    """Test an API key by making a test query."""
    service = APIKeyService(db)
    return service.test_api_key(api_key_id, current_user.id, test_request)


@router.post(
    "/{api_key_id}/update-now",
    response_model=APIKeyUpdateNowResponse,
    summary="Update API key data now (manual update)",
)
async def update_api_key_now(
    api_key_id: str,
    current_user: UserResponse = Depends(require_role([UserRole.ADMIN, UserRole.ANALYST])),
    db: Session = Depends(get_db),
) -> APIKeyUpdateNowResponse:
    """Manually update API key data (for manual mode)."""
    service = APIKeyService(db)
    api_key = service.get_api_key(api_key_id, current_user.id)
    if not api_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")

    # For now, this is a placeholder - in production, this would:
    # 1. Decrypt the API key
    # 2. Make API calls to update data
    # 3. Cache the results
    # 4. Update last_used timestamp

    from datetime import datetime, timezone

    api_key.last_used = datetime.now(timezone.utc)
    db.commit()

    return APIKeyUpdateNowResponse(
        success=True,
        message="API key update initiated",
        updated_data={"status": "pending"},
    )


@router.post(
    "/update-all",
    response_model=APIKeyUpdateAllResponse,
    summary="Update all manual mode API keys",
)
async def update_all_api_keys(
    current_user: UserResponse = Depends(require_role([UserRole.ADMIN, UserRole.ANALYST])),
    db: Session = Depends(get_db),
) -> APIKeyUpdateAllResponse:
    """Update all API keys in manual mode."""
    service = APIKeyService(db)
    api_keys = service.list_api_keys(current_user.id)

    # Filter only manual mode and active keys
    from app.models.api_source import UpdateMode

    manual_keys = [
        key
        for key in api_keys
        if key.update_mode == UpdateMode.MANUAL and key.is_active
    ]

    results = []
    successful = 0
    failed = 0

    for api_key in manual_keys:
        try:
            # Placeholder for actual update logic
            from datetime import datetime, timezone

            api_key.last_used = datetime.now(timezone.utc)
            db.commit()

            results.append(
                {
                    "api_key_id": api_key.id,
                    "api_source_id": api_key.api_source_id,
                    "success": True,
                    "message": "Update initiated",
                }
            )
            successful += 1
        except Exception as e:
            results.append(
                {
                    "api_key_id": api_key.id,
                    "api_source_id": api_key.api_source_id,
                    "success": False,
                    "error": str(e),
                }
            )
            failed += 1

    return APIKeyUpdateAllResponse(
        total=len(manual_keys),
        successful=successful,
        failed=failed,
        results=results,
    )

