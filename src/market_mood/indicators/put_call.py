"""Put/Call Ratio indicator."""
from typing import Optional, Dict, Any, Literal
from datetime import datetime

from src.market_mood.models import IndicatorType, IndicatorValue
from src.market_mood.data_providers import YahooFinanceProvider


class PutCallRatioIndicator:
    """Put/Call Ratio indicator for sentiment assessment."""

    def __init__(self, provider: Optional[YahooFinanceProvider] = None):
        """Initialize Put/Call ratio indicator.

        Args:
            provider: YahooFinanceProvider instance. If None, creates new instance.
        """
        self.provider = provider or YahooFinanceProvider()
        self.indicator_type = IndicatorType.PUT_CALL_RATIO

    def calculate(self) -> Optional[Dict[str, Any]]:
        """Calculate Put/Call ratio score (-100 to +100).

        Returns:
            Dictionary with score, trend, and metadata, or None if calculation fails
        """
        indicator_value = self.provider.fetch_with_retry(self.indicator_type)

        if indicator_value is None:
            return None

        pcr_value = indicator_value.value

        # Normalize PCR to -100 to +100 scale
        # Low PCR (< 0.7) = bullish (puts less than calls) = positive score (greed)
        # High PCR (> 1.3) = bearish (puts more than calls) = negative score (fear)
        # Normal range (0.7-1.3) = neutral around 0
        if pcr_value <= 0.5:
            score = 80.0
        elif pcr_value <= 0.7:
            score = 50.0
        elif pcr_value <= 0.9:
            score = 20.0
        elif pcr_value <= 1.1:
            score = -10.0
        elif pcr_value <= 1.3:
            score = -40.0
        elif pcr_value <= 1.8:
            score = -70.0
        else:
            score = -90.0

        trend = 'stable'

        return {
            'score': score,
            'normalized_score': score / 100.0,
            'raw_value': pcr_value,
            'trend': trend,
            'timestamp': indicator_value.timestamp,
            'source': indicator_value.source,
            'metadata': {
                'indicator': 'put_call_ratio',
                'volatility': indicator_value.metadata.get('volatility'),
                'date': indicator_value.metadata.get('date'),
                'estimated': indicator_value.metadata.get('estimated'),
                'interpretation': self._interpret_pcr(pcr_value),
            }
        }

    def _interpret_pcr(self, pcr_value: float) -> str:
        """Interpret Put/Call ratio.

        Args:
            pcr_value: Put/Call ratio

        Returns:
            Interpretation string
        """
        if pcr_value <= 0.5:
            return "Very low PCR - extreme bullishness (greed)"
        elif pcr_value <= 0.7:
            return "Low PCR - bullish sentiment (greed)"
        elif pcr_value <= 0.9:
            return "Slightly low PCR - mild bullishness (slight greed)"
        elif pcr_value <= 1.1:
            return "Normal PCR - balanced sentiment (neutral)"
        elif pcr_value <= 1.3:
            return "Slightly high PCR - mild bearishness (slight fear)"
        elif pcr_value <= 1.8:
            return "High PCR - bearish sentiment (fear)"
        else:
            return "Very high PCR - extreme bearishness (extreme fear)"
