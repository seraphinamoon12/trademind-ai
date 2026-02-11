"""Caching layer for market mood indicators."""
from typing import Optional, Any
from datetime import datetime, timedelta
import logging
from src.core.cache import cache as global_cache
from src.market_mood.models import IndicatorType
from src.market_mood.config import MarketMoodConfig
from src.market_mood.exceptions import CacheError

logger = logging.getLogger(__name__)


class MarketMoodCache:
    """Cache manager for market mood indicators."""

    def __init__(
        self,
        config: Optional[MarketMoodConfig] = None,
        cache_client=None
    ):
        """Initialize the cache manager.
        
        Args:
            config: MarketMoodConfig instance. If None, uses default config.
            cache_client: Custom cache client. If None, uses global cache.
        """
        self.config = config or MarketMoodConfig()
        self.cache = cache_client or global_cache

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        try:
            return self.cache.get(key)
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        indicator_type: Optional[IndicatorType] = None
    ) -> bool:
        """Set value in cache with TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds. If None, uses default for indicator_type
            indicator_type: Indicator type to determine default TTL
            
        Returns:
            True if successful, False otherwise
        """
        if ttl is None and indicator_type is not None:
            ttl = self.get_default_ttl(indicator_type)
        elif ttl is None:
            ttl = 300  # Default 5 minutes

        try:
            return self.cache.set(key, value, ttl)
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete key from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if successful, False otherwise
        """
        try:
            return self.cache.delete(key)
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False

    def clear(self, pattern: str = "market_mood:*") -> int:
        """Clear all keys matching pattern.
        
        Args:
            pattern: Pattern to match keys
            
        Returns:
            Number of keys deleted
        """
        try:
            return self.cache.clear_pattern(pattern)
        except Exception as e:
            logger.error(f"Cache clear error for pattern {pattern}: {e}")
            return 0

    def invalidate_indicator(self, indicator_type: IndicatorType) -> int:
        """Invalidate all cache entries for an indicator type.
        
        Args:
            indicator_type: Type of indicator to invalidate
            
        Returns:
            Number of keys deleted
        """
        pattern = f"market_mood:*:{indicator_type.value}"
        return self.clear(pattern)

    def invalidate_source(self, source: str) -> int:
        """Invalidate all cache entries for a data source.
        
        Args:
            source: Data source name
            
        Returns:
            Number of keys deleted
        """
        pattern = f"market_mood:{source}:*"
        return self.clear(pattern)

    def get_default_ttl(self, indicator_type: IndicatorType) -> int:
        """Get default TTL for an indicator type.
        
        Args:
            indicator_type: Type of indicator
            
        Returns:
            TTL in seconds
        """
        ttl_map = {
            IndicatorType.VIX: self.config.vix_cache_ttl,
            IndicatorType.MARKET_BREADTH: self.config.breadth_cache_ttl,
            IndicatorType.PUT_CALL_RATIO: self.config.put_call_cache_ttl,
            IndicatorType.MA_TRENDS: self.config.ma_trends_cache_ttl,
            IndicatorType.FEAR_GREED: self.config.fear_greed_cache_ttl,
            IndicatorType.DXY: self.config.dxy_cache_ttl,
            IndicatorType.CREDIT_SPREADS: self.config.credit_spreads_cache_ttl,
            IndicatorType.YIELD_CURVE: self.config.yield_curve_cache_ttl,
        }
        return ttl_map.get(indicator_type, 300)

    def get_or_fetch(
        self,
        key: str,
        fetch_func,
        ttl: Optional[int] = None,
        indicator_type: Optional[IndicatorType] = None
    ) -> Optional[Any]:
        """Get value from cache or fetch using provided function.
        
        Args:
            key: Cache key
            fetch_func: Function to fetch data if not cached
            ttl: Time-to-live in seconds
            indicator_type: Indicator type for default TTL
            
        Returns:
            Cached or fetched value
        """
        cached = self.get(key)
        if cached is not None:
            return cached

        try:
            value = fetch_func()
            if value is not None:
                self.set(key, value, ttl, indicator_type)
            return value
        except Exception as e:
            logger.error(f"Error in get_or_fetch for key {key}: {e}")
            return None


# Global cache instance
market_mood_cache = MarketMoodCache()
