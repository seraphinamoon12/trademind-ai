"""Tests for market mood indicators."""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.market_mood.indicators import (
    VIXIndicator,
    MarketBreadthIndicator,
    PutCallRatioIndicator,
    MATrendsIndicator,
    FearGreedIndicator,
    DXYIndicator,
    CreditSpreadsIndicator,
    YieldCurveIndicator,
)
from src.market_mood.models import IndicatorType, IndicatorValue


@pytest.fixture
def mock_indicator_value():
    """Create a mock indicator value."""
    return IndicatorValue(
        indicator_type=IndicatorType.VIX,
        value=20.0,
        source="test",
        metadata={"previous": 18.0, "date": "2024-01-01"},
    )


class TestVIXIndicator:
    """Tests for VIXIndicator."""

    @pytest.fixture
    def vix_indicator(self):
        """Create VIX indicator."""
        return VIXIndicator()

    def test_calculate_low_vix(self, vix_indicator, mock_indicator_value):
        """Test VIX calculation with low VIX value."""
        mock_indicator_value.value = 10.0
        with patch.object(vix_indicator.provider, 'fetch_with_retry', return_value=mock_indicator_value):
            result = vix_indicator.calculate()

        assert result is not None
        assert result['score'] == 80.0
        assert result['raw_value'] == 10.0
        assert result['trend'] == 'stable'

    def test_calculate_high_vix(self, vix_indicator, mock_indicator_value):
        """Test VIX calculation with high VIX value."""
        mock_indicator_value.value = 35.0
        with patch.object(vix_indicator.provider, 'fetch_with_retry', return_value=mock_indicator_value):
            result = vix_indicator.calculate()

        assert result is not None
        assert result['score'] == -70.0
        assert result['raw_value'] == 35.0

    def test_calculate_normal_vix(self, vix_indicator, mock_indicator_value):
        """Test VIX calculation with normal VIX value."""
        mock_indicator_value.value = 18.0
        with patch.object(vix_indicator.provider, 'fetch_with_retry', return_value=mock_indicator_value):
            result = vix_indicator.calculate()

        assert result is not None
        assert result['score'] == 20.0

    def test_calculate_none_result(self, vix_indicator):
        """Test VIX calculation when provider returns None."""
        with patch.object(vix_indicator.provider, 'fetch_with_retry', return_value=None):
            result = vix_indicator.calculate()

        assert result is None

    def test_trend_improving(self, vix_indicator, mock_indicator_value):
        """Test trend detection for improving (decreasing) VIX."""
        mock_indicator_value.value = 15.0
        mock_indicator_value.metadata['previous'] = 18.0
        with patch.object(vix_indicator.provider, 'fetch_with_retry', return_value=mock_indicator_value):
            result = vix_indicator.calculate()

        assert result['trend'] == 'improving'

    def test_trend_declining(self, vix_indicator, mock_indicator_value):
        """Test trend detection for declining (increasing) VIX."""
        mock_indicator_value.value = 21.0
        mock_indicator_value.metadata['previous'] = 20.0
        with patch.object(vix_indicator.provider, 'fetch_with_retry', return_value=mock_indicator_value):
            result = vix_indicator.calculate()

        assert result['trend'] == 'declining'


class TestMarketBreadthIndicator:
    """Tests for MarketBreadthIndicator."""

    @pytest.fixture
    def breadth_indicator(self):
        """Create market breadth indicator."""
        return MarketBreadthIndicator()

    def test_calculate_high_breadth(self, breadth_indicator, mock_indicator_value):
        """Test breadth calculation with high breadth score."""
        mock_indicator_value.indicator_type = IndicatorType.MARKET_BREADTH
        mock_indicator_value.value = 85.0
        mock_indicator_value.metadata = {'price_change': 2.0, 'date': '2024-01-01'}
        with patch.object(breadth_indicator.provider, 'fetch_with_retry', return_value=mock_indicator_value):
            result = breadth_indicator.calculate()

        assert result is not None
        assert result['score'] == 70.0  # (85 - 50) * 2
        assert result['trend'] == 'improving'

    def test_calculate_low_breadth(self, breadth_indicator, mock_indicator_value):
        """Test breadth calculation with low breadth score."""
        mock_indicator_value.indicator_type = IndicatorType.MARKET_BREADTH
        mock_indicator_value.value = 20.0
        mock_indicator_value.metadata = {'price_change': -3.0, 'date': '2024-01-01'}
        with patch.object(breadth_indicator.provider, 'fetch_with_retry', return_value=mock_indicator_value):
            result = breadth_indicator.calculate()

        assert result is not None
        assert result['score'] == -60.0  # (20 - 50) * 2
        assert result['trend'] == 'declining'


