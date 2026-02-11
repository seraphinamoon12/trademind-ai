"""Position manager for tracking and managing portfolio positions."""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, field
import requests
import time

from src.brokers.base import Position as BrokerPosition, Account
from src.config import settings

logger = logging.getLogger(__name__)


@dataclass
class PositionInfo:
    """Enhanced position information with P&L tracking."""
    symbol: str
    quantity: int
    avg_cost: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    entry_date: Optional[str] = None
    sector: Optional[str] = None


class PositionManager:
    """
    Manages portfolio positions with caching and P&L monitoring using TradeMind API.
    
    Features:
    - Fetches positions from TradeMind API
    - Caches positions to avoid repeated API calls
    - Tracks entry prices for P&L calculations
    - Monitors take-profit and stop-loss thresholds
    - Calculates sector exposure
    """

    def __init__(
        self,
        api_base_url: Optional[str] = None,
        cache_ttl_seconds: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Initialize position manager.
        
        Args:
            api_base_url: Base URL for TradeMind API (default: http://localhost:8000)
            cache_ttl_seconds: Cache time-to-live in seconds
            max_retries: Maximum number of retry attempts for API calls
            retry_delay: Delay between retry attempts in seconds
        """
        self.api_base_url = api_base_url or "http://localhost:8000"
        self.cache_ttl_seconds = cache_ttl_seconds
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        self._positions: Dict[str, PositionInfo] = {}
        self._last_fetch: Optional[float] = None
        self._account: Optional[Account] = None
        
        self.take_profit_pct = settings.take_profit_pct
        self.stop_loss_pct = settings.stop_loss_pct
        self.max_position_pct = settings.max_position_pct
        
        self._entry_prices: Dict[str, Tuple[float, datetime]] = {}

    def _make_api_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        json_data: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        Make HTTP request to TradeMind API with retry logic.
        
        Args:
            method: HTTP method (GET, POST, DELETE, etc.)
            endpoint: API endpoint path
            params: Query parameters
            data: Form data
            json_data: JSON payload
            
        Returns:
            Response JSON or None if failed
        """
        url = f"{self.api_base_url}{endpoint}"
        
        # Log API request details for debugging (Medium Priority Fix #5)
        logger.debug(f"API Request: {method} {url} - Params: {params} - Data: {data} - JSON: {json_data}")
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"API Request: {method} {url} (attempt {attempt + 1}/{self.max_retries})")
                
                response = requests.request(
                    method=method,
                    url=url,
                    params=params,
                    data=data,
                    json=json_data,
                    timeout=90
                )
                
                if response.status_code == 200:
                    logger.debug(f"API Success: {method} {url} - Status: {response.status_code}")
                    logger.debug(f"API Response: {response.text[:200]}")
                    return response.json()
                else:
                    logger.warning(f"API Error: {method} {url} - Status: {response.status_code} - {response.text}")
                    
            except requests.exceptions.Timeout:
                logger.warning(f"API Timeout: {method} {url} after 90s (attempt {attempt + 1}/{self.max_retries})")
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"API Connection Error: {method} {url} - {str(e)} (attempt {attempt + 1}/{self.max_retries})")
                logger.info("Connection failed - will fall back to simulation mode if persistent")
            except Exception as e:
                logger.error(f"API Request Error: {method} {url} - {type(e).__name__}: {e}")
                
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay)
                
        logger.error(f"API Request failed after {self.max_retries} attempts: {method} {url}")
        logger.info("Falling back to simulation mode due to API unavailability")
        return None

    async def fetch_positions(self, force_refresh: bool = False) -> Dict[str, PositionInfo]:
        """
        Fetch current positions from TradeMind API.
        
        Args:
            force_refresh: Force refresh even if cache is valid
            
        Returns:
            Dict mapping symbol -> PositionInfo
        """
        now = datetime.now(timezone.utc).timestamp()
        if not force_refresh and self._last_fetch is not None:
            if now - self._last_fetch < self.cache_ttl_seconds:
                logger.debug("Using cached positions")
                return self._positions

        try:
            # Fetch positions from API
            positions_response = self._make_api_request("GET", "/api/ibkr/positions")
            account_response = self._make_api_request("GET", "/api/ibkr/account")
            
            if not positions_response:
                logger.error("Failed to fetch positions from API")
                self._positions = {}
                return {}
            
            # Parse account info - handle both dict and list responses
            if account_response:
                if isinstance(account_response, dict) and "account" in account_response:
                    account_data = account_response["account"]
                elif isinstance(account_response, dict):
                    account_data = account_response
                else:
                    account_data = {}
                
                if account_data:
                    self._account = Account(
                        account_id=account_data.get("account_id", "unknown"),
                        cash_balance=account_data.get("cash_balance", 0.0),
                        portfolio_value=account_data.get("portfolio_value", 0.0),
                        buying_power=account_data.get("buying_power", 0.0),
                        margin_available=0.0,
                        total_pnl=0.0,
                        daily_pnl=0.0
                    )
            
            # Parse positions - handle both dict and list responses
            if isinstance(positions_response, dict):
                positions_list = positions_response.get("positions", [])
            elif isinstance(positions_response, list):
                positions_list = positions_response
            else:
                logger.warning(f"Unexpected positions response type: {type(positions_response)}")
                positions_list = []
            self._positions = {}
            
            for pos_data in positions_list:
                # Skip zero positions
                quantity = pos_data.get("quantity", 0)
                if abs(quantity) < 0.01:
                    continue

                symbol = pos_data["symbol"]
                avg_cost = pos_data.get("average_cost", pos_data.get("avg_cost", 0.0))
                current_price = pos_data.get("market_price", pos_data.get("current_price", 0.0))
                market_value = pos_data.get("market_value", 0.0)
                unrealized_pnl = pos_data.get("unrealized_pnl", 0.0)

                # Track entry price if this is a new position
                if symbol not in self._entry_prices:
                    self._entry_prices[symbol] = (avg_cost, datetime.now(timezone.utc))
                else:
                    entry_price, _ = self._entry_prices[symbol]
                    if entry_price != avg_cost:
                        # Average cost changed, update
                        self._entry_prices[symbol] = (avg_cost, datetime.now(timezone.utc))

                unrealized_pnl_pct = (
                    ((current_price - avg_cost) / avg_cost * 100)
                    if avg_cost > 0 else 0
                )

                self._positions[symbol] = PositionInfo(
                    symbol=symbol,
                    quantity=quantity,
                    avg_cost=avg_cost,
                    current_price=current_price,
                    market_value=market_value,
                    unrealized_pnl=unrealized_pnl,
                    unrealized_pnl_pct=unrealized_pnl_pct,
                    sector=self._get_sector(symbol)
                )

            self._last_fetch = now
            logger.info(f"Fetched {len(self._positions)} positions from API")
            
        except Exception as e:
            logger.error(f"Failed to fetch positions: {e}")
            self._positions = {}
            return {}

        return self._positions

    def get_position(self, symbol: str) -> Optional[PositionInfo]:
        """Get position info for a symbol."""
        return self._positions.get(symbol)

    def has_position(self, symbol: str) -> bool:
        """Check if we hold a position in symbol."""
        return symbol in self._positions and abs(self._positions[symbol].quantity) > 0

    def get_position_quantity(self, symbol: str) -> int:
        """Get position quantity for a symbol."""
        pos = self._positions.get(symbol)
        return pos.quantity if pos else 0

    def get_portfolio_value(self) -> float:
        """Get total portfolio value."""
        if self._account:
            return self._account.portfolio_value
        return sum(pos.market_value for pos in self._positions.values())

    def get_cash_balance(self) -> float:
        """Get available cash balance."""
        if self._account:
            return self._account.cash_balance
        return 0.0

    def get_cash_available_for_trade(self) -> float:
        """Get cash available for new positions (cash - reserved for safety)."""
        cash = self.get_cash_balance()
        # Reserve 10% for safety margin
        return cash * 0.90

    def get_sector_exposure(self) -> Dict[str, float]:
        """
        Calculate sector exposure in portfolio.
        
        Returns:
            Dict mapping sector -> exposure value
        """
        sector_exposure: Dict[str, float] = {}
        for pos in self._positions.values():
            if pos.quantity == 0:
                continue
            sector = pos.sector or "Unknown"
            sector_exposure[sector] = sector_exposure.get(sector, 0) + pos.market_value
        return sector_exposure

    def get_sector_exposure_pct(self, symbol: Optional[str] = None) -> Dict[str, float]:
        """
        Get sector exposure as percentage of portfolio.
        
        Args:
            symbol: Optional symbol to add to calculation (for checking before trade)
            
        Returns:
            Dict mapping sector -> exposure percentage
        """
        portfolio_value = self.get_portfolio_value()
        if portfolio_value <= 0:
            return {}
        
        sector_values = self.get_sector_exposure()
        
        # If checking for a potential new trade
        if symbol:
            pos = self.get_position(symbol)
            if pos:
                # Position already exists - it's already counted in get_sector_exposure()
                # No need to add it again to avoid double-counting
                pass
            else:
                # New position, estimate value (~5% of portfolio)
                sector = self._get_sector(symbol) or "Unknown"
                estimated_value = portfolio_value * self.max_position_pct
                sector_values[sector] = sector_values.get(sector, 0) + estimated_value
        
        return {
            sector: value / portfolio_value
            for sector, value in sector_values.items()
        }

    def check_exit_triggers(
        self,
        symbol: str,
        custom_take_profit: Optional[float] = None,
        custom_stop_loss: Optional[float] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Check if position should be exited based on take-profit/stop-loss.
        
        Args:
            symbol: Symbol to check
            custom_take_profit: Custom take-profit % (overrides default)
            custom_stop_loss: Custom stop-loss % (overrides default)
            
        Returns:
            Tuple of (should_exit, reason, action)
            - action is "SELL" for long positions, "BUY" for short positions
        """
        pos = self.get_position(symbol)
        if not pos or pos.quantity == 0:
            return False, "No position", None

        take_profit = custom_take_profit or self.take_profit_pct
        stop_loss = custom_stop_loss or self.stop_loss_pct

        # For long positions
        if pos.quantity > 0:
            if pos.unrealized_pnl_pct >= take_profit * 100:
                return True, (
                    f"Take-profit triggered: {pos.unrealized_pnl_pct:.1f}% gain "
                    f"(threshold: {take_profit:.0%})"
                ), "SELL"
            
            if pos.unrealized_pnl_pct <= -stop_loss * 100:
                return True, (
                    f"Stop-loss triggered: {pos.unrealized_pnl_pct:.1f}% loss "
                    f"(threshold: -{stop_loss:.0%})"
                ), "SELL"
        
        # For short positions
        else:
            if pos.unrealized_pnl_pct <= -take_profit * 100:
                return True, (
                    f"Take-profit triggered (short): {pos.unrealized_pnl_pct:.1f}% gain "
                    f"(threshold: -{take_profit:.0%})"
                ), "BUY"
            
            if pos.unrealized_pnl_pct >= stop_loss * 100:
                return True, (
                    f"Stop-loss triggered (short): {pos.unrealized_pnl_pct:.1f}% loss "
                    f"(threshold: {stop_loss:.0%})"
                ), "BUY"

        return False, "No exit trigger", None

    def check_position_size(
        self,
        symbol: str,
        proposed_quantity: int
    ) -> Tuple[bool, str]:
        """
        Check if proposed position size is acceptable.
        
        Args:
            symbol: Symbol to check
            proposed_quantity: Proposed quantity to add/buy
            
        Returns:
            Tuple of (is_valid, reason)
        """
        current_pos = self.get_position(symbol)
        current_qty = abs(current_pos.quantity) if current_pos else 0
        portfolio_value = self.get_portfolio_value()
        
        if portfolio_value <= 0:
            return False, "Invalid portfolio value"
        
        # Get current price (use position price if available)
        current_price = current_pos.current_price if current_pos else 0
        if current_price <= 0:
            return False, "Invalid current price"
        
        # Calculate new position value
        new_qty = current_qty + proposed_quantity
        new_position_value = new_qty * current_price
        new_position_pct = new_position_value / portfolio_value
        
        if new_position_pct > self.max_position_pct:
            return False, (
                f"Position would be {new_position_pct:.1%} of portfolio "
                f"(max: {self.max_position_pct:.0%})"
            )
        
        return True, f"Position would be {new_position_pct:.1%} of portfolio"

    def check_sector_limit(
        self,
        symbol: str,
        proposed_value: float
    ) -> Tuple[bool, str]:
        """
        Check if sector limit would be exceeded.
        
        Args:
            symbol: Symbol to add
            proposed_value: Proposed value of position
            
        Returns:
            Tuple of (is_valid, reason)
        """
        sector = self._get_sector(symbol)
        if not sector:
            return True, "Unknown sector - allowing trade"
        
        sector_exposure = self.get_sector_exposure_pct()
        current_exposure = sector_exposure.get(sector, 0)
        portfolio_value = self.get_portfolio_value()
        
        if portfolio_value <= 0:
            return True, "No portfolio value"
        
        new_exposure = current_exposure + (proposed_value / portfolio_value)
        max_sector_pct = settings.max_sector_allocation_pct
        
        if new_exposure > max_sector_pct:
            return False, (
                f"{sector} would be {new_exposure:.1%} of portfolio "
                f"(max: {max_sector_pct:.0%})"
            )
        
        return True, f"{sector} would be {new_exposure:.1%} of portfolio"

    def check_cash_availability(
        self,
        symbol: str,
        quantity: int
    ) -> Tuple[bool, str]:
        """
        Check if sufficient cash is available for a BUY order.
        
        Args:
            symbol: Symbol to buy
            quantity: Quantity to buy
            
        Returns:
            Tuple of (is_valid, reason)
        """
        cash_available = self.get_cash_available_for_trade()
        
        # Get current price
        pos = self.get_position(symbol)
        current_price = pos.current_price if pos else 0
        
        if current_price <= 0:
            return False, "Unable to get current price"
        
        required_cash = quantity * current_price
        
        if required_cash > cash_available:
            return False, (
                f"Insufficient cash: need ${required_cash:,.2f}, "
                f"have ${cash_available:,.2f}"
            )
        
        return True, f"Sufficient cash: ${cash_available:,.2f}"

    def get_position_summary(self) -> Dict[str, Any]:
        """Get summary of current positions."""
        portfolio_value = self.get_portfolio_value()
        cash = self.get_cash_balance()
        invested_value = portfolio_value - cash
        
        positions_summary = []
        for pos in self._positions.values():
            positions_summary.append({
                "symbol": pos.symbol,
                "quantity": pos.quantity,
                "avg_cost": pos.avg_cost,
                "current_price": pos.current_price,
                "market_value": pos.market_value,
                "unrealized_pnl": pos.unrealized_pnl,
                "unrealized_pnl_pct": pos.unrealized_pnl_pct,
                "sector": pos.sector
            })
        
        return {
            "portfolio_value": portfolio_value,
            "cash_balance": cash,
            "invested_value": invested_value,
            "cash_pct": cash / portfolio_value if portfolio_value > 0 else 0,
            "invested_pct": invested_value / portfolio_value if portfolio_value > 0 else 0,
            "num_positions": len([p for p in self._positions.values() if p.quantity != 0]),
            "positions": positions_summary,
            "sector_exposure": self.get_sector_exposure_pct()
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert positions to dict format for TradingState."""
        return {
            symbol: {
                "quantity": pos.quantity,
                "avg_cost": pos.avg_cost,
                "current_price": pos.current_price,
                "market_value": pos.market_value,
                "unrealized_pnl": pos.unrealized_pnl,
                "unrealized_pnl_pct": pos.unrealized_pnl_pct,
                "sector": pos.sector
            }
            for symbol, pos in self._positions.items()
        }

    def _get_sector(self, symbol: str) -> Optional[str]:
        """Get sector for a symbol (simplified)."""
        from src.risk.sector_monitor import sector_monitor
        return sector_monitor.get_sector(symbol)
