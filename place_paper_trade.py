#!/usr/bin/env python3
"""Place a paper trade through IB Gateway."""
import asyncio
import sys
sys.path.insert(0, '.')

from src.brokers.ibkr.async_broker import IBKRThreadedBroker
from src.brokers.base import Order, OrderType, OrderSide


async def place_paper_trade():
    """Place a paper trade via IB Gateway."""
    print("=" * 60)
    print("🚀 TradeMind AI - Paper Trading via IB Gateway")
    print("=" * 60)
    
    # Connect to IB Gateway
    print("\n📡 Connecting to IB Gateway...")
    broker = IBKRThreadedBroker(
        host='127.0.0.1',
        port=7497,  # Paper trading port
        client_id=100,  # Unique client ID for this session
        paper_trading=True
    )
    
    try:
        await broker.connect()
        print("✅ Connected to IB Gateway (Paper Trading)")
        
        # Get account info
        print("\n💰 Getting account information...")
        account = await broker.get_account()
        print(f"   Account ID: {account.account_id}")
        print(f"   Cash Balance: ${account.cash_balance:,.2f}")
        print(f"   Buying Power: ${account.buying_power:,.2f}")
        
        # Create order
        print("\n📊 Placing paper trade...")
        print("   Symbol: AAPL")
        print("   Quantity: 10 shares")
        print("   Side: BUY")
        print("   Type: MARKET")
        
        order = Order(
            order_id="",  # Will be assigned by broker
            symbol="AAPL",
            quantity=10,
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            price=0.0  # Market order
        )
        
        # Place order
        order_id = await broker.place_order(order)
        print(f"\n✅ Order placed successfully!")
        print(f"   Order ID: {order_id}")
        print(f"   Status: {order.status.value}")
        
        # Wait a moment for order to process
        print("\n⏳ Waiting for order status...")
        await asyncio.sleep(2)
        
        # Get order status
        orders = await broker.get_orders()
        print(f"\n📋 Open Orders: {len(orders)}")
        for o in orders:
            print(f"   {o.order_id}: {o.symbol} {o.side.value} {o.quantity} @ {o.price} - {o.status.value}")
        
        # Get positions
        print("\n📈 Current Positions:")
        positions = await broker.get_positions()
        if positions:
            for pos in positions:
                print(f"   {pos.symbol}: {pos.quantity} shares @ ${pos.avg_cost:.2f}")
        else:
            print("   No positions yet (market order may still be filling)")
        
        print("\n" + "=" * 60)
        print("✅ Paper trade demonstration complete!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n🔌 Disconnecting from IB Gateway...")
        await broker.disconnect()
        print("✅ Disconnected")


if __name__ == "__main__":
    asyncio.run(place_paper_trade())
