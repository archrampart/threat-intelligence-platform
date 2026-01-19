"""Seed default admin user for development."""

from app.db.base import SessionLocal
from app.models.user import User, UserRole
from app.core.security import get_password_hash


def seed_default_user() -> None:
    """Seed default admin user for development."""
    db = SessionLocal()

    try:
        # Check if admin user already exists
        existing = db.query(User).filter(User.username == "admin").first()
        if existing:
            print("Default admin user already exists. Skipping seed.")
            return

        # Create default admin user
        admin_user = User(
            id="00000000-0000-0000-0000-000000000001",
            username="admin",
            email="admin@threatintel.local",
            password_hash=get_password_hash("admin123"),
            role=UserRole.ADMIN,
            is_active=True,
            language_preference="en",
        )
        db.add(admin_user)

        # Create default analyst user
        analyst_user = User(
            id="00000000-0000-0000-0000-000000000002",
            username="analyst",
            email="analyst@threatintel.local",
            password_hash=get_password_hash("analyst123"),
            role=UserRole.ANALYST,
            is_active=True,
            language_preference="en",
        )
        db.add(analyst_user)

        # Create default viewer user
        viewer_user = User(
            id="00000000-0000-0000-0000-000000000003",
            username="viewer",
            email="viewer@threatintel.local",
            password_hash=get_password_hash("viewer123"),
            role=UserRole.VIEWER,
            is_active=True,
            language_preference="en",
        )
        db.add(viewer_user)

        db.commit()
        print("Successfully seeded default users:")
        print("  - admin / admin123 (ADMIN)")
        print("  - analyst / analyst123 (ANALYST)")
        print("  - viewer / viewer123 (VIEWER)")
    except Exception as e:
        db.rollback()
        print(f"Error seeding default users: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_default_user()





