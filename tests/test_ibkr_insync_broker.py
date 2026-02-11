"""Test script for IBKRInsyncBroker with proper mocking.

Tests are designed to run without requiring a real IB Gateway connection.
Uses unittest.mock to mock the ib_insync library.
"""
import asyncio
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.brokers.ibkr.ibkr_insync_broker import IBKRInsyncBroker
from src.brokers.base import Order, OrderSide, OrderType
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MockIB:
    """Mock ib_insync.IB class for testing."""

    def __init__(self):
        self._connected = False
        self._managed_accounts = ["U12345678"]
        self._positions = []
        self._trades = []
        self._account_summary = []

    def isConnected(self):
        return self._connected

    def managedAccounts(self):
        return self._managed_accounts

    def positions(self):
        return self._positions

    def openTrades(self):
        return self._trades

    async def accountSummaryAsync(self):
        return self._account_summary

    async def connectAsync(self, host, port, clientId, timeout):
        await asyncio.sleep(0.1)
        self._connected = True

    def disconnect(self):
        self._connected = False

    def reqPositions(self):
        pass

    def reqMktData(self, contract, tick_types, snapshot, regulatory):
        mock_ticker = Mock()
        mock_ticker.marketPrice = Mock(return_value=150.0)
        mock_ticker.last = 150.0
        mock_ticker.ask = 150.5
        mock_ticker.bid = 149.5
        return mock_ticker

    def placeOrder(self, contract, order):
        mock_trade = Mock()
        mock_trade.order = Mock()
        mock_trade.order.orderId = 1001
        return mock_trade

    def cancelOrder(self, order):
        pass

    async def reqHistoricalDataAsync(self, contract, endDateTime, durationStr, barSizeSetting, whatToShow, useRTH, formatDate):
        mock_bars = []
        for i in range(5):
            mock_bar = Mock()
            mock_bar.date = Mock()
            mock_bar.date.isoformat = Mock(return_value=f"2024-01-{10+i:02d}T00:00:00")
            mock_bar.open = 149.0 + i
            mock_bar.high = 151.0 + i
            mock_bar.low = 148.0 + i
            mock_bar.close = 150.0 + i
            mock_bar.volume = 1000000
            mock_bar.barCount = 100
            mock_bars.append(mock_bar)
        return mock_bars


def create_mock_position(symbol, quantity, avg_cost):
    """Create a mock position object."""
    mock_pos = Mock()
    mock_pos.contract = Mock()
    mock_pos.contract.symbol = symbol
    mock_pos.contract.currency = "USD"
    mock_pos.position = quantity
    mock_pos.avgCost = avg_cost
    return mock_pos


def create_mock_account_summary_item(tag, value):
    """Create a mock account summary item."""
    mock_item = Mock()
    mock_item.tag = tag
    mock_item.value = value
    return mock_item


def create_mock_trade(order_id, symbol, side, order_type, status, filled=0):
    """Create a mock trade object."""
    mock_trade = Mock()
    mock_trade.contract = Mock()
    mock_trade.contract.symbol = symbol
    mock_trade.order = Mock()
    mock_trade.order.orderId = order_id
    mock_trade.order.action = side
    mock_trade.order.orderType = order_type
    mock_trade.order.totalQuantity = 100
    mock_trade.order.lmtPrice = 150.0
    mock_trade.order.auxPrice = None
    mock_trade.orderStatus = Mock()
    mock_trade.orderStatus.status = status
    mock_trade.orderStatus.filled = filled
    mock_trade.orderStatus.avgFillPrice = 150.0
    return mock_trade


