#!/usr/bin/env python3
"""
Paper trading validation script.
Run for a week to verify all functionality before going live.
"""
import asyncio
import json
from datetime import datetime
from src.brokers.ibkr.client import IBKRBroker
from src.brokers.base import Order, OrderType, OrderSide


class PaperTradingValidator:
    """Validates IBKR paper trading functionality."""
    
    def __init__(self, broker: IBKRBroker):
        self.broker = broker
        self.results = []
    
    async def validate_connection(self):
        """Test connection and disconnection."""
        print("Validating connection...")
        assert self.broker.is_connected
        print("✓ Connection validated")
    
    async def validate_order_placement(self):
        """Test order placement and cancellation."""
        print("\nValidating order placement...")
        
        market_order = Order(
            order_id=f"validate-market-{int(datetime.now().timestamp())}",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=1
        )
        order_id = await self.broker.place_order(market_order)
        print(f"✓ Market order placed: {order_id}")
        
        limit_order = Order(
            order_id=f"validate-limit-{int(datetime.now().timestamp())}",
            symbol="TSLA",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=1,
            price=100.0
        )
        limit_id = await self.broker.place_order(limit_order)
        print(f"✓ Limit order placed: {limit_id}")
        
        await self.broker.cancel_order(limit_id)
        print(f"✓ Limit order cancelled")
        
        self.results.append({"test": "order_placement", "status": "passed"})
    
    async def validate_position_tracking(self):
        """Test position synchronization."""
        print("\nValidating position tracking...")
        
        positions = await self.broker.get_positions()
        print(f"✓ Retrieved {len(positions)} positions")
        
        for pos in positions:
            print(f"  - {pos.symbol}: {pos.quantity} @ ${pos.avg_cost:.2f}")
        
        self.results.append({"test": "position_tracking", "status": "passed"})
    
    async def validate_account_info(self):
        """Test account information retrieval."""
        print("\nValidating account info...")
        
        account = await self.broker.get_account()
        print(f"✓ Account: {account.account_id}")
        print(f"  - Cash: ${account.cash_balance:,.2f}")
        print(f"  - Portfolio Value: ${account.portfolio_value:,.2f}")
        print(f"  - Buying Power: ${account.buying_power:,.2f}")
        
        self.results.append({"test": "account_info", "status": "passed"})
    
    async def validate_market_data(self):
        """Test market data retrieval."""
        print("\nValidating market data...")
        
        price = await self.broker.get_market_price("SPY")
        print(f"✓ SPY price: ${price:.2f}")
        
        bars = await self.broker.get_historical_bars("SPY", duration="1 D", bar_size="1 hour")
        print(f"✓ Retrieved {len(bars)} historical bars")
        
        self.results.append({"test": "market_data", "status": "passed"})
    
    async def run_all_validations(self):
        """Run all validation tests."""
        print("=" * 50)
        print("PAPER TRADING VALIDATION")
        print("=" * 50)
        
        try:
            await self.validate_connection()
            await self.validate_order_placement()
            await self.validate_position_tracking()
            await self.validate_account_info()
            await self.validate_market_data()
            
            print("\n" + "=" * 50)
            print("ALL VALIDATIONS PASSED ✓")
            print("=" * 50)
            
            with open("validation_results.json", "w") as f:
                json.dump({
                    "timestamp": datetime.now().isoformat(),
                    "results": self.results,
                    "status": "passed"
                }, f, indent=2)
            
            return True
            
        except Exception as e:
            print(f"\n✗ VALIDATION FAILED: {e}")
            return False


async def main():
    """Main validation entry point."""
    broker = IBKRBroker(port=7497, paper_trading=True)
    
    try:
        await broker.connect()
        validator = PaperTradingValidator(broker)
        success = await validator.run_all_validations()
        return 0 if success else 1
    finally:
        await broker.disconnect()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
