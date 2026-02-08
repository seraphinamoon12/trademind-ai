"""Error handling tests for IBKR broker."""
import pytest
from src.brokers.ibkr.client import IBKRBroker
from src.brokers.base import Order, OrderType, OrderSide


@pytest.mark.asyncio
async def test_connection_refused():
    """Test handling when TWS is not running."""
    broker = IBKRBroker(port=9999)
    with pytest.raises(Exception):
        await broker.connect()


@pytest.mark.asyncio
async def test_order_without_connection():
    """Test placing order when not connected."""
    broker = IBKRBroker()
    broker._connected = False
    
    order = Order(
        order_id="error-test",
        symbol="AAPL",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=1
    )
    
    with pytest.raises(ConnectionError):
        await broker.place_order(order)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_cancel_nonexistent_order():
    """Test cancelling an order that doesn't exist."""
    broker = IBKRBroker(port=7497)
    await broker.connect()
    
    result = await broker.cancel_order("nonexistent-order-id")
    assert result is False
    
    await broker.disconnect()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_invalid_symbol():
    """Test handling invalid symbol."""
    broker = IBKRBroker(port=7497)
    await broker.connect()
    
    with pytest.raises(ValueError):
        await broker.get_market_price("INVALID_SYMBOL_XYZ")
    
    await broker.disconnect()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_invalid_order_validation():
    """Test validating an order with invalid parameters."""
    broker = IBKRBroker(port=7497)
    await broker.connect()
    
    order = Order(
        order_id="invalid-test",
        symbol="AAPL",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=1,
        price=None
    )
    
    is_valid, message = await broker.validate_order(order)
    assert is_valid is False
    assert "price" in message.lower()
    
    await broker.disconnect()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_negative_quantity_order():
    """Test placing an order with negative quantity."""
    broker = IBKRBroker(port=7497)
    await broker.connect()
    
    order = Order(
        order_id="negative-test",
        symbol="AAPL",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=-1
    )
    
    is_valid, message = await broker.validate_order(order)
    assert is_valid is False
    assert "quantity" in message.lower()
    
    await broker.disconnect()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_stop_order_without_stop_price():
    """Test stop order without stop price."""
    broker = IBKRBroker(port=7497)
    await broker.connect()
    
    order = Order(
        order_id="stop-test",
        symbol="AAPL",
        side=OrderSide.BUY,
        order_type=OrderType.STOP,
        quantity=1,
        stop_price=None
    )
    
    is_valid, message = await broker.validate_order(order)
    assert is_valid is False
    assert "stop" in message.lower()
    
    await broker.disconnect()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_stop_limit_order_without_prices():
    """Test stop limit order without both prices."""
    broker = IBKRBroker(port=7497)
    await broker.connect()
    
    order = Order(
        order_id="stop-limit-test",
        symbol="AAPL",
        side=OrderSide.BUY,
        order_type=OrderType.STOP_LIMIT,
        quantity=1,
        price=None,
        stop_price=None
    )
    
    is_valid, message = await broker.validate_order(order)
    assert is_valid is False
    
    await broker.disconnect()
