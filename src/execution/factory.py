"""Broker factory for creating broker instances."""
from typing import Dict, Any, Optional, List
import logging

from src.brokers.base import BaseBroker
from src.brokers.ibkr.client import IBKRBroker
from src.execution.paper import PaperBroker

logger = logging.getLogger(__name__)


class BrokerFactory:
    """Factory for creating broker instances based on configuration."""

    @staticmethod
    def create_broker(broker_type: str, config: Optional[Dict[str, Any]] = None) -> BaseBroker:
        """
        Create a broker instance.

        Args:
            broker_type: Type of broker ('paper', 'ibkr')
            config: Broker-specific configuration

        Returns:
            Instance of the requested broker

        Raises:
            ValueError: If broker_type is not supported
        """
        config = config or {}

        if broker_type.lower() == 'paper':
            logger.info("Creating PaperBroker instance")
            return PaperBroker()

        elif broker_type.lower() == 'ibkr':
            logger.info("Creating IBKRBroker instance")
            return IBKRBroker(
                host=config.get('host', '127.0.0.1'),
                port=config.get('port', 7497),
                client_id=config.get('client_id', 1),
                account=config.get('account'),
                paper_trading=config.get('paper_trading', True)
            )

        else:
            raise ValueError(f"Unsupported broker type: {broker_type}")

    @staticmethod
    def list_supported_brokers() -> List[str]:
        """Return list of supported broker types."""
        return ['paper', 'ibkr']
