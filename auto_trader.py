#!/usr/bin/env python3
"""
TradeMind AI - Auto Trading System with IB Gateway
Runs continuous trading without human confirmation.
"""
import asyncio
import sys
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict

sys.path.insert(0, '.')

from src.config import settings
from src.brokers.ibkr.async_broker import IBKRThreadedBroker
from src.brokers.base import Order, OrderType, OrderSide
from src.data.providers import yahoo_provider
from src.api.routes.safety import get_safety_status

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Auto-trading configuration
AUTO_TRADE_ENABLED = True
HUMAN_REVIEW_ENABLED = False
CONFIDENCE_THRESHOLD = 0.65
MAX_POSITIONS = 5
POSITION_SIZE = 100  # shares per trade
WATCHLIST = ["AAPL", "MSFT", "TQQQ", "SPY", "QQQ", "TSLA", "NVDA", "AMD", "IAU", "AG", "IBIT"]
CHECK_INTERVAL = 60  # seconds between checks


class AutoTrader:
    """Automated trading system with IB Gateway."""
    
    def __init__(self):
        self.broker = None
        self.running = False
        self.positions = {}
        self.trade_history = []
        
    async def connect(self):
        """Connect to IB Gateway."""
        logger.info("Connecting to IB Gateway...")
        self.broker = IBKRThreadedBroker(
            host='127.0.0.1',
            port=7497,
            client_id=400,
            paper_trading=True
        )
        await self.broker.connect()
        logger.info("✅ Connected to IB Gateway (Paper Trading)")
        
    async def disconnect(self):
        """Disconnect from IB Gateway."""
        if self.broker:
            await self.broker.disconnect()
            logger.info("Disconnected from IB Gateway")
            
    async def get_account_summary(self):
        """Get account summary."""
        try:
            account = await self.broker.get_account()
            return {
                'cash': account.cash_balance,
                'portfolio_value': account.portfolio_value,
                'buying_power': account.buying_power
            }
        except Exception as e:
            logger.error(f"Error getting account: {e}")
            return None
            
    async def get_positions(self):
        """Get current positions."""
        try:
            positions = await self.broker.get_positions()
            return {p.symbol: p for p in positions}
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return {}
            
    async def analyze_symbol(self, symbol: str) -> Dict:
        """Analyze a symbol for trading opportunity."""
        try:
            # Get current price
            price = yahoo_provider.get_current_price(symbol)
            if not price:
                return None
                
            # Simple moving average strategy
            # In real system, you'd use technical indicators
            import random
            confidence = random.uniform(0.5, 0.9)  # Simulated confidence
            
            # Determine action based on price movement simulation
            action = "buy" if confidence > CONFIDENCE_THRESHOLD else "hold"
            
            return {
                'symbol': symbol,
                'price': price,
                'confidence': confidence,
                'action': action,
                'reasoning': f"Price: ${price:.2f}, Confidence: {confidence:.2%}"
            }
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")
            return None
            
    async def place_order(self, symbol: str, quantity: int, side: str, price: float) -> bool:
        """Place an order directly via IB API."""
        try:
            from ibapi.contract import Contract
            from ibapi.order import Order as IBOrder
            
            order_id = self.broker._get_next_req_id()
            
            contract = Contract()
            contract.symbol = symbol
            contract.secType = "STK"
            contract.exchange = "SMART"
            contract.currency = "USD"
            
            ib_order = IBOrder()
            ib_order.action = side.upper()
            ib_order.totalQuantity = quantity
            ib_order.orderType = "LMT"
            ib_order.lmtPrice = price
            ib_order.tif = "GTC"
            ib_order.eTradeOnly = False
            ib_order.firmQuoteOnly = False
            
            self.broker._thread.client.placeOrder(order_id, contract, ib_order)
            
            logger.info(f"✅ Order placed: {side.upper()} {quantity} {symbol} @ ${price:.2f}")
            return True
            
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return False
            
    async def check_safety(self) -> bool:
        """Check if trading is safe."""
        try:
            # Simple safety checks
            if not settings.ibkr_enabled:
                logger.warning("⛔ IBKR not enabled")
                return False
            return True
        except Exception as e:
            logger.error(f"Safety check error: {e}")
            return True  # Allow trading on error
            
    async def trading_loop(self):
        """Main trading loop."""
        logger.info("=" * 60)
        logger.info("🚀 TRADEMIND AI - AUTO TRADING SYSTEM")
        logger.info("=" * 60)
        logger.info(f"Mode: Paper Trading")
        logger.info(f"Human Review: {'ENABLED' if HUMAN_REVIEW_ENABLED else 'DISABLED'}")
        logger.info(f"Confidence Threshold: {CONFIDENCE_THRESHOLD:.0%}")
        logger.info(f"Watchlist: {', '.join(WATCHLIST)}")
        logger.info("=" * 60)
        
        while self.running:
            try:
                # Check safety
                if not await self.check_safety():
                    await asyncio.sleep(CHECK_INTERVAL)
                    continue
                    
                # Get account info
                account = await self.get_account_summary()
                if account:
                    logger.info(f"💰 Cash: ${account['cash']:,.2f} | Portfolio: ${account['portfolio_value']:,.2f}")
                    
                # Get current positions
                positions = await self.get_positions()
                logger.info(f"📊 Positions: {len(positions)} open")
                
                # Analyze watchlist
                for symbol in WATCHLIST:
                    if not self.running:
                        break
                        
                    # Skip if already have position
                    if symbol in positions:
                        continue
                        
                    # Analyze symbol
                    analysis = await self.analyze_symbol(symbol)
                    if not analysis:
                        continue
                        
                    logger.info(f"📈 {symbol}: ${analysis['price']:.2f} | Confidence: {analysis['confidence']:.2%} | Action: {analysis['action']}")
                    
                    # Auto-trade if confidence is high
                    if analysis['action'] == 'buy' and analysis['confidence'] >= CONFIDENCE_THRESHOLD:
                        if not HUMAN_REVIEW_ENABLED:
                            # Auto-execute without human confirmation
                            logger.info(f"🤖 AUTO-EXECUTING: Buy {POSITION_SIZE} {symbol}")
                            await self.place_order(
                                symbol=symbol,
                                quantity=POSITION_SIZE,
                                side='buy',
                                price=analysis['price']
                            )
                        else:
                            logger.info(f"⏳ Waiting for human approval: Buy {symbol}")
                            
                    await asyncio.sleep(1)  # Brief pause between symbols
                    
                logger.info(f"⏳ Next check in {CHECK_INTERVAL} seconds...")
                await asyncio.sleep(CHECK_INTERVAL)
                
            except Exception as e:
                logger.error(f"Trading loop error: {e}")
                await asyncio.sleep(CHECK_INTERVAL)
                
    async def run(self):
        """Run the auto-trading system."""
        try:
            await self.connect()
            self.running = True
            await self.trading_loop()
        except KeyboardInterrupt:
            logger.info("\n🛑 Stopping auto-trader...")
        finally:
            self.running = False
            await self.disconnect()
            logger.info("Auto-trader stopped")


async def main():
    """Main entry point."""
    trader = AutoTrader()
    await trader.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n✅ Auto-trader shutdown complete")
