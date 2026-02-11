"""Credit Spreads indicator."""
from typing import Optional, Dict, Any, Literal
from datetime import datetime

from src.market_mood.models import IndicatorType, IndicatorValue
from src.market_mood.data_providers import FREDProvider


class CreditSpreadsIndicator:
    """Credit Spreads indicator for credit risk assessment."""

    def __init__(self, provider: Optional[FREDProvider] = None):
        """Initialize Credit Spreads indicator.

        Args:
            provider: FREDProvider instance. If None, creates new instance.
        """
        self.provider = provider or FREDProvider()
        self.indicator_type = IndicatorType.CREDIT_SPREADS

    def calculate(self) -> Optional[Dict[str, Any]]:
        """Calculate credit spreads score (-100 to +100).

        Returns:
            Dictionary with score, trend, and metadata, or None if calculation fails
        """
        indicator_value = self.provider.fetch_with_retry(self.indicator_type)

        if indicator_value is None:
            return None

        credit_score = indicator_value.value

        # Convert 0-100 credit score to -100 to +100 scale
        # 0 = wide spreads (high risk = fear), 100 = tight spreads (low risk = greed)
        score = (credit_score - 50) * 2

        trend = 'stable'

        return {
            'score': score,
            'normalized_score': score / 100.0,
            'raw_value': credit_score,
            'trend': trend,
            'timestamp': indicator_value.timestamp,
            'source': indicator_value.source,
            'metadata': {
                'indicator': 'credit_spreads',
                'spread_data': indicator_value.metadata.get('spread_data'),
                'aaa_yield': indicator_value.metadata.get('aaa_yield'),
                'baa_yield': indicator_value.metadata.get('baa_yield'),
                'date': indicator_value.metadata.get('date'),
                'interpretation': self._interpret_credit(credit_score),
            }
        }

    def _interpret_credit(self, credit_score: float) -> str:
        """Interpret credit spread score.

        Args:
            credit_score: Credit spread score (0-100)

        Returns:
            Interpretation string
        """
        if credit_score >= 75:
            return "Very tight spreads - high confidence (greed)"
        elif credit_score >= 60:
            return "Tight spreads - healthy credit markets (greed)"
        elif credit_score >= 40:
            return "Moderate spreads - normal conditions (neutral)"
        elif credit_score >= 25:
            return "Wide spreads - credit concerns (fear)"
        else:
            return "Very wide spreads - credit stress (extreme fear)"
