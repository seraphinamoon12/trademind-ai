"""Pytest configuration for IBKR tests."""
import pytest
import pytest_asyncio
import asyncio
import socket


def _is_tws_running(port=7497):
    """Check if TWS/IB Gateway is running on the specified port."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            s.connect(('127.0.0.1', port))
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def pytest_collection_modifyitems(config, items):
    """Skip integration tests if TWS is not running."""
    if not _is_tws_running():
        skip_integration = pytest.mark.skip(reason="TWS/IB Gateway not running - skipping integration tests")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)


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
