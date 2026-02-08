"""Base broker interface and data models."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict, Any, Tuple


class OrderStatus(Enum):
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    FILLED = "FILLED"
    PARTIAL = "PARTIAL"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class Order:
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: int
    price: Optional[float] = None
    stop_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    avg_fill_price: Optional[float] = None
    commission: Optional[float] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Position:
    symbol: str
    quantity: int
    avg_cost: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    realized_pnl: float = 0.0
    currency: str = "USD"


@dataclass
class Account:
    account_id: str
    cash_balance: float
    portfolio_value: float
    buying_power: float
    margin_available: float
    total_pnl: float
    daily_pnl: float
    currency: str = "USD"
    positions: List[Position] = field(default_factory=list)


class BaseBroker(ABC):
    """Abstract base class for broker implementations."""

    def __init__(self):
        self._connected = False

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to broker."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to broker."""
        pass

    @property
    def is_connected(self) -> bool:
        """Check if broker is connected."""
        return self._connected

    @abstractmethod
    async def place_order(self, order: Order) -> str:
        """Place an order and return order ID."""
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order by ID."""
        pass

    @abstractmethod
    async def get_order_status(self, order_id: str) -> OrderStatus:
        """Get status of an order."""
        pass

    @abstractmethod
    async def get_orders(self, status: Optional[str] = None) -> List[Order]:
        """Get orders with optional status filtering."""
        pass

    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """Get all current positions."""
        pass

    @abstractmethod
    async def get_account(self) -> Account:
        """Get account information."""
        pass

    @abstractmethod
    async def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get comprehensive portfolio summary."""
        pass

    @abstractmethod
    async def get_market_price(self, symbol: str) -> float:
        """Get current market price for a symbol."""
        pass

    @abstractmethod
    async def validate_order(self, order: Order) -> Tuple[bool, str]:
        """Validate if an order can be placed."""
        pass
