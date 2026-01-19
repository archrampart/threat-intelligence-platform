"""Metrics collection middleware."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from typing import Callable

from app.utils.monitoring import RequestTimer


class MetricsMiddleware(BaseHTTPMiddleware):
    """Collect metrics for all requests."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Collect metrics for request."""
        endpoint = request.url.path
        method = request.method
        
        with RequestTimer(endpoint, method):
            try:
                response = await call_next(request)
                return response
            except Exception as e:
                # Record error
                from app.utils.monitoring import metrics_collector
                metrics_collector.record_request(endpoint, method, 500, 0)
                raise









