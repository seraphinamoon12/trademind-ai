"""Market data providers."""
from datetime import datetime, timedelta
from typing import Optional, List
import yfinance as yf
import pandas as pd
from src.core.cache import cache, generate_data_key
from src.config import settings


class YahooFinanceProvider:
    """Yahoo Finance data provider."""

    def __init__(self):
        self.cache_ttl = settings.cache_duration_minutes * 60

    def get_historical(
        self,
        symbol: str,
        period: str = "1y",
        interval: str = "1d"
    ) -> Optional[pd.DataFrame]:
        """Fetch historical OHLCV data."""
        cache_key = generate_data_key('yf', symbol, 'historical', period, interval=interval)

        # Check cache
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)

            if df.empty:
                return None

            # Clean up column names
            df.columns = [c.lower().replace(' ', '_') for c in df.columns]
            df = df.reset_index()
            # Rename Date column to lowercase
            if 'Date' in df.columns:
                df = df.rename(columns={'Date': 'date'})

            # Cache the result
            cache.set(cache_key, df, self.cache_ttl)

            return df
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            return None

    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current stock price."""
        cache_key = generate_data_key('yf', symbol, 'price')

        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            price = info.get('currentPrice') or info.get('regularMarketPrice')

            if price:
                cache.set(cache_key, price, 60)  # 1 minute TTL for prices

            return price
        except Exception as e:
            print(f"Error fetching price for {symbol}: {e}")
            return None

    def get_multiple_prices(self, symbols: List[str]) -> dict:
        """Get current prices for multiple symbols."""
        result = {}
        for symbol in symbols:
            price = self.get_current_price(symbol)
            if price:
                result[symbol] = price
        return result


# Global provider instance
yahoo_provider = YahooFinanceProvider()
