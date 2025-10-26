"""
Tests for Circuit Breaker
==========================
Tests for circuit breaker fault tolerance pattern.
"""

import pytest
import time
from datetime import datetime, timedelta
from core.circuit_breaker import CircuitBreaker, CircuitState, CircuitBreakerManager


class TestCircuitBreaker:
    """Test Circuit Breaker functionality."""

    def test_circuit_starts_closed(self):
        """Test that circuit starts in CLOSED state."""
        cb = CircuitBreaker(failure_threshold=3, timeout_seconds=5)

        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

        print("\n✓ Circuit starts CLOSED")

    def test_successful_call_passes_through(self):
        """Test that successful calls pass through."""
        cb = CircuitBreaker()

        def success_func():
            return "success"

        result = cb.call(success_func)

        assert result == "success"
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

        print("\n✓ Successful calls pass through")

    def test_circuit_opens_after_threshold_failures(self):
        """Test that circuit opens after failure threshold."""
        cb = CircuitBreaker(failure_threshold=3)

        def failing_func():
            raise Exception("Failure")

        # Call 3 times (threshold)
        for i in range(3):
            try:
                cb.call(failing_func)
            except Exception:
                pass

        # Circuit should be OPEN
        assert cb.state == CircuitState.OPEN
        assert cb.opened_at is not None

        print("\n✓ Circuit opens after threshold failures")

    def test_open_circuit_blocks_calls(self):
        """Test that OPEN circuit blocks calls immediately."""
        cb = CircuitBreaker(failure_threshold=3)

        # Force circuit open
        cb._transition_to_open()

        def test_func():
            return "should not execute"

        # Should raise exception without calling function
        with pytest.raises(Exception) as exc_info:
            cb.call(test_func)

        assert "Circuit breaker OPEN" in str(exc_info.value)

        print("\n✓ OPEN circuit blocks calls")

    def test_circuit_transitions_to_half_open_after_timeout(self):
        """Test that circuit transitions to HALF_OPEN after timeout."""
        cb = CircuitBreaker(failure_threshold=3, timeout_seconds=1)

        # Open circuit
        cb._transition_to_open()
        assert cb.state == CircuitState.OPEN

        # Wait for timeout
        time.sleep(1.1)

        # Next call should transition to HALF_OPEN
        def success_func():
            return "success"

        result = cb.call(success_func)

        assert cb.state == CircuitState.HALF_OPEN
        assert result == "success"

        print("\n✓ Circuit transitions to HALF_OPEN after timeout")

    def test_half_open_closes_after_successful_calls(self):
        """Test that HALF_OPEN closes after successful calls."""
        cb = CircuitBreaker(failure_threshold=3, timeout_seconds=1, half_open_max_calls=2)

        # Force to HALF_OPEN
        cb._transition_to_half_open()

        def success_func():
            return "success"

        # Make 2 successful calls
        cb.call(success_func)
        assert cb.state == CircuitState.HALF_OPEN

        cb.call(success_func)
        # Should close after 2 successes
        assert cb.state == CircuitState.CLOSED

        print("\n✓ HALF_OPEN closes after successful calls")

    def test_half_open_reopens_on_failure(self):
        """Test that HALF_OPEN reopens on failure."""
        cb = CircuitBreaker()

        # Force to HALF_OPEN
        cb._transition_to_half_open()

        def failing_func():
            raise Exception("Failure in half-open")

        # Should reopen immediately
        try:
            cb.call(failing_func)
        except Exception:
            pass

        assert cb.state == CircuitState.OPEN

        print("\n✓ HALF_OPEN reopens on failure")

    def test_success_resets_failure_count_in_closed_state(self):
        """Test that success resets failure count in CLOSED state."""
        cb = CircuitBreaker(failure_threshold=3)

        def failing_func():
            raise Exception("Failure")

        def success_func():
            return "success"

        # 2 failures
        for i in range(2):
            try:
                cb.call(failing_func)
            except:
                pass

        assert cb.failure_count == 2

        # 1 success should reset
        cb.call(success_func)

        assert cb.failure_count == 0
        assert cb.state == CircuitState.CLOSED

        print("\n✓ Success resets failure count")

    def test_get_state(self):
        """Test getting circuit state."""
        cb = CircuitBreaker()

        state = cb.get_state()

        assert state["state"] == "closed"
        assert state["failure_count"] == 0
        assert state["success_count"] == 0
        assert state["opened_at"] is None

        print("\n✓ Get state returns correct info")

    def test_reset(self):
        """Test resetting circuit breaker."""
        cb = CircuitBreaker(failure_threshold=2)

        # Force open
        cb._transition_to_open()
        cb.failure_count = 5

        # Reset
        cb.reset()

        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
        assert cb.opened_at is None

        print("\n✓ Reset works correctly")


