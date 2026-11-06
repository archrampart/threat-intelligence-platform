"""Rate limiting middleware for API endpoints (in-memory, per client IP)."""

import time
from collections import defaultdict, deque
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

_SKIP_PATHS = {"/api/v1/health", "/docs", "/openapi.json", "/redoc"}
_LOGIN_PATHS = {"/api/v1/auth/login", "/api/v1/auth/refresh"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limiter.

    * Generic API limit per minute / per hour.
    * Much stricter per-minute limit for authentication endpoints (brute-force protection).
    * X-Forwarded-For is only honoured when ``trust_proxy_headers`` is enabled, otherwise
      any client could bypass the limiter by sending a random header value.
    """

    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        login_requests_per_minute: int = 10,
        trust_proxy_headers: bool = False,
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.login_requests_per_minute = login_requests_per_minute
        self.trust_proxy_headers = trust_proxy_headers
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._login_hits: dict[str, deque[float]] = defaultdict(deque)
        self._last_cleanup = time.monotonic()

    def _client_ip(self, request: Request) -> str:
        if self.trust_proxy_headers:
            real_ip = request.headers.get("X-Real-IP")
            if real_ip:
                return real_ip.strip()
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                # Right-most entry is the one appended by our own proxy.
                return forwarded.split(",")[-1].strip()
        return request.client.host if request.client else "unknown"

    @staticmethod
    def _prune(bucket: deque[float], cutoff: float) -> None:
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()

    def _cleanup(self, now: float) -> None:
        if now - self._last_cleanup < 60:
            return
        for store, window in ((self._hits, 3600), (self._login_hits, 60)):
            for key in list(store.keys()):
                self._prune(store[key], now - window)
                if not store[key]:
                    del store[key]
        self._last_cleanup = now

    @staticmethod
    def _too_many(detail: str, retry_after: int) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content={"detail": detail},
            headers={"Retry-After": str(retry_after)},
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        if request.method == "OPTIONS" or path in _SKIP_PATHS:
            return await call_next(request)

        now = time.monotonic()
        self._cleanup(now)
        ip = self._client_ip(request)

        if path in _LOGIN_PATHS:
            bucket = self._login_hits[ip]
            self._prune(bucket, now - 60)
            if len(bucket) >= self.login_requests_per_minute:
                return self._too_many("Too many authentication attempts. Try again later.", 60)
            bucket.append(now)

        hits = self._hits[ip]
        self._prune(hits, now - 3600)
        minute_count = sum(1 for ts in hits if ts > now - 60)
        if minute_count >= self.requests_per_minute:
            return self._too_many(f"Rate limit exceeded: {self.requests_per_minute} requests per minute", 60)
        if len(hits) >= self.requests_per_hour:
            return self._too_many(f"Rate limit exceeded: {self.requests_per_hour} requests per hour", 3600)
        hits.append(now)

        response = await call_next(request)
        response.headers["X-RateLimit-Limit-Minute"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining-Minute"] = str(max(0, self.requests_per_minute - minute_count - 1))
        response.headers["X-RateLimit-Limit-Hour"] = str(self.requests_per_hour)
        response.headers["X-RateLimit-Remaining-Hour"] = str(max(0, self.requests_per_hour - len(hits)))
        return response
