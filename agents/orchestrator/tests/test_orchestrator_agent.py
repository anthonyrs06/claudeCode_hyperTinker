"""
Tests for Orchestrator Agent
=============================
Integration tests that validate request routing to specialized agents.
"""

import pytest
from agents.orchestrator.orchestrator_agent import OrchestratorAgent


# Test user address
TEST_USER_ADDRESS = "0x0d1d9635d0640821d15e323ac8e92d6ff22d9581"


class TestOrchestratorAgent:
    """Test Orchestrator Agent routing functionality."""

    def test_agent_creation(self):
        """Test orchestrator instantiation."""
        orchestrator = OrchestratorAgent()
        assert orchestrator.agent_name == "orchestrator_agent"
        assert orchestrator.price_agent is not None
        assert orchestrator.trades_agent is not None
        assert orchestrator.candles_agent is not None
        assert orchestrator.account_agent is not None
        assert orchestrator.error_recovery_agent is not None

        print(f"\n✓ Orchestrator created with 5 specialized agents")

    def test_route_price_request_specific_coin(self):
        """Test routing price request for specific coin."""
        orchestrator = OrchestratorAgent()

        result = orchestrator.route_request("What is the BTC price?")

        assert result["success"] == True
        assert result["agent"] == "price_book"
        assert result["action"] == "get_price"
        assert result["result"]["coin"] == "BTC"
        assert result["result"]["price"] > 0

        print(f"\n✓ Routed BTC price request")
        print(f"  Price: ${result['result']['price']:,.2f}")

    def test_route_price_request_all_coins(self):
        """Test routing request for all prices."""
        orchestrator = OrchestratorAgent()

        result = orchestrator.route_request("Show me all mid prices")

        assert result["success"] == True
        assert result["agent"] == "price_book"
        assert result["action"] == "get_all_mids"
        assert isinstance(result["result"], dict)
        assert len(result["result"]) > 0

        print(f"\n✓ Routed all prices request")
        print(f"  Fetched {result['metadata']['num_coins']} coins")

    def test_route_orderbook_request(self):
        """Test routing order book request."""
        orchestrator = OrchestratorAgent()

        result = orchestrator.route_request("Show me ETH order book")

        assert result["success"] == True
        assert result["agent"] == "price_book"
        assert result["action"] == "get_l2_book"
        assert result["result"]["coin"] == "ETH"
        assert "levels" in result["result"]

        print(f"\n✓ Routed order book request for ETH")

    def test_route_spread_request(self):
        """Test routing spread request."""
        orchestrator = OrchestratorAgent()

        result = orchestrator.route_request("What is the bid-ask spread for SOL?")

        assert result["success"] == True
        assert result["agent"] == "price_book"
        assert result["action"] == "get_spread"
        assert result["result"]["coin"] == "SOL"
        assert "spread" in result["result"]

        print(f"\n✓ Routed spread request for SOL")
        print(f"  Spread: {result['result']['spread_bps']} bps")

    def test_route_candles_request(self):
        """Test routing candles request."""
        orchestrator = OrchestratorAgent()

        result = orchestrator.route_request("Show me BTC 1h candles")

        assert result["success"] == True
        assert result["agent"] == "candles"
        assert result["action"] == "get_recent_candles"
        assert "candles" in result["result"]
        assert "stats" in result["result"]
        assert result["metadata"]["interval"] == "1h"

        print(f"\n✓ Routed candles request")
        print(f"  Interval: {result['metadata']['interval']}")
        print(f"  Candles: {result['metadata']['num_candles']}")

    def test_route_account_request(self):
        """Test routing account request with address."""
        orchestrator = OrchestratorAgent()

        request = f"Show account summary for {TEST_USER_ADDRESS}"
        result = orchestrator.route_request(request)

        assert result["success"] == True
        assert result["agent"] == "account"
        assert result["action"] == "get_account_summary"
        assert "account_value" in result["result"]

        print(f"\n✓ Routed account request")
        print(f"  Account value: ${result['result']['account_value']:.2f}")

    def test_route_positions_request(self):
        """Test routing positions request."""
        orchestrator = OrchestratorAgent()

        request = f"Show positions for {TEST_USER_ADDRESS}"
        result = orchestrator.route_request(request)

        assert result["success"] == True
        assert result["agent"] == "account"
        assert result["action"] == "get_positions"
        assert isinstance(result["result"], list)

        print(f"\n✓ Routed positions request")
        print(f"  Positions: {result['metadata']['num_positions']}")

    def test_route_trades_request(self):
        """Test routing trades request with address."""
        orchestrator = OrchestratorAgent()

        request = f"Show trade summary for {TEST_USER_ADDRESS}"
        result = orchestrator.route_request(request)

        assert result["success"] == True
        assert result["agent"] == "trades_fills"
        assert result["action"] == "get_trade_summary"
        assert "total_fills" in result["result"]

        print(f"\n✓ Routed trades request")
        print(f"  Total fills: {result['result']['total_fills']}")

    def test_route_meta_request(self):
        """Test routing metadata request."""
        orchestrator = OrchestratorAgent()

        result = orchestrator.route_request("List all available coins")

        assert result["success"] == True
        assert result["agent"] == "price_book"
        assert result["action"] == "get_coins_list"
        assert isinstance(result["result"], list)
        assert len(result["result"]) > 0

        print(f"\n✓ Routed coins list request")
        print(f"  Available coins: {result['metadata']['num_coins']}")

    def test_missing_address_for_account(self):
        """Test error handling when address missing for account query."""
        orchestrator = OrchestratorAgent()

        result = orchestrator.route_request("Show my account")

        assert result["success"] == False
        assert "address required" in result["error"].lower()

        print(f"\n✓ Properly rejected account query without address")

    def test_missing_address_for_trades(self):
        """Test error handling when address missing for trade query."""
        orchestrator = OrchestratorAgent()

        result = orchestrator.route_request("Show my trades")

        assert result["success"] == False
        assert "address required" in result["error"].lower()

        print(f"\n✓ Properly rejected trade query without address")

    def test_unknown_intent(self):
        """Test handling of unknown intent."""
        orchestrator = OrchestratorAgent()

        result = orchestrator.route_request("Hello world")

        assert result["success"] == False
        assert "Unable to determine intent" in result["error"]

        print(f"\n✓ Properly handled unknown intent")

    def test_extract_coin(self):
        """Test coin extraction from request."""
        orchestrator = OrchestratorAgent()

        coin = orchestrator._extract_coin("What is the BTC price?")
        assert coin == "BTC"

        coin = orchestrator._extract_coin("Show me ETH orderbook")
        assert coin == "ETH"

        coin = orchestrator._extract_coin("no coin here")
        assert coin is None

        print(f"\n✓ Coin extraction working")

    def test_extract_address(self):
        """Test address extraction from request."""
        orchestrator = OrchestratorAgent()

        address = orchestrator._extract_address(f"Check {TEST_USER_ADDRESS}")
        assert address == TEST_USER_ADDRESS

        address = orchestrator._extract_address("no address here")
        assert address is None

        print(f"\n✓ Address extraction working")

    def test_classify_intent(self):
        """Test intent classification."""
        orchestrator = OrchestratorAgent()

        assert orchestrator._classify_intent("what is the price") == "price"
        assert orchestrator._classify_intent("show orderbook") == "book"
        assert orchestrator._classify_intent("get candles") == "candles"
        assert orchestrator._classify_intent("account balance") == "account"
        assert orchestrator._classify_intent("my trades") == "trades"
        assert orchestrator._classify_intent("random text") == "unknown"

        print(f"\n✓ Intent classification working")

    def test_get_routing_stats(self):
        """Test getting routing statistics."""
        orchestrator = OrchestratorAgent()

        stats = orchestrator.get_routing_stats()

        assert "available_agents" in stats
        assert "routing_patterns" in stats
        assert len(stats["available_agents"]) == 5

        print(f"\n✓ Routing stats:")
        print(f"  Agents: {len(stats['available_agents'])}")
        print(f"  Logic: {stats['routing_logic']}")

    def test_multiple_requests_sequence(self):
        """Test handling multiple requests in sequence."""
        orchestrator = OrchestratorAgent()

        # Request 1: Price
        result1 = orchestrator.route_request("BTC price")
        assert result1["success"] == True
        assert result1["agent"] == "price_book"

        # Request 2: Candles
        result2 = orchestrator.route_request("SOL 4h candles")
        assert result2["success"] == True
        assert result2["agent"] == "candles"
        assert result2["metadata"]["interval"] == "4h"

        # Request 3: Meta
        result3 = orchestrator.route_request("list coins")
        assert result3["success"] == True
        assert result3["agent"] == "price_book"
        assert result3["action"] == "get_coins_list"

        print(f"\n✓ Handled 3 sequential requests successfully")

    def test_error_recovery_integration(self):
        """Test that errors are handled via error recovery agent."""
        orchestrator = OrchestratorAgent()

        # Force an error by requesting invalid coin (will fail at some point)
        # The orchestrator should catch and analyze via error recovery
        try:
            result = orchestrator.route_request("Show INVALIDCOIN123 price")
            # May or may not error depending on how agents handle it
            # But should return a valid response structure
            assert "success" in result or "error" in result
            print(f"\n✓ Error handling working (result returned)")
        except Exception as e:
            # Should be caught by orchestrator
            pytest.fail(f"Orchestrator should catch errors, got: {e}")
