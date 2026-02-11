"""Configuration settings for market mood detection."""
from pydantic_settings import BaseSettings
from typing import Optional, Dict


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

    # Indicator weights (should sum to 1.0)
    vix_weight: float = 0.15
    breadth_weight: float = 0.12
    put_call_weight: float = 0.12
    ma_trends_weight: float = 0.15
    fear_greed_weight: float = 0.18
    dxy_weight: float = 0.10
    credit_spreads_weight: float = 0.09
    yield_curve_weight: float = 0.09

    # Mood thresholds for classification (score from -100 to +100)
    extreme_fear_threshold: float = -70.0
    fear_threshold: float = -30.0
    greed_threshold: float = 30.0
    extreme_greed_threshold: float = 70.0

    # Signal generation settings
    enable_signals: bool = True
    signal_confidence_threshold: float = 0.6

    # Trend detection settings
    trend_lookback_days: int = 5
    momentum_threshold: float = 10.0

    # History settings
    history_cache_size: int = 100

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    def get_indicator_weights(self) -> Dict[str, float]:
        """Get all indicator weights as a dictionary.

        Returns:
            Dictionary mapping indicator names to weights
        """
        return {
            'vix': self.vix_weight,
            'breadth': self.breadth_weight,
            'put_call': self.put_call_weight,
            'ma_trends': self.ma_trends_weight,
            'fear_greed': self.fear_greed_weight,
            'dxy': self.dxy_weight,
            'credit_spreads': self.credit_spreads_weight,
            'yield_curve': self.yield_curve_weight,
        }

    def get_total_weight(self) -> float:
        """Get sum of all indicator weights.

        Returns:
            Total weight sum
        """
        return sum(self.get_indicator_weights().values())
