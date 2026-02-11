"""Configuration settings for market mood detection."""
from pydantic_settings import BaseSettings
from typing import Optional


class MarketMoodConfig(BaseSettings):
    """Market Mood configuration settings."""

    # Cache TTL settings (in seconds)
    vix_cache_ttl: int = 300  # 5 minutes
    breadth_cache_ttl: int = 300  # 5 minutes
    put_call_cache_ttl: int = 300  # 5 minutes
    ma_trends_cache_ttl: int = 3600  # 1 hour
    fear_greed_cache_ttl: int = 1800  # 30 minutes
    dxy_cache_ttl: int = 3600  # 1 hour
    credit_spreads_cache_ttl: int = 3600  # 1 hour
    yield_curve_cache_ttl: int = 3600  # 1 hour

    # FRED API settings
    fred_api_key: Optional[str] = None

    # Circuit breaker settings
    circuit_breaker_enabled: bool = True
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_cooldown_seconds: int = 60

    # Rate limiting settings
    yahoo_rate_limit_delay: float = 0.1  # seconds between requests
    fred_rate_limit_delay: float = 0.5  # seconds between requests

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
