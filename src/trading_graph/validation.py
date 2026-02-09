"""Validation helpers for LangGraph workflows."""

from typing import Optional
from datetime import datetime, timezone


class ValidationError(ValueError):
    """Custom validation error."""
    pass


def validate_confidence(confidence: float, field_name: str = "confidence") -> float:
    """Validate confidence is between 0 and 1."""
    if not isinstance(confidence, (int, float)):
        raise ValidationError(f"{field_name} must be a number")
    if confidence < 0 or confidence > 1:
        raise ValidationError(f"{field_name} must be between 0 and 1, got {confidence}")
    return float(confidence)


def validate_symbol(symbol: str) -> str:
    """Validate stock symbol format."""
    if not symbol or not isinstance(symbol, str):
        raise ValidationError("Symbol must be a non-empty string")
    if len(symbol) > 5:
        raise ValidationError(f"Symbol too long: {symbol}")
    return symbol.upper()


def validate_quantity(quantity: int, min_qty: int = 1) -> int:
    """Validate order quantity."""
    if not isinstance(quantity, int):
        raise ValidationError("Quantity must be an integer")
    if quantity < min_qty:
        raise ValidationError(f"Quantity must be at least {min_qty}")
    return quantity


def validate_price(price: Optional[float], field_name: str = "price") -> Optional[float]:
    """Validate price is positive."""
    if price is None:
        return None
    if not isinstance(price, (int, float)):
        raise ValidationError(f"{field_name} must be a number")
    if price <= 0:
        raise ValidationError(f"{field_name} must be positive")
    return float(price)


def get_utc_now() -> str:
    """Get current UTC time as ISO string."""
    return datetime.now(timezone.utc).isoformat()
