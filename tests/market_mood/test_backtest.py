"""Tests for market mood backtesting module."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import json
import pandas as pd
import numpy as np

from src.market_mood.backtest import (
    MoodBacktester,
    BacktestResult,
    Trade,
    MoodSignal,
    run_mood_backtest,
)
from src.market_mood.config import MarketMoodConfig


@pytest.fixture
def sample_price_data():
    """Create sample price data for testing."""
    dates = pd.date_range(start="2023-01-01", end="2023-12-31", freq="D")
    np.random.seed(42)
    
    base_price = 400.0
    prices = []
    for i in range(len(dates)):
        change = np.random.normal(0, 0.01)
        base_price *= (1 + change)
        prices.append(base_price)
    
    data = pd.DataFrame({
        'date': dates,
        'open': [p * (1 + np.random.uniform(-0.005, 0.005)) for p in prices],
        'high': [p * (1 + np.random.uniform(0, 0.01)) for p in prices],
        'low': [p * (1 - np.random.uniform(0, 0.01)) for p in prices],
        'close': prices,
        'volume': [np.random.randint(1000000, 50000000) for _ in range(len(dates))],
    })
    return data


@pytest.fixture
def sample_vix_data():
    """Create sample VIX data for testing."""
    dates = pd.date_range(start="2023-01-01", end="2023-12-31", freq="D")
    np.random.seed(42)
    
    base_vix = 20.0
    vix_values = []
    for i in range(len(dates)):
        change = np.random.normal(0, 0.1)
        base_vix = max(10, min(40, base_vix * (1 + change)))
        vix_values.append(base_vix)
    
    data = pd.DataFrame({
        'date': dates,
        'open': [v * (1 + np.random.uniform(-0.02, 0.02)) for v in vix_values],
        'high': [v * (1 + np.random.uniform(0, 0.05)) for v in vix_values],
        'low': [v * (1 - np.random.uniform(0, 0.05)) for v in vix_values],
        'close': vix_values,
        'volume': [np.random.randint(100000, 1000000) for _ in range(len(dates))],
    })
    return data


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    config = MarketMoodConfig()
    config.signal_confidence_threshold = 0.5
    return config


class TestTrade:
    """Tests for the Trade dataclass."""
    
    def test_trade_creation(self):
        """Test creating a trade object."""
        trade = Trade(
            entry_date=datetime(2023, 1, 1),
            symbol="SPY",
            entry_price=400.0,
            quantity=100,
            signal_type="BUY",
            mood_classification="extreme_fear",
            mood_score=20.0,
            confidence=0.9,
        )
        
        assert trade.entry_date == datetime(2023, 1, 1)
        assert trade.symbol == "SPY"
        assert trade.entry_price == 400.0
        assert trade.quantity == 100
        assert trade.signal_type == "BUY"
        assert trade.mood_classification == "extreme_fear"
        assert trade.mood_score == 20.0
        assert trade.confidence == 0.9
    
    def test_trade_to_dict(self):
        """Test converting trade to dictionary."""
        trade = Trade(
            entry_date=datetime(2023, 1, 1),
            exit_date=datetime(2023, 1, 10),
            symbol="SPY",
            entry_price=400.0,
            exit_price=410.0,
            quantity=100,
            pnl=1000.0,
            pnl_pct=2.5,
        )
        
        trade_dict = trade.to_dict()
        
        assert trade_dict["entry_date"] == "2023-01-01T00:00:00"
        assert trade_dict["exit_date"] == "2023-01-10T00:00:00"
        assert trade_dict["symbol"] == "SPY"
        assert trade_dict["entry_price"] == 400.0
        assert trade_dict["exit_price"] == 410.0
        assert trade_dict["pnl"] == 1000.0
        assert trade_dict["pnl_pct"] == 2.5


class TestMoodSignal:
    """Tests for the MoodSignal dataclass."""
    
    def test_signal_creation(self):
        """Test creating a mood signal."""
        signal = MoodSignal(
            date=datetime(2023, 1, 1),
            signal="BUY",
            mood_classification="fear",
            mood_score=25.0,
            confidence=0.85,
            sentiment="fear",
        )
        
        assert signal.date == datetime(2023, 1, 1)
        assert signal.signal == "BUY"
        assert signal.mood_classification == "fear"
        assert signal.mood_score == 25.0
        assert signal.confidence == 0.85
        assert signal.sentiment == "fear"
    
    def test_signal_to_dict(self):
        """Test converting signal to dictionary."""
        signal = MoodSignal(
            date=datetime(2023, 1, 1),
            signal="STRONG_BUY",
            mood_classification="extreme_fear",
            mood_score=10.0,
            confidence=0.9,
            sentiment="extreme_fear",
        )
        
        signal_dict = signal.to_dict()
        
        assert signal_dict["date"] == "2023-01-01T00:00:00"
        assert signal_dict["signal"] == "STRONG_BUY"
        assert signal_dict["mood_classification"] == "extreme_fear"
        assert signal_dict["mood_score"] == 10.0
        assert signal_dict["confidence"] == 0.9


class TestBacktestResult:
    """Tests for the BacktestResult dataclass."""
    
    def test_result_creation(self):
        """Test creating a backtest result."""
        result = BacktestResult(
            initial_capital=100000.0,
            final_capital=110000.0,
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
        )
        
        assert result.initial_capital == 100000.0
        assert result.final_capital == 110000.0
        assert result.start_date == datetime(2023, 1, 1)
        assert result.end_date == datetime(2023, 12, 31)
    
    def test_result_to_dict(self):
        """Test converting result to dictionary."""
        trade = Trade(
            entry_date=datetime(2023, 1, 1),
            symbol="SPY",
            entry_price=400.0,
            quantity=100,
        )
        signal = MoodSignal(
            date=datetime(2023, 1, 1),
            signal="BUY",
            mood_classification="fear",
            mood_score=25.0,
            confidence=0.85,
            sentiment="fear",
        )
        
        result = BacktestResult(
            trades=[trade],
            equity_curve=[100000.0, 101000.0],
            equity_dates=[datetime(2023, 1, 1), datetime(2023, 1, 2)],
            signals=[signal],
            metrics={"total_return": 0.01, "sharpe_ratio": 1.5},
            initial_capital=100000.0,
            final_capital=110000.0,
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["initial_capital"] == 100000.0
        assert result_dict["final_capital"] == 110000.0
        assert len(result_dict["trades"]) == 1
        assert len(result_dict["signals"]) == 1
        assert len(result_dict["equity_curve"]) == 2
    
    def test_get_performance_summary(self):
        """Test getting performance summary."""
        trade1 = Trade(
            entry_date=datetime(2023, 1, 1),
            symbol="SPY",
            entry_price=400.0,
            quantity=100,
            pnl=1000.0,
        )
        trade2 = Trade(
            entry_date=datetime(2023, 2, 1),
            symbol="SPY",
            entry_price=400.0,
            quantity=100,
            pnl=-500.0,
        )
        
        result = BacktestResult(
            trades=[trade1, trade2],
            equity_curve=[100000.0, 101000.0, 100500.0],
            equity_dates=[datetime(2023, 1, 1), datetime(2023, 1, 2), datetime(2023, 1, 3)],
            metrics={
                "total_return": 0.005,
                "total_return_pct": 0.5,
                "win_rate": 50.0,
                "avg_return": 250.0,
                "max_drawdown": -0.01,
                "sharpe_ratio": 1.2,
                "sortino_ratio": 1.5,
                "calmar_ratio": 0.5,
                "volatility": 0.15,
                "winning_trades": 1,
                "losing_trades": 1,
                "profit_factor": 2.0,
            },
            initial_capital=100000.0,
            final_capital=100500.0,
            buy_and_hold_return=0.03,
        )
        
        summary = result.get_performance_summary()
        
        assert summary["total_return"] == 0.005
        assert summary["total_return_pct"] == 0.5
        assert summary["win_rate"] == 50.0
        assert summary["total_trades"] == 2
        assert summary["winning_trades"] == 1
        assert summary["losing_trades"] == 1
        assert summary["sharpe_ratio"] == 1.2
        assert summary["buy_and_hold_return_pct"] == 3.0


class TestMoodBacktester:
    """Tests for the MoodBacktester class."""
    
    def test_backtester_initialization(self):
        """Test initializing the backtester."""
        backtester = MoodBacktester(
            start_date="2023-01-01",
            end_date="2023-12-31",
            initial_capital=100000,
            symbol="SPY",
        )
        
        assert backtester.start_date == datetime(2023, 1, 1)
        assert backtester.end_date == datetime(2023, 12, 31)
        assert backtester.initial_capital == 100000
        assert backtester.symbol == "SPY"
        assert backtester.current_capital == 100000
    
    @patch('src.market_mood.backtest.yf.Ticker')
    def test_fetch_historical_data_success(self, mock_ticker, sample_price_data, sample_vix_data):
        """Test fetching historical data successfully."""
        mock_price_ticker = MagicMock()
        mock_vix_ticker = MagicMock()
        
        def ticker_side_effect(symbol):
            if symbol == "SPY":
                return mock_price_ticker
            else:
                return mock_vix_ticker
        
        mock_ticker.side_effect = ticker_side_effect
        mock_price_ticker.history.return_value = sample_price_data.set_index('date')
        mock_vix_ticker.history.return_value = sample_vix_data.set_index('date')
        
        backtester = MoodBacktester(
            start_date="2023-01-01",
            end_date="2023-12-31",
            initial_capital=100000,
            symbol="SPY",
        )
        
        result = backtester.fetch_historical_data()
        
        assert result["status"] == "success"
        assert result["price_data_points"] > 0
        assert result["vix_data_points"] > 0
        assert backtester.price_data is not None
        assert backtester.vix_data is not None
    
    @patch('src.market_mood.backtest.yf.Ticker')
    def test_fetch_historical_data_no_vix(self, mock_ticker, sample_price_data):
        """Test fetching historical data without VIX data."""
        mock_ticker_instance = MagicMock()
        mock_ticker.return_value = mock_ticker_instance
        mock_ticker_instance.history.return_value = sample_price_data.set_index('date')
        
        backtester = MoodBacktester(
            start_date="2023-01-01",
            end_date="2023-12-31",
            initial_capital=100000,
            symbol="QQQ",
        )
        
        result = backtester.fetch_historical_data()
        
        assert result["status"] == "success"
        assert result["price_data_points"] > 0
        assert result["vix_data_points"] == 0
    
    def test_calculate_mood_for_date(self):
        """Test calculating mood for a specific date."""
        backtester = MoodBacktester(
            start_date="2023-01-01",
            end_date="2023-01-31",
            initial_capital=100000,
        )
        
        dates = pd.date_range(start="2023-01-01", end="2023-01-10", freq="D")
        backtester.price_data = pd.DataFrame({
            'date': dates,
            'close': [400.0 + i for i in range(len(dates))],
        })
        
        backtester.vix_data = pd.DataFrame({
            'date': dates,
            'close': [35.0, 25.0, 20.0, 15.0, 12.0, 30.0, 28.0, 22.0, 18.0, 16.0],
        })
        
        mood = backtester._calculate_mood_for_date(dates[1])
        
        assert mood["score"] <= 35
        assert mood["sentiment"] in ["extreme_fear", "fear", "neutral", "greed", "extreme_greed"]
        assert "confidence" in mood
        assert "trend" in mood
    
    def test_calculate_position_size(self):
        """Test calculating position size based on signal."""
        backtester = MoodBacktester(
            start_date="2023-01-01",
            end_date="2023-01-31",
            initial_capital=100000,
        )
        backtester.current_capital = 100000
        backtester.price_data = pd.DataFrame({
            'date': [datetime(2023, 1, 1)],
            'close': [400.0],
        })
        backtester.current_date = datetime(2023, 1, 1)
        
        size = backtester._calculate_position_size("BUY", 0.9, 25.0)
        
        assert size > 0
        assert size <= int(100000 / 400.0)
    
    @patch('src.market_mood.backtest.yf.Ticker')
    def test_run_backtest(self, mock_ticker, sample_price_data, sample_vix_data):
        """Test running a full backtest."""
        mock_ticker_instance = MagicMock()
        mock_ticker.return_value = mock_ticker_instance
        
        mock_price_ticker = MagicMock()
        mock_vix_ticker = MagicMock()
        
        def ticker_side_effect(symbol):
            if symbol == "SPY":
                return mock_price_ticker
            else:
                return mock_vix_ticker
        
        mock_ticker.side_effect = ticker_side_effect
        mock_price_ticker.history.return_value = sample_price_data.set_index('date')
        mock_vix_ticker.history.return_value = sample_vix_data.set_index('date')
        
        backtester = MoodBacktester(
            start_date="2023-01-01",
            end_date="2023-03-31",
            initial_capital=100000,
            symbol="SPY",
        )
        
        result = backtester.run_backtest()
        
        assert isinstance(result, BacktestResult)
        assert len(result.trades) >= 0
        assert len(result.equity_curve) > 0
        assert len(result.equity_dates) > 0
        assert len(result.signals) > 0
        assert result.initial_capital == 100000
        assert result.start_date == datetime(2023, 1, 1)
        assert result.end_date == datetime(2023, 3, 31)
    
    def test_calculate_metrics(self, sample_price_data):
        """Test calculating performance metrics."""
        backtester = MoodBacktester(
            start_date="2023-01-01",
            end_date="2023-01-31",
            initial_capital=100000,
        )
        backtester.price_data = sample_price_data
        backtester.equity_curve = [100000.0, 101000.0, 102000.0, 101500.0, 103000.0]
        backtester.equity_dates = [
            datetime(2023, 1, i) for i in range(1, 6)
        ]
        
        trade1 = Trade(
            entry_date=datetime(2023, 1, 1),
            symbol="SPY",
            entry_price=400.0,
            quantity=100,
            pnl=1000.0,
        )
        trade2 = Trade(
            entry_date=datetime(2023, 1, 15),
            symbol="SPY",
            entry_price=405.0,
            quantity=100,
            pnl=-500.0,
        )
        backtester.trades = [trade1, trade2]
        
        result = backtester.calculate_metrics()
        
        assert isinstance(result, BacktestResult)
        assert "total_return" in result.metrics
        assert "sharpe_ratio" in result.metrics
        assert "max_drawdown" in result.metrics
        assert "win_rate" in result.metrics
    
    def test_generate_report(self, sample_price_data):
        """Test generating a backtest report."""
        backtester = MoodBacktester(
            start_date="2023-01-01",
            end_date="2023-01-31",
            initial_capital=100000,
        )
        backtester.price_data = sample_price_data
        backtester.trades = []
        backtester.signals = []
        
        report = backtester.generate_report()
        
        assert "backtest_summary" in report
        assert "performance_metrics" in report
        assert "buy_and_hold" in report
        assert "signals_by_mood" in report
        assert "trades_by_mood" in report
    
    def test_analyze_signals_by_mood(self):
        """Test analyzing signals by mood type."""
        backtester = MoodBacktester(
            start_date="2023-01-01",
            end_date="2023-01-31",
            initial_capital=100000,
        )
        
        backtester.signals = [
            MoodSignal(
                date=datetime(2023, 1, 1),
                signal="BUY",
                mood_classification="fear",
                mood_score=25.0,
                confidence=0.85,
                sentiment="fear",
            ),
            MoodSignal(
                date=datetime(2023, 1, 2),
                signal="SELL",
                mood_classification="greed",
                mood_score=70.0,
                confidence=0.9,
                sentiment="greed",
            ),
        ]
        
        analysis = backtester._analyze_signals_by_mood()
        
        assert "by_mood_classification" in analysis
        assert "by_signal_type" in analysis
        assert analysis["total_signals"] == 2
        assert analysis["by_mood_classification"]["fear"] == 1
        assert analysis["by_mood_classification"]["greed"] == 1
    
    def test_analyze_trades_by_mood(self):
        """Test analyzing trades by mood type."""
        backtester = MoodBacktester(
            start_date="2023-01-01",
            end_date="2023-01-31",
            initial_capital=100000,
        )
        
        backtester.trades = [
            Trade(
                entry_date=datetime(2023, 1, 1),
                symbol="SPY",
                entry_price=400.0,
                quantity=100,
                pnl=1000.0,
                mood_classification="extreme_fear",
            ),
            Trade(
                entry_date=datetime(2023, 1, 15),
                symbol="SPY",
                entry_price=400.0,
                quantity=100,
                pnl=-500.0,
                mood_classification="neutral",
            ),
        ]
        
        analysis = backtester._analyze_trades_by_mood()
        
        assert "extreme_fear" in analysis
        assert "neutral" in analysis
        assert analysis["extreme_fear"]["count"] == 1
        assert analysis["neutral"]["count"] == 1
        assert analysis["extreme_fear"]["winning_trades"] == 1
        assert analysis["neutral"]["winning_trades"] == 0
    
    def test_export_results(self, sample_price_data):
        """Test exporting backtest results to files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backtester = MoodBacktester(
                start_date="2023-01-01",
                end_date="2023-01-31",
                initial_capital=100000,
            )
            backtester.price_data = sample_price_data
            backtester.equity_curve = [100000.0, 101000.0]
            backtester.equity_dates = [
                datetime(2023, 1, 1),
                datetime(2023, 1, 2),
            ]
            backtester.trades = []
            backtester.signals = []
            
            files = backtester.export_results(output_dir=tmpdir)
            
            assert "json_report" in files
            assert "trades_csv" in files
            assert "comprehensive_report" in files
            assert "equity_curve" in files
            
            for file_type, file_path in files.items():
                assert Path(file_path).exists()
            
            json_file = Path(files["json_report"])
            with open(json_file, 'r') as f:
                data = json.load(f)
                assert "trades" in data
                assert "equity_curve" in data


