#!/usr/bin/env python3
"""Place a paper trade directly via IB Gateway."""
import asyncio
import sys
sys.path.insert(0, '.')

from src.brokers.ibkr.ibkr_insync_broker import IBKRInsyncBroker
from src.brokers.base import Order, OrderType, OrderSide


async def place_paper_trade():
    """Place a paper trade via IB Gateway."""
    print("=" * 60)
    print("🚀 TradeMind AI - Direct Paper Trading")
    print("=" * 60)
    
    # Connect to IB Gateway
    print("\n📡 Connecting to IB Gateway...")
    broker = IBKRInsyncBroker(
        host='127.0.0.1',
        port=7497,
        client_id=200
    )
    
    try:
        await broker.connect()
        print("✅ Connected to IB Gateway (Paper Trading)")
        
        # Get account info
        print("\n💰 Account Information:")
        account = await broker.get_account()
        print(f"   Account ID: {account.account_id}")
        print(f"   Cash Balance: ${account.cash_balance:,.2f}")
        print(f"   Buying Power: ${account.buying_power:,.2f}")
        
        # Create order - simple limit order
        print("\n📊 Placing Paper Trade...")
        print("   Symbol: AAPL")
        print("   Quantity: 10 shares")
        print("   Side: BUY")
        print("   Type: LIMIT")
        print("   Price: $190.00")
        
        order = Order(
            order_id="",
            symbol="AAPL",
            quantity=10,
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            price=190.00
        )
        
        # Place order directly without validation that needs market data
        print("\n📝 Submitting order to IB Gateway...")

        order_id = await broker.place_order(order)

        print(f"✅ Order placed!")
        print(f"   Order ID: {order_id}")
        print(f"   Status: Submitted")
        
        # Wait a moment
        await asyncio.sleep(2)
        
        # Check orders
        print("\n📋 Checking open orders...")
        orders = await broker.get_orders()
        if orders:
            for o in orders:
                print(f"   {o.order_id}: {o.symbol} {o.side.value} {o.quantity} @ ${o.price} - {o.status.value}")
        else:
            print("   No open orders (may have filled instantly in paper trading)")
        
        print("\n" + "=" * 60)
        print("✅ Paper trade submitted successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n🔌 Disconnecting...")
        await broker.disconnect()
        print("✅ Disconnected")


if __name__ == "__main__":
    asyncio.run(place_paper_trade())
