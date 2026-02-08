"""Persistence configuration for LangGraph checkpoints."""

from langgraph.checkpoint.sqlite import SqliteSaver
from pathlib import Path

# Database file location
CHECKPOINT_DIR = Path("data/checkpoints")
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

CHECKPOINT_DB = CHECKPOINT_DIR / "trading_agent_checkpoints.db"

# Create checkpointer
def get_checkpointer():
    """Get the LangGraph checkpointer instance."""
    return SqliteSaver.from_conn_string(str(CHECKPOINT_DB))
