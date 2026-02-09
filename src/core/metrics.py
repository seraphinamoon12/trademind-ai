"""Unified performance metrics calculations.

This module provides a single source of truth for calculating
trading performance metrics used across the codebase.
"""
from typing import List, Dict, Optional
import pandas as pd
import numpy as np
import pandas_ta as ta


def calculate_atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14
) -> Optional[float]:
    """Calculate Average True Range using pandas_ta.

    Args:
        high: Series of high prices
        low: Series of low prices
        close: Series of close prices
        period: ATR period (default: 14)

    Returns:
        ATR value or None if calculation fails
    """
    try:
        atr_series = ta.atr(high, low, close, length=period)
        return float(atr_series.iloc[-1]) if not atr_series.empty and pd.notna(atr_series.iloc[-1]) else None
    except Exception:
        return None


def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.02) -> float:
    """Calculate annualized Sharpe ratio.
    
    Args:
        returns: Series of daily returns
        risk_free_rate: Annual risk-free rate (default: 2%)
        
    Returns:
        Annualized Sharpe ratio
    """
    if returns.empty or returns.std() == 0:
        return 0.0
    
    excess_returns = returns - risk_free_rate / 252
    sharpe = np.sqrt(252) * excess_returns.mean() / returns.std()
    return float(sharpe)


def calculate_max_drawdown(equity_curve: pd.Series) -> tuple:
    """Calculate maximum drawdown and its index.
    
    Args:
        equity_curve: Series of portfolio equity values
        
    Returns:
        Tuple of (max_drawdown, drawdown_index)
    """
    if equity_curve.empty:
        return 0.0, None
    
    rolling_max = equity_curve.cummax()
    drawdown = (equity_curve - rolling_max) / rolling_max
    max_dd_idx = drawdown.idxmin()
    max_dd = drawdown.min()
    
    return float(max_dd), max_dd_idx


def calculate_win_rate(trades: List[Dict]) -> float:
    """Calculate win rate from trades.
    
    Args:
        trades: List of trade dictionaries with 'pnl' key
        
    Returns:
        Win rate as percentage (0-100)
    """
    if not trades:
        return 0.0
    
    wins = sum(1 for t in trades if t.get('pnl', 0) > 0)
    return wins / len(trades) * 100


def calculate_profit_factor(trades: List[Dict]) -> float:
    """Calculate profit factor (gross profit / gross loss).
    
    Args:
        trades: List of trade dictionaries with 'pnl' key
        
    Returns:
        Profit factor (float('inf') if no losses, 0 if no wins)
    """
    gross_profit = sum(t.get('pnl', 0) for t in trades if t.get('pnl', 0) > 0)
    gross_loss = abs(sum(t.get('pnl', 0) for t in trades if t.get('pnl', 0) < 0))
    
    if gross_loss == 0:
        return float('inf') if gross_profit > 0 else 0
    
    return gross_profit / gross_loss


def calculate_volatility(returns: pd.Series, annualized: bool = True) -> float:
    """Calculate volatility (standard deviation of returns).
    
    Args:
        returns: Series of returns
        annualized: If True, annualize the volatility
        
    Returns:
        Volatility
    """
    vol = returns.std()
    if annualized and vol is not None:
        vol *= np.sqrt(252)
    return float(vol) if vol is not None else 0.0


def calculate_sortino_ratio(returns: pd.Series, risk_free_rate: float = 0.02) -> float:
    """Calculate Sortino ratio (downside risk adjusted return).
    
    Args:
        returns: Series of returns
        risk_free_rate: Annual risk-free rate (default: 2%)
        
    Returns:
        Sortino ratio
    """
    excess_returns = returns - risk_free_rate / 252
    downside_returns = returns[returns < 0]
    downside_std = downside_returns.std() * np.sqrt(252)
    
    if downside_std == 0:
        return 0.0
    
    return float(excess_returns.mean() * 252 / downside_std)


def calculate_calmar_ratio(returns: pd.Series, max_drawdown: float) -> float:
    """Calculate Calmar ratio (annual return / max drawdown).
    
    Args:
        returns: Series of returns
        max_drawdown: Maximum drawdown value
        
    Returns:
        Calmar ratio
    """
    if max_drawdown == 0:
        return 0.0
    
    annual_return = returns.mean() * 252
    return float(annual_return / abs(max_drawdown))


