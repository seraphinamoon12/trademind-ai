"""Integration tests with live IB Gateway.

These tests require a real IB Gateway connection (paper trading).
Marked with pytest.mark.integration and will be skipped if not available.
"""
import asyncio
import os
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.brokers.ibkr.ibkr_insync_broker import IBKRInsyncBroker, CircuitState
from src.brokers.base import Order, OrderSide, OrderType, OrderStatus
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def broker():
    """Create a broker instance for testing."""
    broker = IBKRInsyncBroker()
    yield broker
    if broker.is_connected:
        asyncio.run(broker.disconnect())


def check_ib_gateway_available():
    """Check if IB Gateway is available for testing."""
    host = os.getenv("IBKR_HOST", "127.0.0.1")
    port = int(os.getenv("IBKR_PORT", "7497"))
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def pytest_collection_modifyitems(config, items):
    """Skip integration tests if IB Gateway is not available."""
    if not check_ib_gateway_available():
        skip_marker = pytest.mark.skip(
            reason="IB Gateway not available - set IBKR_HOST and IBKR_PORT env vars"
        )
        for item in items:
            if item.get_closest_marker("integration"):
                item.add_marker(skip_marker)


@pytest.mark.asyncio
async def test_connection(broker):
    """Test connection to IB Gateway."""
    logger.info("=" * 60)
    logger.info("TEST: Connection")
    logger.info("=" * 60)

    try:
        await broker.connect()
        assert broker.is_connected, "Broker should be connected"
        logger.info("✓ Connection test passed")
    except Exception as e:
        logger.error(f"✗ Connection test failed: {e}")
        raise


@pytest.mark.asyncio
async def test_get_positions(broker):
    """Test fetching positions from IB Gateway."""
    logger.info("=" * 60)
    logger.info("TEST: Get Positions")
    logger.info("=" * 60)

    try:
        await broker.connect()
        positions = await broker.get_positions()
        assert isinstance(positions, list), "Positions should be a list"
        logger.info(f"✓ Fetched {len(positions)} positions")

        for pos in positions:
            logger.info(f"  {pos.symbol}: {pos.quantity} shares @ ${pos.avg_cost:.2f}")

    except Exception as e:
        logger.error(f"✗ Get positions test failed: {e}")
        raise


@pytest.mark.asyncio
async def test_get_account(broker):
    """Test fetching account data from IB Gateway."""
    logger.info("=" * 60)
    logger.info("TEST: Get Account")
    logger.info("=" * 60)

    try:
        await broker.connect()
        account = await broker.get_account()
        assert account.account_id, "Account should have an ID"
        assert account.cash_balance >= 0, "Cash balance should be non-negative"
        assert account.portfolio_value >= 0, "Portfolio value should be non-negative"
        assert account.buying_power >= 0, "Buying power should be non-negative"

        logger.info(f"✓ Account ID: {account.account_id}")
        logger.info(f"  Cash Balance: ${account.cash_balance:,.2f}")
        logger.info(f"  Portfolio Value: ${account.portfolio_value:,.2f}")
        logger.info(f"  Buying Power: ${account.buying_power:,.2f}")

    except Exception as e:
        logger.error(f"✗ Get account test failed: {e}")
        raise


@pytest.mark.asyncio
async def test_place_order(broker):
    """Test placing a paper trade order."""
    logger.info("=" * 60)
    logger.info("TEST: Place Order")
    logger.info("=" * 60)

    order_id = None
    try:
        await broker.connect()

        # Use a low-price stock like SPY for testing
        order = Order(
            order_id="test_" + str(int(asyncio.get_event_loop().time())),
            symbol="SPY",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=1,
            price=0.01,  # Very low price to avoid execution
        )

        is_valid, message = await broker.validate_order(order)
        if not is_valid:
            logger.warning(f"Order validation failed: {message}")
            pytest.skip("Order validation failed - skipping placement test")

        order_id = await broker.place_order(order)
        assert order_id, "Order ID should be returned"
        logger.info(f"✓ Order placed: {order_id}")

    except Exception as e:
        logger.error(f"✗ Place order test failed: {e}")
        raise
    finally:
        # Clean up: cancel the order if it was placed
        if order_id:
            try:
                await asyncio.sleep(1)  # Give IB time to process
                cancelled = await broker.cancel_order(order_id)
                if cancelled:
                    logger.info(f"✓ Order {order_id} cancelled")
            except Exception as e:
                logger.warning(f"Could not cancel order {order_id}: {e}")


