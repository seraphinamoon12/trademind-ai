"""Circuit Breaker - Global trading halt mechanism.

This module provides a trading-specific circuit breaker interface backed by the unified
implementation in src.core.resilience.
"""
from src.core.resilience import CircuitBreaker as UnifiedCircuitBreaker

logger = __import__('logging').getLogger(__name__)


class CircuitBreaker(UnifiedCircuitBreaker):
    """
    Global circuit breaker for trading system.

    Implements tiered drawdown protection:
    - Warning at -10% drawdown
    - Halt at -15% drawdown
    - Daily loss limit at -3%
    - Consecutive loss limit (5 losses)

    This class extends UnifiedCircuitBreaker with trading-specific functionality.
    """

    def __init__(self):
        """Initialize trading circuit breaker with default thresholds."""
        super().__init__(
            failure_threshold=100,  # High threshold for trading operations
            recovery_timeout=86400,  # 24 hours recovery time
            mode="trading"
        )


# Global circuit breaker instance
circuit_breaker = CircuitBreaker()
