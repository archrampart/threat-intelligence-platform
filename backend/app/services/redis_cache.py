"""Redis cache service for CVE and IOC data."""

import json
from datetime import timedelta
from typing import Optional

import redis
from loguru import logger

from app.core.config import get_settings

settings = get_settings()

# Global Redis client instance
_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> Optional[redis.Redis]:
    """Get or create Redis client instance."""
    global _redis_client

    if not settings.redis_enabled:
        return None

    if _redis_client is None:
        try:
            _redis_client = redis.from_url(
                settings.redis_url or "redis://localhost:6379/0",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            # Test connection
            _redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Falling back to in-memory cache.")
            _redis_client = None

    return _redis_client


class RedisCache:
    """Redis cache wrapper for CVE and IOC data."""

    def __init__(self, default_ttl: int = 3600) -> None:
        """Initialize Redis cache with default TTL in seconds."""
        self.default_ttl = default_ttl
        self.client = get_redis_client()

    def get(self, key: str) -> Optional[dict]:
        """Get value from cache."""
        if not self.client:
            return None

        try:
            value = self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.warning(f"Redis get error for key {key}: {e}")
            return None

    def set(self, key: str, value: dict, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL."""
        if not self.client:
            return False

        try:
            ttl = ttl or self.default_ttl
            serialized = json.dumps(value, default=str)
            self.client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.warning(f"Redis set error for key {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self.client:
            return False

        try:
            self.client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Redis delete error for key {key}: {e}")
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if not self.client:
            return False

        try:
            return bool(self.client.exists(key))
        except Exception as e:
            logger.warning(f"Redis exists error for key {key}: {e}")
            return False

    def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern."""
        if not self.client:
            return 0

        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"Redis clear_pattern error for pattern {pattern}: {e}")
            return 0


# Global Redis cache instance
redis_cache = RedisCache(default_ttl=3600)  # 1 hour default TTL











