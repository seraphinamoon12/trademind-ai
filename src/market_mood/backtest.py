"""Backtesting module for Market Mood Detection."""
from typing import Dict, Any, List, Optional, Literal
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import logging
import json
import csv
from pathlib import Path

import yfinance as yf
import pandas as pd
import numpy as np

from src.market_mood.config import MarketMoodConfig
from src.market_mood.signals import SignalGenerator
from src.market_mood.models import MoodScore, IndicatorType
from src.market_mood.exceptions import DataProviderError
from src.core.metrics import (
    calculate_sharpe_ratio,
    calculate_max_drawdown,
    calculate_win_rate,
    calculate_profit_factor,
    calculate_calmar_ratio,
    calculate_sortino_ratio,
    calculate_volatility,
    calculate_cagr,
    generate_performance_report,
)

logger = logging.getLogger(__name__)


@dataclass
class Trade:
    """Represents a single trade in the backtest."""
    
    entry_date: datetime
    exit_date: Optional[datetime] = None
    symbol: str = "SPY"
    entry_price: float = 0.0
    exit_price: Optional[float] = None
    quantity: int = 0
    signal_type: Literal["BUY", "SELL"] = "BUY"
    mood_classification: str = "neutral"
    mood_score: float = 50.0
    confidence: float = 0.0
    entry_reason: str = ""
    exit_reason: str = ""
    pnl: float = 0.0
    pnl_pct: float = 0.0
    holding_period_days: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert trade to dictionary."""
        return {
            "entry_date": self.entry_date.isoformat(),
            "exit_date": self.exit_date.isoformat() if self.exit_date else None,
            "symbol": self.symbol,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "quantity": self.quantity,
            "signal_type": self.signal_type,
            "mood_classification": self.mood_classification,
            "mood_score": self.mood_score,
            "confidence": self.confidence,
            "entry_reason": self.entry_reason,
            "exit_reason": self.exit_reason,
            "pnl": self.pnl,
            "pnl_pct": self.pnl_pct,
            "holding_period_days": self.holding_period_days,
        }


@dataclass
class MoodSignal:
    """Represents a mood-based trading signal."""
    
    date: datetime
    signal: Literal["STRONG_BUY", "BUY", "HOLD", "REDUCE", "SELL", "NO_SIGNAL"]
    mood_classification: str
    mood_score: float
    confidence: float
    sentiment: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert signal to dictionary."""
        return {
            "date": self.date.isoformat(),
            "signal": self.signal,
            "mood_classification": self.mood_classification,
            "mood_score": self.mood_score,
            "confidence": self.confidence,
            "sentiment": self.sentiment,
        }


