"""Nodes for risk assessment, trade execution, and retry logic in LangGraph workflow."""

import pandas as pd
import time
import asyncio
import logging
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Dict, Callable, cast

from src.trading_graph.state import TradingState
from src.trading_graph.types import RiskAssessmentOutput, ExecuteTradeOutput, RetryOutput
from src.agents.risk import RiskAgent
from src.brokers.ibkr.risk_manager import IBKRRiskManager
from src.brokers.ibkr.client import IBKRBroker
from src.execution.signal_executor import SignalExecutor
from src.trading_graph.validation import get_utc_now
from src.config import settings

logger = logging.getLogger(__name__)


def async_retry_with_fallback(max_attempts: int = 3, fallback_value: Any = None):
    """Retry decorator with fallback value on failure."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        logger.error(f"All {max_attempts} attempts failed: {e}")
                        return fallback_value
                    wait_time = 2 ** attempt
                    logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
        return wrapper
    return decorator


async def risk_assessment(state: TradingState) -> RiskAssessmentOutput:
    """
    Perform risk assessment using RiskAgent.

    Validates trade against:
    - Liquidity filters (volume, price, spread)
    - Earnings filter
    - Sector concentration limits
    - Position size limits

    Args:
        state: Trading state with market_data and final_decision

    Returns:
        State updates with risk_signals
    """
    try:
        symbol = state["symbol"]
        market_data_dict = state.get("market_data", {})
        final_decision = state.get("final_decision", {})
        
        if not market_data_dict:
            return {
                "error": "No market data available for risk assessment",
                "current_node": "risk_assessment"
            }
        
        # Convert dict back to DataFrame
        data = pd.DataFrame(market_data_dict)
        if data.empty:
            return {
                "error": "Market data is empty",
                "current_node": "risk_assessment"
            }
        
        # Initialize RiskAgent
        risk_agent = RiskAgent(
            max_position_pct=state.get("max_position_pct", 0.10),
            stop_loss_pct=state.get("stop_loss_pct", 0.05),
            take_profit_pct=state.get("take_profit_pct", 0.10),
            max_daily_loss_pct=state.get("max_daily_loss_pct", 0.03)
        )
        
        # Simulate portfolio context (would come from state in production)
        portfolio_value = state.get("portfolio_value", 100000.0)
        current_holdings = state.get("current_holdings", {})
        daily_pnl = state.get("daily_pnl", 0.0)
        
        # Analyze risk
        signal = await risk_agent.analyze(
            symbol=symbol,
            data=data,
            portfolio_value=portfolio_value,
            current_holdings=current_holdings,
            daily_pnl=daily_pnl
        )
        
        # Convert AgentSignal to risk_signals format
        risk_signals = {
            "decision": signal.decision.value,
            "confidence": signal.confidence,
            "reasoning": signal.reasoning,
            "agent_name": signal.agent_name,
            "data": signal.data or {}
        }
        
        return {
            "risk_signals": risk_signals,
            "current_node": "risk_assessment"
        }
        
    except Exception as e:
        return {
            "error": f"Risk assessment failed: {str(e)}",
            "current_node": "risk_assessment"
        }


async def execute_trade(state: TradingState) -> ExecuteTradeOutput:
    """
    Execute trade via IBKR with full error handling.

    This is the final node in the graph - actually places orders.

    Steps:
    1. Validate state (final_action, human_approved)
    2. Get position size from risk assessment
    3. Connect to broker (if needed)
    4. Create risk manager and executor
    5. Execute the trade via SignalExecutor
    6. Return execution result with order_id and status

    Args:
        state: Trading state with final_action, human_approved, risk_signals

    Returns:
        State updates with executed_trade, order_id, execution_status, execution_time
    """
    start_time = time.time()

    try:
        final_action = state.get("final_action")
        symbol = state["symbol"]

        if not final_action or final_action == "HOLD":
            return {
                "executed_trade": {
                    "action": "HOLD",
                    "symbol": symbol,
                    "quantity": 0,
                    "timestamp": get_utc_now(),
                    "message": "No trade executed - HOLD signal"
                },
                "order_id": None,
                "execution_status": "SKIPPED",
                "execution_time": time.time() - start_time,
                "current_node": "execute_trade"
            }

        if final_action not in ["BUY", "SELL"]:
            return {
                "executed_trade": {},
                "order_id": None,
                "execution_status": "REJECTED",
                "error": f"Invalid action: {final_action}",
                "execution_time": time.time() - start_time,
                "current_node": "execute_trade"
            }

        if not state.get("human_approved", False):
            return {
                "executed_trade": {},
                "order_id": None,
                "execution_status": "REJECTED",
                "error": "Not approved by human",
                "execution_time": time.time() - start_time,
                "current_node": "execute_trade"
            }

        risk_signals = state.get("risk_signals", {})
        position_size = risk_signals.get("data", {}).get("recommended_size", 10)

        if position_size <= 0:
            return {
                "executed_trade": {},
                "order_id": None,
                "execution_status": "REJECTED",
                "error": "Invalid position size",
                "execution_time": time.time() - start_time,
                "current_node": "execute_trade"
            }

        if settings.ibkr_enabled:
            broker = IBKRBroker(
                host=settings.ibkr_host,
                port=settings.ibkr_port,
                client_id=settings.ibkr_client_id,
                paper_trading=settings.ibkr_paper_trading
            )

            if not broker.is_connected:
                await broker.connect()

            risk_mgr = IBKRRiskManager(broker, config={
                "max_order_size": 1000,
                "max_order_value": settings.ibkr_max_order_value,
                "max_position_pct": settings.ibkr_position_size_limit_pct,
                "daily_loss_limit": getattr(settings, 'ibkr_daily_loss_limit', 1000)
            })

            executor = SignalExecutor(broker, risk_mgr)

            result = await executor.execute_from_state(state)

            execution_time = time.time() - start_time
            result["execution_time"] = execution_time
            result["execution_status"] = "SUCCESS" if result.get("order_id") else "FAILED"
            result["current_node"] = "execute_trade"

            return cast(ExecuteTradeOutput, result)
        else:
            executed_trade = {
                "action": final_action,
                "symbol": symbol,
                "quantity": position_size,
                "timestamp": get_utc_now(),
                "message": f"Trade executed (simulated): {final_action} {position_size} {symbol}",
                "decision": state.get("final_decision", {}),
                "risk_assessment": risk_signals
            }

            order_id = f"SIM_ORDER_{int(datetime.now(timezone.utc).timestamp() * 1000)}"

            return {
                "executed_trade": executed_trade,
                "order_id": order_id,
                "execution_status": "SUCCESS",
                "execution_time": time.time() - start_time,
                "current_node": "execute_trade"
            }

    except Exception as e:
        logger.error(f"Trade execution failed: {e}")
        return {
            "executed_trade": {},
            "order_id": None,
            "execution_status": "FAILED",
            "error": str(e),
            "execution_time": time.time() - start_time,
            "current_node": "execute_trade"
        }


@async_retry_with_fallback(max_attempts=3, fallback_value={
    "executed_trade": {},
    "order_id": None,
    "execution_status": "FAILED",
    "error": "Max retries exceeded",
    "current_node": "execute_trade"
})
async def execute_trade_with_retry(state: TradingState) -> ExecuteTradeOutput:
    """Execute trade with automatic retry."""
    return await execute_trade(state)


async def retry_node(state: TradingState) -> RetryOutput:
    """
    Handle retry logic for failed workflows.

    Increments retry_count and iteration counters.
    Clears error state if under retry limit.

    Args:
        state: Trading state with retry_count and error

    Returns:
        State updates with incremented retry_count and cleared error
    """
    try:
        current_retry_count = state.get("retry_count", 0)
        current_iteration = state.get("iteration", 0)
        max_retries = state.get("max_retries", 3)
        
        # Increment counters
        new_retry_count = current_retry_count + 1
        new_iteration = current_iteration + 1
        
        # Check if we've exceeded max retries
        if new_retry_count > max_retries:
            return {
                "error": f"Max retries ({max_retries}) exceeded",
                "retry_count": new_retry_count,
                "iteration": new_iteration,
                "current_node": "retry_node"
            }
        
        # Clear error and increment counters
        result = {
            "error": None,  # Clear error for retry
            "retry_count": new_retry_count,
            "iteration": new_iteration,
            "current_node": "retry_node"
        }

        return cast(RetryOutput, result)
        
    except Exception as e:
        return {
            "error": f"Retry node failed: {str(e)}",
            "retry_count": state.get("retry_count", 0),
            "iteration": state.get("iteration", 0),
            "current_node": "retry_node"
        }