@pytest.mark.asyncio
async def test_cancel_order(broker):
    """Test cancelling an order."""
    logger.info("=" * 60)
    logger.info("TEST: Cancel Order")
    logger.info("=" * 60)

    order_id = None
    try:
        await broker.connect()

        # Place a test order
        order = Order(
            order_id="test_" + str(int(asyncio.get_event_loop().time())),
            symbol="SPY",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=1,
            price=0.01,  # Very low price
        )

        order_id = await broker.place_order(order)
        assert order_id, "Order ID should be returned"
        logger.info(f"✓ Order placed: {order_id}")

        # Wait a moment for IB to process
        await asyncio.sleep(1)

        # Cancel the order
        cancelled = await broker.cancel_order(order_id)
        assert cancelled, "Order should be cancelled"
        logger.info(f"✓ Order {order_id} cancelled")

    except Exception as e:
        logger.error(f"✗ Cancel order test failed: {e}")
        raise


@pytest.mark.asyncio
async def test_stop_limit_order(broker):
    """Test placing a stop-limit order."""
    logger.info("=" * 60)
    logger.info("TEST: Stop-Limit Order")
    logger.info("=" * 60)

    order_id = None
    try:
        await broker.connect()

        # Place a stop-limit order (prices far from market to avoid execution)
        order = Order(
            order_id="test_" + str(int(asyncio.get_event_loop().time())),
            symbol="SPY",
            side=OrderSide.BUY,
            order_type=OrderType.STOP_LIMIT,
            quantity=1,
            stop_price=1000.0,  # High stop price
            price=1001.0,  # High limit price
        )

        is_valid, message = await broker.validate_order(order)
        if not is_valid:
            logger.warning(f"Order validation failed: {message}")
            pytest.skip("Order validation failed - skipping placement test")

        order_id = await broker.place_order(order)
        assert order_id, "Order ID should be returned"
        logger.info(f"✓ Stop-limit order placed: {order_id}")

    except Exception as e:
        logger.error(f"✗ Stop-limit order test failed: {e}")
        raise
    finally:
        # Clean up: cancel the order if it was placed
        if order_id:
            try:
                await asyncio.sleep(1)
                cancelled = await broker.cancel_order(order_id)
                if cancelled:
                    logger.info(f"✓ Stop-limit order {order_id} cancelled")
            except Exception as e:
                logger.warning(f"Could not cancel order {order_id}: {e}")


@pytest.mark.asyncio
async def test_reconnection(broker):
    """Test disconnecting and reconnecting to IB Gateway."""
    logger.info("=" * 60)
    logger.info("TEST: Reconnection")
    logger.info("=" * 60)

    try:
        # Connect initially
        await broker.connect()
        assert broker.is_connected, "Broker should be connected initially"
        logger.info("✓ Initial connection successful")

        # Disconnect
        await broker.disconnect()
        assert not broker.is_connected, "Broker should be disconnected"
        logger.info("✓ Disconnection successful")

        # Reconnect
        await broker.connect()
        assert broker.is_connected, "Broker should be reconnected"
        logger.info("✓ Reconnection successful")

    except Exception as e:
        logger.error(f"✗ Reconnection test failed: {e}")
        raise


