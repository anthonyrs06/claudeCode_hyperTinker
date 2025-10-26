"""
Unit Tests for Base Agent
=========================
Tests the base agent skill invocation capability.
"""

import pytest
from agents.base_agent import BaseAgent


class TestBaseAgent:
    """Test base agent functionality."""

    def test_base_agent_creation(self):
        """Test that base agent can be instantiated."""
        agent = BaseAgent(agent_name="test_agent")
        assert agent.agent_name == "test_agent"
        assert agent.project_root.exists()
        assert agent.python_bin.exists()

    def test_invoke_skill_success(self):
        """Test successful skill invocation."""
        agent = BaseAgent(agent_name="test_agent")

        # Invoke the skill we built in Phase 1
        result = agent.invoke_skill("hyperliquid-fetch-and-cache", {
            "endpoint": "allMids",
            "params": {}
        })

        # Validate response structure
        assert isinstance(result, dict)
        assert "success" in result
        assert result["success"] == True
        assert "data" in result
        assert "metadata" in result

        # Validate data
        assert isinstance(result["data"], dict)
        assert len(result["data"]) > 0  # Should have coins

        # Validate metadata
        assert "source" in result["metadata"]
        assert "endpoint" in result["metadata"]
        assert result["metadata"]["endpoint"] == "allMids"

    def test_invoke_skill_with_params(self):
        """Test skill invocation with parameters."""
        agent = BaseAgent(agent_name="test_agent")

        # Test with coin-specific endpoint
        result = agent.invoke_skill("hyperliquid-fetch-and-cache", {
            "endpoint": "l2Book",
            "params": {"coin": "BTC"}
        })

        assert result["success"] == True
        assert "data" in result
        assert result["data"]["coin"] == "BTC"
        assert "levels" in result["data"]

    def test_invoke_skill_nonexistent(self):
        """Test error handling for nonexistent skill."""
        agent = BaseAgent(agent_name="test_agent")

        with pytest.raises(FileNotFoundError):
            agent.invoke_skill("nonexistent-skill", {})

    def test_validate_response_success(self):
        """Test response validation for successful response."""
        agent = BaseAgent(agent_name="test_agent")

        valid_response = {
            "success": True,
            "data": {"test": "data"},
            "metadata": {}
        }

        # Should not raise
        agent.validate_response(valid_response)

    def test_validate_response_error(self):
        """Test response validation for error response."""
        agent = BaseAgent(agent_name="test_agent")

        error_response = {
            "success": False,
            "error": "Test error"
        }

        # Should not raise
        agent.validate_response(error_response)

    def test_validate_response_invalid(self):
        """Test response validation catches invalid responses."""
        agent = BaseAgent(agent_name="test_agent")

        # Missing success field
        with pytest.raises(ValueError, match="missing 'success'"):
            agent.validate_response({"data": "test"})

        # Success=True but no data
        with pytest.raises(ValueError, match="missing 'data'"):
            agent.validate_response({"success": True})

        # Success=False but no error
        with pytest.raises(ValueError, match="missing 'error'"):
            agent.validate_response({"success": False})

    def test_handle_error(self):
        """Test error handling produces proper error response."""
        agent = BaseAgent(agent_name="test_agent")

        error = Exception("Test error")
        context = {"endpoint": "test", "params": {}}

        result = agent.handle_error(error, context)

        assert result["success"] == False
        assert "error" in result
        assert result["error"] == "Test error"
        assert result["error_type"] == "Exception"
        assert result["context"] == context
        assert result["agent"] == "test_agent"
        assert "timestamp" in result
