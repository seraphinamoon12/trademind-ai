"""Interactive Brokers broker implementation."""

# Import new ib_insync-based broker by default
from src.brokers.ibkr.ibkr_insync_broker import IBKRInsyncBroker as IBKRBroker

# Old threaded broker is optional (requires ibapi)
try:
    from src.brokers.ibkr.async_broker import IBKRThreadedBroker
    _has_old_broker = True
except ImportError:
    _has_old_broker = False
    IBKRThreadedBroker = None

__all__ = ['IBKRBroker', 'IBKRInsyncBroker', 'IBKRThreadedBroker']
