"""Persistence configuration for LangGraph checkpoints."""

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from pathlib import Path

# Database file location
CHECKPOINT_DIR = Path("data/checkpoints")
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

CHECKPOINT_DB = CHECKPOINT_DIR / "trading_agent_checkpoints.db"


async def get_checkpointer():
    """
    Create and return async SQLite checkpointer.

    Uses file-based database for persistence across restarts.
    Creates directory if it doesn't exist.
    """
    return AsyncSqliteSaver.from_conn_string(str(CHECKPOINT_DB))
