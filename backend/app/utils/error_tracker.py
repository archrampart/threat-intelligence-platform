"""Error tracking utilities."""

from typing import Optional, Dict, Any
from datetime import datetime, timezone
from loguru import logger
import traceback


class ErrorTracker:
    """Simple error tracker for logging and monitoring."""

    def __init__(self):
        self.error_log: list[Dict[str, Any]] = []
        self.max_log_size = 100  # Keep last 100 errors

    def log_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        severity: str = "error",
    ):
        """Log an error with context."""
        error_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc(),
            "severity": severity,
            "context": context or {},
        }

        # Log to loguru
        logger.error(
            f"Error: {error_entry['error_type']} - {error_entry['error_message']}",
            context=context,
        )

        # Store in memory log
        self.error_log.append(error_entry)
        if len(self.error_log) > self.max_log_size:
            self.error_log.pop(0)

        return error_entry

    def get_recent_errors(self, limit: int = 10) -> list[Dict[str, Any]]:
        """Get recent errors."""
        return self.error_log[-limit:]

    def get_error_stats(self) -> Dict[str, int]:
        """Get error statistics."""
        stats = {}
        for error in self.error_log:
            error_type = error["error_type"]
            stats[error_type] = stats.get(error_type, 0) + 1
        return stats


# Global error tracker instance
error_tracker = ErrorTracker()