@dataclass
class BacktestResult:
    """Results of a mood-based backtest."""
    
    trades: List[Trade] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)
    equity_dates: List[datetime] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)
    signals: List[MoodSignal] = field(default_factory=list)
    buy_and_hold_return: float = 0.0
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    initial_capital: float = 100000.0
    final_capital: float = 100000.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "trades": [t.to_dict() for t in self.trades],
            "equity_curve": self.equity_curve,
            "equity_dates": [d.isoformat() for d in self.equity_dates],
            "metrics": self.metrics,
            "signals": [s.to_dict() for s in self.signals],
            "buy_and_hold_return": self.buy_and_hold_return,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "initial_capital": self.initial_capital,
            "final_capital": self.final_capital,
        }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get a summary of performance metrics."""
        return {
            "total_return": self.metrics.get("total_return", 0),
            "total_return_pct": self.metrics.get("total_return_pct", 0),
            "annualized_return": self.metrics.get("annualized_return", 0),
            "win_rate": self.metrics.get("win_rate", 0),
            "avg_return": self.metrics.get("avg_return", 0),
            "max_drawdown": self.metrics.get("max_drawdown", 0),
            "sharpe_ratio": self.metrics.get("sharpe_ratio", 0),
            "sortino_ratio": self.metrics.get("sortino_ratio", 0),
            "calmar_ratio": self.metrics.get("calmar_ratio", 0),
            "volatility": self.metrics.get("volatility", 0),
            "total_trades": len(self.trades),
            "winning_trades": self.metrics.get("winning_trades", 0),
            "losing_trades": self.metrics.get("losing_trades", 0),
            "profit_factor": self.metrics.get("profit_factor", 0),
            "buy_and_hold_return_pct": self.buy_and_hold_return * 100,
        }


class MoodBacktester:
    """Backtester for mood-based trading strategies."""
    
    def __init__(
        self,
        start_date: str,
        end_date: str,
        initial_capital: float = 100000,
        symbol: str = "SPY",
        config: Optional[MarketMoodConfig] = None
    ):
        """Initialize the mood backtester.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            initial_capital: Initial capital for backtest
            symbol: Symbol to trade (default: SPY)
            config: MarketMoodConfig instance
        """
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d")
        self.end_date = datetime.strptime(end_date, "%Y-%m-%d")
        self.initial_capital = initial_capital
        self.symbol = symbol
        self.config = config or MarketMoodConfig()
        
        self.signal_generator = SignalGenerator(self.config)
        
        self.price_data: Optional[pd.DataFrame] = None
        self.vix_data: Optional[pd.DataFrame] = None
        self.historical_moods: List[Dict[str, Any]] = []
        
        self.trades: List[Trade] = []
        self.signals: List[MoodSignal] = []
        self.equity_curve: List[float] = []
        self.equity_dates: List[datetime] = []
        self.current_capital = initial_capital
        self.position = 0
        self.entry_price = 0.0
        self.current_trade: Optional[Trade] = None
        
    def fetch_historical_data(self) -> Dict[str, Any]:
        """Fetch historical data for backtesting.
        
        Returns:
            Dictionary with data fetch status
        """
        logger.info(f"Fetching historical data from {self.start_date.date()} to {self.end_date.date()}")
        
        try:
            ticker = yf.Ticker(self.symbol)
            hist = ticker.history(
                start=self.start_date,
                end=self.end_date + timedelta(days=1),
                interval="1d"
            )
            
            if hist.empty:
                raise DataProviderError(f"No data found for {self.symbol}")
            
            self.price_data = hist.reset_index()
            self.price_data.columns = [c.lower() for c in self.price_data.columns]
            
            if 'date' in self.price_data.columns:
                self.price_data['date'] = pd.to_datetime(self.price_data['date'])
            elif 'datetime' in self.price_data.columns:
                self.price_data['date'] = pd.to_datetime(self.price_data['datetime'])
                self.price_data = self.price_data.drop(columns=['datetime'])
            else:
                self.price_data['date'] = pd.to_datetime(self.price_data.index)
            
            logger.info(f"Fetched {len(self.price_data)} days of price data")
            
            vix_ticker = yf.Ticker("^VIX")
            vix_hist = vix_ticker.history(
                start=self.start_date,
                end=self.end_date + timedelta(days=1),
                interval="1d"
            )
            
            if not vix_hist.empty:
                self.vix_data = vix_hist.reset_index()
                self.vix_data.columns = [c.lower() for c in self.vix_data.columns]
                if 'date' in self.vix_data.columns:
                    self.vix_data['date'] = pd.to_datetime(self.vix_data['date'])
                else:
                    self.vix_data['date'] = pd.to_datetime(self.vix_data.index)
                logger.info(f"Fetched {len(self.vix_data)} days of VIX data")
            
            return {
                "status": "success",
                "price_data_points": len(self.price_data),
                "vix_data_points": len(self.vix_data) if self.vix_data is not None else 0,
            }
        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            raise DataProviderError(f"Failed to fetch historical data: {e}")
    
    def _calculate_mood_for_date(self, date: datetime) -> Dict[str, Any]:
        """Calculate mood score for a specific date.
        
        Args:
            date: Date to calculate mood for
            
        Returns:
            Dictionary with mood information
        """
        row = self.price_data[self.price_data['date'].dt.date == date.date()]
        
        if row.empty:
            return {
                "score": 50.0,
                "sentiment": "neutral",
                "confidence": 0.0,
                "trend": "stable",
            }
        
        current_price = float(row['close'].iloc[0])
        
        vix_value = None
        if self.vix_data is not None:
            vix_row = self.vix_data[self.vix_data['date'].dt.date == date.date()]
            if not vix_row.empty:
                vix_value = float(vix_row['close'].iloc[0])
        
        if vix_value is not None:
            if vix_value >= 30:
                mood_score = 20.0
                sentiment = "extreme_fear"
            elif vix_value >= 25:
                mood_score = 35.0
                sentiment = "fear"
            elif vix_value >= 20:
                mood_score = 50.0
                sentiment = "neutral"
            elif vix_value >= 15:
                mood_score = 65.0
                sentiment = "greed"
            else:
                mood_score = 80.0
                sentiment = "extreme_greed"
        else:
            mood_score = 50.0
            sentiment = "neutral"
        
        if len(self.historical_moods) > 0:
            prev_score = self.historical_moods[-1]['score']
            if mood_score > prev_score + 5:
                trend = "improving"
            elif mood_score < prev_score - 5:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "stable"
        
        confidence = 0.8 if vix_value is not None else 0.5
        
        return {
            "score": mood_score,
            "sentiment": sentiment,
            "confidence": confidence,
            "trend": trend,
            "vix": vix_value,
            "price": current_price,
        }
    
    def _calculate_position_size(self, signal: str, confidence: float, mood_score: float) -> int:
        """Calculate position size based on signal and mood.
        
        Args:
            signal: Trading signal
            confidence: Confidence level
            mood_score: Mood score
            
        Returns:
            Number of shares to trade
        """
        sizing_map = {
            "STRONG_BUY": 1.0,
            "BUY": 0.75,
            "SELL": -1.0,
            "REDUCE": -0.75,
        }
        
        base_allocation = sizing_map.get(signal, 0.0)
        
        if base_allocation == 0.0:
            return 0
        
        confidence_multiplier = 0.5 + confidence * 0.5
        mood_multiplier = mood_score / 50.0 if mood_score > 0 else 1.0
        
        if signal in ["BUY", "STRONG_BUY"]:
            if mood_score < 30:
                mood_multiplier = 1.5
            elif mood_score < 50:
                mood_multiplier = 1.2
        
        final_allocation = base_allocation * confidence_multiplier * mood_multiplier
        max_allocation = min(abs(final_allocation), 1.0)
        
        if self.price_data is None or self.price_data.empty:
            return 0
        
        current_price = self.price_data[self.price_data['date'].dt.date == self.current_date.date()]
        if current_price.empty:
            return 0
        
        price = float(current_price['close'].iloc[0])
        shares = int((self.current_capital * max_allocation) / price)
        
        return shares
    
    def run_backtest(self) -> BacktestResult:
        """Run the backtest strategy.
        
        Returns:
            BacktestResult with all results
        """
        logger.info("Running mood-based backtest")
        
        if self.price_data is None or self.price_data.empty:
            self.fetch_historical_data()
        
        self.trades = []
        self.signals = []
        self.equity_curve = []
        self.equity_dates = []
        self.current_capital = self.initial_capital
        self.position = 0
        self.entry_price = 0.0
        self.current_trade = None
        
        for idx, row in self.price_data.iterrows():
            self.current_date = pd.to_datetime(row['date'])
            current_price = float(row['close'])
            
            mood_data = self._calculate_mood_for_date(self.current_date)
            self.historical_moods.append(mood_data)
            
            mood_dict = {
                'score': mood_data['score'],
                'confidence': mood_data['confidence'],
                'trend': mood_data['trend'],
            }
            
            signal_info = self.signal_generator.generate_signals(mood_dict)
            signal = signal_info['signal']
            mood_classification = signal_info['mood_classification']
            
            mood_signal = MoodSignal(
                date=self.current_date,
                signal=signal,
                mood_classification=mood_classification,
                mood_score=mood_data['score'],
                confidence=mood_data['confidence'],
                sentiment=mood_data['sentiment']
            )
            self.signals.append(mood_signal)
            
            position_size = self._calculate_position_size(
                signal, mood_data['confidence'], mood_data['score']
            )
            
            if self.position == 0:
                if signal in ["BUY", "STRONG_BUY"] and position_size > 0:
                    shares = min(position_size, int(self.current_capital / current_price))
                    if shares > 0:
                        self.position = shares
                        self.entry_price = current_price
                        self.current_trade = Trade(
                            entry_date=self.current_date,
                            symbol=self.symbol,
                            entry_price=current_price,
                            quantity=shares,
                            signal_type="BUY",
                            mood_classification=mood_classification,
                            mood_score=mood_data['score'],
                            confidence=mood_data['confidence'],
                            entry_reason=f"{signal} signal, {mood_classification} mood",
                        )
                        self.current_capital -= shares * current_price
            else:
                if signal in ["SELL", "REDUCE"] or (signal == "HOLD" and position_size < 0):
                    if self.current_trade:
                        self.current_trade.exit_date = self.current_date
                        self.current_trade.exit_price = current_price
                        self.current_trade.pnl = (current_price - self.entry_price) * self.position
                        self.current_trade.pnl_pct = ((current_price - self.entry_price) / self.entry_price) * 100
                        self.current_trade.holding_period_days = (self.current_date - self.current_trade.entry_date).days
                        self.current_trade.exit_reason = f"{signal} signal, {mood_classification} mood"
                        self.trades.append(self.current_trade)
                    
                    self.current_capital += self.position * current_price
                    self.position = 0
                    self.entry_price = 0.0
                    self.current_trade = None
            
            portfolio_value = self.current_capital + (self.position * current_price)
            self.equity_curve.append(portfolio_value)
            self.equity_dates.append(self.current_date)
        
        if self.position > 0 and self.current_trade:
            final_price = self.equity_curve[-1] if self.equity_curve else self.entry_price
            self.current_trade.exit_date = self.equity_dates[-1] if self.equity_dates else self.current_date
            self.current_trade.exit_price = final_price / self.position if self.position > 0 else self.entry_price
            self.current_trade.pnl = (self.current_trade.exit_price - self.entry_price) * self.position
            self.current_trade.pnl_pct = ((self.current_trade.exit_price - self.entry_price) / self.entry_price) * 100
            self.current_trade.holding_period_days = (self.current_trade.exit_date - self.current_trade.entry_date).days
            self.current_trade.exit_reason = "End of backtest"
            self.trades.append(self.current_trade)
        
        result = self.calculate_metrics()
        
        logger.info(f"Backtest complete: {len(self.trades)} trades, final capital: ${result.final_capital:,.2f}")
        
        return result
    
    def calculate_metrics(self) -> BacktestResult:
        """Calculate performance metrics.
        
        Returns:
            BacktestResult with calculated metrics
        """
        equity_series = pd.Series(self.equity_curve)
        
        initial_price = self.price_data['close'].iloc[0] if self.price_data is not None else 100
        final_price = self.price_data['close'].iloc[-1] if self.price_data is not None else 100
        buy_and_hold_return = (final_price - initial_price) / initial_price
        
        trade_dicts = [t.to_dict() for t in self.trades]
        
        metrics = generate_performance_report(trade_dicts, equity_series)
        
        if not equity_series.empty:
            years = (self.end_date - self.start_date).days / 365.25
            metrics['annualized_return'] = calculate_cagr(
                self.initial_capital,
                equity_series.iloc[-1],
                years if years > 0 else 1
            ) * 100
        else:
            metrics['annualized_return'] = 0.0
        
        metrics['winning_trades'] = sum(1 for t in self.trades if t.pnl > 0)
        metrics['losing_trades'] = sum(1 for t in self.trades if t.pnl <= 0)
        metrics['avg_return'] = np.mean([t.pnl for t in self.trades]) if self.trades else 0.0
        
        return BacktestResult(
            trades=self.trades,
            equity_curve=self.equity_curve,
            equity_dates=self.equity_dates,
            metrics=metrics,
            signals=self.signals,
            buy_and_hold_return=buy_and_hold_return,
            start_date=self.start_date,
            end_date=self.end_date,
            initial_capital=self.initial_capital,
            final_capital=self.equity_curve[-1] if self.equity_curve else self.initial_capital,
        )
    
    def generate_report(self, output_file: Optional[str] = None) -> Dict[str, Any]:
        """Generate a comprehensive backtest report.
        
        Args:
            output_file: Optional file path to save report
            
        Returns:
            Dictionary with report data
        """
        result = self.calculate_metrics()
        
        report = {
            "backtest_summary": {
                "symbol": self.symbol,
                "start_date": self.start_date.isoformat(),
                "end_date": self.end_date.isoformat(),
                "initial_capital": self.initial_capital,
                "final_capital": result.final_capital,
                "total_trades": len(result.trades),
            },
            "performance_metrics": result.metrics,
            "buy_and_hold": {
                "return": result.buy_and_hold_return,
                "return_pct": result.buy_and_hold_return * 100,
            },
            "signals_by_mood": self._analyze_signals_by_mood(),
            "trades_by_mood": self._analyze_trades_by_mood(),
        }
        
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            logger.info(f"Report saved to {output_file}")
        
        return report
    
    def _analyze_signals_by_mood(self) -> Dict[str, Any]:
        """Analyze signals distribution by mood type.
        
        Returns:
            Dictionary with signal analysis
        """
        mood_counts = {}
        signal_counts = {}
        
        for signal in self.signals:
            mood = signal.mood_classification
            sig = signal.signal
            
            mood_counts[mood] = mood_counts.get(mood, 0) + 1
            signal_counts[sig] = signal_counts.get(sig, 0) + 1
        
        return {
            "by_mood_classification": mood_counts,
            "by_signal_type": signal_counts,
            "total_signals": len(self.signals),
        }
    
    def _analyze_trades_by_mood(self) -> Dict[str, Any]:
        """Analyze trade performance by mood type.
        
        Returns:
            Dictionary with trade analysis by mood
        """
        mood_trades = {}
        
        for trade in self.trades:
            mood = trade.mood_classification
            if mood not in mood_trades:
                mood_trades[mood] = {
                    "count": 0,
                    "total_pnl": 0.0,
                    "winning_trades": 0,
                    "avg_pnl": 0.0,
                }
            
            mood_trades[mood]["count"] += 1
            mood_trades[mood]["total_pnl"] += trade.pnl
            if trade.pnl > 0:
                mood_trades[mood]["winning_trades"] += 1
        
        for mood in mood_trades:
            count = mood_trades[mood]["count"]
            mood_trades[mood]["avg_pnl"] = mood_trades[mood]["total_pnl"] / count if count > 0 else 0.0
            mood_trades[mood]["win_rate"] = (mood_trades[mood]["winning_trades"] / count * 100) if count > 0 else 0.0
        
        return mood_trades
    
    def export_results(self, output_dir: str = "backtest_results") -> Dict[str, str]:
        """Export backtest results to files.
        
        Args:
            output_dir: Directory to save output files
            
        Returns:
            Dictionary with file paths
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        result = self.calculate_metrics()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        files = {}
        
        json_file = output_path / f"backtest_{self.symbol}_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(result.to_dict(), f, indent=2, default=str)
        files["json_report"] = str(json_file)
        
        csv_file = output_path / f"trades_{self.symbol}_{timestamp}.csv"
        with open(csv_file, 'w', newline='') as f:
            if result.trades:
                writer = csv.DictWriter(f, fieldnames=result.trades[0].to_dict().keys())
                writer.writeheader()
                for trade in result.trades:
                    writer.writerow(trade.to_dict())
        files["trades_csv"] = str(csv_file)
        
        report_file = output_path / f"report_{self.symbol}_{timestamp}.json"
        report = self.generate_report()
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        files["comprehensive_report"] = str(report_file)
        
        equity_csv = output_path / f"equity_{self.symbol}_{timestamp}.csv"
        with open(equity_csv, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Date", "Equity"])
            for date, equity in zip(result.equity_dates, result.equity_curve):
                writer.writerow([date.isoformat(), equity])
        files["equity_curve"] = str(equity_csv)
        
        logger.info(f"Results exported to {output_dir}")
        
        return files


def run_mood_backtest(
    start_date: str,
    end_date: str,
    initial_capital: float = 100000,
    symbol: str = "SPY"
) -> BacktestResult:
    """Convenience function to run a mood backtest.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        initial_capital: Initial capital
        symbol: Symbol to backtest
        
    Returns:
        BacktestResult
    """
    backtester = MoodBacktester(
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
        symbol=symbol
    )
    
    return backtester.run_backtest()