class TestPutCallRatioIndicator:
    """Tests for PutCallRatioIndicator."""

    @pytest.fixture
    def pcr_indicator(self):
        """Create Put/Call ratio indicator."""
        return PutCallRatioIndicator()

    def test_calculate_low_pcr(self, pcr_indicator, mock_indicator_value):
        """Test PCR calculation with low PCR."""
        mock_indicator_value.indicator_type = IndicatorType.PUT_CALL_RATIO
        mock_indicator_value.value = 0.6
        mock_indicator_value.metadata = {'date': '2024-01-01'}
        with patch.object(pcr_indicator.provider, 'fetch_with_retry', return_value=mock_indicator_value):
            result = pcr_indicator.calculate()

        assert result is not None
        assert result['score'] == 50.0

    def test_calculate_high_pcr(self, pcr_indicator, mock_indicator_value):
        """Test PCR calculation with high PCR."""
        mock_indicator_value.indicator_type = IndicatorType.PUT_CALL_RATIO
        mock_indicator_value.value = 1.5
        mock_indicator_value.metadata = {'date': '2024-01-01'}
        with patch.object(pcr_indicator.provider, 'fetch_with_retry', return_value=mock_indicator_value):
            result = pcr_indicator.calculate()

        assert result is not None
        assert result['score'] == -70.0


class TestMATrendsIndicator:
    """Tests for MATrendsIndicator."""

    @pytest.fixture
    def ma_indicator(self):
        """Create MA trends indicator."""
        return MATrendsIndicator()

    def test_calculate_bullish_ma(self, ma_indicator, mock_indicator_value):
        """Test MA calculation with bullish setup."""
        mock_indicator_value.indicator_type = IndicatorType.MA_TRENDS
        mock_indicator_value.value = 80.0
        mock_indicator_value.metadata = {'trend_data': {}, 'date': '2024-01-01'}
        with patch.object(ma_indicator.provider, 'fetch_with_retry', return_value=mock_indicator_value):
            result = ma_indicator.calculate()

        assert result is not None
        assert result['score'] == 60.0  # (80 - 50) * 2

    def test_calculate_bearish_ma(self, ma_indicator, mock_indicator_value):
        """Test MA calculation with bearish setup."""
        mock_indicator_value.indicator_type = IndicatorType.MA_TRENDS
        mock_indicator_value.value = 25.0
        mock_indicator_value.metadata = {'trend_data': {}, 'date': '2024-01-01'}
        with patch.object(ma_indicator.provider, 'fetch_with_retry', return_value=mock_indicator_value):
            result = ma_indicator.calculate()

        assert result is not None
        assert result['score'] == -50.0  # (25 - 50) * 2


