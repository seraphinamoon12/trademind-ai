"""IBKR Integration Module for TradeMind.

Provides synchronization between TradeMind and IB Gateway.
"""
import asyncio
import logging
import threading
from typing import Optional, Dict, List
from datetime import datetime
from sqlalchemy.orm import Session

from src.config import settings
from src.core.database import get_db, Holding, Trade, PortfolioSnapshot

logger = logging.getLogger(__name__)


class IBKRIntegration:
    """Manages integration between TradeMind and IB Gateway."""

    _instance = None
    _lock = threading.Lock()
    _broker = None
    _connected = False
    _account_id: Optional[str] = None

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    @property
    def is_connected(self) -> bool:
        return self._connected and self._broker is not None

    @property
    def broker(self):
        return self._broker

    async def initialize_in_loop(self) -> bool:
        """Initialize broker in the current event loop.

        MUST be called from within a running event loop (e.g., FastAPI lifespan).
        This ensures all asyncio primitives are bound to the correct event loop.
        """
        if not settings.ibkr_enabled:
            logger.info("IBKR integration disabled in settings")
            return False

        if self._broker is not None:
            logger.info("IBKR broker already initialized")
            return True

        try:
            from src.brokers.ibkr.ibkr_insync_broker import IBKRInsyncBroker

            self._broker = IBKRInsyncBroker(
                host=settings.ibkr_host,
                port=settings.ibkr_port,
                client_id=settings.ibkr_client_id,
                account=settings.ibkr_account
            )

            # Initialize event loop-dependent resources
            await self._broker.initialize_in_loop()

            logger.info("✅ IBKR insync broker initialized in event loop")
            return True

        except Exception as e:
            logger.error(f"❌ IBKR initialization error: {e}")
            return False

    async def connect(self) -> bool:
        """Connect to IB Gateway.

        Deprecated: Use initialize_in_loop() followed by ensure_connected() instead.
        This method is kept for backward compatibility.
        """
        # Just delegate to initialize_in_loop
        return await self.initialize_in_loop()
    
    async def ensure_connected(self) -> bool:
        """Ensure connection to IB Gateway (lazy connection)."""
        if not settings.ibkr_enabled:
            return False

        # Initialize broker if not already done
        if not self._broker:
            logger.info("Broker not initialized, initializing in current event loop...")
            await self.initialize_in_loop()
            if not self._broker:
                logger.error("❌ Failed to initialize broker")
                return False

        if self._connected:
            return True

        try:
            if self._broker is None:
                logger.error("❌ Broker is None, cannot connect")
                return False
            await self._broker.connect()
            self._connected = True
            logger.info(f"✅ Connected to IB Gateway on port {settings.ibkr_port}")
            return True
        except Exception as e:
            logger.error(f"❌ IBKR connection error: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from IB Gateway."""
        if self._broker and self._connected:
            await self._broker.disconnect()
            self._connected = False
            logger.info("🔌 Disconnected from IB Gateway")
    
    async def sync_portfolio(self, db: Session = None) -> Dict:
        """Sync TradeMind portfolio with IB Gateway account."""
        if not await self.ensure_connected():
            logger.warning("Cannot sync - not connected to IB Gateway")
            return {"success": False, "error": "Not connected"}
        
        should_close = db is None
        if db is None:
            db = next(get_db())
        
        try:
            if self._broker is None:
                raise RuntimeError("Broker not initialized")
            # Get IB account info
            account = await self._broker.get_account()
            
            # Get IB positions
            positions = await self._broker.get_positions()
            
            # Update portfolio snapshot
            snapshot = PortfolioSnapshot(
                timestamp=datetime.utcnow(),
                total_value=account.portfolio_value,
                cash_balance=account.cash_balance,
                invested_value=account.portfolio_value - account.cash_balance,
                daily_pnl=0.0,
                total_return_pct=0.0
            )
            db.add(snapshot)
            
            # Sync holdings - only delete holdings that exist in IB positions
            # Get current IB symbols to identify which holdings to delete
            ib_symbols = {pos.symbol for pos in positions}
            db.query(Holding).filter(Holding.symbol.in_(ib_symbols)).delete(synchronize_session=False)

            for pos in positions:
                holding = Holding(
                    symbol=pos.symbol,
                    quantity=pos.quantity,
                    avg_cost=pos.avg_cost,
                    current_price=getattr(pos, 'market_price', pos.avg_cost),
                    market_value=getattr(pos, 'market_value', pos.quantity * pos.avg_cost),
                    unrealized_pnl=getattr(pos, 'unrealized_pnl', 0.0),
                    stop_loss_pct=0.05,
                    sector=None
                )
                db.add(holding)
            
            db.commit()
            
            logger.info(f"✅ Portfolio synced with IB Gateway")
            logger.info(f"   Cash: ${account.cash_balance:,.2f}")
            logger.info(f"   Positions: {len(positions)}")
            
            return {
                "success": True,
                "cash_balance": account.cash_balance,
                "portfolio_value": account.portfolio_value,
                "positions_count": len(positions)
            }
            
        except Exception as e:
            logger.error(f"❌ Portfolio sync error: {e}")
            db.rollback()
            return {"success": False, "error": str(e)}
        finally:
            if should_close:
                db.close()
    
    async def get_account_summary(self) -> Optional[Dict]:
        """Get account summary from IB Gateway."""
        if not await self.ensure_connected():
            return None
        
        try:
            if self._broker is None:
                raise RuntimeError("Broker not initialized")
            account = await self._broker.get_account()
            return {
                "account_id": account.account_id,
                "cash_balance": account.cash_balance,
                "portfolio_value": account.portfolio_value,
                "buying_power": account.buying_power,
                "daily_pnl": account.daily_pnl
            }
        except Exception as e:
            logger.error(f"❌ Account summary error: {e}")
            return None


# Global instance - lazy initialization
ibkr_integration = None

def get_ibkr_integration():
    """Get or create IBKR integration instance."""
    global ibkr_integration
    if ibkr_integration is None:
        ibkr_integration = IBKRIntegration()
    return ibkr_integration
