"""Seed initial users.

* Development (or SEED_DEFAULT_USERS=true): admin / analyst / viewer demo accounts.
* Production: only an ``admin`` account is created when no admin exists. Its password
  comes from DEFAULT_ADMIN_PASSWORD, or a random one is generated and logged once.
"""

import secrets

from loguru import logger

from app.core.config import get_settings
from app.core.security import get_password_hash
from app.db.base import SessionLocal
from app.models.user import User, UserRole

_DEMO_USERS = [
    ("00000000-0000-0000-0000-000000000001", "admin", "admin123", UserRole.ADMIN),
    ("00000000-0000-0000-0000-000000000002", "analyst", "analyst123", UserRole.ANALYST),
    ("00000000-0000-0000-0000-000000000003", "viewer", "viewer123", UserRole.VIEWER),
]


def seed_default_user() -> None:
    settings = get_settings()
    db = SessionLocal()
    try:
        if settings.should_seed_default_users:
            created = []
            for user_id, username, password, role in _DEMO_USERS:
                if db.query(User).filter(User.username == username).first():
                    continue
                db.add(
                    User(
                        id=user_id,
                        username=username,
                        email=f"{username}@threatintel.local",
                        password_hash=get_password_hash(password),
                        role=role,
                        is_active=True,
                        language_preference="en",
                    )
                )
                created.append(username)
            db.commit()
            if created:
                logger.warning(
                    "Seeded DEMO users with well-known passwords: {}. Disable with SEED_DEFAULT_USERS=false.",
                    ", ".join(created),
                )
            return

        # Production bootstrap: make sure at least one admin exists.
        if db.query(User).filter(User.role == UserRole.ADMIN).first():
            return
        password = settings.default_admin_password
        generated = False
        if not password:
            password = secrets.token_urlsafe(18)
            generated = True
        db.add(
            User(
                id="00000000-0000-0000-0000-000000000001",
                username="admin",
                email="admin@threatintel.local",
                password_hash=get_password_hash(password),
                role=UserRole.ADMIN,
                is_active=True,
                language_preference="en",
            )
        )
        db.commit()
        if generated:
            logger.warning(
                "Initial admin account created. Username: admin  Password: {}  (shown once - change it now)",
                password,
            )
        else:
            logger.info("Initial admin account created from DEFAULT_ADMIN_PASSWORD")
    except Exception:
        db.rollback()
        logger.exception("Error seeding default users")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_default_user()
