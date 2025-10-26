"""
Tests for Orchestrator Memory Integration (Phase 4)
===================================================
Tests for routing history tracking, performance metrics, and learning.
"""

import pytest
import time
from agents.orchestrator.orchestrator_agent import OrchestratorAgent


class TestOrchestratorMemory:
    """Test Orchestrator Memory Tool integration."""

    def test_memory_initialization(self):
        """Test that memory structures are initialized."""
        orchestrator = OrchestratorAgent()

        # Check routing history exists
        history = orchestrator.memory.read("orchestrator", "routing_history.json", default=None)
        assert history is not None

        # Check performance metrics exist
        performance = orchestrator.memory.read("orchestrator", "task_performance.json", default=None)
        assert performance is not None
        assert "agents" in performance

        print(f"\n✓ Memory structures initialized")

    def test_routing_decision_tracking(self):
        """Test that routing decisions are tracked in memory."""
        orchestrator = OrchestratorAgent()

        # Clear history for clean test
        orchestrator.memory.write("orchestrator", "routing_history.json", [])

        # Make a request (with tracking)
        orchestrator.route_request("What is BTC price?", track_memory=True)

        # Check history was recorded
        history = orchestrator.get_routing_history(limit=1)

        assert len(history) == 1
        assert "BTC price" in history[0]["request"]
        assert history[0]["intent"] == "price"
        assert history[0]["routed_to"] == "price_book"
        assert "response_time_ms" in history[0]
        assert history[0]["success"] == True

        print(f"\n✓ Routing decision tracked:")
        print(f"  Intent: {history[0]['intent']}")
        print(f"  Agent: {history[0]['routed_to']}")
        print(f"  Time: {history[0]['response_time_ms']}ms")

    def test_performance_metrics_tracking(self):
        """Test that performance metrics are updated."""
        orchestrator = OrchestratorAgent()

        # Clear metrics
        orchestrator.memory.write("orchestrator", "task_performance.json", {
            "version": "1.0",
            "agents": {
                "price_book": {"total_requests": 0, "total_time_ms": 0, "errors": 0}
            }
        })

        # Make a request
        orchestrator.route_request("Show BTC price", track_memory=True)

        # Check metrics updated
        metrics = orchestrator.get_performance_metrics()

        assert metrics["total_requests"] >= 1
        assert metrics["agents"]["price_book"]["total_requests"] >= 1
        assert metrics["agents"]["price_book"]["avg_response_ms"] > 0

        print(f"\n✓ Performance metrics:")
        print(f"  Total requests: {metrics['total_requests']}")
        print(f"  Avg response: {metrics['avg_response_ms']}ms")

    def test_multiple_request_tracking(self):
        """Test tracking multiple requests."""
        orchestrator = OrchestratorAgent()

        # Clear history
        orchestrator.memory.write("orchestrator", "routing_history.json", [])

        # Make multiple requests
        requests = [
            "BTC price",
            "ETH orderbook",
            "SOL 1h candles"
        ]

        for req in requests:
            orchestrator.route_request(req, track_memory=True)

        # Check all recorded
        history = orchestrator.get_routing_history(limit=10)

        assert len(history) >= 3

        print(f"\n✓ Tracked {len(history)} requests")

    def test_analyze_routing_patterns(self):
        """Test routing pattern analysis."""
        orchestrator = OrchestratorAgent()

        # Clear and add test data
        orchestrator.memory.write("orchestrator", "routing_history.json", [])

        # Make various requests
        orchestrator.route_request("BTC price", track_memory=True)
        orchestrator.route_request("ETH price", track_memory=True)
        orchestrator.route_request("SOL candles", track_memory=True)

        # Analyze patterns
        analysis = orchestrator.analyze_routing_patterns()

        assert analysis["total_requests"] >= 3
        assert "intent_distribution" in analysis
        assert "agent_utilization" in analysis
        assert analysis["most_common_intent"] is not None

        print(f"\n✓ Routing pattern analysis:")
        print(f"  Most common: {analysis['most_common_intent']}")
        print(f"  Intent dist: {analysis['intent_distribution']}")
        print(f"  Agent util: {analysis['agent_utilization']}")

    def test_performance_metrics_calculation(self):
        """Test that performance calculations are correct."""
        orchestrator = OrchestratorAgent()

        # Manually set known metrics
        orchestrator.memory.write("orchestrator", "task_performance.json", {
            "version": "1.0",
            "agents": {
                "price_book": {
                    "total_requests": 10,
                    "total_time_ms": 2500,  # Should avg 250ms
                    "errors": 1  # Should be 0.1 error rate
                }
            }
        })

        metrics = orchestrator.get_performance_metrics()

        assert metrics["agents"]["price_book"]["total_requests"] == 10
        assert metrics["agents"]["price_book"]["avg_response_ms"] == 250.0
        assert metrics["agents"]["price_book"]["error_rate"] == 0.1
        assert metrics["agents"]["price_book"]["uptime"] == 0.9

        print(f"\n✓ Metric calculations correct:")
        print(f"  Avg: {metrics['agents']['price_book']['avg_response_ms']}ms")
        print(f"  Error rate: {metrics['agents']['price_book']['error_rate']}")

    def test_tracking_can_be_disabled(self):
        """Test that tracking can be disabled."""
        orchestrator = OrchestratorAgent()

        # Clear history
        orchestrator.memory.write("orchestrator", "routing_history.json", [])

        # Make request with tracking disabled
        orchestrator.route_request("BTC price", track_memory=False)

        # History should still be empty
        history = orchestrator.get_routing_history(limit=1)

        assert len(history) == 0

        print(f"\n✓ Tracking can be disabled")

    def test_error_tracking(self):
        """Test that errors are tracked properly."""
        orchestrator = OrchestratorAgent()

        # Clear history
        orchestrator.memory.write("orchestrator", "routing_history.json", [])

        # Make request that will fail (missing address)
        orchestrator.route_request("Show my account", track_memory=True)

        # Check error was tracked
        history = orchestrator.get_routing_history(limit=1)

        assert len(history) == 1
        assert history[0]["success"] == False
        assert "error" in history[0]

        print(f"\n✓ Error tracked:")
        print(f"  Success: {history[0]['success']}")
        print(f"  Error: {history[0].get('error', 'None')[:50]}...")

    def test_max_history_entries(self):
        """Test that history is capped at max entries."""
        orchestrator = OrchestratorAgent()

        # Clear history
        orchestrator.memory.write("orchestrator", "routing_history.json", [])

        # Add many entries (memory manager should cap at 1000)
        for i in range(15):
            orchestrator.route_request("BTC price", track_memory=True)

        history = orchestrator.get_routing_history(limit=1000)

        # Should have 15 entries (less than max)
        assert len(history) == 15

        print(f"\n✓ History tracking: {len(history)} entries")

    def test_routing_history_format(self):
        """Test that routing history has correct format."""
        orchestrator = OrchestratorAgent()

        # Clear and add one entry
        orchestrator.memory.write("orchestrator", "routing_history.json", [])
        orchestrator.route_request("BTC price", track_memory=True)

        history = orchestrator.get_routing_history(limit=1)
        entry = history[0]

        # Validate required fields
        assert "timestamp" in entry
        assert "request" in entry
        assert "intent" in entry
        assert "routed_to" in entry
        assert "response_time_ms" in entry
        assert "success" in entry

        print(f"\n✓ History entry format correct")

    def test_memory_stats(self):
        """Test getting memory statistics."""
        orchestrator = OrchestratorAgent()

        stats = orchestrator.memory.get_stats()

        assert "total_files" in stats
        assert "by_category" in stats
        assert "orchestrator" in stats["by_category"]

        print(f"\n✓ Memory stats:")
        print(f"  Total files: {stats['total_files']}")
        print(f"  Size: {stats['total_size_bytes']} bytes")
