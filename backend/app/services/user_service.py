"""User service - CRUD and authentication operations."""

from uuid import uuid4
from typing import Optional
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.security import get_password_hash, verify_password
from app.models.user import User, UserRole
from app.schemas.auth import UserResponse
from app.schemas.user import UserCreate, UserUpdate
from sqlalchemy.orm.attributes import flag_modified


class UserService:
    """User service for CRUD and authentication operations."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_user_by_id(self, user_id: str) -> User | None:
        """Get user by ID."""
        return self.db.query(User).filter(User.id == user_id).first()

    def get_user_by_username(self, username: str) -> User | None:
        """Get user by username."""
        return self.db.query(User).filter(User.username == username).first()

    def get_user_by_email(self, email: str) -> User | None:
        """Get user by email."""
        return self.db.query(User).filter(User.email == email).first()

    def authenticate_user(self, username: str, password: str) -> User | None:
        """Authenticate a user by username and password."""
        user = self.get_user_by_username(username)
        if not user:
            return None
        if not user.is_active:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    def update_user_last_login(self, user_id: str) -> None:
        """Update user's last login timestamp."""
        user = self.get_user_by_id(user_id)
        if user:
            from datetime import datetime, timezone
            user.last_login = datetime.now(timezone.utc)
            self.db.commit()

    def list_users(
        self,
        search: Optional[str] = None,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """List users with filters and pagination."""
        query = self.db.query(User)

        # Apply filters
        if search:
            query = query.filter(
                or_(
                    User.username.ilike(f"%{search}%"),
                    User.email.ilike(f"%{search}%"),
                )
            )

        if role:
            try:
                role_enum = UserRole(role.lower())
                query = query.filter(User.role == role_enum)
            except ValueError:
                pass

        if is_active is not None:
            query = query.filter(User.is_active == is_active)

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (page - 1) * page_size
        users = query.order_by(User.created_at.desc()).offset(offset).limit(page_size).all()

        # Calculate total pages
        total_pages = (total + page_size - 1) // page_size

        return {
            "items": [self.to_response(user) for user in users],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    def create_user_admin(self, user_data: UserCreate) -> User:
        """Create a new user (admin operation)."""
        # Check if username or email already exists
        if self.get_user_by_username(user_data.username):
            raise ValueError("Username already exists")
        if self.get_user_by_email(user_data.email):
            raise ValueError("Email already exists")

        # Validate role
        try:
            role = UserRole(user_data.role.lower())
        except ValueError:
            role = UserRole.VIEWER

        # Prepare profile_json if full_name is provided
        profile_json = None
        if user_data.full_name and user_data.full_name.strip():
            profile_json = {"full_name": user_data.full_name.strip()}

        # Create user
        user = User(
            id=str(uuid4()),
            username=user_data.username,
            email=user_data.email,
            password_hash=get_password_hash(user_data.password),
            role=role,
            is_active=user_data.is_active,
            language_preference=user_data.language_preference,
            profile_json=profile_json,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_user_admin(self, user_id: str, user_data: UserUpdate) -> User:
        """Update a user (admin operation)."""
        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        # Update username if provided
        if user_data.username is not None:
            existing_user = self.get_user_by_username(user_data.username)
            if existing_user and existing_user.id != user_id:
                raise ValueError("Username already exists")
            user.username = user_data.username

        # Update email if provided
        if user_data.email is not None:
            existing_user = self.get_user_by_email(user_data.email)
            if existing_user and existing_user.id != user_id:
                raise ValueError("Email already exists")
            user.email = user_data.email

        # Update role if provided
        if user_data.role is not None:
            try:
                user.role = UserRole(user_data.role.lower())
            except ValueError:
                pass  # Invalid role, skip

        # Update is_active if provided
        if user_data.is_active is not None:
            user.is_active = user_data.is_active

        # Update language_preference if provided
        if user_data.language_preference is not None:
            user.language_preference = user_data.language_preference

        # Update full_name in profile_json if provided
        if user_data.full_name is not None:
            if user.profile_json is None:
                user.profile_json = {}
            if isinstance(user.profile_json, dict):
                if user_data.full_name:
                    user.profile_json["full_name"] = user_data.full_name
                elif "full_name" in user.profile_json:
                    del user.profile_json["full_name"]
                flag_modified(user, "profile_json")

        self.db.commit()
        self.db.refresh(user)
        return user

    def delete_user(self, user_id: str) -> bool:
        """Delete a user (soft delete by setting is_active=False)."""
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        user.is_active = False
        self.db.commit()
        return True

    def hard_delete_user(self, user_id: str) -> bool:
        """Permanently delete a user from the database."""
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        # Prevent deleting the current admin user (safety check)
        # You may want to add additional checks here
        self.db.delete(user)
        self.db.commit()
        return True

    def activate_user(self, user_id: str, is_active: bool) -> User:
        """Activate or deactivate a user."""
        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        user.is_active = is_active
        self.db.commit()
        self.db.refresh(user)
        return user

    def change_user_role(self, user_id: str, role: str) -> User:
        """Change user role."""
        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        try:
            user.role = UserRole(role.lower())
        except ValueError:
            raise ValueError(f"Invalid role: {role}")

        self.db.commit()
        self.db.refresh(user)
        return user

    def to_response(self, user: User) -> UserResponse:
        """Convert User model to UserResponse schema."""
        # Extract full_name from profile_json if available
        full_name = None
        if user.profile_json and isinstance(user.profile_json, dict):
            full_name = user.profile_json.get("full_name")

        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=full_name,
            role=user.role.value,
            is_active=user.is_active,
            language_preference=user.language_preference,
        )

