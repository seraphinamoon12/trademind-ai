"""Unit tests for IBKR broker client."""
import pytest
import asyncio
from datetime import datetime, timezone
from src.brokers.ibkr.client import IBKRBroker
from src.brokers.base import Order, OrderType, OrderSide


pytestmark = pytest.mark.integration


@pytest.fixture
async def broker():
    """Create and connect IBKR broker for testing."""
    broker = IBKRBroker(port=7497, paper_trading=True)
    await broker.connect()
    yield broker
    await broker.disconnect()


@pytest.mark.asyncio
async def test_connection(broker):
    """Test connection to IBKR."""
    assert broker.is_connected is True


@pytest.mark.asyncio
async def test_disconnect(broker):
    """Test disconnection from IBKR."""
    await broker.disconnect()
    assert broker.is_connected is False


@pytest.mark.asyncio
async def test_place_market_order(broker):
    """Test placing a market order."""
    order = Order(
        order_id="test-1",
        symbol="AAPL",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=1
    )
    order_id = await broker.place_order(order)
    assert order_id is not None
    assert order_id in broker._orders


@pytest.mark.asyncio
async def test_cancel_order(broker):
    """Test cancelling an order."""
    order = Order(
        order_id="test-2",
        symbol="TSLA",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=1,
        price=100.0
    )
    order_id = await broker.place_order(order)
    
    result = await broker.cancel_order(order_id)
    assert result is True


@pytest.mark.asyncio
async def test_get_positions(broker):
    """Test retrieving positions."""
    positions = await broker.get_positions()
    assert isinstance(positions, list)


@pytest.mark.asyncio
async def test_get_account(broker):
    """Test retrieving account info."""
    account = await broker.get_account()
    assert account.account_id is not None
    assert account.cash_balance >= 0


@pytest.mark.asyncio
async def test_get_historical_bars(broker):
    """Test historical bar retrieval."""
    bars = await broker.get_historical_bars(
        symbol="AAPL",
        duration="1 D",
        bar_size="1 hour"
    )
    assert isinstance(bars, list)
    if bars:
        assert "open" in bars[0]
        assert "high" in bars[0]
        assert "low" in bars[0]
        assert "close" in bars[0]


@pytest.mark.asyncio
async def test_validate_order_insufficient_funds(broker):
    """Test order validation rejects orders with insufficient funds."""
    order = Order(
        order_id="test-3",
        symbol="AAPL",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=1000000
    )
    is_valid, message = await broker.validate_order(order)
    assert is_valid is False
    assert "Insufficient" in message


@pytest.mark.asyncio
async def test_get_market_price(broker):
    """Test getting market price."""
    price = await broker.get_market_price("SPY")
    assert price is not None
    assert price > 0


@pytest.mark.asyncio
async def test_place_limit_order(broker):
    """Test placing a limit order."""
    order = Order(
        order_id="test-4",
        symbol="MSFT",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=1,
        price=100.0
    )
    order_id = await broker.place_order(order)
    assert order_id is not None


@pytest.mark.asyncio
async def test_get_portfolio_summary(broker):
    """Test getting portfolio summary."""
    summary = await broker.get_portfolio_summary()
    assert "total_value" in summary
    assert "cash_balance" in summary
    assert "open_positions" in summary
