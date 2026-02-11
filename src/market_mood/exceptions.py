"""Custom exceptions for market mood module."""


class MarketMoodError(Exception):
    """Base exception for market mood errors."""
    pass


class DataProviderError(MarketMoodError):
    """Exception raised when data provider fails."""
    pass


class CacheError(MarketMoodError):
    """Exception raised when cache operations fail."""
    pass


class RateLimitError(DataProviderError):
    """Exception raised when rate limit is exceeded."""
    pass


class CircuitBreakerError(DataProviderError):
    """Exception raised when circuit breaker is open."""
    pass
