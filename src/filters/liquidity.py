"""Liquidity filters - ensure we only trade liquid stocks."""
from typing import Tuple
import logging

import yfinance as yf

logger = logging.getLogger(__name__)


class LiquidityFilter:
    """
    Ensure we only trade liquid stocks.
    
    Filters:
    - Min $1M average daily dollar volume
    - Min $5 price
    - Max 0.2% spread
    - Min $1B market cap
    """
    
    MIN_AVG_DAILY_VOLUME = 1_000_000  # $1M
    MIN_PRICE = 5.00
    MAX_SPREAD_PCT = 0.002  # 0.2%
    MIN_MARKET_CAP = 1_000_000_000  # $1B
    
    def validate(self, symbol: str) -> Tuple[bool, str]:
        """
        Validate symbol meets liquidity requirements.
        
        Args:
            symbol: Stock symbol to validate
            
        Returns:
            Tuple[bool, str]: (is_valid, reason)
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            if not info:
                return False, "Could not fetch symbol info"
            
            # Check price
            current_price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose', 0)
            if current_price < self.MIN_PRICE:
                return False, f"Price ${current_price:.2f} below ${self.MIN_PRICE}"
            
            # Check volume
            avg_volume = info.get('averageVolume') or info.get('averageDailyVolume10Day', 0)
            dollar_volume = avg_volume * current_price
            if dollar_volume < self.MIN_AVG_DAILY_VOLUME:
                return False, (
                    f"Volume ${dollar_volume:,.0f} below "
                    f"${self.MIN_AVG_DAILY_VOLUME:,.0f}"
                )
            
            # Check market cap
            market_cap = info.get('marketCap', 0)
            if market_cap < self.MIN_MARKET_CAP:
                return False, (
                    f"Market cap ${market_cap:,.0f} below "
                    f"${self.MIN_MARKET_CAP:,.0f}"
                )
            
            # Check spread (if available)
            bid = info.get('bid', 0)
            ask = info.get('ask', 0)
            if bid > 0 and ask > 0:
                mid = (ask + bid) / 2
                spread_pct = (ask - bid) / mid
                if spread_pct > self.MAX_SPREAD_PCT:
                    return False, f"Spread {spread_pct:.2%} above {self.MAX_SPREAD_PCT:.2%}"
            
            return True, "OK"
            
        except Exception as e:
            logger.warning(f"Error validating {symbol}: {e}")
            return False, f"Validation error: {str(e)}"
    
    def get_liquidity_info(self, symbol: str) -> dict:
        """Get detailed liquidity information."""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            if not info:
                return {'error': 'Could not fetch info'}
            
            current_price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose', 0)
            avg_volume = info.get('averageVolume') or info.get('averageDailyVolume10Day', 0)
            market_cap = info.get('marketCap', 0)
            
            bid = info.get('bid', 0)
            ask = info.get('ask', 0)
            spread_pct = None
            if bid > 0 and ask > 0:
                mid = (ask + bid) / 2
                spread_pct = (ask - bid) / mid
            
            dollar_volume = avg_volume * current_price
            
            return {
                'symbol': symbol,
                'price': current_price,
                'avg_volume': avg_volume,
                'dollar_volume': dollar_volume,
                'market_cap': market_cap,
                'bid': bid,
                'ask': ask,
                'spread_pct': spread_pct,
                'checks': {
                    'price_ok': current_price >= self.MIN_PRICE,
                    'volume_ok': dollar_volume >= self.MIN_AVG_DAILY_VOLUME,
                    'market_cap_ok': market_cap >= self.MIN_MARKET_CAP,
                    'spread_ok': spread_pct is None or spread_pct <= self.MAX_SPREAD_PCT
                }
            }
            
        except Exception as e:
            logger.warning(f"Error getting liquidity info for {symbol}: {e}")
            return {'error': str(e)}


# Global liquidity filter instance
liquidity_filter = LiquidityFilter()
