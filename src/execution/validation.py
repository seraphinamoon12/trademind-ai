"""Unified order validation functions.

This module provides centralized validation for orders across
different brokers and execution contexts.
"""
from typing import Tuple, Optional
import logging

from src.brokers.base import Order, OrderType, OrderSide

logger = logging.getLogger(__name__)


def validate_order_symbol(symbol: str) -> Tuple[bool, str]:
    """Validate order symbol.

    Args:
        symbol: Stock symbol

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not symbol or not isinstance(symbol, str):
        return False, "Symbol must be a non-empty string"

    if len(symbol.strip()) == 0:
        return False, "Symbol cannot be empty"

    return True, "OK"


def validate_order_quantity(
    quantity: int,
    min_quantity: int = 1,
    max_quantity: int = 1000000
) -> Tuple[bool, str]:
    """Validate order quantity.

    Args:
        quantity: Order quantity
        min_quantity: Minimum allowed quantity
        max_quantity: Maximum allowed quantity

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(quantity, int):
        return False, f"Quantity must be an integer, got {type(quantity).__name__}"

    if quantity <= 0:
        return False, "Order quantity must be positive"

    if quantity < min_quantity:
        return False, f"Quantity must be at least {min_quantity}"

    if quantity > max_quantity:
        return False, f"Quantity exceeds maximum of {max_quantity}"

    return True, "OK"


def validate_order_price(
    price: Optional[float],
    order_type: OrderType
) -> Tuple[bool, str]:
    """Validate order price.

    Args:
        price: Order price
        order_type: Type of order

    Returns:
        Tuple of (is_valid, error_message)
    """
    if order_type == OrderType.MARKET:
        return True, "OK"

    if order_type == OrderType.LIMIT:
        if price is None:
            return False, "Limit orders require a price"
        if price <= 0:
            return False, f"Limit price must be positive, got {price}"
        return True, "OK"

    if order_type == OrderType.STOP:
        return True, "OK"

    if order_type == OrderType.STOP_LIMIT:
        return True, "OK"

    return False, f"Unsupported order type: {order_type}"


def validate_stop_price(
    stop_price: Optional[float],
    order_type: OrderType
) -> Tuple[bool, str]:
    """Validate stop price.

    Args:
        stop_price: Stop price
        order_type: Type of order

    Returns:
        Tuple of (is_valid, error_message)
    """
    if order_type in (OrderType.MARKET, OrderType.LIMIT):
        return True, "OK"

    if order_type == OrderType.STOP:
        if stop_price is None:
            return False, "Stop orders require a stop price"
        if stop_price <= 0:
            return False, f"Stop price must be positive, got {stop_price}"
        return True, "OK"

    if order_type == OrderType.STOP_LIMIT:
        if stop_price is None:
            return False, "Stop limit orders require a stop price"
        if stop_price <= 0:
            return False, f"Stop price must be positive, got {stop_price}"
        return True, "OK"

    return False, f"Unsupported order type: {order_type}"


def validate_order_type(order_type: str, available_types: list = None) -> Tuple[bool, str]:
    """Validate order type.

    Args:
        order_type: Order type string
        available_types: List of available order types

    Returns:
        Tuple of (is_valid, error_message)
    """
    if available_types is None:
        available_types = ['MARKET', 'LIMIT', 'STOP', 'STOP_LIMIT']

    order_type_upper = order_type.upper() if order_type else ''

    if order_type_upper not in available_types:
        return False, f"Invalid order type: {order_type}. Must be one of {available_types}"

    return True, "OK"


def validate_order_side(side: str) -> Tuple[bool, str]:
    """Validate order side.

    Args:
        side: Order side (BUY or SELL)

    Returns:
        Tuple of (is_valid, error_message)
    """
    side_upper = side.upper() if side else ''

    if side_upper not in ['BUY', 'SELL']:
        return False, f"Invalid order side: {side}. Must be BUY or SELL"

    return True, "OK"


def validate_order_funds(
    quantity: int,
    price: float,
    available_cash: float,
    side: OrderSide,
    commission_rate: float = 0.0
) -> Tuple[bool, str]:
    """Validate order against available funds.

    Args:
        quantity: Order quantity
        price: Order price
        available_cash: Available cash/buying power
        side: Order side
        commission_rate: Commission rate (default: 0)

    Returns:
        Tuple of (is_valid, error_message)
    """
    if side == OrderSide.BUY:
        gross_value = quantity * price
        commission = gross_value * commission_rate
        total_cost = gross_value + commission

        if total_cost > available_cash:
            return False, f"Insufficient cash: need ${total_cost:.2f}, have ${available_cash:.2f}"

    return True, "OK"


def validate_order_shares(
    symbol: str,
    quantity: int,
    side: OrderSide,
    current_holdings: dict
) -> Tuple[bool, str]:
    """Validate order against current holdings.

    Args:
        symbol: Stock symbol
        quantity: Order quantity
        side: Order side
        current_holdings: Dictionary of current holdings {symbol: quantity}

    Returns:
        Tuple of (is_valid, error_message)
    """
    if side == OrderSide.SELL:
        current_qty = current_holdings.get(symbol, 0)
        if quantity > abs(current_qty):
            return False, f"Insufficient shares: have {abs(current_qty)}, need {quantity}"

    return True, "OK"


def validate_order(order: Order) -> Tuple[bool, str]:
    """Comprehensive order validation.

    Args:
        order: Order object to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Validate symbol
    is_valid, msg = validate_order_symbol(order.symbol)
    if not is_valid:
        return False, msg

    # Validate quantity
    is_valid, msg = validate_order_quantity(order.quantity)
    if not is_valid:
        return False, msg

    # Validate order type
    is_valid, msg = validate_order_type(order.order_type.value)
    if not is_valid:
        return False, msg

    # Validate price
    is_valid, msg = validate_order_price(order.price, order.order_type)
    if not is_valid:
        return False, msg

    # Validate stop price
    is_valid, msg = validate_stop_price(order.stop_price, order.order_type)
    if not is_valid:
        return False, msg

    # Validate side
    is_valid, msg = validate_order_side(order.side.value)
    if not is_valid:
        return False, msg

    return True, "OK"


def validate_order_with_context(
    order: Order,
    available_cash: Optional[float] = None,
    current_holdings: Optional[dict] = None,
    commission_rate: float = 0.0
) -> Tuple[bool, str]:
    """Validate order with additional context.

    Args:
        order: Order object to validate
        available_cash: Available cash for buy orders
        current_holdings: Current holdings for sell orders
        commission_rate: Commission rate

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Base validation
    is_valid, msg = validate_order(order)
    if not is_valid:
        return False, msg

    # Validate against available funds (for buy orders)
    if available_cash is not None and order.side == OrderSide.BUY:
        price = order.price or 0
        is_valid, msg = validate_order_funds(
            order.quantity,
            price,
            available_cash,
            order.side,
            commission_rate
        )
        if not is_valid:
            return False, msg

    # Validate against current holdings (for sell orders)
    if current_holdings is not None and order.side == OrderSide.SELL:
        holdings = current_holdings if isinstance(current_holdings, dict) else {}
        is_valid, msg = validate_order_shares(
            order.symbol,
            order.quantity,
            order.side,
            holdings
        )
        if not is_valid:
            return False, msg

    return True, "OK"
