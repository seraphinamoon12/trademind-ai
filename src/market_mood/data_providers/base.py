"""Base data provider interface for market mood indicators."""
from abc import ABC, abstractmethod
from typing import Optional, Any, Dict
import logging
from src.core.resilience import CircuitBreaker
from src.market_mood.exceptions import DataProviderError, CircuitBreakerError
from src.market_mood.models import IndicatorType, IndicatorValue
from src.market_mood.config import MarketMoodConfig

logger = logging.getLogger(__name__)


class BaseDataProvider(ABC):
    """Abstract base class for all market mood data providers."""

    def __init__(self, config: Optional[MarketMoodConfig] = None):
        """Initialize the data provider.
        
        Args:
            config: MarketMoodConfig instance. If None, uses default config.
        """
        self.config = config or MarketMoodConfig()
        self.source = self.__class__.__name__.replace("Provider", "").lower()
        
        # Circuit breaker for API reliability
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=self.config.circuit_breaker_failure_threshold,
            recovery_timeout=self.config.circuit_breaker_cooldown_seconds,
            mode="api"
        ) if self.config.circuit_breaker_enabled else None

    @abstractmethod
    def fetch(self, indicator_type: IndicatorType, **kwargs) -> Optional[IndicatorValue]:
        """Fetch indicator data.
        
        Args:
            indicator_type: Type of indicator to fetch
            **kwargs: Additional parameters for the specific indicator
            
        Returns:
            IndicatorValue if successful, None otherwise
        """
        pass

    def get_cache_key(self, indicator_type: IndicatorType, **kwargs) -> str:
        """Generate cache key for the indicator.
        
        Args:
            indicator_type: Type of indicator
            **kwargs: Additional parameters
            
        Returns:
            Cache key string
        """
        parts = ["market_mood", self.source, indicator_type.value]
        for k, v in sorted(kwargs.items()):
            parts.append(f"{k}={v}")
        return ":".join(parts)

    def get_cache_ttl(self, indicator_type: IndicatorType) -> int:
        """Get cache TTL for a specific indicator type.
        
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

    def _check_circuit_breaker(self) -> None:
        """Check if circuit breaker allows execution.
        
        Raises:
            CircuitBreakerError: If circuit breaker is open
        """
        if self.circuit_breaker and not self.circuit_breaker.can_execute():
            raise CircuitBreakerError(
                f"Circuit breaker is open for {self.source}. "
                f"Wait {self.config.circuit_breaker_cooldown_seconds} seconds before retrying."
            )

    def _record_success(self) -> None:
        """Record successful API operation."""
        if self.circuit_breaker:
            self.circuit_breaker.record_success()

    def _record_failure(self) -> None:
        """Record failed API operation."""
        if self.circuit_breaker:
            self.circuit_breaker.record_failure()

    def fetch_with_retry(
        self,
        indicator_type: IndicatorType,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        **kwargs
    ) -> Optional[IndicatorValue]:
        """Fetch indicator data with retry logic.
        
        Args:
            indicator_type: Type of indicator to fetch
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            **kwargs: Additional parameters
            
        Returns:
            IndicatorValue if successful, None otherwise
        """
        import time
        
        for attempt in range(max_retries):
            try:
                self._check_circuit_breaker()
                
                result = self.fetch(indicator_type, **kwargs)
                
                if result is not None:
                    self._record_success()
                    return result
                
                logger.warning(
                    f"Attempt {attempt + 1}/{max_retries}: "
                    f"Failed to fetch {indicator_type} from {self.source}"
                )
                
            except CircuitBreakerError as e:
                logger.error(f"Circuit breaker open: {e}")
                self._record_failure()
                return None
                
            except DataProviderError as e:
                logger.warning(
                    f"Attempt {attempt + 1}/{max_retries}: "
                    f"Data provider error: {e}"
                )
                self._record_failure()
                
            except Exception as e:
                logger.error(
                    f"Attempt {attempt + 1}/{max_retries}: "
                    f"Unexpected error: {e}"
                )
                self._record_failure()
            
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
        
        return None

    def get_circuit_breaker_status(self) -> Optional[Dict[str, Any]]:
        """Get circuit breaker status.
        
        Returns:
            Dictionary with circuit breaker status or None if disabled
        """
        if self.circuit_breaker:
            return self.circuit_breaker.get_status()
        return None
