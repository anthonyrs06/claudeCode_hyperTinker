"""
Tests for Error Recovery Agent
===============================
Unit tests for error analysis and retry logic.
"""

import pytest
from agents.error_recovery.error_recovery_agent import ErrorRecoveryAgent


class TestErrorRecoveryAgent:
    """Test Error Recovery Agent functionality."""

    def test_agent_creation(self):
        """Test agent instantiation."""
        agent = ErrorRecoveryAgent()
        assert agent.agent_name == "error_recovery_agent"
        assert len(agent.error_history) == 0

    def test_analyze_rate_limit_error(self):
        """Test analyzing rate limit error."""
        agent = ErrorRecoveryAgent()

        error = Exception("Rate limit exceeded")
        context = {"endpoint": "allMids"}

        analysis = agent.analyze_error(error, context)

        assert analysis["error_type"] == "rate_limit"
        assert analysis["recoverable"] == True
        assert analysis["strategy"]["max_retries"] > 0
        assert "rate limit" in analysis["error_message"].lower()

        print(f"\n✓ Rate limit error analyzed")
        print(f"  Strategy: {analysis['strategy']['recovery']}")

    def test_analyze_timeout_error(self):
        """Test analyzing timeout error."""
        agent = ErrorRecoveryAgent()

        error = Exception("Request timeout after 30 seconds")
        context = {"endpoint": "l2Book"}

        analysis = agent.analyze_error(error, context)

        assert analysis["error_type"] == "timeout"
        assert analysis["recoverable"] == True

        print(f"\n✓ Timeout error analyzed")

    def test_analyze_validation_error(self):
        """Test analyzing validation error."""
        agent = ErrorRecoveryAgent()

        error = Exception("Validation failed: invalid schema")
        context = {"endpoint": "userFills"}

        analysis = agent.analyze_error(error, context)

        assert analysis["error_type"] == "validation"
        assert analysis["recoverable"] == False  # Validation errors not recoverable

        print(f"\n✓ Validation error analyzed (not recoverable)")

    def test_execute_with_retry_success(self):
        """Test retry logic with eventual success."""
        agent = ErrorRecoveryAgent()

        # Function that fails twice then succeeds
        attempt_count = [0]

        def flaky_function():
            attempt_count[0] += 1
            if attempt_count[0] < 3:
                raise Exception("Temporary failure")
            return "success"

        result = agent.execute_with_retry(
            flaky_function,
            max_retries=3,
            base_delay=0.1,  # Short delay for testing
            context={"test": "retry_success"}
        )

        assert result == "success"
        assert attempt_count[0] == 3

        print(f"\n✓ Retry logic succeeded after {attempt_count[0]} attempts")

    def test_execute_with_retry_failure(self):
        """Test retry logic with all attempts failing."""
        agent = ErrorRecoveryAgent()

        def always_fails():
            raise Exception("Persistent failure")

        with pytest.raises(Exception, match="Persistent failure"):
            agent.execute_with_retry(
                always_fails,
                max_retries=2,
                base_delay=0.1,
                context={"test": "retry_failure"}
            )

        print(f"\n✓ Retry logic properly gave up after max retries")

    def test_get_error_summary(self):
        """Test error summary generation."""
        agent = ErrorRecoveryAgent()

        # Create some errors
        agent.analyze_error(Exception("Rate limit exceeded"), {"endpoint": "allMids"})
        agent.analyze_error(Exception("Timeout"), {"endpoint": "l2Book"})
        agent.analyze_error(Exception("Rate limit 429"), {"endpoint": "candles"})
        agent.analyze_error(Exception("Validation failed"), {"endpoint": "userFills"})

        summary = agent.get_error_summary()

        assert summary["total_errors"] == 4
        assert summary["by_type"]["rate_limit"] == 2
        assert summary["by_type"]["timeout"] == 1
        assert summary["by_type"]["validation"] == 1
        assert summary["recoverable_count"] == 3
        assert summary["unrecoverable_count"] == 1

        print(f"\n✓ Error summary:")
        print(f"  Total: {summary['total_errors']}")
        print(f"  By type: {summary['by_type']}")
        print(f"  Recoverable: {summary['recoverable_count']}")

    def test_get_retry_suggestion(self):
        """Test getting retry suggestions."""
        agent = ErrorRecoveryAgent()

        # Test known error type
        strategy = agent.get_retry_suggestion("rate_limit")
        assert strategy["max_retries"] > 0
        assert strategy["base_delay"] > 0

        # Test unknown error type
        unknown_strategy = agent.get_retry_suggestion("unknown_type")
        assert "description" in unknown_strategy

        print(f"\n✓ Retry suggestions retrieved")

    def test_is_transient_error(self):
        """Test transient error detection."""
        agent = ErrorRecoveryAgent()

        # Transient errors
        assert agent.is_transient_error(Exception("Timeout")) == True
        assert agent.is_transient_error(Exception("Rate limit exceeded")) == True
        assert agent.is_transient_error(Exception("HTTP 500")) == True
        assert agent.is_transient_error(Exception("Network error")) == True

        # Non-transient errors
        assert agent.is_transient_error(Exception("Validation failed")) == False
        assert agent.is_transient_error(Exception("Invalid parameters")) == False

        print(f"\n✓ Transient error detection working")

    def test_calculate_backoff_delay(self):
        """Test exponential backoff calculation."""
        agent = ErrorRecoveryAgent()

        # Test exponential increase
        delay0 = agent.calculate_backoff_delay(0, base_delay=1.0)
        delay1 = agent.calculate_backoff_delay(1, base_delay=1.0)
        delay2 = agent.calculate_backoff_delay(2, base_delay=1.0)

        assert delay0 == 1.0
        assert delay1 == 2.0
        assert delay2 == 4.0

        # Test max delay cap
        delay10 = agent.calculate_backoff_delay(10, base_delay=1.0, max_delay=60.0)
        assert delay10 == 60.0  # Capped at max

        print(f"\n✓ Backoff delays: {delay0}s -> {delay1}s -> {delay2}s")

    def test_clear_error_history(self):
        """Test clearing error history."""
        agent = ErrorRecoveryAgent()

        # Add errors
        agent.analyze_error(Exception("Error 1"), {})
        agent.analyze_error(Exception("Error 2"), {})

        assert len(agent.error_history) == 2

        # Clear
        agent.clear_error_history()

        assert len(agent.error_history) == 0

        print(f"\n✓ Error history cleared")

    def test_error_history_tracking(self):
        """Test that errors are tracked in history."""
        agent = ErrorRecoveryAgent()

        initial_count = len(agent.error_history)

        # Analyze several errors
        agent.analyze_error(Exception("Error 1"), {"test": 1})
        agent.analyze_error(Exception("Error 2"), {"test": 2})

        assert len(agent.error_history) == initial_count + 2

        # Check most recent error
        latest = agent.error_history[-1]
        assert "Error 2" in latest["error_message"]

        print(f"\n✓ Error history tracked: {len(agent.error_history)} errors")
