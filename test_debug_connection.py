"""Debug connection test for IBKR threaded broker."""
import asyncio
import sys
import os
import logging

# Enable debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

sys.path.insert(0, os.path.dirname(__file__))

from src.brokers.ibkr.async_broker import IBKRThreadedBroker


async def test_connection():
    """Test basic connection and account retrieval."""
    print("=" * 60)
    print("Testing IBKR Threaded Client (DEBUG MODE)")
    print("=" * 60)

    broker = IBKRThreadedBroker(
        host='127.0.0.1',
        port=7497,
        client_id=10
    )

    try:
        print("\n[1/2] Connecting to IB Gateway...")
        await broker.connect()
        print("      ✓ Connected successfully")

        # Give it a moment
        await asyncio.sleep(2)

        print("\n[2/2] Getting account information...")
        print("      Sending account summary request...")
        account = await broker.get_account()
        print(f"      Account ID: {account.account_id}")
        print(f"      Cash Balance: ${account.cash_balance:,.2f}")
        print(f"      Portfolio Value: ${account.portfolio_value:,.2f}")
        print(f"      Buying Power: ${account.buying_power:,.2f}")
        print(f"      ✓ Account info retrieved")

        print("\n" + "=" * 60)
        print("Test passed! ✓")
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
