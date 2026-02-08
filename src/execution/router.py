"""Execution router for routing orders to appropriate broker."""
import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime

from src.brokers.base import BaseBroker, Order, Position, Account, OrderStatus, OrderType, OrderSide
from src.execution.factory import BrokerFactory

logger = logging.getLogger(__name__)


class ExecutionRouter:
    """Router for managing trade execution through brokers."""

    def __init__(self, broker_type: str = 'paper', broker_config: Optional[Dict[str, Any]] = None):
        """
        Initialize the execution router.

        Args:
            broker_type: Type of broker to use ('paper', 'ibkr')
            broker_config: Broker-specific configuration
        """
        self.broker_type = broker_type
        self.broker_config = broker_config or {}
        self.broker: Optional[BaseBroker] = None
        self._connected = False

    async def connect(self) -> None:
        """Connect to the broker."""
        if self._connected:
            logger.warning("Already connected to broker")
            return

        self.broker = BrokerFactory.create_broker(self.broker_type, self.broker_config)

        if hasattr(self.broker, 'connect'):
            await self.broker.connect()
            self._connected = self.broker.is_connected
            logger.info(f"Connected to {self.broker_type} broker")
        else:
            self._connected = True
            logger.info(f"Using {self.broker_type} broker (sync mode)")

    async def disconnect(self) -> None:
        """Disconnect from the broker."""
        if not self._connected or self.broker is None:
            return

        if hasattr(self.broker, 'disconnect'):
            await self.broker.disconnect()

        self._connected = False
        logger.info(f"Disconnected from {self.broker_type} broker")

    @property
    def is_connected(self) -> bool:
        """Check if router is connected to broker."""
        return self._connected and (self.broker.is_connected if self.broker else False)

    async def place_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        order_type: str = 'market',
        price: Optional[float] = None,
        stop_price: Optional[float] = None
    ) -> str:
        """
        Place an order through the broker.

        Args:
            symbol: Trading symbol
            side: 'BUY' or 'SELL'
            quantity: Number of shares
            order_type: 'market', 'limit', 'stop', 'stop_limit'
            price: Limit price (for limit orders)
            stop_price: Stop price (for stop orders)

        Returns:
            Order ID

        Raises:
            ValueError: If order parameters are invalid
            ConnectionError: If not connected to broker
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to broker")

        try:
            side_enum = OrderSide[side.upper()]
            order_type_enum = OrderType[order_type.upper()]
        except KeyError as e:
            raise ValueError(f"Invalid order parameter: {e}")

        order = Order(
            order_id=f"ORD_{int(datetime.utcnow().timestamp() * 1000)}",
            symbol=symbol,
            side=side_enum,
            order_type=order_type_enum,
            quantity=quantity,
            price=price,
            stop_price=stop_price
        )

        is_valid, message = await self._validate_order(order)
        if not is_valid:
            raise ValueError(f"Order validation failed: {message}")

        if hasattr(self.broker, 'place_order'):
            order_id = await self.broker.place_order(order)
            logger.info(f"Placed order {order_id} for {symbol}: {side} {quantity} shares")
            return order_id
        else:
            raise NotImplementedError(f"Broker {self.broker_type} does not support order placement")

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order by ID."""
        if not self.is_connected:
            raise ConnectionError("Not connected to broker")

        if hasattr(self.broker, 'cancel_order'):
            result = await self.broker.cancel_order(order_id)
            logger.info(f"Cancel order {order_id}: {'success' if result else 'failed'}")
            return result
        else:
            logger.warning(f"Broker {self.broker_type} does not support order cancellation")
            return False

    async def get_order_status(self, order_id: str) -> OrderStatus:
        """Get status of an order."""
        if not self.is_connected:
            raise ConnectionError("Not connected to broker")

        if hasattr(self.broker, 'get_order_status'):
            return await self.broker.get_order_status(order_id)
        else:
            logger.warning(f"Broker {self.broker_type} does not support order status queries")
            return OrderStatus.PENDING

    async def get_positions(self) -> List[Position]:
        """Get all current positions."""
        if not self.is_connected:
            raise ConnectionError("Not connected to broker")

        if hasattr(self.broker, 'get_positions'):
            return await self.broker.get_positions()
        else:
            return []

    async def get_account(self) -> Optional[Account]:
        """Get account information."""
        if not self.is_connected:
            raise ConnectionError("Not connected to broker")

        if hasattr(self.broker, 'get_account'):
            return await self.broker.get_account()
        else:
            return None

    async def get_market_price(self, symbol: str) -> float:
        """Get current market price for a symbol."""
        if not self.is_connected:
            raise ConnectionError("Not connected to broker")

        if hasattr(self.broker, 'get_market_price'):
            return await self.broker.get_market_price(symbol)
        else:
            raise NotImplementedError(f"Broker {self.broker_type} does not support market price queries")

    async def _validate_order(self, order: Order) -> Tuple[bool, str]:
        """Validate an order before placement."""
        if order.quantity <= 0:
            return False, "Order quantity must be positive"

        if order.order_type == OrderType.LIMIT and order.price is None:
            return False, "Limit orders require a price"

        if order.order_type == OrderType.STOP and order.stop_price is None:
            return False, "Stop orders require a stop price"

        if hasattr(self.broker, 'validate_order'):
            return await self.broker.validate_order(order)

        return True, "Order valid"
