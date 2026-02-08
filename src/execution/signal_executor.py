"""Execute trading signals through IBKR with safety checks."""
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from src.brokers.base import Order, OrderType, OrderSide

logger = logging.getLogger(__name__)


class SignalExecutor:
    """Execute trading signals through IBKR with safety checks."""

    def __init__(self, broker, risk_manager):
        self.broker = broker
        self.risk = risk_manager

    async def execute_signal(
        self,
        symbol: str,
        signal_type: str,
        quantity: int,
        order_type: str = "MARKET",
        price: Optional[float] = None,
        stop_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Execute a trading signal with full risk checks.

        Steps:
        1. Validate signal parameters
        2. Check risk limits (via risk_manager)
        3. Create Order object
        4. Place order via broker
        5. Return execution result with order_id
        """
        result = {
            "symbol": symbol,
            "signal_type": signal_type,
            "quantity": quantity,
            "order_type": order_type,
            "success": False,
            "order_id": None,
            "message": "",
            "timestamp": datetime.utcnow().isoformat()
        }

        try:
            if signal_type not in ["BUY", "SELL", "CLOSE"]:
                return self._error_result(
                    result,
                    f"Invalid signal_type: {signal_type}. Must be BUY, SELL, or CLOSE"
                )

            if order_type.upper() not in ["MARKET", "LIMIT", "STOP", "STOP_LIMIT"]:
                return self._error_result(
                    result,
                    f"Invalid order_type: {order_type}"
                )

            if quantity <= 0:
                return self._error_result(
                    result,
                    f"Invalid quantity: {quantity}. Must be positive"
                )

            if order_type.upper() == "LIMIT" and price is None:
                return self._error_result(
                    result,
                    "Limit orders require a price"
                )

            if order_type.upper() in ["STOP", "STOP_LIMIT"] and stop_price is None:
                return self._error_result(
                    result,
                    "Stop orders require a stop_price"
                )

            if signal_type == "CLOSE":
                positions = await self.broker.get_positions()
                position = next((p for p in positions if p.symbol == symbol), None)

                if position is None or position.quantity == 0:
                    return self._error_result(
                        result,
                        f"No position to close for {symbol}"
                    )

                actual_quantity = abs(position.quantity)
                actual_signal = "SELL" if position.quantity > 0 else "BUY"
            else:
                actual_quantity = quantity
                actual_signal = signal_type

            side = OrderSide[actual_signal]
            order_type_enum = OrderType[order_type.upper()]

            order = Order(
                order_id=f"SIGNAL_{int(datetime.utcnow().timestamp() * 1000)}",
                symbol=symbol,
                side=side,
                order_type=order_type_enum,
                quantity=actual_quantity,
                price=price,
                stop_price=stop_price
            )

            is_valid, message = await self.risk.validate_order(order)
            if not is_valid:
                return self._error_result(
                    result,
                    f"Risk validation failed: {message}"
                )

            order_id = await self.broker.place_order(order)

            result["success"] = True
            result["order_id"] = order_id
            result["message"] = f"Order placed successfully"
            result["executed_quantity"] = actual_quantity
            result["executed_signal"] = actual_signal

            logger.info(
                f"Signal executed: {signal_type} {actual_quantity} {symbol} "
                f"as {order_type} order {order_id}"
            )

        except Exception as e:
            logger.error(f"Error executing signal: {e}")
            return self._error_result(
                result,
                f"Execution error: {str(e)}"
            )

        return result

    def _error_result(self, result: Dict[str, Any], message: str) -> Dict[str, Any]:
        """Create an error result."""
        result["success"] = False
        result["message"] = message
        return result

    async def execute_signal_batch(
        self,
        signals: list[Dict[str, Any]]
    ) -> list[Dict[str, Any]]:
        """
        Execute multiple signals in sequence.

        Args:
            signals: List of signal dicts with keys:
                - symbol: str
                - signal_type: str (BUY, SELL, CLOSE)
                - quantity: int
                - order_type: str (optional, default MARKET)
                - price: float (optional, for LIMIT orders)
                - stop_price: float (optional, for STOP orders)

        Returns:
            List of execution results
        """
        results = []

        for i, signal in enumerate(signals):
            logger.info(f"Executing signal {i+1}/{len(signals)}: {signal.get('symbol')}")

            result = await self.execute_signal(
                symbol=signal["symbol"],
                signal_type=signal["signal_type"],
                quantity=signal["quantity"],
                order_type=signal.get("order_type", "MARKET"),
                price=signal.get("price"),
                stop_price=signal.get("stop_price")
            )

            results.append(result)

            if not result["success"]:
                logger.warning(
                    f"Signal execution failed: {result['message']}. "
                    f"Continuing with remaining signals."
                )

        return results

    async def get_risk_summary(self) -> Dict[str, Any]:
        """Get current portfolio risk summary."""
        return await self.risk.check_portfolio_risk()
