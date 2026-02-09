"""Unit tests for LangGraph nodes."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch

from src.trading_graph.state import TradingState
from src.trading_graph.nodes.data_nodes import fetch_market_data
from src.trading_graph.nodes.analysis_nodes import technical_analysis, sentiment_analysis, make_decision
from src.trading_graph.nodes.execution_nodes import risk_assessment, execute_trade, retry_node


@pytest.fixture
def sample_market_data():
    """Create sample market data for testing."""
    dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
    data = pd.DataFrame({
        'open': np.random.uniform(140, 160, 100),
        'high': np.random.uniform(140, 160, 100),
        'low': np.random.uniform(140, 160, 100),
        'close': np.random.uniform(140, 160, 100),
        'volume': np.random.randint(1_000_000, 10_000_000, 100)
    }, index=dates)
    return data


@pytest.fixture
def base_state():
    """Create a base trading state for testing."""
    return {
        "symbol": "AAPL",
        "timeframe": "1d",
        "market_data": {},
        "technical_indicators": {},
        "technical_signals": {},
        "sentiment_signals": {},
        "risk_signals": {},
        "debate_result": {},
        "final_decision": {},
        "final_action": None,
        "confidence": 0.0,
        "executed_trade": {},
        "order_id": None,
        "human_approved": None,
        "human_feedback": None,
        "messages": [],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "workflow_id": "test_workflow",
        "iteration": 0,
        "current_node": None,
        "error": None,
        "retry_count": 0
    }


@pytest.mark.asyncio
async def test_fetch_market_data(base_state):
    """Test fetch_market_data node."""
    with patch('src.data.providers.YahooFinanceProvider.get_historical') as mock_get_historical, \
         patch('src.data.indicators.TechnicalIndicators.add_all_indicators') as mock_indicators:
        mock_data = pd.DataFrame({
            'open': [150.0],
            'high': [152.0],
            'low': [149.0],
            'close': [151.0],
            'volume': [1000000]
        })
        mock_indicators.return_value = mock_data
        mock_get_historical.return_value = mock_data
        
        result = await fetch_market_data(base_state)
        
        assert result['current_node'] == 'fetch_market_data'
        assert 'error' not in result
        assert 'market_data' in result
        assert 'technical_indicators' in result


@pytest.mark.asyncio
async def test_fetch_market_data_error(base_state):
    """Test fetch_market_data node with error."""
    with patch('src.data.providers.YahooFinanceProvider.get_historical') as mock_get_historical:
        mock_get_historical.side_effect = Exception("API error")
        
        result = await fetch_market_data(base_state)
        
        assert result['current_node'] == 'fetch_market_data'
        assert 'error' in result
        assert 'API error' in result['error']


@pytest.mark.asyncio
async def test_technical_analysis(base_state, sample_market_data):
    """Test technical_analysis node."""
    state = base_state.copy()
    state['market_data'] = sample_market_data.to_dict()
    
    result = await technical_analysis(state)
    
    assert result['current_node'] == 'technical_analysis'
    assert 'error' not in result
    assert 'technical_signals' in result
    assert 'decision' in result['technical_signals']
    assert 'confidence' in result['technical_signals']
    assert result['technical_signals']['decision'] in ['BUY', 'SELL', 'HOLD']


@pytest.mark.asyncio
async def test_technical_analysis_no_data(base_state):
    """Test technical_analysis node with no data."""
    result = await technical_analysis(base_state)
    
    assert result['current_node'] == 'technical_analysis'
    assert 'error' in result
    assert 'No market data' in result['error']


@pytest.mark.asyncio
async def test_sentiment_analysis(base_state, sample_market_data):
    """Test sentiment_analysis node."""
    state = base_state.copy()
    state['market_data'] = sample_market_data.to_dict()
    
    with patch('src.agents.sentiment.SentimentAgent') as MockAgent:
        mock_agent = Mock()
        mock_agent.analyze = AsyncMock(return_value=Mock(
            decision=Mock(value='BUY'),
            confidence=0.75,
            reasoning='Bullish sentiment',
            agent_name='sentiment',
            data={'sentiment': 'bullish'}
        ))
        MockAgent.return_value = mock_agent
        
        result = await sentiment_analysis(state)
        
        assert result['current_node'] == 'sentiment_analysis'
        assert 'error' not in result
        assert 'sentiment_signals' in result
        assert 'decision' in result['sentiment_signals']
        assert 'confidence' in result['sentiment_signals']


@pytest.mark.asyncio
async def test_sentiment_analysis_no_data(base_state):
    """Test sentiment_analysis node with no data."""
    result = await sentiment_analysis(base_state)
    
    assert result['current_node'] == 'sentiment_analysis'
    assert 'error' in result
    assert 'No market data' in result['error']


@pytest.mark.asyncio
async def test_make_decision(base_state):
    """Test make_decision node with all signals."""
    state = base_state.copy()
    state['technical_signals'] = {
        'decision': 'BUY',
        'confidence': 0.80,
        'reasoning': 'RSI oversold'
    }
    state['sentiment_signals'] = {
        'decision': 'BUY',
        'confidence': 0.70,
        'reasoning': 'Bullish sentiment'
    }
    state['risk_signals'] = {
        'decision': 'HOLD',
        'confidence': 0.90,
        'reasoning': 'Risk check passed'
    }
    
    result = await make_decision(state)
    
    assert result['current_node'] == 'make_decision'
    assert 'error' not in result
    assert 'final_decision' in result
    assert 'final_action' in result
    assert 'confidence' in result
    assert result['final_action'] in ['BUY', 'SELL', 'HOLD']


@pytest.mark.asyncio
async def test_make_decision_risk_veto(base_state):
    """Test make_decision node with risk veto."""
    state = base_state.copy()
    state['technical_signals'] = {
        'decision': 'BUY',
        'confidence': 0.80,
        'reasoning': 'RSI oversold'
    }
    state['sentiment_signals'] = {
        'decision': 'BUY',
        'confidence': 0.70,
        'reasoning': 'Bullish sentiment'
    }
    state['risk_signals'] = {
        'decision': 'VETO',
        'confidence': 0.95,
        'reasoning': 'Liquidity violation'
    }
    
    result = await make_decision(state)
    
    assert result['current_node'] == 'make_decision'
    assert result['final_action'] == 'HOLD'
    assert result['confidence'] >= 0.95
    assert 'veto' in result['final_decision']['reasoning'].lower()


@pytest.mark.asyncio
async def test_make_decision_missing_signals(base_state):
    """Test make_decision node with missing signals."""
    result = await make_decision(base_state)
    
    assert result['current_node'] == 'make_decision'
    assert 'error' in result
    assert 'Missing required signals' in result['error']


@pytest.mark.asyncio
async def test_risk_assessment(base_state, sample_market_data):
    """Test risk_assessment node."""
    state = base_state.copy()
    state['market_data'] = sample_market_data.to_dict()
    state['final_decision'] = {'decision': 'BUY', 'confidence': 0.75}
    
    with patch('src.agents.risk.RiskAgent') as MockAgent:
        mock_agent = Mock()
        mock_agent.analyze = AsyncMock(return_value=Mock(
            decision=Mock(value='HOLD'),
            confidence=0.80,
            reasoning='Risk check passed',
            agent_name='risk',
            data={'recommended_size': 10}
        ))
        MockAgent.return_value = mock_agent
        
        result = await risk_assessment(state)
        
        assert result['current_node'] == 'risk_assessment'
        assert 'error' not in result
        assert 'risk_signals' in result
        assert 'decision' in result['risk_signals']


@pytest.mark.asyncio
async def test_risk_assessment_no_data(base_state):
    """Test risk_assessment node with no data."""
    result = await risk_assessment(base_state)
    
    assert result['current_node'] == 'risk_assessment'
    assert 'error' in result
    assert 'No market data' in result['error']


@pytest.mark.asyncio
async def test_execute_trade_buy(base_state):
    """Test execute_trade node with BUY signal."""
    state = base_state.copy()
    state['final_action'] = 'BUY'
    state['final_decision'] = {'decision': 'BUY', 'confidence': 0.75}
    state['risk_signals'] = {
        'data': {'recommended_size': 10}
    }
    state['human_approved'] = True  # Add human approval
    
    result = await execute_trade(state)
    
    assert result['current_node'] == 'execute_trade'
    assert 'error' not in result
    assert 'executed_trade' in result
    assert result['executed_trade']['action'] == 'BUY'
    assert 'order_id' in result


@pytest.mark.asyncio
async def test_execute_trade_hold(base_state):
    """Test execute_trade node with HOLD signal."""
    state = base_state.copy()
    state['final_action'] = 'HOLD'
    
    result = await execute_trade(state)
    
    assert result['current_node'] == 'execute_trade'
    assert 'error' not in result
    assert 'executed_trade' in result
    assert result['executed_trade']['action'] == 'HOLD'
    assert result['order_id'] is None


@pytest.mark.asyncio
async def test_retry_node(base_state):
    """Test retry_node increments counters."""
    state = base_state.copy()
    state['error'] = 'Some error'
    state['retry_count'] = 0
    state['iteration'] = 0
    
    result = await retry_node(state)
    
    assert result['current_node'] == 'retry_node'
    assert result['retry_count'] == 1
    assert result['iteration'] == 1
    assert result['error'] is None  # Error should be cleared


@pytest.mark.asyncio
async def test_retry_node_max_exceeded(base_state):
    """Test retry_node with max retries exceeded."""
    state = base_state.copy()
    state['retry_count'] = 3
    state['iteration'] = 3
    state['max_retries'] = 3
    
    result = await retry_node(state)
    
    assert result['current_node'] == 'retry_node'
    assert result['retry_count'] == 4
    assert 'error' in result
    assert 'Max retries' in result['error']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
