"""Rate limiting middleware for API endpoints."""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Callable

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.config import get_settings

settings = get_settings()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware to prevent API abuse."""

    def __init__(self, app, requests_per_minute: int = 60, requests_per_hour: int = 1000):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        # Store request counts per IP
        self.request_counts: dict[str, list[datetime]] = defaultdict(list)
        # Cleanup old entries periodically
        self._last_cleanup = datetime.now()

    def _cleanup_old_entries(self):
        """Remove old request timestamps to prevent memory leaks."""
        now = datetime.now()
        if (now - self._last_cleanup).seconds < 60:
            return  # Only cleanup once per minute

        cutoff_minute = now - timedelta(minutes=1)
        cutoff_hour = now - timedelta(hours=1)

        for ip in list(self.request_counts.keys()):
            # Keep only recent requests
            self.request_counts[ip] = [
                ts for ts in self.request_counts[ip]
                if ts > cutoff_hour
            ]
            # Remove empty entries
            if not self.request_counts[ip]:
                del self.request_counts[ip]

        self._last_cleanup = now

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request."""
        # Check for forwarded IP (when behind proxy)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting."""
        # Skip rate limiting for health checks, docs, and auth endpoints
        skip_paths = [
            "/api/v1/health",
            "/api/v1/auth/login",
            "/docs",
            "/openapi.json",
            "/redoc",
        ]
        if request.url.path in skip_paths:
            return await call_next(request)

        # Cleanup old entries periodically
        self._cleanup_old_entries()

        # Get client IP
        client_ip = self._get_client_ip(request)
        now = datetime.now()

        # Get request history for this IP
        request_history = self.request_counts[client_ip]

        # Remove requests older than 1 hour
        cutoff_hour = now - timedelta(hours=1)
        request_history[:] = [ts for ts in request_history if ts > cutoff_hour]

        # Check minute limit
        cutoff_minute = now - timedelta(minutes=1)
        recent_requests = [ts for ts in request_history if ts > cutoff_minute]
        if len(recent_requests) >= self.requests_per_minute:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded: {self.requests_per_minute} requests per minute",
                headers={"Retry-After": "60"},
            )

        # Check hour limit
        if len(request_history) >= self.requests_per_hour:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded: {self.requests_per_hour} requests per hour",
                headers={"Retry-After": "3600"},
            )

        # Record this request
        request_history.append(now)

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        remaining_minute = max(0, self.requests_per_minute - len(recent_requests) - 1)
        remaining_hour = max(0, self.requests_per_hour - len(request_history))
        response.headers["X-RateLimit-Limit-Minute"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining-Minute"] = str(remaining_minute)
        response.headers["X-RateLimit-Limit-Hour"] = str(self.requests_per_hour)
        response.headers["X-RateLimit-Remaining-Hour"] = str(remaining_hour)

        return response

