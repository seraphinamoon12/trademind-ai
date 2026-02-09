"""Pydantic validation for TradingState and enhanced error handling."""
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, Field, field_validator, model_validator, ValidationError

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Severity levels for errors."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TradingStateValidator(BaseModel):
    """Pydantic validator for TradingState."""
    
    # Required fields
    symbol: str = Field(..., min_length=1, max_length=10)
    timeframe: str = Field(default="1d")
    
    # Trading decision fields
    final_action: Optional[Literal["BUY", "SELL", "HOLD"]] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Trade execution fields
    quantity: Optional[int] = Field(default=None, gt=0)
    price: Optional[float] = Field(default=None, gt=0)
    
    # Metadata
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    workflow_id: Optional[str] = None
    iteration: int = Field(default=0, ge=0)
    current_node: Optional[str] = None
    
    @field_validator('symbol')
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """Validate symbol is alphabetic and uppercase."""
        if not v:
            raise ValueError('Symbol cannot be empty')
        if not v.isalpha():
            raise ValueError('Symbol must be alphabetic')
        return v.upper()
    
    @field_validator('timeframe')
    @classmethod
    def validate_timeframe(cls, v: str) -> str:
        """Validate timeframe is a valid trading timeframe."""
        valid_timeframes = ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w"]
        v = v.lower()
        if v not in valid_timeframes:
            raise ValueError(f'Timeframe must be one of {valid_timeframes}')
        return v
    
    @model_validator(mode='after')
    def validate_consistency(self) -> 'TradingStateValidator':
        """Validate field consistency."""
        # If action is BUY or SELL, quantity should be provided
        if self.final_action in ["BUY", "SELL"] and self.quantity is None:
            raise ValueError('Quantity is required for BUY/SELL actions')
        
        # If HOLD, confidence should be low
        if self.final_action == "HOLD" and self.confidence > 0.3:
            raise ValueError('HOLD action should have low confidence (< 0.3)')
        
        return self


class ErrorHandler:
    """Structured error handler for LangGraph workflow."""
    
    def __init__(self):
        self.errors: List[Dict[str, Any]] = []
        self.max_errors = 100  # Keep last 100 errors
    
    def log_error(
        self,
        node: str,
        error: Exception,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        state: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log an error with context.
        
        Args:
            node: Node where error occurred
            error: Exception that occurred
            severity: Error severity level
            state: Current trading state (for debugging)
        """
        error_info = {
            "node": node,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "severity": severity.value,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Add sanitized state snapshot (exclude large fields like messages)
        if state:
            error_info["state_snapshot"] = {
                k: v for k, v in state.items()
                if k != "messages" and not k.startswith("_")
            }
        
        self.errors.append(error_info)
        
        # Keep only recent errors
        if len(self.errors) > self.max_errors:
            self.errors = self.errors[-self.max_errors:]
        
        # Log based on severity
        if severity == ErrorSeverity.CRITICAL:
            logger.critical(f"Critical error in {node}: {error}")
        elif severity == ErrorSeverity.HIGH:
            logger.error(f"High severity error in {node}: {error}")
        elif severity == ErrorSeverity.MEDIUM:
            logger.warning(f"Error in {node}: {error}")
        else:
            logger.debug(f"Low severity error in {node}: {error}")
    
    def get_recent_errors(
        self,
        severity: Optional[ErrorSeverity] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get recent errors, optionally filtered by severity.
        
        Args:
            severity: Filter by severity (None for all)
            limit: Maximum number of errors to return
            
        Returns:
            List of error dictionaries
        """
        errors = self.errors
        
        if severity:
            errors = [e for e in errors if e["severity"] == severity.value]
        
        return errors[-limit:]
    
    def clear_errors(self) -> None:
        """Clear all logged errors."""
        self.errors.clear()
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of all logged errors."""
        if not self.errors:
            return {"total": 0, "by_severity": {}, "by_node": {}}
        
        summary = {"total": len(self.errors)}
        
        # Count by severity
        by_severity = {}
        for error in self.errors:
            sev = error["severity"]
            by_severity[sev] = by_severity.get(sev, 0) + 1
        summary["by_severity"] = by_severity
        
        # Count by node
        by_node = {}
        for error in self.errors:
            node = error["node"]
            by_node[node] = by_node.get(node, 0) + 1
        summary["by_node"] = by_node
        
        return summary


def validate_state(state: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate a TradingState dictionary.
    
    Args:
        state: Dictionary representing TradingState
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        TradingStateValidator(**state)
        return True, None
    except ValidationError as e:
        error_msg = f"State validation failed: {e}"
        logger.error(error_msg)
        return False, error_msg


def create_error_state(
    node: str,
    error: Exception,
    current_state: Dict[str, Any],
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
) -> Dict[str, Any]:
    """
    Create an error state for LangGraph workflow.
    
    Args:
        node: Node where error occurred
        error: Exception that occurred
        current_state: Current state
        severity: Error severity
        
    Returns:
        Updated state with error information
    """
    return {
        "error": f"{type(error).__name__}: {str(error)}",
        "current_node": f"{node}_error",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# Global error handler instance
_global_error_handler = ErrorHandler()


def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance."""
    return _global_error_handler
