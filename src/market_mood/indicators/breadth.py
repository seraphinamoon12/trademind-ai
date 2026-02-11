"""Market breadth indicator."""
from typing import Optional, Dict, Any, Literal
from datetime import datetime

from src.market_mood.models import IndicatorType, IndicatorValue
from src.market_mood.data_providers import YahooFinanceProvider


class MarketBreadthIndicator:
    """Market breadth indicator for market participation assessment."""

    def __init__(self, provider: Optional[YahooFinanceProvider] = None):
        """Initialize market breadth indicator.

        Args:
            provider: YahooFinanceProvider instance. If None, creates new instance.
        """
        self.provider = provider or YahooFinanceProvider()
        self.indicator_type = IndicatorType.MARKET_BREADTH

    def calculate(self) -> Optional[Dict[str, Any]]:
        """Calculate market breadth score (-100 to +100).

        Returns:
            Dictionary with score, trend, and metadata, or None if calculation fails
        """
        indicator_value = self.provider.fetch_with_retry(self.indicator_type)

        if indicator_value is None:
            return None

        breadth_score = indicator_value.value

        # Convert 0-100 breadth score to -100 to +100 scale
        # 0 = strong negative (fear), 50 = neutral, 100 = strong positive (greed)
        score = (breadth_score - 50) * 2

        # Determine trend based on price change
        price_change = indicator_value.metadata.get('price_change', 0)
        trend = self._determine_trend(price_change)

        return {
            'score': score,
            'normalized_score': score / 100.0,
            'raw_value': breadth_score,
            'trend': trend,
            'timestamp': indicator_value.timestamp,
            'source': indicator_value.source,
            'metadata': {
                'indicator': 'market_breadth',
                'breadth_data': indicator_value.metadata.get('breadth_data'),
                'price_change': price_change,
                'volume_change': indicator_value.metadata.get('volume_change'),
                'date': indicator_value.metadata.get('date'),
                'interpretation': self._interpret_breadth(breadth_score),
            }
        }

    def _determine_trend(
        self,
        price_change: float
    ) -> Literal['improving', 'declining', 'stable']:
        """Determine if breadth is improving or declining.

        Args:
            price_change: Price change percentage

        Returns:
            Trend direction
        """
        if price_change > 1:
            return 'improving'
        elif price_change < -1:
            return 'declining'
        else:
            return 'stable'

    def _interpret_breadth(self, breadth_score: float) -> str:
        """Interpret breadth score.

        Args:
            breadth_score: Breadth score (0-100)

        Returns:
            Interpretation string
        """
        if breadth_score >= 75:
            return "Very strong breadth - broad market participation (greed)"
        elif breadth_score >= 60:
            return "Strong breadth - healthy market advance (greed)"
        elif breadth_score >= 50:
            return "Moderate breadth - balanced market (neutral)"
        elif breadth_score >= 35:
            return "Weak breadth - selective participation (fear)"
        elif breadth_score >= 20:
            return "Poor breadth - market decline (fear)"
        else:
            return "Very poor breadth - market stress (extreme fear)"