def calculate_cagr(beginning_value: float, ending_value: float, years: float) -> float:
    """Calculate Compound Annual Growth Rate.
    
    Args:
        beginning_value: Starting portfolio value
        ending_value: Ending portfolio value
        years: Number of years
        
    Returns:
        Annualized growth rate
    """
    if beginning_value <= 0 or years <= 0:
        return 0.0
    return (ending_value / beginning_value) ** (1 / years) - 1


def calculate_beta(returns: pd.Series, market_returns: pd.Series) -> float:
    """Calculate beta relative to market.
    
    Args:
        returns: Portfolio returns
        market_returns: Market returns
        
    Returns:
        Beta value
    """
    covariance = returns.cov(market_returns)
    market_variance = market_returns.var()
    return float(covariance / market_variance) if market_variance != 0 else 0.0


def calculate_alpha(
    returns: pd.Series,
    market_returns: pd.Series,
    risk_free_rate: float = 0.02
) -> float:
    """Calculate alpha (excess return).
    
    Args:
        returns: Portfolio returns
        market_returns: Market returns
        risk_free_rate: Annual risk-free rate
        
    Returns:
        Alpha value
    """
    beta = calculate_beta(returns, market_returns)
    portfolio_return = returns.mean() * 252
    market_return = market_returns.mean() * 252
    return portfolio_return - (risk_free_rate + beta * (market_return - risk_free_rate))


def generate_performance_report(
    trades: List[Dict],
    equity_curve: pd.Series,
    market_data: Optional[pd.Series] = None,
    risk_free_rate: float = 0.02
) -> Dict:
    """Generate comprehensive performance report.
    
    Args:
        trades: List of trade dictionaries with 'pnl' key
        equity_curve: Series of portfolio equity values
        market_data: Optional market returns for relative metrics
        risk_free_rate: Annual risk-free rate
        
    Returns:
        Dictionary with all performance metrics
    """
    if not trades or equity_curve.empty:
        return {
            'total_trades': 0,
            'win_rate': 0,
            'profit_factor': 0,
            'sharpe_ratio': 0,
            'max_drawdown': 0,
            'sortino_ratio': 0,
            'calmar_ratio': 0,
            'volatility': 0,
            'total_return': 0
        }
    
    returns = equity_curve.pct_change().dropna()
    max_dd, _ = calculate_max_drawdown(equity_curve)
    total_return = (equity_curve.iloc[-1] - equity_curve.iloc[0]) / equity_curve.iloc[0]
    
    report = {
        'total_trades': len(trades),
        'win_rate': calculate_win_rate(trades),
        'profit_factor': calculate_profit_factor(trades),
        'sharpe_ratio': calculate_sharpe_ratio(returns, risk_free_rate),
        'sortino_ratio': calculate_sortino_ratio(returns, risk_free_rate),
        'max_drawdown': max_dd,
        'max_drawdown_pct': max_dd * 100,
        'calmar_ratio': calculate_calmar_ratio(returns, max_dd),
        'volatility': calculate_volatility(returns),
        'total_return': total_return,
        'total_return_pct': total_return * 100
    }
    
    if market_data is not None:
        market_returns = market_data.pct_change().dropna()
        report['beta'] = calculate_beta(returns, market_returns)
        report['alpha'] = calculate_alpha(returns, market_returns, risk_free_rate)
        report['correlation'] = returns.corr(market_returns)
    
    return report


def calculate_win_rate_from_trade_pairs(
    trades: List[Dict],
    buy_key: str = 'action',
    sell_key: str = 'action',
    price_key: str = 'price',
    quantity_key: str = 'quantity'
) -> float:
    """Calculate win rate by matching buy-sell trade pairs.
    
    This is useful when trades are stored as individual entries
    rather than with pre-calculated P&L.
    
    Args:
        trades: List of trade dictionaries
        buy_key: Key that identifies buy action
        sell_key: Key that identifies sell action
        price_key: Key for price in trade dict
        quantity_key: Key for quantity in trade dict
        
    Returns:
        Win rate as percentage (0-100)
    """
    if len(trades) < 2:
        return 0.0
    
    wins = 0
    total_trades = 0
    
    for i in range(0, len(trades) - 1, 2):
        if i + 1 >= len(trades):
            break
        
        buy_trade = trades[i]
        sell_trade = trades[i + 1]
        
        if buy_trade.get(buy_key) == "BUY" and sell_trade.get(sell_key) == "SELL":
            total_trades += 1
            profit = (sell_trade.get(price_key, 0) - buy_trade.get(price_key, 0)) * buy_trade.get(quantity_key, 0)
            if profit > 0:
                wins += 1
    
    return float(wins / total_trades) * 100 if total_trades > 0 else 0.0
