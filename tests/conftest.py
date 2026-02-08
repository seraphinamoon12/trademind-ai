"""Pytest configuration for IBKR tests."""
import pytest
import pytest_asyncio
import asyncio


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def paper_broker():
    """Create paper broker for testing without IBKR connection."""
    from src.execution.paper import PaperBroker
    broker = PaperBroker()
    await broker.connect()
    yield broker
    await broker.disconnect()


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (requires TWS/IB Gateway)"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )
