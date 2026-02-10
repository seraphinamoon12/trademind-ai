"""Simple test to check if request queue works."""
import asyncio
import sys
import os
import logging
import time

# Enable info logging
logging.basicConfig(
    level=logging.INFO,
    format='%(name)s - %(levelname)s - %(message)s'
)

sys.path.insert(0, os.path.dirname(__file__))

from src.brokers.ibkr.async_broker import IBKRThreadedBroker


async def test():
    print("Connecting...")
    broker = IBKRThreadedBroker(host='127.0.0.1', port=7497, client_id=11)

    try:
        await broker.connect()
        print(f"Connected! Thread running: {broker._thread.running.is_set()}")
        print(f"Next order ID: {broker._thread.wrapper.next_order_id}")

        print("\nWaiting 2 seconds...")
        await asyncio.sleep(2)

        print("\nCalling get_account()...")
        account = await broker.get_account()
        print(f"SUCCESS! Cash: ${account.cash_balance:,.2f}")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if broker.is_connected:
            await broker.disconnect()


if __name__ == "__main__":
    asyncio.run(test())
