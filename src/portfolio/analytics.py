"""Portfolio analytics and performance calculations."""
from typing import List, Dict, Optional
import pandas as pd
import numpy as np
from datetime import datetime

# Import all metrics from the unified module
from src.core.metrics import (
    calculate_returns,
    calculate_sharpe_ratio,
    calculate_max_drawdown,
    calculate_win_rate,
    calculate_profit_factor,
    calculate_volatility,
    calculate_sortino_ratio,
    calculate_cagr,
    calculate_beta,
    calculate_alpha,
    generate_performance_report
)


def calculate_returns(equity_curve: pd.Series) -> pd.Series:
    """Calculate returns from equity curve."""
    return equity_curve.pct_change().dropna()
