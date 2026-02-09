"""Performance metrics calculations.

DEPRECATED: Import from src.core.metrics instead.
This module kept for backward compatibility only.
"""

from src.core.metrics import (
    calculate_sharpe_ratio,
    calculate_max_drawdown,
    calculate_win_rate,
    calculate_profit_factor,
    calculate_calmar_ratio,
    generate_performance_report,
    calculate_volatility,
    calculate_sortino_ratio,
    calculate_cagr,
    calculate_beta,
    calculate_alpha
)

import warnings
warnings.warn(
    "Importing from src.backtest.metrics is deprecated. "
    "Use src.core.metrics instead.",
    DeprecationWarning,
    stacklevel=2
)


def calculate_metrics_summary(trades, equity_curve):
    """Calculate comprehensive performance metrics."""
    return generate_performance_report(trades, equity_curve)
