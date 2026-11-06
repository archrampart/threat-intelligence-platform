"""IOC type detection utility."""

import re
from typing import Optional


def detect_ioc_type(value: str) -> Optional[str]:
    """
    Detect IOC type from value.
    
    Returns: 'ip', 'domain', 'url', 'hash', or None
    """
    if not value or not isinstance(value, str):
        return "unknown"
    
    value = value.strip()
    if not value:
        return "unknown"
    
    # Hash detection (MD5, SHA1, SHA256)
    # MD5: 32 hex chars
    # SHA1: 40 hex chars
    # SHA256: 64 hex chars
    hash_pattern = re.compile(r'^[a-fA-F0-9]{32}$|^[a-fA-F0-9]{40}$|^[a-fA-F0-9]{64}$')
    if hash_pattern.match(value):
        return "hash"
    
    # URL detection (starts with http://, https://, or ftp://)
    if value.startswith(('http://', 'https://', 'ftp://')):
        return "url"
    
    # IP address detection (IPv4)
    ipv4_pattern = re.compile(
        r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    )
    if ipv4_pattern.match(value):
        return "ip"
    
    # IPv6 detection (simplified)
    ipv6_pattern = re.compile(
        r'^(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$|^::1$|^::$'
    )
    if ipv6_pattern.match(value):
        return "ip"
    
    # Email detection (contains @ and domain pattern)
    email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}$')
    if email_pattern.match(value):
        return "email"
    
    # Domain detection (contains dots, no spaces, valid domain chars)
    # This is a simplified check - assumes if it's not IP/URL/Hash/Email and has valid domain chars, it's a domain
    domain_pattern = re.compile(r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}$')
    if domain_pattern.match(value):
        return "domain"
    
    # If nothing matches, return "unknown" instead of None
    return "unknown"