class TestFearGreedIndicator:
    """Tests for FearGreedIndicator."""

    @pytest.fixture
    def fg_indicator(self):
        """Create Fear & Greed indicator."""
        return FearGreedIndicator()

    def test_calculate_greed(self, fg_indicator, mock_indicator_value):
        """Test Fear & Greed calculation with greed."""
        mock_indicator_value.indicator_type = IndicatorType.FEAR_GREED
        mock_indicator_value.value = 80.0
        mock_indicator_value.metadata = {'components': {}, 'date': '2024-01-01'}
        with patch.object(fg_indicator.provider, 'fetch_with_retry', return_value=mock_indicator_value):
            result = fg_indicator.calculate()

        assert result is not None
        assert result['score'] == 60.0  # (80 - 50) * 2

    def test_calculate_fear(self, fg_indicator, mock_indicator_value):
        """Test Fear & Greed calculation with fear."""
        mock_indicator_value.indicator_type = IndicatorType.FEAR_GREED
        mock_indicator_value.value = 20.0
        mock_indicator_value.metadata = {'components': {}, 'date': '2024-01-01'}
        with patch.object(fg_indicator.provider, 'fetch_with_retry', return_value=mock_indicator_value):
            result = fg_indicator.calculate()

        assert result is not None
        assert result['score'] == -60.0  # (20 - 50) * 2


class TestDXYIndicator:
    """Tests for DXYIndicator."""

    @pytest.fixture
    def dxy_indicator(self):
        """Create DXY indicator."""
        return DXYIndicator()

    def test_calculate_strong_dxy(self, dxy_indicator, mock_indicator_value):
        """Test DXY calculation with strong DXY."""
        mock_indicator_value.indicator_type = IndicatorType.DXY
        mock_indicator_value.value = 80.0
        mock_indicator_value.metadata = {'dxy_value': 105.0, 'change': 2.0, 'date': '2024-01-01'}
        with patch.object(dxy_indicator.provider, 'fetch_with_retry', return_value=mock_indicator_value):
            result = dxy_indicator.calculate()

        assert result is not None
        assert result['score'] == 60.0  # (80 - 50) * 2
        assert result['trend'] == 'declining'


class TestCreditSpreadsIndicator:
    """Tests for CreditSpreadsIndicator."""

    @pytest.fixture
    def credit_indicator(self):
        """Create credit spreads indicator."""
        return CreditSpreadsIndicator()

    def test_calculate_tight_spreads(self, credit_indicator, mock_indicator_value):
        """Test credit spreads calculation with tight spreads."""
        mock_indicator_value.indicator_type = IndicatorType.CREDIT_SPREADS
        mock_indicator_value.value = 85.0
        mock_indicator_value.metadata = {'spread_data': {}, 'aaa_yield': 4.0, 'baa_yield': 4.5, 'date': '2024-01-01'}
        with patch.object(credit_indicator.provider, 'fetch_with_retry', return_value=mock_indicator_value):
            result = credit_indicator.calculate()

        assert result is not None
        assert result['score'] == 70.0  # (85 - 50) * 2


class TestYieldCurveIndicator:
    """Tests for YieldCurveIndicator."""

    @pytest.fixture
    def yc_indicator(self):
        """Create yield curve indicator."""
        return YieldCurveIndicator()

    def test_calculate_steep_curve(self, yc_indicator, mock_indicator_value):
        """Test yield curve calculation with steep curve."""
        mock_indicator_value.indicator_type = IndicatorType.YIELD_CURVE
        mock_indicator_value.value = 85.0
        mock_indicator_value.metadata = {'yield_curve_data': {}, 'yield_10y': 4.0, 'yield_2y': 2.0, 'date': '2024-01-01'}
        with patch.object(yc_indicator.provider, 'fetch_with_retry', return_value=mock_indicator_value):
            result = yc_indicator.calculate()

        assert result is not None
        assert result['score'] == 70.0  # (85 - 50) * 2

    def test_calculate_inverted_curve(self, yc_indicator, mock_indicator_value):
        """Test yield curve calculation with inverted curve."""
        mock_indicator_value.indicator_type = IndicatorType.YIELD_CURVE
        mock_indicator_value.value = 20.0
        mock_indicator_value.metadata = {'yield_curve_data': {}, 'yield_10y': 3.5, 'yield_2y': 4.0, 'date': '2024-01-01'}
        with patch.object(yc_indicator.provider, 'fetch_with_retry', return_value=mock_indicator_value):
            result = yc_indicator.calculate()

        assert result is not None
        assert result['score'] == -60.0  # (20 - 50) * 2
