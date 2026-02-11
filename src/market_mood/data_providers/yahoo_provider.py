"""Yahoo Finance data provider for market mood indicators."""
from typing import Optional, List, Any
import yfinance as yf
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
import time

from src.market_mood.data_providers.base import BaseDataProvider
from src.market_mood.data_providers.cache import market_mood_cache
from src.market_mood.models import (
    IndicatorType,
    IndicatorValue,
    MarketBreadthData,
    MATrendData,
)
from src.market_mood.exceptions import DataProviderError
from src.market_mood.config import MarketMoodConfig

logger = logging.getLogger(__name__)


class YahooFinanceProvider(BaseDataProvider):
    """Yahoo Finance provider for market mood indicators."""

    VIX_SYMBOL = "^VIX"
    SPY_SYMBOL = "^GSPC"
    PUT_CALL_INDEX = "^PC"

    def __init__(self, config: Optional[MarketMoodConfig] = None, cache_client: Optional[Any] = None):
        """Initialize Yahoo Finance provider.
        
        Args:
            config: MarketMoodConfig instance
            cache_client: Optional custom cache client
        """
        super().__init__(config)
        self.cache = cache_client or market_mood_cache
        self.source = "yahoo"

    def fetch(self, indicator_type: IndicatorType, **kwargs) -> Optional[IndicatorValue]:
        """Fetch indicator data from Yahoo Finance.
        
        Args:
            indicator_type: Type of indicator to fetch
            **kwargs: Additional parameters
            
        Returns:
            IndicatorValue if successful, None otherwise
        """
        try:
            if indicator_type == IndicatorType.VIX:
                return self._fetch_vix(**kwargs)
            elif indicator_type == IndicatorType.MARKET_BREADTH:
                return self._fetch_market_breadth(**kwargs)
            elif indicator_type == IndicatorType.PUT_CALL_RATIO:
                return self._fetch_put_call_ratio(**kwargs)
            elif indicator_type == IndicatorType.MA_TRENDS:
                return self._fetch_ma_trends(**kwargs)
            else:
                logger.warning(f"Unsupported indicator type: {indicator_type}")
                return None
        except Exception as e:
            logger.error(f"Error fetching {indicator_type}: {e}")
            raise DataProviderError(f"Failed to fetch {indicator_type}: {e}")

    def _fetch_vix(self, **kwargs) -> Optional[IndicatorValue]:
        """Fetch VIX (CBOE Volatility Index).
        
        Returns:
            IndicatorValue with VIX value
        """
        cache_key = self.get_cache_key(IndicatorType.VIX)
        
        def fetch_vix_data():
            try:
                time.sleep(self.config.yahoo_rate_limit_delay)
                ticker = yf.Ticker(self.VIX_SYMBOL)
                hist = ticker.history(period="5d")
                
                if hist.empty:
                    logger.error(f"No data found for {self.VIX_SYMBOL}")
                    return None
                
                latest = hist.iloc[-1]
                vix_value = float(latest['Close'])
                
                date_str = None
                if len(hist) > 0:
                    idx = hist.index[-1]
                    if hasattr(idx, 'isoformat'):
                        date_str = idx.isoformat()
                    else:
                        date_str = str(idx)
                
                previous = float(hist.iloc[-2]['Close']) if len(hist) > 1 else None
                
                return IndicatorValue(
                    indicator_type=IndicatorType.VIX,
                    value=vix_value,
                    source=self.source,
                    metadata={
                        "symbol": self.VIX_SYMBOL,
                        "date": date_str,
                        "previous": previous,
                    }
                )
            except Exception as e:
                logger.error(f"Error fetching VIX: {e}")
                raise DataProviderError(f"VIX fetch failed: {e}")
        
        return self.cache.get_or_fetch(
            cache_key,
            fetch_vix_data,
            ttl=self.get_cache_ttl(IndicatorType.VIX),
            indicator_type=IndicatorType.VIX
        )

    def _fetch_market_breadth(self, **kwargs) -> Optional[IndicatorValue]:
        """Fetch market breadth data.
        
        Returns:
            IndicatorValue with breadth score
        """
        cache_key = self.get_cache_key(IndicatorType.MARKET_BREADTH)
        
        def fetch_breadth_data():
            try:
                time.sleep(self.config.yahoo_rate_limit_delay)
                
                # Use S&P 500 as proxy for breadth
                ticker = yf.Ticker(self.SPY_SYMBOL)
                hist = ticker.history(period="1mo")
                
                if hist.empty:
                    logger.error(f"No data found for {self.SPY_SYMBOL}")
                    return None
                
                latest = hist.iloc[-1]
                prev = hist.iloc[-2] if len(hist) > 1 else latest
                
                # Calculate simple breadth metrics
                price_change = (latest['Close'] - prev['Close']) / prev['Close'] * 100
                
                # Volume change
                volume_change = (latest['Volume'] - prev['Volume']) / prev['Volume'] * 100 if prev['Volume'] > 0 else 0
                
                # Estimate advance/decline ratio based on price action
                if price_change > 1:
                    ad_ratio = 2.0
                elif price_change > 0.5:
                    ad_ratio = 1.5
                elif price_change > 0:
                    ad_ratio = 1.2
                elif price_change > -0.5:
                    ad_ratio = 0.8
                else:
                    ad_ratio = 0.5
                
                # Estimate new highs/lows
                new_highs = max(0, int(price_change * 10)) if price_change > 0 else 0
                new_lows = max(0, int(abs(price_change) * 10)) if price_change < 0 else 0
                
                breadth_data = MarketBreadthData(
                    advance_decline_ratio=ad_ratio,
                    new_highs=new_highs,
                    new_lows=new_lows,
                    advancing_volume=int(latest['Volume'] * max(0, ad_ratio / 2)),
                    declining_volume=int(latest['Volume'] * max(0, 1 - ad_ratio / 2)),
                )
                
                return IndicatorValue(
                    indicator_type=IndicatorType.MARKET_BREADTH,
                    value=breadth_data.get_breadth_score(),
                    source=self.source,
                    metadata={
                        "breadth_data": breadth_data.model_dump(),
                        "price_change": price_change,
                        "volume_change": volume_change,
                        "date": hist.index[-1].isoformat(),
                    }
                )
            except Exception as e:
                logger.error(f"Error fetching market breadth: {e}")
                raise DataProviderError(f"Market breadth fetch failed: {e}")
        
        return self.cache.get_or_fetch(
            cache_key,
            fetch_breadth_data,
            ttl=self.get_cache_ttl(IndicatorType.MARKET_BREADTH),
            indicator_type=IndicatorType.MARKET_BREADTH
        )

    def _fetch_put_call_ratio(self, **kwargs) -> Optional[IndicatorValue]:
        """Fetch Put/Call ratio.
        
        Returns:
            IndicatorValue with Put/Call ratio
        """
        cache_key = self.get_cache_key(IndicatorType.PUT_CALL_RATIO)
        
        def fetch_pcr_data():
            try:
                time.sleep(self.config.yahoo_rate_limit_delay)
                
                # Using CBOE Put/Call Index from Yahoo Finance
                # Note: Yahoo Finance may not have direct PCR, using alternative
                ticker = yf.Ticker(self.SPY_SYMBOL)
                hist = ticker.history(period="5d")
                
                if hist.empty:
                    logger.error(f"No data found for {self.SPY_SYMBOL}")
                    return None
                
                latest = hist.iloc[-1]
                prev = hist.iloc[-2] if len(hist) > 1 else latest
                
                # Calculate price volatility as proxy for PCR
                volatility = hist['Close'].pct_change().std() * np.sqrt(252)
                
                # Estimate PCR based on volatility
                # Higher volatility = more puts = higher PCR
                base_pcr = 1.0
                pcr_adjustment = min(2.0, max(-0.5, (volatility - 0.15) * 5))
                pcr_value = base_pcr + pcr_adjustment
                
                return IndicatorValue(
                    indicator_type=IndicatorType.PUT_CALL_RATIO,
                    value=pcr_value,
                    source=self.source,
                    metadata={
                        "volatility": float(volatility),
                        "date": hist.index[-1].isoformat(),
                        "estimated": True,
                    }
                )
            except Exception as e:
                logger.error(f"Error fetching put/call ratio: {e}")
                raise DataProviderError(f"Put/Call ratio fetch failed: {e}")
        
        return self.cache.get_or_fetch(
            cache_key,
            fetch_pcr_data,
            ttl=self.get_cache_ttl(IndicatorType.PUT_CALL_RATIO),
            indicator_type=IndicatorType.PUT_CALL_RATIO
        )

    def _fetch_ma_trends(self, symbols: Optional[List[str]] = None, **kwargs) -> Optional[IndicatorValue]:
        """Fetch moving average trends.
        
        Args:
            symbols: List of symbols to analyze. If None, uses S&P 500.
            
        Returns:
            IndicatorValue with MA trend score
        """
        cache_key = self.get_cache_key(IndicatorType.MA_TRENDS, symbols=symbols)
        
        def fetch_ma_data():
            try:
                time.sleep(self.config.yahoo_rate_limit_delay)
                
                if symbols is None:
                    symbols = [self.SPY_SYMBOL]
                
                total_score = 0.0
                count = 0
                
                trend_data = {}
                
                for symbol in symbols:
                    ticker = yf.Ticker(symbol)
                    hist = ticker.history(period="1y")
                    
                    if hist.empty:
                        logger.warning(f"No data found for {symbol}")
                        continue
                    
                    latest = hist.iloc[-1]
                    current_price = float(latest['Close'])
                    
                    # Calculate 50-day and 200-day MAs
                    ma50 = hist['Close'].rolling(window=50).mean().iloc[-1]
                    ma200 = hist['Close'].rolling(window=200).mean().iloc[-1]
                    
                    # Calculate slopes
                    if len(hist) >= 20:
                        ma50_slope = (hist['Close'].iloc[-1] - hist['Close'].iloc[-20]) / 20
                        ma200_slope = (hist['Close'].iloc[-1] - hist['Close'].iloc[-50]) / 50
                    else:
                        ma50_slope = 0
                        ma200_slope = 0
                    
                    ma_data = MATrendData(
                        symbol=symbol,
                        price_above_50ma=current_price > ma50,
                        price_above_200ma=current_price > ma200,
                        ma50_slope=float(ma50_slope),
                        ma200_slope=float(ma200_slope),
                    )
                    
                    score = ma_data.get_trend_score()
                    total_score += score
                    count += 1
                    
                    trend_data[symbol] = {
                        "ma_data": ma_data.model_dump(),
                        "score": score,
                    }
                
                if count == 0:
                    return None
                
                avg_score = total_score / count
                
                return IndicatorValue(
                    indicator_type=IndicatorType.MA_TRENDS,
                    value=avg_score,
                    source=self.source,
                    metadata={
                        "trend_data": trend_data,
                        "symbols_analyzed": symbols,
                    }
                )
            except Exception as e:
                logger.error(f"Error fetching MA trends: {e}")
                raise DataProviderError(f"MA trends fetch failed: {e}")
        
        return self.cache.get_or_fetch(
            cache_key,
            fetch_ma_data,
            ttl=self.get_cache_ttl(IndicatorType.MA_TRENDS),
            indicator_type=IndicatorType.MA_TRENDS
        )

    def get_all_indicators(self, symbols: Optional[List[str]] = None) -> dict:
        """Fetch all available indicators from Yahoo Finance.
        
        Args:
            symbols: Symbols to use for MA trends
            
        Returns:
            Dictionary with indicator_type as key and IndicatorValue as value
        """
        indicators = {}
        
        for indicator_type in [
            IndicatorType.VIX,
            IndicatorType.MARKET_BREADTH,
            IndicatorType.PUT_CALL_RATIO,
            IndicatorType.MA_TRENDS,
        ]:
            try:
                if indicator_type == IndicatorType.MA_TRENDS:
                    value = self.fetch_with_retry(indicator_type, symbols=symbols)
                else:
                    value = self.fetch_with_retry(indicator_type)
                
                if value:
                    indicators[indicator_type] = value
            except Exception as e:
                logger.warning(f"Failed to fetch {indicator_type}: {e}")
        
        return indicators
