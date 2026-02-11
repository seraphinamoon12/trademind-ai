"""Nodes for risk assessment, trade execution, and retry logic in LangGraph workflow."""

import pandas as pd
import time
import asyncio
import logging
import requests
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Dict, Callable, cast, Optional

from src.trading_graph.state import TradingState
from src.trading_graph.types import RiskAssessmentOutput, ExecuteTradeOutput, RetryOutput
from src.agents.risk import RiskAgent
from src.trading_graph.validation import get_utc_now
from src.config import settings

logger = logging.getLogger(__name__)


def _place_order_via_api(symbol: str, action: str, quantity: int, order_type: str = "MKT", price: Optional[float] = None) -> Dict[str, Any]:
    """
    Place order via TradeMind API with retry logic.

    Args:
        symbol: Stock symbol (e.g., "AAPL")
        action: "BUY" or "SELL"
        quantity: Number of shares
        order_type: "MKT" or "LMT"
        price: Limit price (required for LMT orders)

    Returns:
        Dict with order_id, status, symbol, action, quantity

    Raises:
        Exception: If API call fails after retries
    """
    base_url = settings.trademind_api_url
    endpoint = f"{base_url}/api/ibkr/orders"

    payload = {
        "symbol": symbol,
        "action": action,
        "quantity": quantity,
        "order_type": order_type
    }

    if order_type == "LMT" and price is not None:
        payload["price"] = price

    max_retries = 3
    retry_delay = 1

    for attempt in range(max_retries):
        try:
            logger.info(f"API Call {attempt + 1}/{max_retries}: POST {endpoint} - {payload}")
            response = requests.post(
                endpoint,
                json=payload,
                timeout=30,
                headers={"Content-Type": "application/json"}
            )

            response.raise_for_status()
            result = response.json()

            logger.info(f"API Response: {result}")
            return result

        except requests.exceptions.Timeout:
            logger.warning(f"API timeout on attempt {attempt + 1}/{max_retries}")
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"API connection error on attempt {attempt + 1}/{max_retries}: {e}")
        except requests.exceptions.HTTPError as e:
            logger.error(f"API HTTP error: {e.response.status_code} - {e.response.text}")
            if e.response.status_code < 500:
                raise
        except Exception as e:
            logger.error(f"Unexpected API error on attempt {attempt + 1}/{max_retries}: {e}")

        if attempt < max_retries - 1:
            time.sleep(retry_delay)

    raise Exception(f"Failed to place order via API after {max_retries} attempts")


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
    Perform risk assessment using RiskAgent with position awareness.

    Validates trade against:
    - Liquidity filters (volume, price, spread)
    - Earnings filter
    - Sector concentration limits
    - Position size limits
    - Cash availability (for BUY)
    - Position holding check (for SELL)

    Args:
        state: Trading state with market_data, final_decision, and position data

    Returns:
        State updates with risk_signals
    """
    try:
        symbol = state["symbol"]
        market_data_dict = state.get("market_data", {})
        final_decision = state.get("final_decision", {})
        final_action = state.get("final_action")
        
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
        
        # Position-aware checks
        positions = state.get("positions", {})
        portfolio_value = state.get("portfolio_value", 100000.0)
        cash_balance = state.get("cash_balance", 0.0)
        sector_exposure = state.get("sector_exposure", {})
        
        # Check SELL - only if we have a position
        if final_action == "SELL":
            position = positions.get(symbol)
            if not position or position.get("quantity", 0) == 0:
                risk_signals = {
                    "decision": "HOLD",
                    "confidence": 1.0,
                    "reasoning": f"Cannot SELL {symbol} - no position held",
                    "agent_name": "position_manager",
                    "data": {
                        "recommended_size": 0,
                        "position_held": False,
                        "risk_level": "HIGH"
                    }
                }
                return {
                    "risk_signals": risk_signals,
                    "current_node": "risk_assessment"
                }
        
        # Initialize RiskAgent
        risk_agent = RiskAgent(
            max_position_pct=state.get("max_position_pct", settings.max_position_pct),
            stop_loss_pct=state.get("stop_loss_pct", settings.stop_loss_pct),
            take_profit_pct=state.get("take_profit_pct", settings.take_profit_pct),
            max_daily_loss_pct=state.get("max_daily_loss_pct", settings.max_daily_loss_pct)
        )
        
        # Convert positions to format expected by RiskAgent
        current_holdings = {}
        for sym, pos_data in positions.items():
            if isinstance(pos_data, dict):
                current_holdings[sym] = {
                    "quantity": pos_data.get("quantity", 0),
                    "market_value": pos_data.get("market_value", 0),
                    "avg_cost": pos_data.get("avg_cost", 0)
                }
        
        daily_pnl = state.get("daily_pnl", 0.0)
        
        # Analyze risk
        signal = await risk_agent.analyze(
            symbol=symbol,
            data=data,
            portfolio_value=portfolio_value,
            current_holdings=current_holdings,
            daily_pnl=daily_pnl
        )
        
        # Additional position-aware validations
        signal_data = signal.data or {}
        
        # Sector exposure check
        if final_action == "BUY":
            from src.risk.sector_monitor import sector_monitor
            can_add, sector_msg = sector_monitor.can_add_to_sector(
                holdings=current_holdings,
                symbol=symbol,
                portfolio_value=portfolio_value,
                estimated_position_value=signal_data.get("recommended_size", 0) * data.iloc[-1].get("close", 0)
            )
            if not can_add:
                risk_signals = {
                    "decision": "HOLD",
                    "confidence": 1.0,
                    "reasoning": f"Sector limit: {sector_msg}",
                    "agent_name": "position_manager",
                    "data": {
                        "recommended_size": 0,
                        "sector_check": sector_msg,
                        "risk_level": "HIGH"
                    }
                }
                return {
                    "risk_signals": risk_signals,
                    "current_node": "risk_assessment"
                }
        
        # Cash availability check for BUY
        if final_action == "BUY":
            recommended_size = signal_data.get("recommended_size", 0)
            if recommended_size > 0:
                current_price = data.iloc[-1].get("close", 0)
                if current_price > 0:
                    required_cash = recommended_size * current_price
                    available_cash = cash_balance * 0.90  # Reserve 10% for safety
                    
                    if required_cash > available_cash:
                        # Adjust position size to fit available cash
                        adjusted_size = int(available_cash / current_price)
                        if adjusted_size > 0:
                            signal_data["recommended_size"] = adjusted_size
                            signal_data["cash_constraint"] = f"Adjusted from {recommended_size} to {adjusted_size} shares"
                        else:
                            risk_signals = {
                                "decision": "HOLD",
                                "confidence": 1.0,
                                "reasoning": f"Insufficient cash: need ${required_cash:,.2f}, have ${available_cash:,.2f}",
                                "agent_name": "position_manager",
                                "data": {
                                    "recommended_size": 0,
                                    "cash_required": required_cash,
                                    "cash_available": available_cash,
                                    "risk_level": "HIGH"
                                }
                            }
                            return {
                                "risk_signals": risk_signals,
                                "current_node": "risk_assessment"
                            }
        
        # Position size check
        if final_action == "BUY":
            position = positions.get(symbol, {})
            current_qty = position.get("quantity", 0) if position else 0
            current_qty = abs(current_qty)
            recommended_size = signal_data.get("recommended_size", 0)
            new_qty = current_qty + recommended_size
            
            current_price = data.iloc[-1].get("close", 0)
            if current_price > 0:
                new_position_value = new_qty * current_price
                new_position_pct = new_position_value / portfolio_value if portfolio_value > 0 else 0
                
                max_pct = settings.max_position_pct
                if new_position_pct > max_pct:
                    # Adjust to max allowed
                    adjusted_value = portfolio_value * max_pct
                    adjusted_size = int(adjusted_value / current_price) - current_qty
                    
                    if adjusted_size > 0:
                        signal_data["recommended_size"] = adjusted_size
                        signal_data["position_constraint"] = (
                            f"Adjusted position size: {new_position_pct:.1%} > {max_pct:.0%}"
                        )
                    else:
                        risk_signals = {
                            "decision": "HOLD",
                            "confidence": 1.0,
                            "reasoning": f"Position would be {new_position_pct:.1%} of portfolio (max: {max_pct:.0%})",
                            "agent_name": "position_manager",
                            "data": {
                                "recommended_size": 0,
                                "current_position_pct": (current_qty * current_price) / portfolio_value,
                                "new_position_pct": new_position_pct,
                                "risk_level": "HIGH"
                            }
                        }
                        return {
                            "risk_signals": risk_signals,
                            "current_node": "risk_assessment"
                        }
        
        # Convert AgentSignal to risk_signals format
        risk_signals = {
            "decision": signal.decision.value,
            "confidence": signal.confidence,
            "reasoning": signal.reasoning,
            "agent_name": signal.agent_name,
            "data": signal_data
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
    Execute trade via IBKR with full error handling and position awareness.

    This is the final node in the graph - actually places orders.

    Steps:
    1. Validate state (final_action, human_approved)
    2. Check position constraints (SELL requires holding, BUY checks cash)
    3. Get position size from risk assessment
    4. Execute trade via TradeMind API
    5. Return execution result with order_id and status

    Args:
        state: Trading state with final_action, human_approved, risk_signals, positions

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

        # Position-aware validation
        positions = state.get("positions", {})
        
        # SELL: Must have a position
        if final_action == "SELL":
            position = positions.get(symbol)
            if not position or position.get("quantity", 0) == 0:
                return {
                    "executed_trade": {},
                    "order_id": None,
                    "execution_status": "REJECTED",
                    "error": f"Cannot SELL {symbol} - no position held",
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

        # BUY: Check cash availability
        if final_action == "BUY":
            cash_balance = state.get("cash_balance", 0)
            if cash_balance <= 0:
                return {
                    "executed_trade": {},
                    "order_id": None,
                    "execution_status": "REJECTED",
                    "error": "Insufficient cash available",
                    "execution_time": time.time() - start_time,
                    "current_node": "execute_trade"
                }

        if settings.ibkr_enabled:
            try:
                api_result = _place_order_via_api(
                    symbol=symbol,
                    action=final_action,
                    quantity=int(position_size),
                    order_type="MKT"
                )
            except Exception as api_error:
                logger.error(f"API order placement failed: {api_error}")
                return {
                    "executed_trade": {},
                    "order_id": None,
                    "execution_status": "FAILED",
                    "error": f"API error: {str(api_error)}",
                    "execution_time": time.time() - start_time,
                    "current_node": "execute_trade"
                }

            execution_time = time.time() - start_time

            executed_trade = {
                "action": final_action,
                "symbol": symbol,
                "quantity": position_size,
                "timestamp": get_utc_now(),
                "message": f"Trade executed via TradeMind API: {final_action} {position_size} {symbol}",
                "order_type": "MKT",
                "decision": state.get("final_decision", {}),
                "risk_assessment": risk_signals
            }

            return {
                "executed_trade": executed_trade,
                "order_id": api_result.get("order_id"),
                "execution_status": api_result.get("status", "SUCCESS"),
                "execution_time": execution_time,
                "current_node": "execute_trade"
            }
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
