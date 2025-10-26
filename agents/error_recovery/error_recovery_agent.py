"""
Error Recovery Agent
====================
Utility agent for error handling, retry strategies, and recovery analysis.

Design Principle:
- Provides error analysis and recovery utilities
- Tracks error patterns for debugging
- Suggests recovery strategies based on error type
- Token usage: ~2K per analysis

Note: Full Memory Tool integration and learning capabilities
will be added in Phase 4 (Memory Integration).
"""

from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import time
from agents.base_agent import BaseAgent


class ErrorRecoveryAgent(BaseAgent):
    """
    Analyzes errors and provides recovery strategies.

    This agent provides utility methods for error handling
    across the multi-agent system.
    """

    # Known error types and recovery strategies
    ERROR_STRATEGIES = {
        "rate_limit": {
            "description": "API rate limit exceeded",
            "recovery": "Wait and retry with exponential backoff",
            "max_retries": 3,
            "base_delay": 1.0
        },
        "timeout": {
            "description": "Request timeout",
            "recovery": "Retry with increased timeout",
            "max_retries": 3,
            "base_delay": 0.5
        },
        "network": {
            "description": "Network error",
            "recovery": "Retry with exponential backoff",
            "max_retries": 3,
            "base_delay": 1.0
        },
        "validation": {
            "description": "Data validation failed",
            "recovery": "No retry - check data format",
            "max_retries": 0,
            "base_delay": 0
        },
        "not_found": {
            "description": "Resource not found",
            "recovery": "No retry - verify parameters",
            "max_retries": 0,
            "base_delay": 0
        },
        "server_error": {
            "description": "Server error (5xx)",
            "recovery": "Retry with exponential backoff",
            "max_retries": 3,
            "base_delay": 2.0
        }
    }

    def __init__(self):
        super().__init__(agent_name="error_recovery_agent")
        self.error_history: List[Dict[str, Any]] = []

    def analyze_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze an error and suggest recovery strategy.

        Args:
            error: The exception that occurred
            context: Context information (endpoint, params, etc.)

        Returns:
            {
                "error_type": "rate_limit",
                "error_message": "Rate limit exceeded",
                "recoverable": true,
                "strategy": {
                    "description": "Wait and retry",
                    "max_retries": 3,
                    "base_delay": 1.0
                },
                "context": {...}
            }

        Token usage: ~2K
        """
        error_str = str(error).lower()
        error_type = "unknown"

        # Classify error type
        if "rate limit" in error_str or "429" in error_str:
            error_type = "rate_limit"
        elif "timeout" in error_str:
            error_type = "timeout"
        elif "network" in error_str or "connection" in error_str:
            error_type = "network"
        elif "validation" in error_str or "schema" in error_str:
            error_type = "validation"
        elif "404" in error_str or "not found" in error_str:
            error_type = "not_found"
        elif "500" in error_str or "502" in error_str or "503" in error_str:
            error_type = "server_error"

        strategy = self.ERROR_STRATEGIES.get(error_type, {
            "description": "Unknown error",
            "recovery": "Retry with caution",
            "max_retries": 1,
            "base_delay": 1.0
        })

        analysis = {
            "error_type": error_type,
            "error_message": str(error),
            "recoverable": strategy["max_retries"] > 0,
            "strategy": strategy,
            "context": context,
            "timestamp": datetime.now().isoformat()
        }

        # Track error for pattern analysis
        self.error_history.append(analysis)

        return analysis

    def execute_with_retry(
        self,
        func: Callable,
        max_retries: int = 3,
        base_delay: float = 1.0,
        context: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Execute a function with retry logic.

        Args:
            func: Function to execute
            max_retries: Maximum number of retries
            base_delay: Base delay in seconds
            context: Context for error tracking

        Returns:
            Function result

        Raises:
            Exception: If all retries fail

        Token usage: ~2K per attempt
        """
        last_error = None
        context = context or {}

        for attempt in range(max_retries + 1):
            try:
                return func()
            except Exception as e:
                last_error = e

                # Analyze error
                analysis = self.analyze_error(e, {
                    **context,
                    "attempt": attempt + 1,
                    "max_retries": max_retries
                })

                # If not recoverable or last attempt, raise
                if not analysis["recoverable"] or attempt >= max_retries:
                    raise

                # Calculate delay with exponential backoff
                delay = base_delay * (2 ** attempt)

                # Wait before retry
                time.sleep(delay)

        # Should never reach here, but just in case
        raise last_error

    def get_error_summary(self) -> Dict[str, Any]:
        """
        Get summary of recent errors.

        Returns:
            {
                "total_errors": 10,
                "by_type": {
                    "rate_limit": 5,
                    "timeout": 3,
                    "network": 2
                },
                "recoverable_count": 8,
                "unrecoverable_count": 2,
                "recent_errors": [...]  # Last 10 errors
            }

        Token usage: ~0 (local calculation)
        """
        if not self.error_history:
            return {
                "total_errors": 0,
                "by_type": {},
                "recoverable_count": 0,
                "unrecoverable_count": 0,
                "recent_errors": []
            }

        # Count by type
        by_type = {}
        recoverable = 0
        unrecoverable = 0

        for error in self.error_history:
            error_type = error["error_type"]
            by_type[error_type] = by_type.get(error_type, 0) + 1

            if error["recoverable"]:
                recoverable += 1
            else:
                unrecoverable += 1

        return {
            "total_errors": len(self.error_history),
            "by_type": by_type,
            "recoverable_count": recoverable,
            "unrecoverable_count": unrecoverable,
            "recent_errors": self.error_history[-10:]  # Last 10
        }

    def clear_error_history(self):
        """Clear error history."""
        self.error_history = []

    def get_retry_suggestion(self, error_type: str) -> Dict[str, Any]:
        """
        Get retry suggestion for a specific error type.

        Args:
            error_type: Type of error

        Returns:
            Strategy dict with retry parameters

        Token usage: ~0 (lookup)
        """
        return self.ERROR_STRATEGIES.get(error_type, {
            "description": "Unknown error",
            "recovery": "Manual investigation required",
            "max_retries": 0,
            "base_delay": 0
        })

    def is_transient_error(self, error: Exception) -> bool:
        """
        Determine if an error is transient (recoverable).

        Args:
            error: The exception

        Returns:
            True if error is likely transient

        Token usage: ~0
        """
        error_str = str(error).lower()

        transient_indicators = [
            "timeout",
            "rate limit",
            "429",
            "500",
            "502",
            "503",
            "network",
            "connection"
        ]

        return any(indicator in error_str for indicator in transient_indicators)

    def calculate_backoff_delay(
        self,
        attempt: int,
        base_delay: float = 1.0,
        max_delay: float = 60.0
    ) -> float:
        """
        Calculate exponential backoff delay.

        Args:
            attempt: Attempt number (0-indexed)
            base_delay: Base delay in seconds
            max_delay: Maximum delay cap

        Returns:
            Delay in seconds

        Token usage: ~0
        """
        delay = base_delay * (2 ** attempt)
        return min(delay, max_delay)
