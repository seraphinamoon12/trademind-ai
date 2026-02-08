"""Backtesting engine using Backtrader."""
from datetime import datetime
from typing import List, Dict, Optional, Callable
import pandas as pd
import backtrader as bt

from src.strategies.base import SignalType
from src.config import settings


class BacktraderStrategy(bt.Strategy):
    """Backtrader wrapper for our strategies."""
    
    params = (
        ('strategy_fn', None),
        ('symbol', ''),
        ('stop_loss', 0.05),
        ('take_profit', 0.10),
        ('max_position_pct', 0.10),
    )
    
    def __init__(self):
        self.data_df = None
        self.orders = []
        self.trades = []
        
    def next(self):
        """Called on each new bar."""
        if self.params.strategy_fn is None:
            return
        
        # Build dataframe from backtrader data
        if self.data_df is None:
            # Initialize with historical data
            self.data_df = pd.DataFrame()
        
        # Add current bar
        new_row = pd.DataFrame([{
            'open': self.data.open[0],
            'high': self.data.high[0],
            'low': self.data.low[0],
            'close': self.data.close[0],
            'volume': self.data.volume[0],
        }])
        
        self.data_df = pd.concat([self.data_df, new_row], ignore_index=True)
        
        # Need enough data
        if len(self.data_df) < 50:
            return
        
        # Generate signal
        signal = self.params.strategy_fn(self.data_df, self.params.symbol)
        
        if signal is None or signal.signal == SignalType.HOLD:
            return
        
        # Execute trade
        size = self._calculate_position_size(signal.price)
        
        if signal.signal == SignalType.BUY and not self.position:
            self.buy(size=size)
        elif signal.signal == SignalType.SELL and self.position:
            self.sell(size=self.position.size)
    
    def _calculate_position_size(self, price: float) -> int:
        """Calculate position size based on portfolio value."""
        cash = self.broker.getcash()
        max_value = cash * self.params.max_position_pct
        return int(max_value / price) if price > 0 else 0
    
    def notify_order(self, order):
        """Called when order status changes."""
        if order.status in [order.Completed]:
            self.orders.append({
                'type': 'buy' if order.isbuy() else 'sell',
                'price': order.executed.price,
                'size': order.executed.size,
                'value': order.executed.value,
                'commission': order.executed.comm
            })


class BacktestEngine:
    """Backtesting engine wrapper."""
    
    def __init__(
        self,
        initial_cash: float = None,
        commission: float = 0.001,  # 0.1%
        slippage: float = 0.001     # 0.1%
    ):
        self.initial_cash = initial_cash or settings.starting_capital
        self.commission = commission
        self.slippage = slippage
        self.cerebro = None
    
    def run(
        self,
        data: pd.DataFrame,
        symbol: str,
        strategy_fn: Callable,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> dict:
        """Run backtest and return results."""
        
        self.cerebro = bt.Cerebro()
        
        # Configure broker
        self.cerebro.broker.setcash(self.initial_cash)
        self.cerebro.broker.setcommission(commission=self.commission)
        
        # Add slippage
        self.cerebro.broker.set_slippage_perc(self.slippage)
        
        # Prepare data
        if 'date' in data.columns:
            data = data.set_index('date')
        elif 'time' in data.columns:
            data = data.set_index('time')
        
        # Ensure index is datetime
        data.index = pd.to_datetime(data.index)
        
        # Filter by date range
        if start_date:
            data = data[data.index >= start_date]
        if end_date:
            data = data[data.index <= end_date]
        
        # Create backtrader data feed
        bt_data = bt.feeds.PandasData(
            dataname=data,
            datetime=None,  # Use index
            open='open',
            high='high',
            low='low',
            close='close',
            volume='volume',
            openinterest=-1
        )
        
        self.cerebro.adddata(bt_data)
        
        # Add strategy
        self.cerebro.addstrategy(
            BacktraderStrategy,
            strategy_fn=strategy_fn,
            symbol=symbol,
            stop_loss=settings.stop_loss_pct,
            take_profit=settings.take_profit_pct,
            max_position_pct=settings.max_position_pct
        )
        
        # Add analyzers
        self.cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        self.cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        self.cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        self.cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        
        # Run backtest
        results = self.cerebro.run()
        strat = results[0]
        
        # Extract results
        final_value = self.cerebro.broker.getvalue()
        initial_value = self.initial_cash
        total_return = (final_value - initial_value) / initial_value
        
        # Get analyzer results
        sharpe = strat.analyzers.sharpe.get_analysis()
        drawdown = strat.analyzers.drawdown.get_analysis()
        trades = strat.analyzers.trades.get_analysis()
        returns = strat.analyzers.returns.get_analysis()
        
        return {
            'symbol': symbol,
            'initial_value': initial_value,
            'final_value': final_value,
            'total_return': total_return,
            'total_return_pct': total_return * 100,
            'sharpe_ratio': sharpe.get('sharperatio', 0),
            'max_drawdown': drawdown.get('max', {}).get('drawdown', 0),
            'max_drawdown_pct': drawdown.get('max', {}).get('drawdown', 0),
            'total_trades': trades.get('total', {}).get('total', 0),
            'winning_trades': trades.get('won', {}).get('total', 0),
            'losing_trades': trades.get('lost', {}).get('total', 0),
            'win_rate': (
                trades.get('won', {}).get('total', 0) / 
                trades.get('total', {}).get('total', 1) * 100
            ) if trades.get('total', {}).get('total', 0) > 0 else 0,
            'avg_trade_return': returns.get('rtot', 0),
            'commission_paid': initial_value * self.commission * trades.get('total', {}).get('total', 0),
        }
    
    def plot(self, filename: str = None):
        """Plot backtest results."""
        if self.cerebro:
            self.cerebro.plot(style='candlestick', barup='green', bardown='red')
