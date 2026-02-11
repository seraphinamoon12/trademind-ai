"""FRED (Federal Reserve Economic Data) provider for market mood indicators."""
from typing import Optional
import logging
from datetime import datetime, timedelta
import time

import pandas as pd

from src.market_mood.data_providers.base import BaseDataProvider
from src.market_mood.data_providers.cache import market_mood_cache
from src.market_mood.models import (
    IndicatorType,
    IndicatorValue,
    FearGreedComponents,
    YieldCurveData,
    CreditSpreadData,
)
from src.market_mood.exceptions import DataProviderError

logger = logging.getLogger(__name__)

try:
    from fredapi import Fred
    FRED_AVAILABLE = True
except ImportError:
    FRED_AVAILABLE = False
    logger.warning("fredapi not installed. FRED provider will not be available.")


class FREDProvider(BaseDataProvider):
    """FRED provider for market mood indicators."""

    # FRED series codes
    DXY_SERIES = "DTWEXBGS"  # Trade Weighted U.S. Dollar Index
    YIELD_10Y = "DGS10"  # 10-Year Treasury Constant Maturity Rate
    YIELD_2Y = "DGS2"  # 2-Year Treasury Constant Maturity Rate
    YIELD_3M = "DGS3MO"  # 3-Month Treasury Constant Maturity Rate
    AAA_BOND = "AAA"  # Moody's Seasoned AAA Corporate Bond Yield
    BAA_BOND = "BAA"  # Moody's Seasoned BAA Corporate Bond Yield
    SP500 = "SP500"  # S&P 500 Composite Index

    def __init__(self, config=None, cache_client=None):
        """Initialize FRED provider.
        
        Args:
            config: MarketMoodConfig instance
            cache_client: Optional custom cache client
        """
        super().__init__(config)
        self.cache = cache_client or market_mood_cache
        self.source = "fred"
        self._fred = None

    @property
    def fred(self):
        """Lazy-load FRED client."""
        if not FRED_AVAILABLE:
            raise DataProviderError("fredapi not installed. Install with: pip install fredapi")
        
        if self._fred is None:
            api_key = self.config.fred_api_key
            if not api_key:
                raise DataProviderError("FRED API key not configured. Set FRED_API_KEY in environment.")
            self._fred = Fred(api_key=api_key)
        
        return self._fred

    def fetch(self, indicator_type: IndicatorType, **kwargs) -> Optional[IndicatorValue]:
        """Fetch indicator data from FRED.
        
        Args:
            indicator_type: Type of indicator to fetch
            **kwargs: Additional parameters
            
        Returns:
            IndicatorValue if successful, None otherwise
        """
        try:
            if indicator_type == IndicatorType.FEAR_GREED:
                return self._fetch_fear_greed_components(**kwargs)
            elif indicator_type == IndicatorType.DXY:
                return self._fetch_dxy(**kwargs)
            elif indicator_type == IndicatorType.CREDIT_SPREADS:
                return self._fetch_credit_spreads(**kwargs)
            elif indicator_type == IndicatorType.YIELD_CURVE:
                return self._fetch_yield_curve(**kwargs)
            else:
                logger.warning(f"Unsupported indicator type: {indicator_type}")
                return None
        except Exception as e:
            logger.error(f"Error fetching {indicator_type}: {e}")
            raise DataProviderError(f"Failed to fetch {indicator_type}: {e}")

    def _fetch_fear_greed_components(self, **kwargs) -> Optional[IndicatorValue]:
        """Fetch Fear & Greed components from FRED data.
        
        Returns:
            IndicatorValue with Fear & Greed composite score
        """
        cache_key = self.get_cache_key(IndicatorType.FEAR_GREED)
        
        def fetch_fg_data():
            try:
                time.sleep(self.config.fred_rate_limit_delay)
                
                # Fetch S&P 500 for momentum
                sp500_data = self._fetch_series(self.SP500, lookback_days=30)
                momentum = self._calculate_momentum(sp500_data)
                
                # Use breadth from S&P 500 (simplified)
                breadth = 50.0  # Default neutral
                
                # Put/Call - estimated from VIX (not available in FRED)
                put_call = None
                
                # Safe haven - estimated from gold/USD ratio
                safe_haven = None
                
                # Junk bond spread - estimated from corporate bond yields
                junk_bond = None
                
                components = FearGreedComponents(
                    momentum=momentum,
                    breadth=breadth,
                    put_call=put_call,
                    safe_haven=safe_haven,
                    junk_bond=junk_bond,
                )
                
                return IndicatorValue(
                    indicator_type=IndicatorType.FEAR_GREED,
                    value=components.get_composite_score(),
                    source=self.source,
                    metadata={
                        "components": components.model_dump(),
                        "sp500_data": sp500_data[-5:] if sp500_data else [],
                    }
                )
            except Exception as e:
                logger.error(f"Error fetching Fear & Greed components: {e}")
                raise DataProviderError(f"Fear & Greed fetch failed: {e}")
        
        return self.cache.get_or_fetch(
            cache_key,
            fetch_fg_data,
            ttl=self.get_cache_ttl(IndicatorType.FEAR_GREED),
            indicator_type=IndicatorType.FEAR_GREED
        )

    def _fetch_dxy(self, **kwargs) -> Optional[IndicatorValue]:
        """Fetch U.S. Dollar Index (DXY).
        
        Returns:
            IndicatorValue with DXY value
        """
        cache_key = self.get_cache_key(IndicatorType.DXY)
        
        def fetch_dxy_data():
            try:
                time.sleep(self.config.fred_rate_limit_delay)
                
                dxy_data = self._fetch_series(self.DXY_SERIES, lookback_days=30)
                
                if not dxy_data:
                    logger.error(f"No data found for {self.DXY_SERIES}")
                    return None
                
                latest_value = dxy_data[-1]['value']
                
                # Calculate DXY score (higher DXY = stronger USD = risk-off = fear)
                # Normalize: 100-110 = fear, 90-100 = neutral, <90 = greed
                if latest_value >= 110:
                    dxy_score = 10.0
                elif latest_value >= 105:
                    dxy_score = 25.0
                elif latest_value >= 100:
                    dxy_score = 40.0
                elif latest_value >= 95:
                    dxy_score = 60.0
                elif latest_value >= 90:
                    dxy_score = 75.0
                else:
                    dxy_score = 90.0
                
                # Calculate change
                change = 0
                if len(dxy_data) >= 2:
                    change = (dxy_data[-1]['value'] - dxy_data[-2]['value']) / dxy_data[-2]['value'] * 100
                
                return IndicatorValue(
                    indicator_type=IndicatorType.DXY,
                    value=dxy_score,
                    source=self.source,
                    metadata={
                        "dxy_value": latest_value,
                        "change": change,
                        "series": self.DXY_SERIES,
                        "date": dxy_data[-1]['date'].isoformat() if dxy_data else None,
                    }
                )
            except Exception as e:
                logger.error(f"Error fetching DXY: {e}")
                raise DataProviderError(f"DXY fetch failed: {e}")
        
        return self.cache.get_or_fetch(
            cache_key,
            fetch_dxy_data,
            ttl=self.get_cache_ttl(IndicatorType.DXY),
            indicator_type=IndicatorType.DXY
        )

    def _fetch_credit_spreads(self, **kwargs) -> Optional[IndicatorValue]:
        """Fetch credit spreads.
        
        Returns:
            IndicatorValue with credit spread score
        """
        cache_key = self.get_cache_key(IndicatorType.CREDIT_SPREADS)
        
        def fetch_spread_data():
            try:
                time.sleep(self.config.fred_rate_limit_delay)
                
                # Fetch AAA and BAA bond yields
                aaa_data = self._fetch_series(self.AAA_BOND, lookback_days=30)
                baa_data = self._fetch_series(self.BAA_BOND, lookback_days=30)
                
                if not aaa_data or not baa_data:
                    logger.error("No data found for credit spreads")
                    return None
                
                latest_aaa = aaa_data[-1]['value']
                latest_baa = baa_data[-1]['value']
                
                spread_baa_aaa = latest_baa - latest_aaa
                
                # Estimate high yield spread (using BAA as proxy)
                spread_high_yield_treasury = latest_baa - 2.0  # Rough estimate vs Treasury
                
                spread_data = CreditSpreadData(
                    spread_baa_aaa=spread_baa_aaa,
                    spread_high_yield_treasury=spread_high_yield_treasury,
                )
                
                return IndicatorValue(
                    indicator_type=IndicatorType.CREDIT_SPREADS,
                    value=spread_data.get_credit_score(),
                    source=self.source,
                    metadata={
                        "spread_data": spread_data.model_dump(),
                        "aaa_yield": latest_aaa,
                        "baa_yield": latest_baa,
                        "date": aaa_data[-1]['date'].isoformat(),
                    }
                )
            except Exception as e:
                logger.error(f"Error fetching credit spreads: {e}")
                raise DataProviderError(f"Credit spreads fetch failed: {e}")
        
        return self.cache.get_or_fetch(
            cache_key,
            fetch_spread_data,
            ttl=self.get_cache_ttl(IndicatorType.CREDIT_SPREADS),
            indicator_type=IndicatorType.CREDIT_SPREADS
        )

    def _fetch_yield_curve(self, **kwargs) -> Optional[IndicatorValue]:
        """Fetch yield curve data.
        
        Returns:
            IndicatorValue with yield curve score
        """
        cache_key = self.get_cache_key(IndicatorType.YIELD_CURVE)
        
        def yield_curve_data():
            try:
                time.sleep(self.config.fred_rate_limit_delay)
                
                # Fetch 10Y, 2Y, and 3M yields
                yield_10y_data = self._fetch_series(self.YIELD_10Y, lookback_days=30)
                yield_2y_data = self._fetch_series(self.YIELD_2Y, lookback_days=30)
                yield_3m_data = self._fetch_series(self.YIELD_3M, lookback_days=30)
                
                if not yield_10y_data or not yield_2y_data:
                    logger.error("No data found for yield curve")
                    return None
                
                latest_10y = yield_10y_data[-1]['value']
                latest_2y = yield_2y_data[-1]['value'] if yield_2y_data else None
                latest_3m = yield_3m_data[-1]['value'] if yield_3m_data else None
                
                spread_10y_2y = latest_10y - latest_2y if latest_2y else 0
                spread_10y_3m = latest_10y - latest_3m if latest_3m else 0
                
                yc_data = YieldCurveData(
                    spread_10y_2y=spread_10y_2y,
                    spread_10y_3m=spread_10y_3m,
                )
                
                return IndicatorValue(
                    indicator_type=IndicatorType.YIELD_CURVE,
                    value=yc_data.get_yield_curve_score(),
                    source=self.source,
                    metadata={
                        "yield_curve_data": yc_data.model_dump(),
                        "yield_10y": latest_10y,
                        "yield_2y": latest_2y,
                        "yield_3m": latest_3m,
                        "date": yield_10y_data[-1]['date'].isoformat(),
                    }
                )
            except Exception as e:
                logger.error(f"Error fetching yield curve: {e}")
                raise DataProviderError(f"Yield curve fetch failed: {e}")
        
        return self.cache.get_or_fetch(
            cache_key,
            yield_curve_data,
            ttl=self.get_cache_ttl(IndicatorType.YIELD_CURVE),
            indicator_type=IndicatorType.YIELD_CURVE
        )

    def _fetch_series(self, series_id: str, lookback_days: int = 30) -> list:
        """Fetch a FRED time series.
        
        Args:
            series_id: FRED series ID
            lookback_days: Number of days to look back
            
        Returns:
            List of dicts with 'date' and 'value' keys
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=lookback_days)
            
            data = self.fred.get_series(
                series_id,
                observation_start=start_date.strftime('%Y-%m-%d'),
                observation_end=end_date.strftime('%Y-%m-%d')
            )
            
            result = []
            for date, value in data.items():
                if value is not None and not pd.isna(value):
                    result.append({
                        'date': date if isinstance(date, datetime) else pd.to_datetime(date),
                        'value': float(value),
                    })
            
            return result
        except Exception as e:
            logger.error(f"Error fetching series {series_id}: {e}")
            return []

    def _calculate_momentum(self, price_data: list) -> Optional[float]:
        """Calculate momentum score from price data.
        
        Args:
            price_data: List of price data points
            
        Returns:
            Momentum score (0-100) or None
        """
        if not price_data or len(price_data) < 2:
            return None
        
        latest = price_data[-1]['value']
        previous = price_data[0]['value']
        
        change_pct = (latest - previous) / previous * 100
        
        # Convert to 0-100 score
        if change_pct > 5:
            return 90.0
        elif change_pct > 2:
            return 75.0
        elif change_pct > 0:
            return 60.0
        elif change_pct > -2:
            return 45.0
        elif change_pct > -5:
            return 30.0
        else:
            return 15.0

    def get_all_indicators(self) -> dict:
        """Fetch all available indicators from FRED.
        
        Returns:
            Dictionary with indicator_type as key and IndicatorValue as value
        """
        indicators = {}
        
        for indicator_type in [
            IndicatorType.FEAR_GREED,
            IndicatorType.DXY,
            IndicatorType.CREDIT_SPREADS,
            IndicatorType.YIELD_CURVE,
        ]:
            try:
                value = self.fetch_with_retry(indicator_type)
                if value:
                    indicators[indicator_type] = value
            except Exception as e:
                logger.warning(f"Failed to fetch {indicator_type}: {e}")
        
        return indicators
