"""Quick connection test for IBKR threaded broker."""
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
        print("\n[1/3] Connecting to IB Gateway...")
        await broker.connect()
        print("      ✓ Connected successfully")

        print("\n[2/3] Getting account information...")
        account = await broker.get_account()
        print(f"      Account ID: {account.account_id}")
        print(f"      Cash Balance: ${account.cash_balance:,.2f}")
        print(f"      Portfolio Value: ${account.portfolio_value:,.2f}")
        print(f"      Buying Power: ${account.buying_power:,.2f}")
        print(f"      ✓ Account info retrieved")

        print("\n[3/3] Getting positions...")
        positions = await broker.get_positions()
        print(f"      Found {len(positions)} positions:")
        for pos in positions:
            print(f"        - {pos.symbol}: {pos.quantity} shares @ ${pos.current_price:.2f}")
        print(f"      ✓ Positions retrieved")

        print("\n" + "=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        if broker.is_connected:
            print("\nDisconnecting...")
            await broker.disconnect()
            print("      ✓ Disconnected")


if __name__ == "__main__":
    success = asyncio.run(test_connection())
    sys.exit(0 if success else 1)
