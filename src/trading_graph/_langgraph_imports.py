"""Helper module to import from system langgraph package (avoiding shadowing by src.langgraph)."""
import sys
import importlib
from typing import Any

# Helper function to safely import from system langgraph
def import_langgraph(module_path: str) -> Any:
    """
    Import from the system langgraph package, avoiding shadowing by src.langgraph.
    
    Args:
        module_path: Module path like 'graph.state' or 'checkpoint.memory'
        
    Returns:
        The imported module
    """
    # Save original path
    original_path = sys.path.copy()
    
    # Temporarily remove src paths to access system langgraph
    if 'src' in sys.modules or any('/src' in p for p in sys.path):
        sys.path = [p for p in sys.path if '/src' not in p and not p.endswith('/src')]
    
    try:
        # Import the module
        module = importlib.import_module(f'langgraph.{module_path}')
        return module
    except ImportError as e:
        # Try direct import if sub-module import fails
        try:
            return importlib.import_module('langgraph')
        except ImportError:
            raise
    finally:
        # Restore original path
        sys.path = original_path


# Lazy-load common langgraph imports
_state_graph = None
_add_messages = None
_start = None
_end = None

def get_StateGraph():
    """Get StateGraph from system langgraph."""
    try:
        # Always try to remove src.langgraph from sys.modules temporarily
        if 'src.langgraph' in sys.modules:
            src_langgraph = sys.modules.pop('src.langgraph')
            try:
                from langgraph.graph.state import StateGraph as SG
                return SG
            finally:
                sys.modules['src.langgraph'] = src_langgraph
        else:
            from langgraph.graph.state import StateGraph as SG
            return SG
    except ImportError:
        try:
            from langgraph import StateGraph as SG
            return SG
        except ImportError:
            return None

def get_add_messages():
    """Get add_messages from system langgraph."""
    global _add_messages
    if _add_messages is None:
        try:
            if 'src.langgraph' in sys.modules:
                src_langgraph = sys.modules.pop('src.langgraph')
                try:
                    from langgraph.graph import add_messages as am
                    _add_messages = am
                finally:
                    sys.modules['src.langgraph'] = src_langgraph
            else:
                from langgraph.graph import add_messages as am
                _add_messages = am
        except ImportError:
            # Fallback: define a simple add_messages function
            def add_messages(left, right):
                if left is None:
                    return right or []
                if right is None:
                    return left
                return left + right
            _add_messages = add_messages
    return _add_messages

def get_START_END():
    """Get START and END constants from system langgraph."""
    global _start, _end
    if _start is None or _end is None:
        try:
            if 'src.langgraph' in sys.modules:
                src_langgraph = sys.modules.pop('src.langgraph')
                try:
                    from langgraph.constants import START, END
                    _start, _end = START, END
                finally:
                    sys.modules['src.langgraph'] = src_langgraph
            else:
                from langgraph.constants import START, END
                _start, _end = START, END
        except ImportError:
            _start = "__start__"
            _end = "__end__"
    return _start, _end

def get_MemorySaver():
    """Get MemorySaver from system langgraph."""
    try:
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
    except ImportError:
        return None
