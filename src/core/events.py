"""Redis event bus for pub/sub communication."""
import json
import redis
from typing import Callable, Optional
from src.config import settings


class EventBus:
    """Redis-based event bus for micro-agent communication."""
    
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or settings.redis_url
        self.client = redis.from_url(self.redis_url, decode_responses=True)
        self.pubsub = None
    
    def publish(self, channel: str, data: dict) -> bool:
        """Publish an event to a channel."""
        try:
            message = json.dumps(data)
            self.client.publish(channel, message)
            return True
        except Exception as e:
            print(f"Error publishing to {channel}: {e}")
            return False
    
    def subscribe(self, channel: str, callback: Callable[[dict], None]):
        """Subscribe to a channel with a callback."""
        if self.pubsub is None:
            self.pubsub = self.client.pubsub()
        
        self.pubsub.subscribe(channel)
        
        for message in self.pubsub.listen():
            if message['type'] == 'message':
                try:
                    data = json.loads(message['data'])
                    callback(data)
                except json.JSONDecodeError as e:
                    print(f"Error decoding message: {e}")
    
    def close(self):
        """Close pubsub connection."""
        if self.pubsub:
            self.pubsub.close()


# Event types
class Events:
    MARKET_DATA_UPDATED = "market.data.updated"
    SIGNAL_GENERATED = "signal.generated"
    RISK_CHECKED = "risk.checked"
    ORDER_EXECUTED = "order.executed"
    PORTFOLIO_UPDATED = "portfolio.updated"
    AGENT_DECISION = "agent.decision"
    CIRCUIT_BREAKER = "safety.circuit_breaker"
    RISK_EVENT = "safety.risk_event"


# Global event bus instance
event_bus = EventBus()
