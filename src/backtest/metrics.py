"""Performance metrics calculations."""
from typing import List, Dict
import pandas as pd
import numpy as np


def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.02) -> float:
    """Calculate annualized Sharpe ratio."""
    if returns.empty or returns.std() == 0:
        return 0.0
    
    excess_returns = returns - risk_free_rate / 252  # Daily risk-free rate
    return np.sqrt(252) * excess_returns.mean() / returns.std()


def calculate_max_drawdown(equity_curve: pd.Series) -> tuple:
    """Calculate maximum drawdown."""
    rolling_max = equity_curve.cummax()
    drawdown = (equity_curve - rolling_max) / rolling_max
    max_dd_idx = drawdown.idxmin()
    max_dd = drawdown.min()
    
    return max_dd, max_dd_idx


def calculate_win_rate(trades: List[Dict]) -> float:
    """Calculate win rate from trades."""
    if not trades:
        return 0.0
    
    wins = sum(1 for t in trades if t.get('pnl', 0) > 0)
    return wins / len(trades) * 100


def calculate_profit_factor(trades: List[Dict]) -> float:
    """Calculate profit factor (gross profit / gross loss)."""
    gross_profit = sum(t.get('pnl', 0) for t in trades if t.get('pnl', 0) > 0)
    gross_loss = abs(sum(t.get('pnl', 0) for t in trades if t.get('pnl', 0) < 0))
    
    if gross_loss == 0:
        return float('inf') if gross_profit > 0 else 0
    
    return gross_profit / gross_loss


def calculate_calmar_ratio(returns: pd.Series, max_drawdown: float) -> float:
    """Calculate Calmar ratio (annual return / max drawdown)."""
    if max_drawdown == 0:
        return 0.0
    
    annual_return = returns.mean() * 252
    return annual_return / abs(max_drawdown)


def calculate_metrics_summary(trades: List[Dict], equity_curve: pd.Series) -> Dict:
    """Calculate comprehensive performance metrics."""
    if not trades or equity_curve.empty:
        return {
            'total_trades': 0,
            'win_rate': 0,
            'profit_factor': 0,
            'sharpe_ratio': 0,
            'max_drawdown': 0,
            'calmar_ratio': 0,
            'avg_trade_return': 0,
            'total_return': 0
        }
    
    # Calculate returns from equity curve
    returns = equity_curve.pct_change().dropna()
    
    total_return = (equity_curve.iloc[-1] - equity_curve.iloc[0]) / equity_curve.iloc[0]
    max_dd, _ = calculate_max_drawdown(equity_curve)
    
    return {
        'total_trades': len(trades),
        'win_rate': calculate_win_rate(trades),
        'profit_factor': calculate_profit_factor(trades),
        'sharpe_ratio': calculate_sharpe_ratio(returns),
        'max_drawdown': max_dd,
        'max_drawdown_pct': max_dd * 100,
        'calmar_ratio': calculate_calmar_ratio(returns, max_dd),
        'avg_trade_return': total_return / len(trades) if trades else 0,
        'total_return': total_return,
        'total_return_pct': total_return * 100
    }
