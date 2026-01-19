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


@router.post(
    "/bulk-add-free",
    status_code=status.HTTP_201_CREATED,
    summary="Add all free API sources (no API key required)",
)
async def bulk_add_free_sources(
    current_user: UserResponse = Depends(require_role([UserRole.ADMIN, UserRole.ANALYST])),
    db: Session = Depends(get_db),
):
    """
    Add all free API sources (authentication_type=NONE) for the current user.
    Only adds sources that don't already exist for the user.
    
    Returns:
        - total_free_sources: Total number of free sources available
        - newly_added: Number of sources added in this operation
        - already_exists: Number of sources user already had
        - added_sources: List of newly added source names
    """
    from app.models.api_source import AuthenticationType, APISource, APIKey
    from sqlalchemy import and_
    
    # Get all free sources (authentication_type = NONE)
    free_sources = db.query(APISource).filter(
        APISource.authentication_type == AuthenticationType.NONE
    ).all()
    
    newly_added = []
    already_exists = 0
    
    for source in free_sources:
        # Check if user already has this source
        existing = db.query(APIKey).filter(
            and_(
                APIKey.user_id == current_user.id,
                APIKey.api_source_id == source.id
            )
        ).first()
        
        if existing:
            already_exists += 1
            continue
        
        # Create new API key entry (with empty key since it's not required)
        from app.models.api_source import TestStatus, UpdateMode
        from datetime import datetime, timezone
        import uuid
        
        new_api_key = APIKey(
            id=f"apikey-{uuid.uuid4()}",
            user_id=current_user.id,
            api_source_id=source.id,
            api_key="FREE_SOURCE_NO_KEY_REQUIRED",  # Placeholder for free sources (field is NOT NULL)
            is_active=True,
            test_status=TestStatus.NOT_TESTED,
            update_mode=UpdateMode.MANUAL,  # Default to MANUAL (OFF) to avoid auto API usage
            created_at=datetime.now(timezone.utc),
        )
        db.add(new_api_key)
        newly_added.append(source.name)
    
    db.commit()
    
    return {
        "success": True,
        "total_free_sources": len(free_sources),
        "newly_added": len(newly_added),
        "already_exists": already_exists,
        "added_sources": newly_added,
        "message": f"Successfully added {len(newly_added)} free threat intelligence sources"
    }

