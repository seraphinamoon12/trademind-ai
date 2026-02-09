"""Redis cache utilities and cache key generation helpers."""
import json
import pickle
from typing import Any, Optional
from datetime import datetime, timezone
import hashlib
import redis
from src.config import settings


class Cache:
    """Redis cache wrapper."""

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or settings.redis_url
        self.client = redis.from_url(self.redis_url)

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            data = self.client.get(key)
            if data:
                return pickle.loads(data)
            return None
        except Exception as e:
            print(f"Cache get error: {e}")
            return None

    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in cache with TTL (seconds)."""
        try:
            data = pickle.dumps(value)
            self.client.setex(key, ttl, data)
            return True
        except Exception as e:
            print(f"Cache set error: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            self.client.delete(key)
            return True
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False

    def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern."""
        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            print(f"Cache clear error: {e}")
            return 0


# Global cache instance
cache = Cache()


def generate_cache_key(prefix: str, *args, **kwargs) -> str:
    """Generate a consistent cache key.

    Args:
        prefix: Prefix for the key (e.g., 'symbol', 'indicator')
        *args: Positional arguments to include in the key
        **kwargs: Keyword arguments to include in the key

    Returns:
        A string cache key
    """
    key_parts = [prefix]

    for arg in args:
        key_parts.append(str(arg))

    for k, v in sorted(kwargs.items()):
        key_parts.append(f"{k}={v}")

    return ":".join(key_parts)


def generate_symbol_key(symbol: str, timeframe: str = '1d', indicator: str = None) -> str:
    """Generate cache key for symbol-based data.

    Args:
        symbol: Stock symbol
        timeframe: Timeframe (e.g., '1d', '1h', '5m')
        indicator: Optional indicator name

    Returns:
        A cache key string

    Examples:
        >>> generate_symbol_key('AAPL', '1d')
        'AAPL:1d'
        >>> generate_symbol_key('AAPL', '1h', 'RSI')
        'AAPL:1h:RSI'
    """
    parts = [symbol, timeframe]
    if indicator:
        parts.append(indicator)
    return ":".join(parts)


def generate_daily_symbol_key(symbol: str, suffix: str = '') -> str:
    """Generate cache key that resets daily (not time-sensitive).

    Useful for data that should be cached for the day but refreshed
    on the next trading day.

    Args:
        symbol: Stock symbol
        suffix: Optional suffix for the key

    Returns:
        A cache key string with date
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    parts = [symbol, today]
    if suffix:
        parts.append(suffix)
    return ":".join(parts)


def generate_hash_key(prefix: str, *args, **kwargs) -> str:
    """Generate a hashed cache key for large inputs.

    Args:
        prefix: Prefix for the key
        *args: Positional arguments to hash
        **kwargs: Keyword arguments to hash

    Returns:
        A short cache key using hash
    """
    key_str = generate_cache_key(prefix, *args, **kwargs)
    hash_value = hashlib.md5(key_str.encode()).hexdigest()[:12]
    return f"{prefix}:{hash_value}"


def generate_data_key(
    source: str,
    symbol: str,
    data_type: str,
    period: str = None,
    **extra_params
) -> str:
    """Generate cache key for market data.

    Args:
        source: Data source (e.g., 'yf', 'ibkr')
        symbol: Stock symbol
        data_type: Type of data (e.g., 'historical', 'price', 'quote')
        period: Optional time period
        **extra_params: Additional parameters

    Returns:
        A cache key string

    Examples:
        >>> generate_data_key('yf', 'AAPL', 'historical', '1y')
        'yf:AAPL:historical:1y'
        >>> generate_data_key('yf', 'AAPL', 'price')
        'yf:AAPL:price'
    """
    parts = [source, symbol, data_type]
    if period:
        parts.append(period)
    for k, v in sorted(extra_params.items()):
        parts.append(f"{k}={v}")
    return ":".join(parts)


def is_cache_valid(
    cache_key: str,
    cache_timestamp: float,
    ttl_seconds: int,
    current_time: float = None
) -> bool:
    """Check if a cached value is still valid.

    Args:
        cache_key: The cache key (for logging)
        cache_timestamp: When the value was cached (timestamp)
        ttl_seconds: Time-to-live in seconds
        current_time: Optional current timestamp (for testing)

    Returns:
        True if cache is valid, False otherwise
    """
    if current_time is None:
        import time
        current_time = time.time()

    age = current_time - cache_timestamp
    is_valid = age < ttl_seconds

    if not is_valid:
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Cache expired for {cache_key}: age={age:.1f}s, ttl={ttl_seconds}s")

    return is_valid


class CacheKeyBuilder:
    """Builder for creating complex cache keys."""

    def __init__(self, prefix: str):
        self.prefix = prefix
        self._parts = [prefix]

    def add(self, value: Any, name: str = None) -> 'CacheKeyBuilder':
        """Add a part to the cache key.

        Args:
            value: Value to add
            name: Optional name for named parts

        Returns:
            Self for chaining
        """
        if name:
            self._parts.append(f"{name}={value}")
        else:
            self._parts.append(str(value))
        return self

    def add_date(self, date: datetime = None, name: str = 'date') -> 'CacheKeyBuilder':
        """Add a date part to the cache key.

        Args:
            date: Date to use (default: today in UTC)
            name: Optional name for the date part

        Returns:
            Self for chaining
        """
        if date is None:
            date = datetime.now(timezone.utc)
        date_str = date.strftime("%Y-%m-%d")
        return self.add(date_str, name)

    def add_hash(self, *args) -> 'CacheKeyBuilder':
        """Add a hashed part to the cache key.

        Args:
            *args: Values to hash

        Returns:
            Self for chaining
        """
        hash_value = hashlib.md5("|".join(str(a) for a in args).encode()).hexdigest()[:12]
        return self.add(hash_value)

    def build(self) -> str:
        """Build the final cache key.

        Returns:
            The cache key string
        """
        return ":".join(self._parts)
