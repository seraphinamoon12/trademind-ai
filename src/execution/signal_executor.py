"""Execute trading signals through IBKR with safety checks."""
import logging
import asyncio
import sqlite3
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timezone

from src.brokers.base import Order, OrderType, OrderSide
from src.trading_graph.validation import get_utc_now
from src.trading_graph.state import TradingState
from src.config import settings

logger = logging.getLogger(__name__)


class ExecutionLogger:
    """Persistent execution logging to SQLite."""

    def __init__(self, db_path: str = "data/executions.db"):
        """
        Initialize execution logger.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database with trades table."""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                symbol TEXT,
                action TEXT,
                quantity INTEGER,
                price REAL,
                confidence REAL,
                order_id TEXT,
                status TEXT,
                error TEXT
            )
        """)
        conn.commit()
        conn.close()

    def log_trade(self, state: Dict[str, Any], result: Dict[str, Any]):
        """
        Log a trade execution.

        Args:
            state: Trading state dictionary
            result: Execution result dictionary
        """
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO trades (timestamp, symbol, action, quantity, price,
                              confidence, order_id, status, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            get_utc_now(),
            state.get("symbol", ""),
            state.get("final_action", "HOLD"),
            state.get("final_decision", {}).get("quantity", 0),
            state.get("market_data", {}).get("price", 0),
            state.get("confidence", 0),
            result.get("order_id", ""),
            "success" if result.get("order_id") else "failed",
            result.get("error", "")
        ))
        conn.commit()
        conn.close()


class SignalExecutor:
    """Execute trading signals through IBKR with safety checks."""

    def __init__(self, broker, risk_manager):
        """
        Initialize SignalExecutor with broker and risk manager.

        Args:
            broker: IBKR broker connection
            risk_manager: Risk manager instance for validation
        """
        self.broker = broker
        self.risk = risk_manager
        self._execution_log = []
        self._execution_logger = ExecutionLogger()

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
            "timestamp": get_utc_now()
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
                order_id=f"SIGNAL_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
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
        Execute multiple signals concurrently.

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
        # Create tasks for all signals
        tasks = [
            self.execute_signal(
                symbol=signal["symbol"],
                signal_type=signal["signal_type"],
                quantity=signal["quantity"],
                order_type=signal.get("order_type", "MARKET"),
                price=signal.get("price"),
                stop_price=signal.get("stop_price")
            )
            for i, signal in enumerate(signals)
        ]

        # Run all concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any exceptions
        processed_results = []
        for i, (signal, result) in enumerate(zip(signals, results)):
            if isinstance(result, Exception):
                logger.error(f"Signal execution failed for {signal.get('symbol')}: {result}")
                processed_results.append({
                    "symbol": signal["symbol"],
                    "signal_type": signal["signal_type"],
                    "quantity": signal["quantity"],
                    "success": False,
                    "message": f"Execution error: {str(result)}",
                    "error": str(result)
                })
            else:
                processed_results.append(result)
                if not result["success"]:
                    logger.warning(
                        f"Signal execution failed: {result['message']}. "
                        f"Continuing with remaining signals."
                    )

        return processed_results

    async def get_risk_summary(self) -> Dict[str, Any]:
        """Get current portfolio risk summary."""
        return await self.risk.check_portfolio_risk()
    
    async def execute_from_state(
        self,
        state: TradingState
    ) -> Dict[str, Any]:
        """
        Execute trade based on LangGraph state.
        
        Args:
            state: Trading state with final_action and decision
            
        Returns:
            Execution result dict
        """
        action = state.get("final_action", "HOLD")
        symbol = state["symbol"]
        
        if action == "HOLD":
            log_entry = {
                "timestamp": get_utc_now(),
                "symbol": symbol,
                "action": "HOLD",
                "confidence": state.get("confidence", 0.0),
                "executed": False,
                "reason": "No trade - HOLD signal"
            }
            self._execution_log.append(log_entry)
            logger.info(f"HOLD: {symbol} (confidence: {state.get('confidence', 0.0):.2f})")
            
            return {
                "executed_trade": None,
                "order_id": None,
                "current_node": "execute_trade"
            }
        
        # Get position size from decision
        decision = state.get("final_decision", {})
        quantity = decision.get("quantity", 100)
        
        # Pre-trade validation
        is_valid, msg = await self.pre_trade_check(state)
        if not is_valid:
            logger.error(f"Pre-trade check failed: {msg}")
            log_entry = {
                "timestamp": get_utc_now(),
                "symbol": symbol,
                "action": action,
                "quantity": quantity,
                "executed": False,
                "error": msg
            }
            self._execution_log.append(log_entry)
            # Persistent logging to SQLite
            self._execution_logger.log_trade(dict(state), {"success": False, "error": msg})

            return {
                "executed_trade": None,
                "order_id": None,
                "error": msg,
                "current_node": "execute_trade"
            }
        
        # Execute trade
        try:
            result = await self.execute_signal(
                symbol=symbol,
                signal_type=action,
                quantity=quantity,
                order_type="MARKET"
            )
            
            # Post-trade logging
            await self._log_execution(state, result)
            # Persistent logging to SQLite
            self._execution_logger.log_trade(dict(state), result)
            
            return {
                "executed_trade": result,
                "order_id": result.get("order_id"),
                "current_node": "execute_trade"
            }
            
        except Exception as e:
            logger.error(f"Trade execution failed: {e}")
            log_entry = {
                "timestamp": get_utc_now(),
                "symbol": symbol,
                "action": action,
                "quantity": quantity,
                "executed": False,
                "error": str(e)
            }
            self._execution_log.append(log_entry)
            # Persistent logging to SQLite
            self._execution_logger.log_trade(dict(state), {"success": False, "error": str(e)})

            return {
                "executed_trade": None,
                "order_id": None,
                "error": str(e),
                "current_node": "execute_trade"
            }
    
    async def pre_trade_check(self, state: TradingState) -> Tuple[bool, str]:
        """
        Perform pre-trade validation.
        
        Args:
            state: Trading state
            
        Returns:
            Tuple of (is_valid, message)
        """
        action = state.get("final_action", "HOLD")
        symbol = state["symbol"]
        confidence = state.get("confidence", 0.0)
        
        # Validate action
        if action not in ["BUY", "SELL"]:
            return False, f"Invalid action: {action}"
        
        # Validate confidence threshold
        if confidence < settings.confidence_threshold_low:
            return False, f"Confidence {confidence:.2f} below minimum threshold ({settings.confidence_threshold_low})"
        
        # Validate with risk manager
        is_valid, msg = await self.risk.validate_trade(state)
        if not is_valid:
            return False, f"Risk validation failed: {msg}"
        
        return True, "OK"
    
    async def _log_execution(
        self,
        state: TradingState,
        result: Dict[str, Any]
    ):
        """
        Log trade execution details.
        
        Args:
            state: Trading state
            result: Execution result
        """
        log_entry = {
            "timestamp": get_utc_now(),
            "symbol": state["symbol"],
            "action": state.get("final_action"),
            "confidence": state.get("confidence"),
            "decision": state.get("final_decision", {}),
            "result": result,
            "executed": result.get("success", False)
        }
        
        self._execution_log.append(log_entry)
        
        logger.info(
            f"Trade executed: {state['symbol']} {state.get('final_action')} "
            f"{result.get('executed_quantity', 0)} shares "
            f"(order_id: {result.get('order_id')})"
        )
    
    def get_execution_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent execution logs.
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List of execution log entries
        """
        return self._execution_log[-limit:]
