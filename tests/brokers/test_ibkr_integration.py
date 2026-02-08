"""Integration tests for IBKR broker."""
import pytest
import pytest_asyncio
import asyncio
from src.brokers.ibkr.client import IBKRBroker
from src.brokers.ibkr.risk_manager import IBKRRiskManager
from src.execution.signal_executor import SignalExecutor
from src.brokers.base import Order, OrderType, OrderSide


pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def connected_broker():
    """Create connected broker for integration tests."""
    broker = IBKRBroker(port=7497, paper_trading=True)
    await broker.connect()
    yield broker
    await broker.disconnect()


@pytest_asyncio.fixture
async def risk_manager(connected_broker):
    """Create risk manager with test config."""
    config = {
        "max_order_size": 100,
        "max_order_value": 10000,
        "max_position_pct": 0.25,
        "daily_loss_limit": 500
    }
    return IBKRRiskManager(connected_broker, config)


@pytest_asyncio.fixture
async def signal_executor(connected_broker, risk_manager):
    """Create signal executor for testing."""
    return SignalExecutor(connected_broker, risk_manager)


@pytest.mark.asyncio
async def test_full_order_lifecycle(connected_broker):
    """Test complete order lifecycle: place -> get status -> cancel."""
    order = Order(
        order_id="lifecycle-test",
        symbol="MSFT",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=1,
        price=200.0
    )
    order_id = await connected_broker.place_order(order)
    
    status = await connected_broker.get_order_status(order_id)
    assert status is not None
    
    orders = await connected_broker.get_orders(status="open")
    assert any(o.order_id == order_id for o in orders)
    
    result = await connected_broker.cancel_order(order_id)
    assert result is True


@pytest.mark.asyncio
async def test_signal_execution_flow(signal_executor):
    """Test full signal execution with risk checks."""
    result = await signal_executor.execute_signal(
        symbol="AAPL",
        signal_type="BUY",
        quantity=1,
        order_type="MARKET"
    )
    
    assert result["success"] is True
    assert "order_id" in result


@pytest.mark.asyncio
async def test_portfolio_sync(connected_broker):
    """Test portfolio data synchronization."""
    initial_positions = await connected_broker.get_positions()
    initial_account = await connected_broker.get_account()
    
    order = Order(
        order_id="portfolio-test",
        symbol="SPY",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=1
    )
    await connected_broker.place_order(order)
    
    await asyncio.sleep(2)
    
    summary = await connected_broker.get_portfolio_summary()
    assert "total_value" in summary
    assert "cash_balance" in summary
    assert "open_positions" in summary


@pytest.mark.asyncio
async def test_risk_manager_validation(risk_manager):
    """Test risk manager order validation."""
    order = Order(
        order_id="risk-test",
        symbol="AAPL",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=10000
    )
    is_valid, message = await risk_manager.validate_order(order)
    assert is_valid is False


@pytest.mark.asyncio
async def test_market_data_subscription(connected_broker):
    """Test market data subscription."""
    await connected_broker.subscribe_market_data("SPY")
    quote = connected_broker.get_quote("SPY")
    assert quote is not None
    assert "last" in quote or "bid" in quote


@pytest.mark.asyncio
async def test_close_position_signal(signal_executor):
    """Test closing a position via signal."""
    result = await signal_executor.execute_signal(
        symbol="AAPL",
        signal_type="CLOSE",
        quantity=1,
        order_type="MARKET"
    )
    
    if "No position to close" in result.get("message", ""):
        assert result["success"] is False
    else:
        assert result["success"] is True or "No position to close" in result.get("message", "")


@pytest.mark.asyncio
async def test_batch_signal_execution(signal_executor):
    """Test executing multiple signals in batch."""
    signals = [
        {
            "symbol": "AAPL",
            "signal_type": "BUY",
            "quantity": 1,
            "order_type": "MARKET"
        },
        {
            "symbol": "MSFT",
            "signal_type": "BUY",
            "quantity": 1,
            "order_type": "MARKET"
        }
    ]
    
    results = await signal_executor.execute_signal_batch(signals)
    assert len(results) == 2


@pytest.mark.asyncio
async def test_portfolio_risk_check(risk_manager):
    """Test portfolio risk checking."""
    risk_summary = await risk_manager.check_portfolio_risk()
    assert "risk_level" in risk_summary
    assert risk_summary["risk_level"] in ["LOW", "MEDIUM", "HIGH"]
