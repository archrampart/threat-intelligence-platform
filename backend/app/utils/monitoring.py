"""Monitoring and metrics utilities."""

from datetime import datetime, timezone
from typing import Dict, Optional
from collections import defaultdict
import time

from loguru import logger


class MetricsCollector:
    """Simple in-memory metrics collector."""

    def __init__(self):
        self.request_counts: Dict[str, int] = defaultdict(int)
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.response_times: Dict[str, list[float]] = defaultdict(list)
        self.api_call_counts: Dict[str, int] = defaultdict(int)
        self.start_time = datetime.now(timezone.utc)

    def record_request(self, endpoint: str, method: str, status_code: int, response_time: float):
        """Record a request metric."""
        key = f"{method} {endpoint}"
        self.request_counts[key] += 1
        
        if status_code >= 400:
            self.error_counts[key] += 1
        
        # Keep only last 100 response times per endpoint
        if len(self.response_times[key]) >= 100:
            self.response_times[key] = self.response_times[key][-99:]
        self.response_times[key].append(response_time)

    def record_api_call(self, api_name: str, success: bool = True):
        """Record an external API call."""
        self.api_call_counts[api_name] += 1
        if not success:
            self.error_counts[f"api_{api_name}"] += 1

    def get_metrics(self) -> Dict:
        """Get current metrics."""
        avg_response_times = {
            key: sum(times) / len(times) if times else 0
            for key, times in self.response_times.items()
        }
        
        return {
            "uptime_seconds": (datetime.now(timezone.utc) - self.start_time).total_seconds(),
            "start_time": self.start_time.isoformat(),
            "request_counts": dict(self.request_counts),
            "error_counts": dict(self.error_counts),
            "average_response_times": avg_response_times,
            "api_call_counts": dict(self.api_call_counts),
        }

    def reset(self):
        """Reset all metrics."""
        self.request_counts.clear()
        self.error_counts.clear()
        self.response_times.clear()
        self.api_call_counts.clear()
        self.start_time = datetime.now(timezone.utc)


# Global metrics collector instance
metrics_collector = MetricsCollector()


class RequestTimer:
    """Context manager for timing requests."""

    def __init__(self, endpoint: str, method: str):
        self.endpoint = endpoint
        self.method = method
        self.start_time: Optional[float] = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            response_time = time.time() - self.start_time
            status_code = 500 if exc_type else 200
            metrics_collector.record_request(self.endpoint, self.method, status_code, response_time)
        return False









