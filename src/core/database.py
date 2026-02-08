"""Database models and connection."""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    create_engine, Column, Integer, BigInteger, String, Float, DateTime, 
    Numeric, JSON, text, Boolean, ForeignKey
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects.postgresql import JSONB

from src.config import settings

# Database engine - use connect_args for psycopg2
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Session:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_timescale():
    """Initialize TimescaleDB extensions and hypertables."""
    with engine.connect() as conn:
        # Enable TimescaleDB extension
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb;"))
        conn.commit()


class MarketData(Base):
    """OHLCV market data - TimescaleDB hypertable."""
    __tablename__ = "market_data"
    
    time = Column(DateTime(timezone=True), primary_key=True)
    symbol = Column(String(10), primary_key=True)
    open = Column(Numeric(12, 4))
    high = Column(Numeric(12, 4))
    low = Column(Numeric(12, 4))
    close = Column(Numeric(12, 4))
    volume = Column(BigInteger)
    
    def __repr__(self):
        return f"<MarketData({self.symbol}, {self.time})>"


class Indicator(Base):
    """Technical indicators - TimescaleDB hypertable."""
    __tablename__ = "indicators"
    
    time = Column(DateTime(timezone=True), primary_key=True)
    symbol = Column(String(10), primary_key=True)
    rsi = Column(Numeric(5, 2))
    macd = Column(Numeric(10, 4))
    macd_signal = Column(Numeric(10, 4))
    ma_50 = Column(Numeric(12, 4))
    ma_200 = Column(Numeric(12, 4))
    bb_upper = Column(Numeric(12, 4))
    bb_lower = Column(Numeric(12, 4))
    
    def __repr__(self):
        return f"<Indicator({self.symbol}, {self.time})>"


class Trade(Base):
    """Trade execution records."""
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow)
    symbol = Column(String(10), nullable=False, index=True)
    action = Column(String(10), nullable=False)  # BUY, SELL
    quantity = Column(Integer, nullable=False)
    price = Column(Numeric(12, 4), nullable=False)
    total_value = Column(Numeric(15, 2), nullable=False)
    strategy = Column(String(50), nullable=False)
    reasoning = Column(String(500))
    confidence = Column(Numeric(3, 2))
    agent_signals = Column(JSONB)
    
    # Safety fields
    transaction_costs = Column(Numeric(10, 4), default=0)
    slippage = Column(Numeric(10, 4), default=0)
    atr_at_entry = Column(Numeric(10, 4))
    position_heat = Column(Numeric(10, 4))  # Risk amount for this position
    stop_price = Column(Numeric(12, 4))
    
    def __repr__(self):
        return f"<Trade({self.action} {self.quantity} {self.symbol})>"


class Holding(Base):
    """Current portfolio holdings."""
    __tablename__ = "holdings"
    
    symbol = Column(String(10), primary_key=True)
    quantity = Column(Integer, nullable=False, default=0)
    avg_cost = Column(Numeric(12, 4), default=0)
    current_price = Column(Numeric(12, 4))
    market_value = Column(Numeric(15, 2))
    unrealized_pnl = Column(Numeric(15, 2))
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Safety fields
    stop_loss_pct = Column(Numeric(5, 4), default=0.05)  # Default 5%
    stop_price = Column(Numeric(12, 4))
    sector = Column(String(50))
    
    def __repr__(self):
        return f"<Holding({self.symbol}: {self.quantity})>"


class PortfolioSnapshot(Base):
    """Portfolio value snapshots over time."""
    __tablename__ = "portfolio_snapshots"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    total_value = Column(Numeric(15, 2))
    cash_balance = Column(Numeric(15, 2))
    invested_value = Column(Numeric(15, 2))
    daily_pnl = Column(Numeric(15, 2))
    daily_pnl_pct = Column(Numeric(8, 4))
    total_return_pct = Column(Numeric(8, 4))
    
    # Safety fields
    portfolio_heat = Column(Numeric(10, 4))  # Total heat
    portfolio_heat_pct = Column(Numeric(5, 4))
    open_positions = Column(Integer)
    max_positions = Column(Integer, default=5)
    drawdown_pct = Column(Numeric(8, 4))
    
    def __repr__(self):
        return f"<PortfolioSnapshot(${self.total_value})>"


