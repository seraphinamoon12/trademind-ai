"""Test stub for threaded IBKR client integration."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from src.brokers.ibkr.async_broker import IBKRThreadedBroker


async def test_connection():
    """Test basic connection and account retrieval."""
    print("=" * 60)
    print("Testing IBKR Threaded Client")
    print("=" * 60)

    broker = IBKRThreadedBroker(
        host='127.0.0.1',
        port=7497,
        client_id=10
    )

    try:
        print("\n[1/4] Connecting to IB Gateway...")
        await broker.connect()
        print("      ✓ Connected successfully")

        print("\n[2/4] Getting account information...")
        account = await broker.get_account()
        print(f"      Account ID: {account.account_id}")
        print(f"      Cash Balance: ${account.cash_balance:,.2f}")
        print(f"      Portfolio Value: ${account.portfolio_value:,.2f}")
        print(f"      Buying Power: ${account.buying_power:,.2f}")
        print(f"      ✓ Account info retrieved")

        print("\n[3/4] Getting positions...")
        positions = await broker.get_positions()
        print(f"      Found {len(positions)} positions:")
        for pos in positions:
            print(f"        - {pos.symbol}: {pos.quantity} shares @ ${pos.current_price:.2f}")
        print(f"      ✓ Positions retrieved")

        print("\n[4/4] Getting portfolio summary...")
        summary = await broker.get_portfolio_summary()
        print(f"      Total Value: ${summary['total_value']:,.2f}")
        print(f"      Cash Balance: ${summary['cash_balance']:,.2f}")
        print(f"      Invested Value: ${summary['invested_value']:,.2f}")
        print(f"      Open Positions: {summary['open_positions']}")
        print(f"      ✓ Portfolio summary retrieved")

        print("\n" + "=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if broker.is_connected:
            print("\nDisconnecting...")
            await broker.disconnect()
            print("      ✓ Disconnected")


async def test_market_price():
    """Test getting market price for a symbol."""
    print("\n" + "=" * 60)
    print("Testing Market Price Retrieval")
    print("=" * 60)

    broker = IBKRThreadedBroker(
        host='127.0.0.1',
        port=7497,
        client_id=11
    )

    try:
        print("\nConnecting...")
        await broker.connect()
        print("✓ Connected")

        symbols = ['AAPL', 'MSFT', 'GOOGL']
        for symbol in symbols:
            print(f"\nGetting price for {symbol}...")
            try:
                price = await broker.get_market_price(symbol)
                print(f"  {symbol}: ${price:.2f}")
            except Exception as e:
                print(f"  Error getting {symbol}: {e}")

    finally:
        if broker.is_connected:
            await broker.disconnect()


async def test_historical_data():
    """Test getting historical data."""
    print("\n" + "=" * 60)
    print("Testing Historical Data")
    print("=" * 60)

    broker = IBKRThreadedBroker(
        host='127.0.0.1',
        port=7497,
        client_id=12
    )

    try:
        print("\nConnecting...")
        await broker.connect()
        print("✓ Connected")

        print("\nGetting 1-hour bars for AAPL...")
        bars = await broker.get_historical_bars(
            'AAPL',
            duration='1 D',
            bar_size='1 hour',
            what_to_show='TRADES'
        )
        print(f"Retrieved {len(bars)} bars")
        if bars:
            print(f"Most recent bar: {bars[-1]}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if broker.is_connected:
            await broker.disconnect()


async def test_order_validation():
    """Test order validation."""
    print("\n" + "=" * 60)
    print("Testing Order Validation")
    print("=" * 60)

    from src.brokers.base import Order, OrderType, OrderSide

    broker = IBKRThreadedBroker(
        host='127.0.0.1',
        port=7497,
        client_id=13
    )

    try:
        print("\nConnecting...")
        await broker.connect()
        print("✓ Connected")

        test_order = Order(
            order_id="test_1",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10
        )

        print(f"\nValidating order: Buy 10 shares of AAPL at market...")
        valid, message = await broker.validate_order(test_order)
        print(f"  Valid: {valid}")
        print(f"  Message: {message}")

        test_order = Order(
            order_id="test_2",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=1000,
            price=100.0
        )

        print(f"\nValidating order: Buy 1000 shares of AAPL at $100...")
        valid, message = await broker.validate_order(test_order)
        print(f"  Valid: {valid}")
        print(f"  Message: {message}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if broker.is_connected:
            await broker.disconnect()


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("IBKR Threaded Client Test Suite")
    print("=" * 60)
    print("\nMake sure IB Gateway is running on port 7497")
    print("Press Enter to start or Ctrl+C to cancel...")
    try:
        await asyncio.to_thread(input)
    except KeyboardInterrupt:
        print("\nCancelled")
        return

    await test_connection()
    await test_market_price()
    await test_historical_data()
    await test_order_validation()


if __name__ == "__main__":
    asyncio.run(main())
