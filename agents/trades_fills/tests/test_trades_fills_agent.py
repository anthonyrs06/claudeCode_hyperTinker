"""
Tests for Trades & Fills Agent
===============================
Integration tests that validate end-to-end flow:
Agent → Skill → Hyperliquid API → Cache → Return

Note: These tests use real API calls. Some tests may return empty
results if the test address has no trading activity.
"""

import pytest
from agents.trades_fills.trades_fills_agent import TradesFillsAgent


# Test user address (public address with trading activity)
# Using a known address from Hyperliquid leaderboard
TEST_USER_ADDRESS = "0x0d1d9635d0640821d15e323ac8e92d6ff22d9581"


class TestTradesFillsAgent:
    """Test Trades & Fills Agent functionality."""

    def test_agent_creation(self):
        """Test agent instantiation."""
        agent = TradesFillsAgent()
        assert agent.agent_name == "trades_fills_agent"
        assert agent.skill_name == "hyperliquid-fetch-and-cache"

    def test_get_user_fills(self):
        """Test fetching user fills."""
        agent = TradesFillsAgent()

        # Fetch fills for test address
        result = agent.get_user_fills(TEST_USER_ADDRESS, use_cache=True)

        # Validate structure
        assert isinstance(result, list)

        # If fills exist, validate structure
        if len(result) > 0:
            first_fill = result[0]
            assert "coin" in first_fill
            assert "px" in first_fill
            assert "sz" in first_fill
            assert "side" in first_fill
            assert "time" in first_fill

            print(f"\n✓ Fetched {len(result)} fills for user")
            print(f"  Most recent: {first_fill['coin']} @ ${first_fill['px']}")
        else:
            print(f"\n✓ No fills found for test address (address may be inactive)")

    # Note: Skipping test_get_recent_trades - Hyperliquid API does not provide
    # a public endpoint for recent market trades

    def test_get_open_orders(self):
        """Test fetching open orders."""
        agent = TradesFillsAgent()

        # Get open orders
        result = agent.get_open_orders(TEST_USER_ADDRESS, use_cache=False)

        # Validate structure
        assert isinstance(result, list)

        # If orders exist, validate structure
        if len(result) > 0:
            first_order = result[0]
            assert "coin" in first_order
            assert "side" in first_order
            assert "limitPx" in first_order
            assert "sz" in first_order
            assert "oid" in first_order

            print(f"\n✓ Found {len(result)} open orders")
            print(f"  First: {first_order['side']} {first_order['sz']} {first_order['coin']} @ ${first_order['limitPx']}")
        else:
            print(f"\n✓ No open orders for test address")

    def test_get_user_funding(self):
        """Test fetching user funding payments."""
        agent = TradesFillsAgent()

        # Get funding payments
        result = agent.get_user_funding(TEST_USER_ADDRESS, use_cache=True)

        # Validate structure
        assert isinstance(result, list)

        # If funding exists, validate structure
        if len(result) > 0:
            first_funding = result[0]
            assert "coin" in first_funding
            assert "time" in first_funding

            print(f"\n✓ Fetched {len(result)} funding payments")
            print(f"  Most recent: {first_funding['coin']}")
        else:
            print(f"\n✓ No funding payments for test address")

    def test_get_trade_summary(self):
        """Test trade summary calculation."""
        agent = TradesFillsAgent()

        # Get summary
        summary = agent.get_trade_summary(TEST_USER_ADDRESS)

        # Validate structure
        assert isinstance(summary, dict)
        assert "total_fills" in summary
        assert "open_orders" in summary
        assert "recent_coins_traded" in summary
        assert "last_trade_time" in summary

        # Validate types
        assert isinstance(summary["total_fills"], int)
        assert isinstance(summary["open_orders"], int)
        assert isinstance(summary["recent_coins_traded"], list)
        assert isinstance(summary["last_trade_time"], int)

        print(f"\n✓ Trade summary:")
        print(f"  Total fills: {summary['total_fills']}")
        print(f"  Open orders: {summary['open_orders']}")
        print(f"  Coins traded: {summary['recent_coins_traded'][:5]}")

    def test_get_fills_by_coin(self):
        """Test filtering fills by coin."""
        agent = TradesFillsAgent()

        # Get all fills first
        all_fills = agent.get_user_fills(TEST_USER_ADDRESS, use_cache=True)

        if len(all_fills) > 0:
            # Get first coin from fills
            test_coin = all_fills[0]["coin"]

            # Filter by that coin
            filtered_fills = agent.get_fills_by_coin(TEST_USER_ADDRESS, test_coin)

            # Validate all fills are for that coin
            assert isinstance(filtered_fills, list)
            assert all(fill["coin"] == test_coin for fill in filtered_fills)

            print(f"\n✓ Filtered {len(filtered_fills)} fills for {test_coin}")
        else:
            print(f"\n✓ No fills to filter (test address inactive)")

    def test_get_pnl_summary(self):
        """Test PnL summary calculation."""
        agent = TradesFillsAgent()

        # Get PnL summary
        pnl = agent.get_pnl_summary(TEST_USER_ADDRESS)

        # Validate structure
        assert isinstance(pnl, dict)
        assert "total_closed_pnl" in pnl
        assert "total_fees" in pnl
        assert "net_pnl" in pnl
        assert "num_trades" in pnl

        # Validate types
        assert isinstance(pnl["total_closed_pnl"], (int, float))
        assert isinstance(pnl["total_fees"], (int, float))
        assert isinstance(pnl["net_pnl"], (int, float))
        assert isinstance(pnl["num_trades"], int)

        # Validate calculation
        expected_net = round(pnl["total_closed_pnl"] - pnl["total_fees"], 2)
        assert pnl["net_pnl"] == expected_net

        print(f"\n✓ PnL summary:")
        print(f"  Closed PnL: ${pnl['total_closed_pnl']:.2f}")
        print(f"  Total fees: ${pnl['total_fees']:.2f}")
        print(f"  Net PnL: ${pnl['net_pnl']:.2f}")
        print(f"  Trades: {pnl['num_trades']}")

    def test_cache_behavior(self):
        """Test that caching works for user fills."""
        import time

        agent = TradesFillsAgent()

        # First call (force refresh)
        start1 = time.time()
        result1 = agent.get_user_fills(TEST_USER_ADDRESS, use_cache=False)
        duration1 = time.time() - start1

        # Second call (should hit cache)
        start2 = time.time()
        result2 = agent.get_user_fills(TEST_USER_ADDRESS, use_cache=True)
        duration2 = time.time() - start2

        # Both should return same data
        assert len(result1) == len(result2)

        print(f"\n✓ Cache behavior:")
        print(f"  First call (API): {duration1:.3f}s")
        print(f"  Second call (cache): {duration2:.3f}s")
        if duration2 < duration1:
            speedup = duration1 / duration2
            print(f"  Speedup: {speedup:.1f}x faster")

    def test_multiple_user_queries(self):
        """Test multiple queries for same user (cache performance)."""
        agent = TradesFillsAgent()

        print(f"\n✓ Testing multiple user queries:")

        # First query - fills
        fills = agent.get_user_fills(TEST_USER_ADDRESS, use_cache=True)
        print(f"  Fills: {len(fills)}")

        # Second query - funding (should use separate cache)
        funding = agent.get_user_funding(TEST_USER_ADDRESS, use_cache=True)
        print(f"  Funding payments: {len(funding)}")

        # Third query - open orders (typically no cache)
        orders = agent.get_open_orders(TEST_USER_ADDRESS, use_cache=False)
        print(f"  Open orders: {len(orders)}")

    def test_error_handling_invalid_address(self):
        """Test error handling for invalid user address."""
        agent = TradesFillsAgent()

        # This might not fail (API might return empty list)
        # but at minimum shouldn't crash
        try:
            result = agent.get_user_fills("0xinvalid", use_cache=False)
            assert isinstance(result, list)
            print(f"\n✓ Invalid address handled gracefully (returned {len(result)} fills)")
        except Exception as e:
            # Expected to fail with some error
            assert len(str(e)) > 0
            print(f"\n✓ Invalid address properly rejected: {e}")

    # Note: Removed test_error_handling_invalid_coin - not applicable since
    # we don't have a coin-based trades endpoint
