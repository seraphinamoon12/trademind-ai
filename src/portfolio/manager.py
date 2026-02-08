"""Portfolio Manager."""
from datetime import datetime
from typing import Dict, List, Optional
from decimal import Decimal
from sqlalchemy.orm import Session

from src.core.database import (
    get_db, Holding, Trade, PortfolioSnapshot, 
    AgentDecision, RiskEvent
)
from src.config import settings
from src.costs import cost_model
from src.risk import position_risk_manager


class PortfolioManager:
    """Manages portfolio state, holdings, and trade execution with safety tracking."""
    
    def __init__(self, starting_capital: float = None):
        self.starting_capital = starting_capital or settings.starting_capital
        self.cash_balance = self.starting_capital
        self.holdings: Dict[str, dict] = {}
    
    def get_holdings(self, db: Session = None) -> Dict[str, dict]:
        """Get current holdings from database."""
        should_close = db is None
        if db is None:
            db = next(get_db())
        
        try:
            holdings = db.query(Holding).all()
            return {
                h.symbol: {
                    'quantity': h.quantity,
                    'avg_cost': float(h.avg_cost),
                    'current_price': float(h.current_price) if h.current_price else None,
                    'market_value': float(h.market_value) if h.market_value else 0,
                    'unrealized_pnl': float(h.unrealized_pnl) if h.unrealized_pnl else 0,
                    'stop_loss_pct': float(h.stop_loss_pct) if h.stop_loss_pct else 0.05,
                    'stop_price': float(h.stop_price) if h.stop_price else None,
                    'sector': h.sector
                }
                for h in holdings
            }
        finally:
            if should_close:
                db.close()
    
    def get_portfolio_value(self, db: Session = None) -> dict:
        """Get total portfolio value."""
        should_close = db is None
        if db is None:
            db = next(get_db())
        
        try:
            holdings = self.get_holdings(db)
            invested_value = sum(h['market_value'] for h in holdings.values())
            
            # Get cash from latest snapshot
            latest = db.query(PortfolioSnapshot).order_by(
                PortfolioSnapshot.timestamp.desc()
            ).first()
            
            cash = float(latest.cash_balance) if latest else self.starting_capital
            total = cash + invested_value
            
            # Calculate daily P&L if we have previous snapshot
            daily_pnl = 0
            daily_pnl_pct = 0
            if latest and latest.daily_pnl:
                daily_pnl = float(latest.daily_pnl)
                daily_pnl_pct = float(latest.daily_pnl_pct) if latest.daily_pnl_pct else 0
            
            return {
                'total_value': total,
                'cash_balance': cash,
                'invested_value': invested_value,
                'total_return_pct': (total - self.starting_capital) / self.starting_capital * 100,
                'daily_pnl': daily_pnl,
                'daily_pnl_pct': daily_pnl_pct
            }
        finally:
            if should_close:
                db.close()
    
    def execute_trade(
        self,
        symbol: str,
        action: str,  # BUY or SELL
        quantity: int,
        price: float,
        strategy: str,
        reasoning: str,
        confidence: float,
        agent_signals: dict,
        db: Session = None,
        # Safety fields
        atr: float = None,
        stop_price: float = None,
        stop_loss_pct: float = None,
        sector: str = None
    ) -> bool:
        """Execute a trade and update portfolio with safety tracking."""
        should_close = db is None
        if db is None:
            db = next(get_db())
        
        try:
            total_value = quantity * price
            
            # Calculate transaction costs
            costs = cost_model.calculate_cost(quantity, price, is_market_order=True)
            
            # Calculate position heat
            position_heat = 0
            if stop_loss_pct and total_value > 0:
                position_heat = total_value * stop_loss_pct
            
            # Create trade record
            trade = Trade(
                symbol=symbol.upper(),
                action=action,
                quantity=quantity,
                price=Decimal(str(price)),
                total_value=Decimal(str(total_value)),
                strategy=strategy,
                reasoning=reasoning[:500],
                confidence=Decimal(str(confidence)),
                agent_signals=agent_signals,
                # Safety fields
                transaction_costs=Decimal(str(costs['total'])),
                slippage=Decimal(str(costs['slippage'])),
                atr_at_entry=Decimal(str(atr)) if atr else None,
                position_heat=Decimal(str(position_heat)) if position_heat > 0 else None,
                stop_price=Decimal(str(stop_price)) if stop_price else None
            )
            db.add(trade)
            
            # Update or create holding
            holding = db.query(Holding).filter(
                Holding.symbol == symbol.upper()
            ).first()
            
            if action == "BUY":
                if holding:
                    # Update average cost
                    total_cost = (holding.quantity * holding.avg_cost) + total_value
                    new_quantity = holding.quantity + quantity
                    holding.avg_cost = Decimal(str(total_cost / new_quantity))
                    holding.quantity = new_quantity
                    # Update safety fields
                    if stop_price:
                        holding.stop_price = Decimal(str(stop_price))
                    if stop_loss_pct:
                        holding.stop_loss_pct = Decimal(str(stop_loss_pct))
                    if sector:
                        holding.sector = sector
                else:
                    holding = Holding(
                        symbol=symbol.upper(),
                        quantity=quantity,
                        avg_cost=Decimal(str(price)),
                        current_price=Decimal(str(price)),
                        stop_price=Decimal(str(stop_price)) if stop_price else None,
                        stop_loss_pct=Decimal(str(stop_loss_pct)) if stop_loss_pct else Decimal('0.05'),
                        sector=sector
                    )
                    db.add(holding)
            
            elif action == "SELL":
                if holding and holding.quantity >= quantity:
                    holding.quantity -= quantity
                    if holding.quantity == 0:
                        db.delete(holding)
                else:
                    raise ValueError(f"Insufficient shares to sell: {symbol}")
            
            db.commit()
            
            # Publish event
            from src.core.events import event_bus, Events
            event_bus.publish(Events.ORDER_EXECUTED, {
                'symbol': symbol,
                'action': action,
                'quantity': quantity,
                'price': price,
                'total_value': total_value,
                'costs': costs
            })
            
            return True
            
        except Exception as e:
            db.rollback()
            print(f"Trade execution error: {e}")
            
            # Log risk event
            try:
                risk_event = RiskEvent(
                    event_type='trade_execution_error',
                    symbol=symbol.upper(),
                    strategy=strategy,
                    reason=str(e)
                )
                db.add(risk_event)
                db.commit()
            except:
                pass
            
            return False
        finally:
            if should_close:
                db.close()
    
    def update_prices(self, prices: Dict[str, float], db: Session = None):
        """Update current prices for all holdings."""
        should_close = db is None
        if db is None:
            db = next(get_db())
        
        try:
            for symbol, price in prices.items():
                holding = db.query(Holding).filter(
                    Holding.symbol == symbol.upper()
                ).first()
                
                if holding:
                    holding.current_price = Decimal(str(price))
                    holding.market_value = Decimal(str(holding.quantity * price))
                    
                    if holding.avg_cost:
                        holding.unrealized_pnl = Decimal(str(
                            holding.market_value - (holding.quantity * float(holding.avg_cost))
                        ))
                    
                    holding.updated_at = datetime.utcnow()
            
            db.commit()
        finally:
            if should_close:
                db.close()
    
    def snapshot(self, db: Session = None):
        """Create portfolio snapshot with safety tracking."""
        should_close = db is None
        if db is None:
            db = next(get_db())
        
        try:
            portfolio = self.get_portfolio_value(db)
            holdings = self.get_holdings(db)
            
            # Calculate portfolio heat
            heat = position_risk_manager.calculate_portfolio_heat(holdings)
            heat_pct = heat / portfolio['total_value'] if portfolio['total_value'] > 0 else 0
            
            snapshot = PortfolioSnapshot(
                total_value=Decimal(str(portfolio['total_value'])),
                cash_balance=Decimal(str(portfolio['cash_balance'])),
                invested_value=Decimal(str(portfolio['invested_value'])),
                total_return_pct=Decimal(str(portfolio['total_return_pct'])),
                # Safety fields
                portfolio_heat=Decimal(str(heat)),
                portfolio_heat_pct=Decimal(str(heat_pct)),
                open_positions=len(holdings),
                max_positions=5
            )
            db.add(snapshot)
            db.commit()
            
        finally:
            if should_close:
                db.close()
    
    def log_agent_decision(
        self,
        symbol: str,
        agent: str,
        decision: str,
        confidence: float,
        reasoning: str,
        data: dict = None,
        db: Session = None
    ):
        """Log an agent decision."""
        should_close = db is None
        if db is None:
            db = next(get_db())
        
        try:
            decision_record = AgentDecision(
                symbol=symbol.upper(),
                agent=agent,
                decision=decision,
                confidence=Decimal(str(confidence)),
                reasoning=reasoning[:1000],
                data=data
            )
            db.add(decision_record)
            db.commit()
        finally:
            if should_close:
                db.close()
    
    def log_risk_event(
        self,
        event_type: str,
        symbol: str = None,
        strategy: str = None,
        reason: str = None,
        details: dict = None,
        db: Session = None
    ):
        """Log a risk event."""
        should_close = db is None
        if db is None:
            db = next(get_db())
        
        try:
            event = RiskEvent(
                event_type=event_type,
                symbol=symbol.upper() if symbol else None,
                strategy=strategy,
                reason=reason,
                details=details
            )
            db.add(event)
            db.commit()
        finally:
            if should_close:
                db.close()
