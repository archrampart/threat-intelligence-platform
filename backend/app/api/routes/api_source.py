"""API Source management endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.routes.auth import get_current_user
from app.core.dependencies import require_role
from app.db.base import get_db
from app.models.user import UserRole
from app.schemas.api_source import (
    APISourceCreate,
    APISourceResponse,
    APISourceTestRequest,
    APISourceTestResponse,
    APISourceUpdate,
)
from app.schemas.auth import UserResponse
from app.services.api_source_service import APISourceService

router = APIRouter(prefix="/api-sources", tags=["api-sources"])


@router.get("", response_model=List[APISourceResponse], summary="List API sources")
async def list_api_sources(
    include_inactive: bool = Query(default=False, description="Include inactive sources"),
    current_user: UserResponse = Depends(require_role([UserRole.ADMIN, UserRole.ANALYST])),
    db: Session = Depends(get_db),
) -> List[APISourceResponse]:
    """List all API sources."""
    service = APISourceService(db)
    api_sources = service.list_api_sources(include_inactive=include_inactive)
    return [APISourceResponse(**service.to_response(source)) for source in api_sources]


@router.post(
    "/",
    response_model=APISourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create API source",
)
async def create_api_source(
    api_source_data: APISourceCreate,
    current_user: UserResponse = Depends(require_role([UserRole.ADMIN, UserRole.ANALYST])),
    db: Session = Depends(get_db),
) -> APISourceResponse:
    """Create a new API source (custom)."""
    service = APISourceService(db)
    try:
        api_source = service.create_api_source(current_user.id, api_source_data)
        return APISourceResponse(**service.to_response(api_source))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{api_source_id}", response_model=APISourceResponse, summary="Get API source")
async def get_api_source(
    api_source_id: str,
    current_user: UserResponse = Depends(require_role([UserRole.ADMIN, UserRole.ANALYST])),
    db: Session = Depends(get_db),
) -> APISourceResponse:
    """Get API source by ID."""
    service = APISourceService(db)
    api_source = service.get_api_source(api_source_id)
    if not api_source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API source not found")
    return APISourceResponse(**service.to_response(api_source))


@router.put("/{api_source_id}", response_model=APISourceResponse, summary="Update API source")
async def update_api_source(
    api_source_id: str,
    api_source_data: APISourceUpdate,
    current_user: UserResponse = Depends(require_role([UserRole.ADMIN, UserRole.ANALYST])),
    db: Session = Depends(get_db),
) -> APISourceResponse:
    """Update an API source."""
    service = APISourceService(db)
    try:
        api_source = service.update_api_source(api_source_id, api_source_data)
        return APISourceResponse(**service.to_response(api_source))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete(
    "/{api_source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete API source",
)
async def delete_api_source(
    api_source_id: str,
    current_user: UserResponse = Depends(require_role([UserRole.ADMIN, UserRole.ANALYST])),
    db: Session = Depends(get_db),
) -> None:
    """Delete an API source (only custom sources)."""
    service = APISourceService(db)
    try:
        deleted = service.delete_api_source(api_source_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API source not found")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/{api_source_id}/test",
    response_model=APISourceTestResponse,
    summary="Test API source configuration",
)
async def test_api_source(
    api_source_id: str,
    test_request: APISourceTestRequest,
    current_user: UserResponse = Depends(require_role([UserRole.ADMIN, UserRole.ANALYST])),
    db: Session = Depends(get_db),
) -> APISourceTestResponse:
    """Test an API source configuration."""
    service = APISourceService(db)
    return service.test_api_source(api_source_id, test_request)

