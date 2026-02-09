"""Persistence configuration for LangGraph checkpoints."""

from pathlib import Path
import sys

# Helper to import MemorySaver from system langgraph (avoid shadowing)
def _import_memory_saver():
    """Import MemorySaver from system langgraph package."""
    if 'src.langgraph' in sys.modules:
        src_langgraph = sys.modules.pop('src.langgraph')
        try:
            from langgraph.checkpoint.memory import MemorySaver
            return MemorySaver
        finally:
            sys.modules['src.langgraph'] = src_langgraph
    else:
        from langgraph.checkpoint.memory import MemorySaver
        return MemorySaver

MemorySaver = _import_memory_saver()

# Database file location (reserved for future SQLite implementation)
CHECKPOINT_DIR = Path("data/checkpoints")
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

CHECKPOINT_DB = CHECKPOINT_DIR / "trading_agent_checkpoints.db"


async def get_checkpointer():
    """
    Create and return checkpointer.

    Uses MemorySaver for in-memory persistence.
    Future implementation: Use AsyncSqliteSaver for file-based persistence.
    """
    return MemorySaver()
