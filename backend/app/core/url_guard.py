"""Outbound URL validation (SSRF protection) for user-configurable API sources."""

import ipaddress
import socket
from urllib.parse import urlsplit

from app.core.config import get_settings

ALLOWED_SCHEMES = {"http", "https"}


class UnsafeURLError(ValueError):
    """Raised when an outbound URL targets a forbidden destination."""


def _is_forbidden_ip(ip: ipaddress._BaseAddress) -> bool:
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
        or (isinstance(ip, ipaddress.IPv4Address) and ip in ipaddress.ip_network("100.64.0.0/10"))
    )


def validate_outbound_url(url: str) -> str:
    """Validate that ``url`` is an http(s) URL pointing to a public address.

    Every resolved address must be public unless ALLOW_PRIVATE_API_TARGETS is enabled.
    Returns the URL unchanged when valid, raises :class:`UnsafeURLError` otherwise.

    Note: this does not fully prevent DNS rebinding between validation and connect;
    it blocks the common SSRF primitives (internal hosts, cloud metadata, redirects).
    """
    parts = urlsplit(url)
    if parts.scheme.lower() not in ALLOWED_SCHEMES:
        raise UnsafeURLError(f"Unsupported URL scheme: {parts.scheme or '(none)'}")
    if not parts.hostname:
        raise UnsafeURLError("URL has no host")
    if parts.username or parts.password:
        raise UnsafeURLError("Credentials in URL are not allowed")

    if get_settings().allow_private_api_targets:
        return url

    host = parts.hostname
    try:
        port = parts.port or (443 if parts.scheme.lower() == "https" else 80)
    except ValueError as exc:
        raise UnsafeURLError("Invalid port") from exc

    try:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise UnsafeURLError(f"Cannot resolve host: {host}") from exc

    for info in infos:
        ip = ipaddress.ip_address(info[4][0].split("%", 1)[0])
        if _is_forbidden_ip(ip):
            raise UnsafeURLError(f"Destination {host} resolves to a non-public address")
    return url
