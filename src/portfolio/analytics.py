"""Portfolio analytics and performance calculations."""
from typing import List, Dict, Optional
import pandas as pd
import numpy as np
from datetime import datetime


def calculate_returns(equity_curve: pd.Series) -> pd.Series:
    """Calculate returns from equity curve."""
    return equity_curve.pct_change().dropna()


def calculate_volatility(returns: pd.Series, annualized: bool = True) -> float:
    """Calculate volatility (standard deviation of returns)."""
    vol = returns.std()
    if annualized:
        vol *= np.sqrt(252)  # Annualize
    return vol


def calculate_beta(returns: pd.Series, market_returns: pd.Series) -> float:
    """Calculate beta relative to market."""
    covariance = returns.cov(market_returns)
    market_variance = market_returns.var()
    return covariance / market_variance if market_variance != 0 else 0


def calculate_alpha(
    returns: pd.Series,
    market_returns: pd.Series,
    risk_free_rate: float = 0.02
) -> float:
    """Calculate alpha (excess return)."""
    beta = calculate_beta(returns, market_returns)
    portfolio_return = returns.mean() * 252
    market_return = market_returns.mean() * 252
    return portfolio_return - (risk_free_rate + beta * (market_return - risk_free_rate))


def calculate_sortino_ratio(returns: pd.Series, risk_free_rate: float = 0.02) -> float:
    """Calculate Sortino ratio (downside risk adjusted return)."""
    excess_returns = returns - risk_free_rate / 252
    downside_returns = returns[returns < 0]
    downside_std = downside_returns.std() * np.sqrt(252)
    
    if downside_std == 0:
        return 0
    
    return excess_returns.mean() * 252 / downside_std


def calculate_cagr(beginning_value: float, ending_value: float, years: float) -> float:
    """Calculate Compound Annual Growth Rate."""
    if beginning_value <= 0 or years <= 0:
        return 0
    return (ending_value / beginning_value) ** (1 / years) - 1


def generate_performance_report(
    trades: List[Dict],
    equity_curve: pd.Series,
    market_data: Optional[pd.Series] = None
) -> Dict:
    """Generate comprehensive performance report."""
    returns = calculate_returns(equity_curve)
    
    report = {
        'summary': {
            'total_return': (equity_curve.iloc[-1] - equity_curve.iloc[0]) / equity_curve.iloc[0],
            'cagr': calculate_cagr(
                equity_curve.iloc[0],
                equity_curve.iloc[-1],
                len(equity_curve) / 252
            ),
            'volatility': calculate_volatility(returns),
            'sharpe_ratio': calculate_sharpe_ratio(returns),
            'sortino_ratio': calculate_sortino_ratio(returns),
        },
        'risk': {
            'max_drawdown': calculate_max_drawdown(equity_curve)[0],
            'var_95': np.percentile(returns, 5) if len(returns) > 0 else 0,
        },
        'trades': {
            'total': len(trades),
            'win_rate': calculate_win_rate(trades),
            'profit_factor': calculate_profit_factor(trades),
            'avg_win': np.mean([t['pnl'] for t in trades if t.get('pnl', 0) > 0]) if trades else 0,
            'avg_loss': np.mean([t['pnl'] for t in trades if t.get('pnl', 0) < 0]) if trades else 0,
        }
    }
    
    if market_data is not None:
        market_returns = market_data.pct_change().dropna()
        report['relative'] = {
            'beta': calculate_beta(returns, market_returns),
            'alpha': calculate_alpha(returns, market_returns),
            'correlation': returns.corr(market_returns)
        }
    
    return report


# Import functions from metrics module for convenience
from src.backtest.metrics import (
    calculate_sharpe_ratio,
    calculate_max_drawdown,
    calculate_win_rate,
    calculate_profit_factor
)
