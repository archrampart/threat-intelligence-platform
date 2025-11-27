"""Error handling middleware."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from loguru import logger

from app.utils.error_tracker import error_tracker


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Global error handler middleware."""

    async def dispatch(self, request: Request, call_next):
        """Handle errors globally."""
        try:
            response = await call_next(request)
            return response
        except RequestValidationError as e:
            # Validation errors
            error_tracker.log_error(e, {"path": request.url.path, "method": request.method}, "warning")
            return JSONResponse(
                status_code=422,
                content={"detail": "Validation error", "errors": e.errors()},
            )
        except HTTPException as e:
            # HTTP exceptions
            if e.status_code >= 500:
                error_tracker.log_error(e, {"path": request.url.path, "method": request.method}, "error")
            return JSONResponse(
                status_code=e.status_code,
                content={"detail": e.detail},
            )
        except StarletteHTTPException as e:
            # Starlette HTTP exceptions
            return JSONResponse(
                status_code=e.status_code,
                content={"detail": e.detail},
            )
        except Exception as e:
            # Unexpected errors
            error_tracker.log_error(e, {"path": request.url.path, "method": request.method}, "critical")
            logger.exception("Unhandled exception")
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"},
            )