async def test_connection():
    """Test connection to IB Gateway with mocking."""
    logger.info("=" * 60)
    logger.info("TEST 1: Connection")
    logger.info("=" * 60)

    with patch('src.brokers.ibkr.ibkr_insync_broker.IB', MockIB):
        broker = IBKRInsyncBroker()

        try:
            await broker.connect()
            logger.info(f"✓ Connected: {broker.is_connected}")

            await broker.disconnect()
            logger.info(f"✓ Disconnected: {not broker.is_connected}")

            return True
        except Exception as e:
            logger.error(f"✗ Connection test failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False


async def test_positions():
    """Test fetching positions with mocking."""
    logger.info("=" * 60)
    logger.info("TEST 2: Positions")
    logger.info("=" * 60)

    with patch('src.brokers.ibkr.ibkr_insync_broker.IB', MockIB):
        broker = IBKRInsyncBroker()

        try:
            await broker.connect()
            logger.info(f"✓ Connected")

            # Setup mock positions
            broker._ib._positions = [
                create_mock_position("AAPL", 100, 150.0),
                create_mock_position("GOOGL", 50, 2500.0),
                create_mock_position("MSFT", 75, 300.0),
            ]

            positions = await broker.get_positions()
            logger.info(f"✓ Fetched {len(positions)} positions")

            for i, pos in enumerate(positions, 1):
                logger.info(
                    f"  Position {i}: {pos.symbol} - {pos.quantity} shares @ "
                    f"${pos.avg_cost:.2f} (P&L: ${pos.unrealized_pnl:.2f})"
                )

            await broker.disconnect()
            return True
        except Exception as e:
            logger.error(f"✗ Positions test failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False


async def test_account_summary():
    """Test fetching account summary with mocking."""
    logger.info("=" * 60)
    logger.info("TEST 3: Account Summary")
    logger.info("=" * 60)

    with patch('src.brokers.ibkr.ibkr_insync_broker.IB', MockIB):
        broker = IBKRInsyncBroker()

        try:
            await broker.connect()
            logger.info(f"✓ Connected")

            # Setup mock account summary
            broker._ib._account_summary = [
                create_mock_account_summary_item("AccountCode", "U12345678"),
                create_mock_account_summary_item("TotalCashBalance", "100000.00"),
                create_mock_account_summary_item("NetLiquidation", "150000.00"),
                create_mock_account_summary_item("BuyingPower", "200000.00"),
                create_mock_account_summary_item("AvailableFunds", "100000.00"),
                create_mock_account_summary_item("RealizedPnL", "5000.00"),
                create_mock_account_summary_item("UnrealizedPnL", "10000.00"),
            ]

            account = await broker.get_account()
            logger.info(f"✓ Account: {account.account_id}")
            logger.info(f"  Cash Balance: ${account.cash_balance:,.2f}")
            logger.info(f"  Portfolio Value: ${account.portfolio_value:,.2f}")
            logger.info(f"  Buying Power: ${account.buying_power:,.2f}")
            logger.info(f"  Total P&L: ${account.total_pnl:,.2f}")

            await broker.disconnect()
            return True
        except Exception as e:
            logger.error(f"✗ Account summary test failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False


async def test_portfolio_summary():
    """Test fetching portfolio summary with mocking."""
    logger.info("=" * 60)
    logger.info("TEST 4: Portfolio Summary")
    logger.info("=" * 60)

    with patch('src.brokers.ibkr.ibkr_insync_broker.IB', MockIB):
        broker = IBKRInsyncBroker()

        try:
            await broker.connect()
            logger.info(f"✓ Connected")

            # Setup mock data
            broker._ib._account_summary = [
                create_mock_account_summary_item("AccountCode", "U12345678"),
                create_mock_account_summary_item("TotalCashBalance", "100000.00"),
                create_mock_account_summary_item("NetLiquidation", "150000.00"),
                create_mock_account_summary_item("BuyingPower", "200000.00"),
                create_mock_account_summary_item("AvailableFunds", "100000.00"),
                create_mock_account_summary_item("RealizedPnL", "5000.00"),
                create_mock_account_summary_item("UnrealizedPnL", "10000.00"),
            ]
            broker._ib._positions = [
                create_mock_position("AAPL", 100, 150.0),
            ]

            summary = await broker.get_portfolio_summary()
            logger.info(f"✓ Portfolio Summary:")
            logger.info(f"  Account: {summary['account_id']}")
            logger.info(f"  Positions: {summary['num_positions']}")
            logger.info(f"  Market Value: ${summary['total_market_value']:,.2f}")
            logger.info(f"  Unrealized P&L: ${summary['total_unrealized_pnl']:,.2f}")

            await broker.disconnect()
            return True
        except Exception as e:
            logger.error(f"✗ Portfolio summary test failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False


async def test_market_price():
    """Test fetching market price with mocking."""
    logger.info("=" * 60)
    logger.info("TEST 5: Market Price")
    logger.info("=" * 60)

    with patch('src.brokers.ibkr.ibkr_insync_broker.IB', MockIB):
        broker = IBKRInsyncBroker()

        try:
            await broker.connect()
            logger.info(f"✓ Connected")

            price = await broker.get_market_price("AAPL")
            logger.info(f"✓ AAPL Market Price: ${price:.2f}")

            await broker.disconnect()
            return True
        except Exception as e:
            logger.error(f"✗ Market price test failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False


async def test_order_validation():
    """Test order validation with mocking."""
    logger.info("=" * 60)
    logger.info("TEST 6: Order Validation")
    logger.info("=" * 60)

    with patch('src.brokers.ibkr.ibkr_insync_broker.IB', MockIB):
        broker = IBKRInsyncBroker()

        try:
            await broker.connect()
            logger.info(f"✓ Connected")

            # Setup mock account for validation
            broker._ib._account_summary = [
                create_mock_account_summary_item("AccountCode", "U12345678"),
                create_mock_account_summary_item("TotalCashBalance", "100000.00"),
                create_mock_account_summary_item("NetLiquidation", "150000.00"),
                create_mock_account_summary_item("BuyingPower", "200000.00"),
                create_mock_account_summary_item("AvailableFunds", "100000.00"),
            ]

            order = Order(
                order_id="test_001",
                symbol="AAPL",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=10,
                price=None
            )

            is_valid, message = await broker.validate_order(order)
            logger.info(f"✓ Order validation: {is_valid} - {message}")

            invalid_order = Order(
                order_id="test_002",
                symbol="",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=10,
                price=None
            )

            is_valid, message = await broker.validate_order(invalid_order)
            logger.info(f"✓ Invalid order validation: {is_valid} - {message}")

            await broker.disconnect()
            return True
        except Exception as e:
            logger.error(f"✗ Order validation test failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False


async def test_orders():
    """Test fetching orders with mocking."""
    logger.info("=" * 60)
    logger.info("TEST 7: Orders")
    logger.info("=" * 60)

    with patch('src.brokers.ibkr.ibkr_insync_broker.IB', MockIB):
        broker = IBKRInsyncBroker()

        try:
            await broker.connect()
            logger.info(f"✓ Connected")

            # Setup mock trades
            broker._ib._trades = [
                create_mock_trade(1001, "AAPL", "BUY", "MKT", "Submitted"),
                create_mock_trade(1002, "GOOGL", "SELL", "LMT", "Filled", 100),
            ]

            orders = await broker.get_orders()
            logger.info(f"✓ Fetched {len(orders)} open orders")

            for i, order in enumerate(orders, 1):
                logger.info(
                    f"  Order {i}: {order.side.value} {order.quantity} {order.symbol} "
                    f"({order.status.value})"
                )

            await broker.disconnect()
            return True
        except Exception as e:
            logger.error(f"✗ Orders test failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False


async def test_historical_bars():
    """Test fetching historical bars with mocking."""
    logger.info("=" * 60)
    logger.info("TEST 8: Historical Bars")
    logger.info("=" * 60)

    with patch('src.brokers.ibkr.ibkr_insync_broker.IB', MockIB):
        broker = IBKRInsyncBroker()

        try:
            await broker.connect()
            logger.info(f"✓ Connected")

            bars = await broker.get_historical_bars(
                symbol="AAPL",
                duration="1 D",
                bar_size="5 mins",
                what_to_show="TRADES"
            )
            logger.info(f"✓ Fetched {len(bars)} historical bars")

            if bars:
                logger.info(f"  First bar: {bars[0]}")
                logger.info(f"  Last bar: {bars[-1]}")

            await broker.disconnect()
            return True
        except Exception as e:
            logger.error(f"✗ Historical bars test failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False


async def test_error_handling():
    """Test error handling."""
    logger.info("=" * 60)
    logger.info("TEST 9: Error Handling")
    logger.info("=" * 60)

    with patch('src.brokers.ibkr.ibkr_insync_broker.IB', MockIB):
        broker = IBKRInsyncBroker()

        try:
            # Simulate connection error by setting an invalid port
            broker._port = 99999
            await broker.connect()
            logger.error("✗ Should have raised connection error")
            return False
        except Exception as e:
            logger.info(f"✓ Caught expected error: {e}")
            return True


async def test_indexerror_bug_fix():
    """Test that IndexError bug in get_account() is fixed."""
    logger.info("=" * 60)
    logger.info("TEST 10: IndexError Bug Fix")
    logger.info("=" * 60)

    with patch('src.brokers.ibkr.ibkr_insync_broker.IB', MockIB):
        broker = IBKRInsyncBroker()

        try:
            await broker.connect()
            logger.info(f"✓ Connected")

            # Test with empty managed accounts list (should not raise IndexError)
            broker._ib._managed_accounts = []
            broker._ib._account_summary = [
                create_mock_account_summary_item("AccountCode", "U12345678"),
                create_mock_account_summary_item("TotalCashBalance", "100000.00"),
                create_mock_account_summary_item("NetLiquidation", "150000.00"),
                create_mock_account_summary_item("BuyingPower", "200000.00"),
                create_mock_account_summary_item("AvailableFunds", "100000.00"),
            ]

            account = await broker.get_account()
            logger.info(f"✓ No IndexError with empty managed accounts")
            logger.info(f"  Account ID: {account.account_id}")

            # Test with provided account (should not raise IndexError)
            broker._account = "U98765432"
            account = await broker.get_account()
            logger.info(f"✓ Works with provided account code")
            logger.info(f"  Account ID: {account.account_id}")

            await broker.disconnect()
            return True
        except IndexError as e:
            logger.error(f"✗ IndexError still present: {e}")
            return False
        except Exception as e:
            logger.error(f"✗ Test failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False


async def test_circuit_breaker():
    """Test circuit breaker functionality."""
    logger.info("=" * 60)
    logger.info("TEST 11: Circuit Breaker")
    logger.info("=" * 60)

    with patch('src.brokers.ibkr.ibkr_insync_broker.IB', MockIB):
        broker = IBKRInsyncBroker()

        try:
            # Set low failure threshold for testing
            broker._circuit_breaker_failure_threshold = 3
            broker._circuit_breaker_cooldown_seconds = 5

            from src.brokers.ibkr.ibkr_insync_broker import CircuitState

            # Record failures to trigger circuit breaker
            for i in range(3):
                broker._record_connection_failure()
                logger.info(f"Recorded failure {i+1}/3, state: {broker._circuit_state.value}")

            # Circuit should be OPEN now
            if broker._circuit_state != CircuitState.OPEN:
                logger.error(f"✗ Circuit should be OPEN after threshold failures, got: {broker._circuit_state.value}")
                return False
            logger.info("✓ Circuit breaker OPEN after threshold failures")

            # Check that circuit breaker rejects connection
            can_connect = broker._check_circuit_breaker()
            if can_connect:
                logger.error("✗ Circuit breaker should reject connection when OPEN")
                return False
            logger.info("✓ Circuit breaker rejected connection while OPEN")

            # Wait for cooldown to expire
            await asyncio.sleep(broker._circuit_breaker_cooldown_seconds + 1)

            # Circuit should be HALF_OPEN now
            can_connect = broker._check_circuit_breaker()
            if not can_connect or broker._circuit_state != CircuitState.HALF_OPEN:
                logger.error(f"✗ Circuit breaker should be HALF_OPEN after cooldown, got: {broker._circuit_state.value}")
                return False
            logger.info("✓ Circuit breaker HALF_OPEN after cooldown")

            # Test reset on successful connection
            broker._reset_circuit_breaker()
            if broker._circuit_state != CircuitState.CLOSED:
                logger.error(f"✗ Circuit should be CLOSED after reset, got: {broker._circuit_state.value}")
                return False
            if broker._failure_count != 0:
                logger.error(f"✗ Failure count should be 0 after reset, got: {broker._failure_count}")
                return False
            logger.info("✓ Circuit breaker reset successfully")

            return True
        except Exception as e:
            logger.error(f"✗ Circuit breaker test failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False


async def test_stop_limit_order():
    """Test STOP_LIMIT order placement."""
    logger.info("=" * 60)
    logger.info("TEST 12: Stop-Limit Order")
    logger.info("=" * 60)

    with patch('src.brokers.ibkr.ibkr_insync_broker.IB', MockIB):
        broker = IBKRInsyncBroker()

        try:
            await broker.connect()
            logger.info(f"✓ Connected")

            # Setup mock account for validation
            broker._ib._account_summary = [
                create_mock_account_summary_item("AccountCode", "U12345678"),
                create_mock_account_summary_item("TotalCashBalance", "100000.00"),
                create_mock_account_summary_item("NetLiquidation", "150000.00"),
                create_mock_account_summary_item("BuyingPower", "200000.00"),
                create_mock_account_summary_item("AvailableFunds", "100000.00"),
            ]

            # Place a stop-limit order
            order = Order(
                order_id="test_stop_limit",
                symbol="AAPL",
                side=OrderSide.BUY,
                order_type=OrderType.STOP_LIMIT,
                quantity=10,
                stop_price=160.0,
                price=165.0,
            )

            order_id = await broker.place_order(order)
            logger.info(f"✓ Stop-limit order placed: {order_id}")

            # Validate the order
            is_valid, message = await broker.validate_order(order)
            if not is_valid:
                logger.error(f"✗ Stop-limit order validation failed: {message}")
                return False
            logger.info(f"✓ Stop-limit order validation passed: {message}")

            # Test invalid stop-limit order (missing prices)
            invalid_order = Order(
                order_id="test_invalid",
                symbol="AAPL",
                side=OrderSide.BUY,
                order_type=OrderType.STOP_LIMIT,
                quantity=10,
            )

            is_valid, message = await broker.validate_order(invalid_order)
            if is_valid:
                logger.error("✗ Stop-limit order without prices should be invalid")
                return False
            logger.info(f"✓ Invalid stop-limit order correctly rejected: {message}")

            await broker.disconnect()
            return True
        except Exception as e:
            logger.error(f"✗ Stop-limit order test failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False


async def main():
    """Run all tests."""
    logger.info("")
    logger.info("╔" + "═" * 58 + "╗")
    logger.info("║" + " " * 10 + "IBKR Insync Broker Tests (Mocked)" + " " * 13 + "║")
    logger.info("╚" + "═" * 58 + "╝")
    logger.info("")

    tests = [
        ("Connection", test_connection),
        ("Positions", test_positions),
        ("Account Summary", test_account_summary),
        ("Portfolio Summary", test_portfolio_summary),
        ("Market Price", test_market_price),
        ("Order Validation", test_order_validation),
        ("Orders", test_orders),
        ("Historical Bars", test_historical_bars),
        ("Error Handling", test_error_handling),
        ("IndexError Bug Fix", test_indexerror_bug_fix),
        ("Circuit Breaker", test_circuit_breaker),
        ("Stop-Limit Order", test_stop_limit_order),
    ]

    results = []
    for test_name, test_func in tests:
        result = await test_func()
        results.append((test_name, result))

    logger.info("")
    logger.info("=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        logger.info(f"{status}: {test_name}")

    logger.info("")
    logger.info(f"Results: {passed}/{total} tests passed")
    logger.info("")

    if passed == total:
        logger.info("🎉 All tests passed!")
    else:
        logger.error(f"❌ {total - passed} test(s) failed")

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    asyncio.run(main())
