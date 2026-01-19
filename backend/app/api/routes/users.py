"""User management endpoints (Admin only)."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.routes.auth import get_current_user
from app.core.dependencies import require_role
from app.db.base import get_db
from app.models.user import UserRole
from app.schemas.auth import UserResponse
from app.schemas.user import (
    ChangeRoleRequest,
    UserCreate,
    UserListResponse,
    UserUpdate,
)
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=UserListResponse, summary="List all users")
def list_users(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_role([UserRole.ADMIN])),
    search: Optional[str] = Query(None, description="Search by username or email"),
    role: Optional[str] = Query(None, description="Filter by role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
) -> UserListResponse:
    """List all users with filters and pagination (Admin only)."""
    service = UserService(db)
    result = service.list_users(
        search=search,
        role=role,
        is_active=is_active,
        page=page,
        page_size=page_size,
    )
    return UserListResponse(**result)


@router.get("/{user_id}", response_model=UserResponse, summary="Get user by ID")
def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_role([UserRole.ADMIN])),
) -> UserResponse:
    """Get user details by ID (Admin only)."""
    service = UserService(db)
    user = service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return service.to_response(user)


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Create new user")
def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_role([UserRole.ADMIN])),
) -> UserResponse:
    """Create a new user (Admin only)."""
    from loguru import logger
    logger.info(f"Creating user with data: username={user_data.username}, email={user_data.email}, role={user_data.role}")
    service = UserService(db)
    try:
        user = service.create_user_admin(user_data)
        return service.to_response(user)
    except ValueError as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/{user_id}", response_model=UserResponse, summary="Update user")
def update_user(
    user_id: str,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_role([UserRole.ADMIN])),
) -> UserResponse:
    """Update user information (Admin only)."""
    service = UserService(db)
    try:
        user = service.update_user_admin(user_id, user_data)
        return service.to_response(user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete user (soft delete)")
def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_role([UserRole.ADMIN])),
) -> None:
    """Delete a user (soft delete by setting is_active=False) (Admin only)."""
    # Prevent deleting yourself
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account"
        )
    service = UserService(db)
    deleted = service.delete_user(user_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")


@router.delete("/{user_id}/hard", status_code=status.HTTP_204_NO_CONTENT, summary="Permanently delete user")
def hard_delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_role([UserRole.ADMIN])),
) -> None:
    """Permanently delete a user from the database (Admin only)."""
    # Prevent deleting yourself
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account"
        )
    
    service = UserService(db)
    deleted = service.hard_delete_user(user_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")


@router.put("/{user_id}/activate", response_model=UserResponse, summary="Activate/deactivate user")
def activate_user(
    user_id: str,
    is_active: bool = Query(..., description="Active status"),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_role([UserRole.ADMIN])),
) -> UserResponse:
    """Activate or deactivate a user (Admin only)."""
    service = UserService(db)
    try:
        user = service.activate_user(user_id, is_active)
        return service.to_response(user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/{user_id}/role", response_model=UserResponse, summary="Change user role")
def change_user_role(
    user_id: str,
    role_data: ChangeRoleRequest,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_role([UserRole.ADMIN])),
) -> UserResponse:
    """Change user role (Admin only)."""
    service = UserService(db)
    try:
        user = service.change_user_role(user_id, role_data.role)
        return service.to_response(user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

