"""Sector concentration monitoring."""
from typing import Tuple, Dict, Any, Optional
import logging

import yfinance as yf

logger = logging.getLogger(__name__)


class SectorConcentrationMonitor:
    """
    Monitor sector concentration to prevent over-concentration.
    
    Simpler alternative to correlation monitoring.
    Prevents over-concentration by sector (e.g., all tech stocks).
    
    Limits:
    - Max 30% of portfolio in any one sector
    """
    
    MAX_SECTOR_PCT = 0.50  # 50% max per sector
    
    def __init__(self):
        self.symbol_to_sector: Dict[str, str] = {}
        self.cache_duration_hours = 24
    
    def can_add_to_sector(
        self, 
        holdings: Dict[str, Any], 
        symbol: str,
        portfolio_value: float,
        estimated_position_value: float = None
    ) -> Tuple[bool, str]:
        """
        Check if adding this symbol would exceed sector limits.
        
        Args:
            holdings: Current holdings with market_value
            symbol: Symbol to potentially add
            portfolio_value: Total portfolio value
            estimated_position_value: Estimated value of new position
            
        Returns:
            Tuple[bool, str]: (can_add, reason)
        """
        sector = self.get_sector(symbol)
        if not sector:
            return True, "Unknown sector - allowing trade"
        
        # Calculate current sector allocation
        sector_value = 0.0
        for sym, holding in holdings.items():
            if isinstance(holding, dict):
                pos_sector = self.get_sector(sym)
                if pos_sector == sector:
                    sector_value += holding.get('market_value', 0)
        
        # Add proposed position
        if estimated_position_value is None:
            # Rough estimate: ~5% of portfolio
            estimated_position_value = portfolio_value * 0.05
        
        new_sector_value = sector_value + estimated_position_value
        new_sector_pct = new_sector_value / portfolio_value if portfolio_value > 0 else 0
        
        if new_sector_pct > self.MAX_SECTOR_PCT:
            return False, (
                f"{sector} allocation would be {new_sector_pct:.1%} "
                f"(max {self.MAX_SECTOR_PCT:.0%})"
            )
        
        return True, f"{sector} at {new_sector_pct:.1%}"
    
    def get_sector(self, symbol: str) -> Optional[str]:
        """Get sector for a symbol (with caching)."""
        if symbol in self.symbol_to_sector:
            return self.symbol_to_sector[symbol]
        
        try:
            # Fetch from yfinance
            info = yf.Ticker(symbol).info
            sector = info.get('sector')
            if sector:
                self.symbol_to_sector[symbol] = sector
                return sector
            
            # Fallback to industry
            industry = info.get('industry')
            if industry:
                self.symbol_to_sector[symbol] = industry
                return industry
            
            return None
        except Exception as e:
            logger.warning(f"Could not get sector for {symbol}: {e}")
            return None
    
    def get_sector_allocation(
        self, 
        holdings: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Get current sector allocation breakdown.
        
        Returns:
            dict: Sector -> allocation value
        """
        allocations: Dict[str, float] = {}
        
        for symbol, holding in holdings.items():
            if not isinstance(holding, dict):
                continue
                
            sector = self.get_sector(symbol) or 'Unknown'
            value = holding.get('market_value', 0)
            allocations[sector] = allocations.get(sector, 0) + value
        
        return allocations
    
    def get_sector_allocation_pct(
        self,
        holdings: Dict[str, Any],
        portfolio_value: float
    ) -> Dict[str, dict]:
        """
        Get sector allocation with percentages.
        
        Returns:
            dict: Sector -> {value, pct, status}
        """
        allocations = self.get_sector_allocation(holdings)
        
        result = {}
        for sector, value in allocations.items():
            pct = value / portfolio_value if portfolio_value > 0 else 0
            
            if pct > self.MAX_SECTOR_PCT:
                status = 'danger'
            elif pct > self.MAX_SECTOR_PCT * 0.8:
                status = 'warning'
            else:
                status = 'ok'
            
            result[sector] = {
                'value': value,
                'pct': pct,
                'status': status,
                'limit': self.MAX_SECTOR_PCT
            }
        
        return result
    
    def get_concentration_status(
        self,
        holdings: Dict[str, Any],
        portfolio_value: float
    ) -> Dict[str, Any]:
        """Get comprehensive concentration status."""
        sector_pcts = self.get_sector_allocation_pct(holdings, portfolio_value)
        
        # Find max concentration
        max_pct = 0
        max_sector = None
        for sector, data in sector_pcts.items():
            if data['pct'] > max_pct:
                max_pct = data['pct']
                max_sector = sector
        
        # Overall status
        if max_pct > self.MAX_SECTOR_PCT:
            status = 'danger'
        elif max_pct > self.MAX_SECTOR_PCT * 0.8:
            status = 'warning'
        else:
            status = 'ok'
        
        return {
            'max_sector': max_sector,
            'max_pct': max_pct,
            'status': status,
            'limit': self.MAX_SECTOR_PCT,
            'sectors': sector_pcts,
            'num_sectors': len(sector_pcts)
        }


# Global sector monitor instance
sector_monitor = SectorConcentrationMonitor()
