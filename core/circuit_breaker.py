"""
Circuit Breaker
===============
Implements circuit breaker pattern for agent fault tolerance.

States:
- CLOSED: Normal operation, requests pass through
- OPEN: Too many failures, requests fail immediately
- HALF_OPEN: Testing if service recovered

This prevents cascading failures when an agent is experiencing issues.
"""

import time
from enum import Enum
from typing import Dict, Callable, Any
from datetime import datetime, timedelta


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, block requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """
    Circuit breaker for agent fault tolerance.

    Prevents repeated calls to failing agents and allows time for recovery.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout_seconds: int = 60,
        half_open_max_calls: int = 3
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            timeout_seconds: How long circuit stays open before trying half-open
            half_open_max_calls: Max successful calls in half-open before closing
        """
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.half_open_max_calls = half_open_max_calls

        # State
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.opened_at = None

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to call
            *args, **kwargs: Arguments to pass to function

        Returns:
            Function result

        Raises:
            Exception: If circuit is open or function fails
        """
        # Check if we should try the call
        if self.state == CircuitState.OPEN:
            # Check if timeout elapsed
            if self._should_attempt_reset():
                self._transition_to_half_open()
            else:
                raise Exception(f"Circuit breaker OPEN for agent (opened at {self.opened_at})")

        try:
            # Make the call
            result = func(*args, **kwargs)

            # Call succeeded
            self._on_success()
            return result

        except Exception as e:
            # Call failed
            self._on_failure()
            raise

    def _on_success(self):
        """Handle successful call."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.half_open_max_calls:
                self._transition_to_closed()
        else:
            # Reset failure count on success
            self.failure_count = 0

    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.state == CircuitState.HALF_OPEN:
            # Failed in half-open state, go back to open
            self._transition_to_open()
        elif self.failure_count >= self.failure_threshold:
            # Too many failures, open circuit
            self._transition_to_open()

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to try half-open."""
        if self.opened_at is None:
            return False

        elapsed = (datetime.now() - self.opened_at).total_seconds()
        return elapsed >= self.timeout_seconds

    def _transition_to_closed(self):
        """Transition to CLOSED state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.opened_at = None

    def _transition_to_open(self):
        """Transition to OPEN state."""
        self.state = CircuitState.OPEN
        self.opened_at = datetime.now()
        self.success_count = 0

    def _transition_to_half_open(self):
        """Transition to HALF_OPEN state."""
        self.state = CircuitState.HALF_OPEN
        self.success_count = 0
        self.failure_count = 0

    def get_state(self) -> Dict[str, Any]:
        """
        Get current circuit breaker state.

        Returns:
            {
                "state": "closed",
                "failure_count": 0,
                "success_count": 0,
                "opened_at": None,
                "last_failure_time": None
            }
        """
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None
        }

    def reset(self):
        """Reset circuit breaker to CLOSED state."""
        self._transition_to_closed()


class CircuitBreakerManager:
    """
    Manages circuit breakers for multiple agents.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout_seconds: int = 60,
        half_open_max_calls: int = 3
    ):
        """Initialize circuit breaker manager."""
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.half_open_max_calls = half_open_max_calls
        self.breakers: Dict[str, CircuitBreaker] = {}

    def get_breaker(self, agent_name: str) -> CircuitBreaker:
        """Get circuit breaker for agent (creates if doesn't exist)."""
        if agent_name not in self.breakers:
            self.breakers[agent_name] = CircuitBreaker(
                failure_threshold=self.failure_threshold,
                timeout_seconds=self.timeout_seconds,
                half_open_max_calls=self.half_open_max_calls
            )
        return self.breakers[agent_name]

    def call(self, agent_name: str, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection for specific agent.

        Args:
            agent_name: Name of agent
            func: Function to call
            *args, **kwargs: Arguments

        Returns:
            Function result
        """
        breaker = self.get_breaker(agent_name)
        return breaker.call(func, *args, **kwargs)

    def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        """Get states of all circuit breakers."""
        return {
            agent: breaker.get_state()
            for agent, breaker in self.breakers.items()
        }

    def reset_all(self):
        """Reset all circuit breakers."""
        for breaker in self.breakers.values():
            breaker.reset()
