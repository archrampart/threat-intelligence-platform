"""Input validation utilities for security."""

import re
from typing import Optional
from urllib.parse import urlparse


def validate_email(email: str) -> bool:
    """Validate email address format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_url(url: str) -> bool:
    """Validate URL format."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def sanitize_string(value: str, max_length: Optional[int] = None) -> str:
    """Sanitize string input to prevent injection attacks."""
    # Remove null bytes
    value = value.replace('\x00', '')
    # Remove control characters except newline and tab
    value = ''.join(char for char in value if ord(char) >= 32 or char in '\n\t')
    # Limit length if specified
    if max_length:
        value = value[:max_length]
    return value.strip()


def validate_username(username: str) -> bool:
    """Validate username format."""
    # Username should be 3-50 characters, alphanumeric and underscores only
    pattern = r'^[a-zA-Z0-9_]{3,50}$'
    return bool(re.match(pattern, username))


def validate_password_strength(password: str) -> tuple[bool, Optional[str]]:
    """Validate password strength."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if len(password) > 128:
        return False, "Password must be less than 128 characters"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one digit"
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    return True, None


def validate_ioc_value(ioc_type: str, ioc_value: str) -> tuple[bool, Optional[str]]:
    """Validate IOC value based on IOC type."""
    if not ioc_value or len(ioc_value) > 1000:
        return False, "IOC value must be between 1 and 1000 characters"
    
    if ioc_type.lower() == "ip":
        ipv4_pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
        if not re.match(ipv4_pattern, ioc_value):
            return False, "Invalid IP address format"
    
    elif ioc_type.lower() == "domain":
        domain_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}$'
        if not re.match(domain_pattern, ioc_value):
            return False, "Invalid domain format"
    
    elif ioc_type.lower() == "url":
        if not validate_url(ioc_value):
            return False, "Invalid URL format"
    
    elif ioc_type.lower() == "email":
        if not validate_email(ioc_value):
            return False, "Invalid email format"
    
    elif ioc_type.lower() == "hash":
        hash_pattern = r'^[a-fA-F0-9]{32}$|^[a-fA-F0-9]{40}$|^[a-fA-F0-9]{64}$'
        if not re.match(hash_pattern, ioc_value):
            return False, "Invalid hash format (must be MD5, SHA1, or SHA256)"
    
    return True, None