@pytest.mark.asyncio
async def test_circuit_breaker():
    """Test circuit breaker triggers after multiple failures."""
    logger.info("=" * 60)
    logger.info("TEST: Circuit Breaker")
    logger.info("=" * 60)

    broker = IBKRInsyncBroker()
    try:
        # Set low failure threshold for testing
        broker._circuit_breaker_failure_threshold = 3
        broker._circuit_breaker_cooldown_seconds = 5

        # Record failures to trigger circuit breaker
        for i in range(3):
            broker._record_connection_failure()
            logger.info(f"Recorded failure {i+1}/3, state: {broker._circuit_state.value}")

        # Circuit should be OPEN now
        assert broker._circuit_state == CircuitState.OPEN, "Circuit should be OPEN after threshold failures"
        logger.info("✓ Circuit breaker OPEN after threshold failures")

        # Check that circuit breaker rejects connection
        can_connect = broker._check_circuit_breaker()
        assert not can_connect, "Circuit breaker should reject connection when OPEN"
        logger.info("✓ Circuit breaker rejected connection while OPEN")

        # Wait for cooldown to expire
        await asyncio.sleep(broker._circuit_breaker_cooldown_seconds + 1)

        # Circuit should be HALF_OPEN now
        can_connect = broker._check_circuit_breaker()
        assert can_connect, "Circuit breaker should allow connection after cooldown"
        assert broker._circuit_state == CircuitState.HALF_OPEN, "Circuit should be HALF_OPEN after cooldown"
        logger.info("✓ Circuit breaker HALF_OPEN after cooldown")

        # Test reset on successful connection
        broker._reset_circuit_breaker()
        assert broker._circuit_state == CircuitState.CLOSED, "Circuit should be CLOSED after reset"
        assert broker._failure_count == 0, "Failure count should be 0 after reset"
        logger.info("✓ Circuit breaker reset successfully")

    finally:
        if broker.is_connected:
            await broker.disconnect()


@pytest.mark.asyncio
async def test_get_market_price(broker):
    """Test fetching market price for a symbol."""
    logger.info("=" * 60)
    logger.info("TEST: Get Market Price")
    logger.info("=" * 60)

    try:
        await broker.connect()
        price = await broker.get_market_price("AAPL")
        assert price > 0, "Price should be positive"
        logger.info(f"✓ AAPL Market Price: ${price:.2f}")

    except Exception as e:
        logger.error(f"✗ Get market price test failed: {e}")
        raise


@pytest.mark.asyncio
async def test_get_portfolio_summary(broker):
    """Test fetching portfolio summary."""
    logger.info("=" * 60)
    logger.info("TEST: Get Portfolio Summary")
    logger.info("=" * 60)

    try:
        await broker.connect()
        summary = await broker.get_portfolio_summary()
        assert "account_id" in summary, "Summary should contain account_id"
        assert "cash_balance" in summary, "Summary should contain cash_balance"
        assert "portfolio_value" in summary, "Summary should contain portfolio_value"
        assert "buying_power" in summary, "Summary should contain buying_power"

        logger.info(f"✓ Portfolio Summary:")
        logger.info(f"  Account: {summary['account_id']}")
        logger.info(f"  Positions: {summary['num_positions']}")
        logger.info(f"  Portfolio Value: ${summary['portfolio_value']:,.2f}")

    except Exception as e:
        logger.error(f"✗ Get portfolio summary test failed: {e}")
        raise


@pytest.mark.asyncio
async def test_get_orders(broker):
    """Test fetching orders."""
    logger.info("=" * 60)
    logger.info("TEST: Get Orders")
    logger.info("=" * 60)

    try:
        await broker.connect()
        orders = await broker.get_orders()
        assert isinstance(orders, list), "Orders should be a list"
        logger.info(f"✓ Fetched {len(orders)} orders")

        for order in orders:
            logger.info(
                f"  {order.side.value} {order.quantity} {order.symbol} "
                f"({order.order_type.value}) - {order.status.value}"
            )

    except Exception as e:
        logger.error(f"✗ Get orders test failed: {e}")
        raise


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