class AgentDecision(Base):
    """Log of agent decisions for explainability."""
    __tablename__ = "agent_decisions"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow)
    symbol = Column(String(10), nullable=False, index=True)
    agent = Column(String(50), nullable=False)  # technical, sentiment, risk, orchestrator
    decision = Column(String(20), nullable=False)  # BUY, SELL, HOLD, VETO
    confidence = Column(Numeric(3, 2))
    data = Column(JSONB)  # Agent-specific data
    reasoning = Column(String(1000))
    
    def __repr__(self):
        return f"<AgentDecision({self.agent}: {self.decision})>"


# ===== SAFETY TABLES =====

class CircuitBreakerEvent(Base):
    """Circuit breaker trigger events."""
    __tablename__ = "circuit_breaker_events"
    
    id = Column(Integer, primary_key=True)
    triggered_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    reason = Column(String(500), nullable=False)
    portfolio_value = Column(Numeric(15, 2))
    daily_pnl = Column(Numeric(15, 2))
    daily_pnl_pct = Column(Numeric(8, 4))
    drawdown_pct = Column(Numeric(8, 4))
    portfolio_heat_pct = Column(Numeric(5, 4))
    reset_at = Column(DateTime(timezone=True))
    reset_by = Column(String(50))
    
    def __repr__(self):
        return f"<CircuitBreakerEvent({self.reason})>"


class RiskEvent(Base):
    """Risk events log."""
    __tablename__ = "risk_events"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow)
    event_type = Column(String(50), nullable=False)  # 'position_rejected', 'strategy_disabled', etc.
    symbol = Column(String(10))
    strategy = Column(String(50))
    reason = Column(String(500))
    details = Column(JSONB)
    
    def __repr__(self):
        return f"<RiskEvent({self.event_type}: {self.reason})>"


class StrategyPerformance(Base):
    """Strategy performance tracking for auto-disable."""
    __tablename__ = "strategy_performance"
    
    strategy_name = Column(String(50), primary_key=True)
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    gross_profit = Column(Numeric(15, 2), default=0)
    gross_loss = Column(Numeric(15, 2), default=0)
    win_rate = Column(Numeric(5, 4), default=0)
    profit_factor = Column(Numeric(8, 4))
    is_enabled = Column(Boolean, default=True)
    disabled_at = Column(DateTime(timezone=True))
    disabled_reason = Column(String(200))
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    def __repr__(self):
        return f"<StrategyPerformance({self.strategy_name}: {self.win_rate:.1%})>"


class SectorAllocation(Base):
    """Sector concentration tracking."""
    __tablename__ = "sector_allocations"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow)
    sector = Column(String(50), nullable=False)
    allocation_pct = Column(Numeric(5, 4))
    value = Column(Numeric(15, 2))
    
    def __repr__(self):
        return f"<SectorAllocation({self.sector}: {self.allocation_pct:.1%})>"


def create_hypertables():
    """Convert tables to TimescaleDB hypertables."""
    with engine.connect() as conn:
        # Market data hypertable
        conn.execute(text("""
            SELECT create_hypertable('market_data', 'time', 
                if_not_exists => TRUE,
                migrate_data => TRUE
            );
        """))
        
        # Indicators hypertable  
        conn.execute(text("""
            SELECT create_hypertable('indicators', 'time',
                if_not_exists => TRUE,
                migrate_data => TRUE
            );
        """))
        
        # Create indexes
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_market_data_symbol_time 
            ON market_data (symbol, time DESC);
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_indicators_symbol_time 
            ON indicators (symbol, time DESC);
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_trades_symbol 
            ON trades (symbol, timestamp DESC);
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_circuit_breaker_triggered 
            ON circuit_breaker_events (triggered_at DESC);
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_risk_events 
            ON risk_events (timestamp DESC);
        """))
        
        conn.commit()


def init_db():
    """Initialize database with all tables and hypertables."""
    init_timescale()
    Base.metadata.create_all(bind=engine)
    create_hypertables()
