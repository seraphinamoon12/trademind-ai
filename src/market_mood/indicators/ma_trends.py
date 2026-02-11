"""Moving Average Trends indicator."""
from typing import Optional, Dict, Any, Literal, List
from datetime import datetime

from src.market_mood.models import IndicatorType, IndicatorValue
from src.market_mood.data_providers import YahooFinanceProvider


class MATrendsIndicator:
    """Moving Average Trends indicator for trend analysis."""

    def __init__(
        self,
        provider: Optional[YahooFinanceProvider] = None,
        symbols: Optional[List[str]] = None
    ):
        """Initialize MA trends indicator.

        Args:
            provider: YahooFinanceProvider instance. If None, creates new instance.
            symbols: List of symbols to analyze. If None, uses default market index.
        """
        self.provider = provider or YahooFinanceProvider()
        self.symbols = symbols
        self.indicator_type = IndicatorType.MA_TRENDS

    def calculate(self) -> Optional[Dict[str, Any]]:
        """Calculate MA trends score (-100 to +100).

        Returns:
            Dictionary with score, trend, and metadata, or None if calculation fails
        """
        indicator_value = self.provider.fetch_with_retry(
            self.indicator_type,
            symbols=self.symbols
        )

        if indicator_value is None:
            return None

        ma_score = indicator_value.value

        # Convert 0-100 MA score to -100 to +100 scale
        # 0 = bearish (fear), 50 = neutral, 100 = bullish (greed)
        score = (ma_score - 50) * 2

        # Determine trend from slopes
        trend_data = indicator_value.metadata.get('trend_data', {})
        trend = self._determine_trend(trend_data)

        return {
            'score': score,
            'normalized_score': score / 100.0,
            'raw_value': ma_score,
            'trend': trend,
            'timestamp': indicator_value.timestamp,
            'source': indicator_value.source,
            'metadata': {
                'indicator': 'ma_trends',
                'trend_data': trend_data,
                'symbols_analyzed': indicator_value.metadata.get('symbols_analyzed'),
                'interpretation': self._interpret_ma(ma_score),
            }
        }

    def _determine_trend(
        self,
        trend_data: Dict[str, Any]
    ) -> Literal['improving', 'declining', 'stable']:
        """Determine if MA trend is improving or declining.

        Args:
            trend_data: Trend data dictionary

        Returns:
            Trend direction
        """
        if not trend_data:
            return 'stable'

        total_slope = 0.0
        count = 0

        for symbol, data in trend_data.items():
            ma_data = data.get('ma_data', {})
            ma50_slope = ma_data.get('ma50_slope', 0)
            ma200_slope = ma_data.get('ma200_slope', 0)

            total_slope += (ma50_slope + ma200_slope) / 2
            count += 1

        if count == 0:
            return 'stable'

        avg_slope = total_slope / count

        if avg_slope > 0.5:
            return 'improving'
        elif avg_slope < -0.5:
            return 'declining'
        else:
            return 'stable'

    def _interpret_ma(self, ma_score: float) -> str:
        """Interpret MA trend score.

        Args:
            ma_score: MA trend score (0-100)

        Returns:
            Interpretation string
        """
        if ma_score >= 80:
            return "Strong bullish setup - price above both MAs with positive slopes (greed)"
        elif ma_score >= 65:
            return "Bullish trend - favorable moving average alignment (greed)"
        elif ma_score >= 50:
            return "Neutral trend - mixed moving average signals (neutral)"
        elif ma_score >= 35:
            return "Bearish trend - unfavorable moving average alignment (fear)"
        elif ma_score >= 20:
            return "Weak trend - price below major MAs (fear)"
        else:
            return "Strong bearish setup - price below both MAs with negative slopes (extreme fear)"