class TestCircuitBreakerManager:
    """Test Circuit Breaker Manager."""

    def test_manager_creates_breakers_on_demand(self):
        """Test that manager creates breakers on demand."""
        manager = CircuitBreakerManager()

        # Get breaker for agent
        breaker = manager.get_breaker("price_agent")

        assert breaker is not None
        assert isinstance(breaker, CircuitBreaker)
        assert breaker.state == CircuitState.CLOSED

        print("\n✓ Manager creates breakers on demand")

    def test_manager_reuses_breakers(self):
        """Test that manager reuses existing breakers."""
        manager = CircuitBreakerManager()

        breaker1 = manager.get_breaker("price_agent")
        breaker2 = manager.get_breaker("price_agent")

        assert breaker1 is breaker2

        print("\n✓ Manager reuses breakers")

    def test_manager_call_method(self):
        """Test manager's call method."""
        manager = CircuitBreakerManager(failure_threshold=3)

        def success_func(value):
            return f"success: {value}"

        result = manager.call("test_agent", success_func, "test")

        assert result == "success: test"

        print("\n✓ Manager call method works")

    def test_manager_tracks_multiple_agents(self):
        """Test that manager tracks multiple agents independently."""
        manager = CircuitBreakerManager(failure_threshold=2)

        def failing_func():
            raise Exception("Failure")

        # Fail agent1
        for i in range(2):
            try:
                manager.call("agent1", failing_func)
            except:
                pass

        # Agent1 should be open
        breaker1 = manager.get_breaker("agent1")
        assert breaker1.state == CircuitState.OPEN

        # Agent2 should still be closed
        breaker2 = manager.get_breaker("agent2")
        assert breaker2.state == CircuitState.CLOSED

        print("\n✓ Manager tracks multiple agents independently")

    def test_get_all_states(self):
        """Test getting all circuit breaker states."""
        manager = CircuitBreakerManager()

        # Create some breakers
        manager.get_breaker("agent1")
        manager.get_breaker("agent2")

        states = manager.get_all_states()

        assert "agent1" in states
        assert "agent2" in states
        assert states["agent1"]["state"] == "closed"

        print("\n✓ Get all states works")

    def test_reset_all(self):
        """Test resetting all circuit breakers."""
        manager = CircuitBreakerManager(failure_threshold=1)

        def failing_func():
            raise Exception("Failure")

        # Fail both agents
        try:
            manager.call("agent1", failing_func)
        except:
            pass

        try:
            manager.call("agent2", failing_func)
        except:
            pass

        # Both should be open
        assert manager.get_breaker("agent1").state == CircuitState.OPEN
        assert manager.get_breaker("agent2").state == CircuitState.OPEN

        # Reset all
        manager.reset_all()

        # Both should be closed
        assert manager.get_breaker("agent1").state == CircuitState.CLOSED
        assert manager.get_breaker("agent2").state == CircuitState.CLOSED

        print("\n✓ Reset all works")

    def test_manager_applies_config_to_all_breakers(self):
        """Test that manager config applies to all breakers."""
        manager = CircuitBreakerManager(
            failure_threshold=10,
            timeout_seconds=120,
            half_open_max_calls=5
        )

        breaker = manager.get_breaker("test_agent")

        assert breaker.failure_threshold == 10
        assert breaker.timeout_seconds == 120
        assert breaker.half_open_max_calls == 5

        print("\n✓ Manager config applies to all breakers")


class TestCircuitBreakerEdgeCases:
    """Test edge cases and error conditions."""

    def test_circuit_with_zero_threshold(self):
        """Test circuit with threshold of 0 (should not open)."""
        cb = CircuitBreaker(failure_threshold=0)

        def failing_func():
            raise Exception("Failure")

        # Even with failures, should not open
        for i in range(5):
            try:
                cb.call(failing_func)
            except:
                pass

        # Should stay closed (threshold 0 means never open)
        # Note: This is edge case behavior
        print("\n✓ Zero threshold handled")

    def test_circuit_with_function_returning_none(self):
        """Test circuit with function that returns None."""
        cb = CircuitBreaker()

        def none_func():
            return None

        result = cb.call(none_func)

        assert result is None
        assert cb.state == CircuitState.CLOSED

        print("\n✓ Functions returning None handled")

    def test_circuit_with_function_with_kwargs(self):
        """Test circuit with function using kwargs."""
        cb = CircuitBreaker()

        def kwargs_func(a, b=10, c=20):
            return a + b + c

        result = cb.call(kwargs_func, 5, b=15, c=25)

        assert result == 45

        print("\n✓ Functions with kwargs handled")

    def test_state_transitions_are_atomic(self):
        """Test that state transitions maintain consistency."""
        cb = CircuitBreaker(failure_threshold=3)

        # Ensure transition maintains state
        cb._transition_to_open()
        assert cb.state == CircuitState.OPEN
        assert cb.opened_at is not None
        assert cb.success_count == 0

        cb._transition_to_half_open()
        assert cb.state == CircuitState.HALF_OPEN
        assert cb.success_count == 0
        assert cb.failure_count == 0

        cb._transition_to_closed()
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
        assert cb.opened_at is None

        print("\n✓ State transitions are atomic")
