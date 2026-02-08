"""Portfolio module."""
from src.portfolio.manager import PortfolioManager
from src.portfolio.analytics import (
    calculate_returns,
    calculate_volatility,
    calculate_cagr,
    generate_performance_report
)

__all__ = [
    'PortfolioManager',
    'calculate_returns',
    'calculate_volatility',
    'calculate_cagr',
    'generate_performance_report'
]
