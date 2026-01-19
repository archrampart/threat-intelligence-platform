"""Encryption utilities for API keys."""

from base64 import b64decode, b64encode

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.core.config import get_settings

settings = get_settings()


def _get_encryption_key() -> bytes:
    """Generate encryption key from settings."""
    # Use secret_key as salt, encryption_key as password
    password = settings.encryption_key.encode()
    salt = settings.secret_key.encode()[:16]  # Use first 16 bytes as salt

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = kdf.derive(password)
    return b64encode(key)


def encrypt_value(value: str) -> str:
    """Encrypt a string value (API key, password, etc.)."""
    if not value:
        return ""
    key = _get_encryption_key()
    fernet = Fernet(key)
    encrypted = fernet.encrypt(value.encode())
    return encrypted.decode()


def decrypt_value(encrypted_value: str) -> str:
    """Decrypt an encrypted string value."""
    if not encrypted_value:
        return ""
    try:
        key = _get_encryption_key()
        fernet = Fernet(key)
        decrypted = fernet.decrypt(encrypted_value.encode())
        return decrypted.decode()
    except Exception:
        # If decryption fails, return empty string
        return ""