class TestConvenienceFunction:
    """Tests for the convenience run_mood_backtest function."""
    
    @patch('src.market_mood.backtest.yf.Ticker')
    @patch('src.market_mood.backtest.MoodBacktester')
    def test_run_mood_backtest(self, mock_backtester, mock_ticker):
        """Test the convenience function."""
        mock_instance = MagicMock()
        mock_result = BacktestResult(
            initial_capital=100000,
            final_capital=110000,
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
        )
        mock_instance.run_backtest.return_value = mock_result
        mock_backtester.return_value = mock_instance
        
        result = run_mood_backtest(
            start_date="2023-01-01",
            end_date="2023-12-31",
            initial_capital=100000,
            symbol="SPY",
        )
        
        mock_backtester.assert_called_once()
        mock_instance.run_backtest.assert_called_once()
        assert isinstance(result, BacktestResult)


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_empty_price_data(self):
        """Test handling empty price data."""
        backtester = MoodBacktester(
            start_date="2023-01-01",
            end_date="2023-01-31",
            initial_capital=100000,
        )
        backtester.price_data = pd.DataFrame()
        
        result = backtester.calculate_metrics()
        
        assert isinstance(result, BacktestResult)
        assert result.final_capital == backtester.initial_capital
    
    def test_no_trades(self):
        """Test backtest with no trades."""
        backtester = MoodBacktester(
            start_date="2023-01-01",
            end_date="2023-01-31",
            initial_capital=100000,
        )
        backtester.equity_curve = [100000.0] * 10
        backtester.equity_dates = [datetime(2023, 1, i) for i in range(1, 11)]
        backtester.trades = []
        
        result = backtester.calculate_metrics()
        
        assert len(result.trades) == 0
        assert result.metrics["total_trades"] == 0
    
    def test_all_winning_trades(self):
        """Test backtest with all winning trades."""
        backtester = MoodBacktester(
            start_date="2023-01-01",
            end_date="2023-01-31",
            initial_capital=100000,
        )
        
        backtester.trades = [
            Trade(
                entry_date=datetime(2023, 1, i),
                symbol="SPY",
                entry_price=400.0,
                quantity=100,
                pnl=1000.0,
            )
            for i in range(1, 6)
        ]
        
        analysis = backtester._analyze_trades_by_mood()
        
        for mood_data in analysis.values():
            if mood_data["count"] > 0:
                assert mood_data["winning_trades"] == mood_data["count"]
                assert mood_data["win_rate"] == 100.0
    
    def test_all_losing_trades(self):
        """Test backtest with all losing trades."""
        backtester = MoodBacktester(
            start_date="2023-01-01",
            end_date="2023-01-31",
            initial_capital=100000,
        )
        
        backtester.trades = [
            Trade(
                entry_date=datetime(2023, 1, i),
                symbol="SPY",
                entry_price=400.0,
                quantity=100,
                pnl=-500.0,
            )
            for i in range(1, 6)
        ]
        
        analysis = backtester._analyze_trades_by_mood()
        
        for mood_data in analysis.values():
            if mood_data["count"] > 0:
                assert mood_data["winning_trades"] == 0
                assert mood_data["win_rate"] == 0.0
