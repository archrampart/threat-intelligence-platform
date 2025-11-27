"""Dependencies for authentication and authorization."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.routes.auth import get_current_user
from app.models.user import UserRole
from app.schemas.auth import UserResponse
from app.services.user_service import UserService

from app.db.base import get_db


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    """Get user service instance."""
    return UserService(db)


def require_role(allowed_roles: list[UserRole]):
    """Dependency factory for role-based access control."""

    def role_checker(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
        user_role = UserRole(current_user.role)
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {[r.value for r in allowed_roles]}",
            )
        return current_user

    return role_checker


# Common role dependencies
RequireAdmin = Annotated[UserResponse, Depends(require_role([UserRole.ADMIN]))]
RequireAnalyst = Annotated[UserResponse, Depends(require_role([UserRole.ADMIN, UserRole.ANALYST]))]
RequireAnyRole = Annotated[UserResponse, Depends(require_role([UserRole.ADMIN, UserRole.ANALYST, UserRole.VIEWER]))]

