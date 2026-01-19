"""Test utilities and helper functions."""

import pytest
from app.utils.ioc_detector import detect_ioc_type


def test_detect_ioc_type_ip():
    """Test IOC type detection for IP addresses."""
    assert detect_ioc_type("192.168.1.1") == "ip"
    assert detect_ioc_type("10.0.0.1") == "ip"
    assert detect_ioc_type("172.16.0.1") == "ip"
    assert detect_ioc_type("8.8.8.8") == "ip"


def test_detect_ioc_type_domain():
    """Test IOC type detection for domains."""
    assert detect_ioc_type("example.com") == "domain"
    assert detect_ioc_type("subdomain.example.com") == "domain"
    assert detect_ioc_type("test.co.uk") == "domain"


def test_detect_ioc_type_url():
    """Test IOC type detection for URLs."""
    assert detect_ioc_type("https://example.com/path") == "url"
    assert detect_ioc_type("http://example.com") == "url"
    assert detect_ioc_type("ftp://example.com/file.txt") == "url"


def test_detect_ioc_type_hash():
    """Test IOC type detection for hashes."""
    # MD5
    assert detect_ioc_type("d41d8cd98f00b204e9800998ecf8427e") == "hash"
    # SHA1
    assert detect_ioc_type("da39a3ee5e6b4b0d3255bfef95601890afd80709") == "hash"
    # SHA256
    assert detect_ioc_type("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855") == "hash"


def test_detect_ioc_type_email():
    """Test IOC type detection for email addresses."""
    assert detect_ioc_type("test@example.com") == "email"
    assert detect_ioc_type("user.name@domain.co.uk") == "email"


def test_detect_ioc_type_unknown():
    """Test IOC type detection for unknown types."""
    assert detect_ioc_type("random_string") == "unknown"
    assert detect_ioc_type("12345") == "unknown"
    assert detect_ioc_type("") == "unknown"









