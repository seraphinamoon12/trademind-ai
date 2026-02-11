"""VIX (CBOE Volatility Index) indicator."""
from typing import Optional, Dict, Any, Literal
from datetime import datetime

from src.market_mood.models import IndicatorType, IndicatorValue
from src.market_mood.data_providers import YahooFinanceProvider


class VIXIndicator:
    """VIX indicator for market volatility assessment."""

    def __init__(self, provider: Optional[YahooFinanceProvider] = None):
        """Initialize VIX indicator.

        Args:
            provider: YahooFinanceProvider instance. If None, creates new instance.
        """
        self.provider = provider or YahooFinanceProvider()
        self.indicator_type = IndicatorType.VIX

    def calculate(self) -> Optional[Dict[str, Any]]:
        """Calculate VIX score (-100 to +100).

        Returns:
            Dictionary with score, trend, and metadata, or None if calculation fails
        """
        indicator_value = self.provider.fetch_with_retry(self.indicator_type)

        if indicator_value is None:
            return None

        vix_value = indicator_value.value

        # Normalize VIX to -100 to +100 scale
        # Low VIX (< 15) = calm/greed = positive score
        # High VIX (> 30) = fearful = negative score
        # Normal range (15-30) = neutral around 0
        if vix_value <= 12:
            score = 80.0
        elif vix_value <= 15:
            score = 50.0
        elif vix_value <= 20:
            score = 20.0
        elif vix_value <= 25:
            score = -10.0
        elif vix_value <= 30:
            score = -40.0
        elif vix_value <= 40:
            score = -70.0
        else:
            score = -90.0

        # Determine trend
        previous = indicator_value.metadata.get('previous')
        trend = self._determine_trend(vix_value, previous)

        return {
            'score': score,
            'normalized_score': score / 100.0,
            'raw_value': vix_value,
            'trend': trend,
            'timestamp': indicator_value.timestamp,
            'source': indicator_value.source,
            'metadata': {
                'indicator': 'vix',
                'previous': previous,
                'date': indicator_value.metadata.get('date'),
                'interpretation': self._interpret_vix(vix_value),
            }
        }

    def _determine_trend(
        self,
        current: float,
        previous: Optional[float]
    ) -> Literal['improving', 'declining', 'stable']:
        """Determine if volatility is improving (decreasing) or declining (increasing).

        Args:
            current: Current VIX value
            previous: Previous VIX value

        Returns:
            Trend direction
        """
        if previous is None:
            return 'stable'

        change_pct = (current - previous) / previous * 100

        if change_pct > 5:
            return 'declining'
        elif change_pct < -5:
            return 'improving'
        else:
            return 'stable'

    def _interpret_vix(self, vix_value: float) -> str:
        """Interpret VIX level.

        Args:
            vix_value: VIX value

        Returns:
            Interpretation string
        """
        if vix_value <= 12:
            return "Extremely low volatility - market complacency (greed)"
        elif vix_value <= 15:
            return "Low volatility - market calm (slight greed)"
        elif vix_value <= 20:
            return "Normal volatility - neutral market"
        elif vix_value <= 25:
            return "Elevated volatility - some concern (slight fear)"
        elif vix_value <= 30:
            return "High volatility - market anxiety (fear)"
        elif vix_value <= 40:
            return "Very high volatility - market panic (extreme fear)"
        else:
            return "Extreme volatility - market crisis (max fear)"
