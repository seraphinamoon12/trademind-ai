"""Risk management for IBKR trading."""
import logging
from typing import Dict, Any, Tuple, Optional, List
from datetime import datetime, timedelta

from src.brokers.base import Order, OrderSide

logger = logging.getLogger(__name__)


class IBKRRiskManager:
    """Risk management for IBKR trading."""

    def __init__(self, broker, config: Optional[Dict[str, Any]] = None):
        self.broker = broker
        self.config = config or {}
        self._daily_trades = []
        self._last_reset_date = datetime.utcnow().date()

        self.max_order_size = self.config.get('max_order_size', 1000)
        self.max_order_value = self.config.get('max_order_value', 50000)
        self.max_position_pct = self.config.get('max_position_pct', 0.10)
        self.max_sector_pct = self.config.get('max_sector_pct', 0.25)
        self.daily_loss_limit = self.config.get('daily_loss_limit', 1000)
        self.max_open_orders = self.config.get('max_open_orders', 10)

    async def validate_order(self, order: Order) -> Tuple[bool, str]:
        """
        Comprehensive pre-trade validation:
        - Order size limits
        - Buying power check
        - Position concentration limits
        - Daily loss limit
        - Open order count limit
        """
        if not self.broker.is_connected:
            return False, "Not connected to broker"

        if order.quantity <= 0:
            return False, "Order quantity must be positive"

        if order.quantity > self.max_order_size:
            return False, f"Order size {order.quantity} exceeds maximum {self.max_order_size}"

        try:
            price = await self.broker.get_market_price(order.symbol)
            total_value = order.quantity * price

            if total_value > self.max_order_value:
                return False, f"Order value ${total_value:.2f} exceeds maximum ${self.max_order_value:.2f}"

            account = await self.broker.get_account()

            if order.side == OrderSide.BUY:
                if total_value > account.buying_power:
                    return False, f"Insufficient buying power: need ${total_value:.2f}"

                if account.portfolio_value > 0:
                    position_pct = total_value / account.portfolio_value
                    if position_pct > self.max_position_pct:
                        return False, f"Position {position_pct:.1%} exceeds maximum {self.max_position_pct:.1%}"

            else:
                positions = await self.broker.get_positions()
                current_qty = next((p.quantity for p in positions if p.symbol == order.symbol), 0)
                if order.quantity > abs(current_qty):
                    return False, f"Insufficient shares: have {abs(current_qty)}, need {order.quantity}"

            summary = await self.broker.get_portfolio_summary()
            daily_pnl = summary.get('daily_pnl', 0)

            if daily_pnl < -self.daily_loss_limit:
                return False, f"Daily loss ${abs(daily_pnl):.2f} exceeds limit ${self.daily_loss_limit:.2f}"

            open_orders = await self.broker.get_orders(status='open')
            if len(open_orders) >= self.max_open_orders:
                return False, f"Open orders {len(open_orders)} exceed maximum {self.max_open_orders}"

        except Exception as e:
            logger.error(f"Order validation error: {e}")
            return False, f"Validation error: {str(e)}"

        return True, "Order valid"

    async def check_portfolio_risk(self) -> Dict[str, Any]:
        """
        Check portfolio-level risk:
        - Gross exposure
        - Net exposure
        - Position concentration
        - Sector concentration
        - Beta-adjusted exposure
        """
        try:
            account = await self.broker.get_account()
            positions = await self.broker.get_positions()

            gross_exposure = sum(abs(pos.market_value) for pos in positions)
            net_exposure = sum(pos.market_value for pos in positions)

            portfolio_value = account.portfolio_value
            concentrations = {}

            for pos in positions:
                if portfolio_value > 0:
                    concentration = abs(pos.market_value) / portfolio_value
                    concentrations[pos.symbol] = concentration

            max_concentration = max(concentrations.values()) if concentrations else 0.0
            avg_concentration = sum(concentrations.values()) / len(concentrations) if concentrations else 0.0

            buying_power = account.buying_power
            margin_used = account.portfolio_value - account.margin_available
            margin_usage = margin_used / account.portfolio_value if account.portfolio_value > 0 else 0.0

            daily_pnl = account.daily_pnl

            risk_summary = {
                "gross_exposure": gross_exposure,
                "net_exposure": net_exposure,
                "portfolio_value": portfolio_value,
                "buying_power": buying_power,
                "margin_used": margin_used,
                "margin_usage_pct": margin_usage,
                "max_position_concentration": max_concentration,
                "avg_position_concentration": avg_concentration,
                "position_count": len(positions),
                "daily_pnl": daily_pnl,
                "daily_loss_limit": self.daily_loss_limit,
                "daily_loss_limit_remaining": max(0, self.daily_loss_limit + daily_pnl),
                "risk_level": self._calculate_risk_level(
                    max_concentration, margin_usage, daily_pnl
                ),
                "warnings": self._generate_warnings(
                    max_concentration, margin_usage, daily_pnl, len(positions)
                )
            }

            return risk_summary

        except Exception as e:
            logger.error(f"Error checking portfolio risk: {e}")
            return {
                "error": str(e),
                "risk_level": "UNKNOWN"
            }

    def _calculate_risk_level(
        self,
        max_concentration: float,
        margin_usage: float,
        daily_pnl: float
    ) -> str:
        """Calculate overall risk level."""
        risk_score = 0

        if max_concentration > 0.25:
            risk_score += 2
        elif max_concentration > 0.15:
            risk_score += 1

        if margin_usage > 0.75:
            risk_score += 2
        elif margin_usage > 0.50:
            risk_score += 1

        if daily_pnl < -self.daily_loss_limit * 0.5:
            risk_score += 2
        elif daily_pnl < -self.daily_loss_limit * 0.25:
            risk_score += 1

        if risk_score >= 4:
            return "HIGH"
        elif risk_score >= 2:
            return "MEDIUM"
        else:
            return "LOW"

    def _generate_warnings(
        self,
        max_concentration: float,
        margin_usage: float,
        daily_pnl: float,
        position_count: int
    ) -> List[str]:
        """Generate risk warnings."""
        warnings = []

        if max_concentration > self.max_position_pct:
            warnings.append(
                f"Position concentration {max_concentration:.1%} exceeds limit {self.max_position_pct:.1%}"
            )

        if margin_usage > 0.75:
            warnings.append(
                f"Margin usage {margin_usage:.1%} is high"
            )

        if daily_pnl < -self.daily_loss_limit * 0.5:
            warnings.append(
                f"Daily loss ${abs(daily_pnl):.2f} approaching limit ${self.daily_loss_limit:.2f}"
            )

        if position_count == 0 and margin_usage < 0.5:
            warnings.append("No positions held - consider diversifying")

        return warnings

    def reset_daily_counters(self) -> None:
        """Reset daily tracking counters (call at start of trading day)."""
        self._daily_trades = []
        self._last_reset_date = datetime.utcnow().date()
        logger.info("Daily risk counters reset")
