"""Backtesting system for LangGraph trading strategies."""

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path

from src.trading_graph.graph import create_trading_graph
from src.data.providers import yahoo_provider

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    """Result of a single backtest run."""
    symbol: str
    start_date: datetime
    end_date: datetime
    trades: List[Dict]
    returns: pd.Series
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_return: float
    benchmark_return: float


class LangGraphBacktester:
    """Backtest trading strategies using LangGraph."""

    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital
        self.results = []

    async def run_backtest(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d"
    ) -> BacktestResult:
        """
        Run backtest for a symbol over a date range.

        Args:
            symbol: Stock symbol
            start_date: Start of backtest period
            end_date: End of backtest period
            interval: Data interval (1d, 1h, etc.)

        Returns:
            BacktestResult with performance metrics
        """
        try:
            logger.info(f"Starting backtest for {symbol} from {start_date} to {end_date}")

            data = await self._fetch_historical_data(symbol, start_date, end_date, interval)
            if data is None or len(data) == 0:
                raise ValueError(f"No data available for {symbol}")

            graph = await create_trading_graph()
            trades = []

            capital = self.initial_capital
            position = 0
            returns = [capital]

            for i in range(len(data) - 1):
                current_data = data.iloc[:i+1]

                if len(current_data) < 10:
                    continue

                state = {
                    "symbol": symbol,
                    "timeframe": interval,
                    "market_data": current_data.to_dict(),
                    "confidence": 0.0,
                    "workflow_id": f"backtest_{symbol}_{i}",
                    "iteration": 0,
                    "messages": [],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "technical_indicators": {},
                    "technical_signals": {},
                    "sentiment_signals": {},
                    "risk_signals": {},
                    "debate_result": {},
                    "final_decision": {},
                    "final_action": None,
                    "executed_trade": {},
                    "order_id": None,
                    "human_approved": True,
                    "human_feedback": None,
                    "current_node": None,
                    "error": None,
                    "retry_count": 0
                }

                try:
                    result = await graph.ainvoke(state, {"thread_id": state["workflow_id"]})

                    final_action = result.get("final_action", "HOLD")
                    if final_action not in ["BUY", "SELL"]:
                        continue

                    price = current_data['close'].iloc[-1]
                    risk_signals = result.get("risk_signals", {})
                    quantity = risk_signals.get("data", {}).get("recommended_size", 10)

                    if final_action == "BUY" and capital > price * quantity:
                        trade = {
                            "date": current_data.index[-1],
                            "action": "BUY",
                            "price": price,
                            "quantity": quantity,
                            "confidence": result.get("confidence", 0.0),
                            "capital": capital
                        }
                        capital -= price * quantity
                        position += quantity
                        trades.append(trade)
                        returns.append(capital + position * price)

                    elif final_action == "SELL" and position > 0:
                        trade = {
                            "date": current_data.index[-1],
                            "action": "SELL",
                            "price": price,
                            "quantity": position,
                            "confidence": result.get("confidence", 0.0),
                            "capital": capital
                        }
                        capital += price * position
                        position = 0
                        trades.append(trade)
                        returns.append(capital)

                except Exception as e:
                    logger.error(f"Backtest error on day {i}: {e}")
                    continue

            returns_series = pd.Series(returns)
            benchmark_return = (data['close'].iloc[-1] / data['close'].iloc[0] - 1)

            result = BacktestResult(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                trades=trades,
                returns=returns_series,
                sharpe_ratio=self._calculate_sharpe(returns_series),
                max_drawdown=self._calculate_max_drawdown(returns_series),
                win_rate=self._calculate_win_rate(trades),
                total_return=(returns_series.iloc[-1] / returns_series.iloc[0] - 1),
                benchmark_return=benchmark_return
            )

            logger.info(f"Backtest completed for {symbol}: {len(trades)} trades")
            self.results.append(result)
            return result

        except Exception as e:
            logger.error(f"Backtest failed for {symbol}: {e}")
            raise

    async def _fetch_historical_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str
    ) -> Optional[pd.DataFrame]:
        """Fetch historical data for backtesting."""
        try:
            import asyncio
            period_days = (end_date - start_date).days
            period_map = {
                "1d": "1y",
                "1h": "1mo",
                "5m": "1wk"
            }
            period = period_map.get(interval, "1y")

            if period_days > 365:
                period = "max"

            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                None,
                yahoo_provider.get_historical,
                symbol,
                period
            )
            if data is None:
                return None

            data = data[start_date:end_date]
            return data

        except Exception as e:
            logger.error(f"Failed to fetch historical data for {symbol}: {e}")
            return None

    def _calculate_sharpe(self, returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio."""
        try:
            from src.core.metrics import calculate_sharpe_ratio
            daily_returns = returns.pct_change().dropna()
            return calculate_sharpe_ratio(daily_returns, risk_free_rate)
        except Exception as e:
            logger.error(f"Sharpe calculation error: {e}")
            return 0.0

    def _calculate_max_drawdown(self, returns: pd.Series) -> float:
        """Calculate maximum drawdown."""
        try:
            from src.core.metrics import calculate_max_drawdown
            max_dd, _ = calculate_max_drawdown(returns)
            return max_dd
        except Exception as e:
            logger.error(f"Max drawdown calculation error: {e}")
            return 0.0

    def _calculate_win_rate(self, trades: List[Dict]) -> float:
        """Calculate win rate from trades."""
        try:
            from src.core.metrics import calculate_win_rate_from_trade_pairs
            return calculate_win_rate_from_trade_pairs(trades)
        except Exception as e:
            logger.error(f"Win rate calculation error: {e}")
            return 0.0

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all backtest results."""
        if not self.results:
            return {}

        total_return = sum(r.total_return for r in self.results)
        avg_sharpe = np.mean([r.sharpe_ratio for r in self.results])
        avg_win_rate = np.mean([r.win_rate for r in self.results])
        total_trades = sum(len(r.trades) for r in self.results)

        return {
            "total_results": len(self.results),
            "total_return": float(total_return),
            "avg_sharpe_ratio": float(avg_sharpe),
            "avg_win_rate": float(avg_win_rate),
            "total_trades": total_trades,
            "results_by_symbol": {
                r.symbol: {
                    "total_return": r.total_return,
                    "sharpe_ratio": r.sharpe_ratio,
                    "win_rate": r.win_rate,
                    "max_drawdown": r.max_drawdown,
                    "num_trades": len(r.trades)
                }
                for r in self.results
            }
        }

    def save_results(self, filepath: Optional[str] = None):
        """Save backtest results to CSV."""
        if not self.results:
            logger.warning("No backtest results to save")
            return

        if filepath is None:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filepath = f"data/backtest_results_{timestamp}.csv"

        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        all_trades = []
        for result in self.results:
            for trade in result.trades:
                trade_row = {
                    "symbol": result.symbol,
                    "date": trade["date"],
                    "action": trade["action"],
                    "price": trade["price"],
                    "quantity": trade["quantity"],
                    "confidence": trade["confidence"]
                }
                all_trades.append(trade_row)

        df = pd.DataFrame(all_trades)
        df.to_csv(filepath, index=False)
        logger.info(f"Backtest results saved to {filepath}")


async def run_backtest_comparison(
    symbols: List[str],
    start_date: datetime,
    end_date: datetime
) -> Dict[str, BacktestResult]:
    """
    Run backtest comparison for multiple symbols.

    Args:
        symbols: List of stock symbols
        start_date: Start date for backtest
        end_date: End date for backtest

    Returns:
        Dictionary mapping symbols to BacktestResult
    """
    backtester = LangGraphBacktester(initial_capital=100000.0)
    results = {}

    for symbol in symbols:
        try:
            result = await backtester.run_backtest(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date
            )
            results[symbol] = result

            print(f"\n{'='*60}")
            print(f"Backtest Results for {result.symbol}")
            print(f"{'='*60}")
            print(f"  Total Return: {result.total_return:.2%}")
            print(f"  Sharpe Ratio: {result.sharpe_ratio:.2f}")
            print(f"  Max Drawdown: {result.max_drawdown:.2%}")
            print(f"  Win Rate: {result.win_rate:.2%}")
            print(f"  Trades: {len(result.trades)}")
            print(f"  Benchmark Return: {result.benchmark_return:.2%}")

        except Exception as e:
            logger.error(f"Backtest failed for {symbol}: {e}")
            results[symbol] = None

    return results


if __name__ == "__main__":
    import asyncio

    async def main():
        results = await run_backtest_comparison(
            symbols=["AAPL", "GOOGL", "MSFT"],
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31)
        )

        backtester = LangGraphBacktester()
        summary = backtester.get_summary()
        print(f"\n{'='*60}")
        print("Summary Statistics")
        print(f"{'='*60}")
        print(f"Total Results: {summary.get('total_results', 0)}")
        print(f"Total Return: {summary.get('total_return', 0):.2%}")
        print(f"Avg Sharpe Ratio: {summary.get('avg_sharpe_ratio', 0):.2f}")
        print(f"Avg Win Rate: {summary.get('avg_win_rate', 0):.2%}")
        print(f"Total Trades: {summary.get('total_trades', 0)}")

    asyncio.run(main())
