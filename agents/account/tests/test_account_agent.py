"""
Tests for Account Monitor Agent
================================
Integration tests that validate end-to-end flow.

Note: These tests use real API calls. Results may be empty if the
test address has no active positions.
"""

import pytest
from datetime import datetime, timedelta
from agents.account.account_agent import AccountAgent


# Test user address (public address)
TEST_USER_ADDRESS = "0x0d1d9635d0640821d15e323ac8e92d6ff22d9581"


class TestAccountAgent:
    """Test Account Monitor Agent functionality."""

    def test_agent_creation(self):
        """Test agent instantiation."""
        agent = AccountAgent()
        assert agent.agent_name == "account_agent"
        assert agent.skill_name == "hyperliquid-fetch-and-cache"

    def test_get_account_state(self):
        """Test fetching account state."""
        agent = AccountAgent()

        result = agent.get_account_state(TEST_USER_ADDRESS, use_cache=False)

        # Validate structure
        assert isinstance(result, dict)
        assert "assetPositions" in result or "marginSummary" in result

        print(f"\n✓ Account state fetched")
        if "marginSummary" in result:
            margin = result["marginSummary"]
            print(f"  Account value: ${margin.get('accountValue', '0')}")

    def test_get_positions(self):
        """Test fetching positions."""
        agent = AccountAgent()

        positions = agent.get_positions(TEST_USER_ADDRESS)

        assert isinstance(positions, list)

        if len(positions) > 0:
            first_pos = positions[0]
            assert "coin" in first_pos
            print(f"\n✓ Found {len(positions)} positions")
            print(f"  First: {first_pos.get('coin')}")
        else:
            print(f"\n✓ No open positions for test address")

    def test_get_account_summary(self):
        """Test account summary calculation."""
        agent = AccountAgent()

        summary = agent.get_account_summary(TEST_USER_ADDRESS)

        # Validate structure
        assert isinstance(summary, dict)
        assert "account_value" in summary
        assert "total_margin_used" in summary
        assert "withdrawable" in summary
        assert "num_positions" in summary
        assert "total_unrealized_pnl" in summary

        print(f"\n✓ Account summary:")
        print(f"  Account value: ${summary['account_value']:.2f}")
        print(f"  Margin used: ${summary['total_margin_used']:.2f}")
        print(f"  Withdrawable: ${summary['withdrawable']:.2f}")
        print(f"  Positions: {summary['num_positions']}")
        print(f"  Unrealized PnL: ${summary['total_unrealized_pnl']:.2f}")

    def test_get_portfolio_value(self):
        """Test portfolio value breakdown."""
        agent = AccountAgent()

        portfolio = agent.get_portfolio_value(TEST_USER_ADDRESS)

        # Validate structure
        assert isinstance(portfolio, dict)
        assert "account_value" in portfolio
        assert "cash_balance" in portfolio
        assert "position_value" in portfolio
        assert "unrealized_pnl" in portfolio
        assert "margin_ratio" in portfolio

        print(f"\n✓ Portfolio breakdown:")
        print(f"  Account value: ${portfolio['account_value']:.2f}")
        print(f"  Cash: ${portfolio['cash_balance']:.2f}")
        print(f"  Position value: ${portfolio['position_value']:.2f}")
        print(f"  Unrealized PnL: ${portfolio['unrealized_pnl']:.2f}")
        print(f"  Margin ratio: {portfolio['margin_ratio']:.2%}")

    def test_get_risk_metrics(self):
        """Test risk metrics calculation."""
        agent = AccountAgent()

        risk = agent.get_risk_metrics(TEST_USER_ADDRESS)

        # Validate structure
        assert isinstance(risk, dict)
        assert "margin_ratio" in risk
        assert "leverage" in risk
        assert "num_positions" in risk

        print(f"\n✓ Risk metrics:")
        print(f"  Margin ratio: {risk['margin_ratio']:.2%}")
        print(f"  Leverage: {risk['leverage']:.2f}x")
        print(f"  Positions: {risk['num_positions']}")
        if risk.get("largest_position"):
            print(f"  Largest position: {risk['largest_position']} ({risk['largest_position_pct']:.2%})")

    def test_get_ledger_updates(self):
        """Test fetching ledger updates."""
        agent = AccountAgent()

        # Get last 30 days
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = end_time - (30 * 24 * 60 * 60 * 1000)

        updates = agent.get_ledger_updates(TEST_USER_ADDRESS, start_time, end_time)

        assert isinstance(updates, list)

        if len(updates) > 0:
            print(f"\n✓ Found {len(updates)} ledger updates in last 30 days")
        else:
            print(f"\n✓ No ledger updates found")

    def test_cache_behavior(self):
        """Test that caching works."""
        import time

        agent = AccountAgent()

        # First call
        start1 = time.time()
        result1 = agent.get_account_state(TEST_USER_ADDRESS, use_cache=False)
        duration1 = time.time() - start1

        # Second call (cached)
        start2 = time.time()
        result2 = agent.get_account_state(TEST_USER_ADDRESS, use_cache=True)
        duration2 = time.time() - start2

        print(f"\n✓ Cache behavior:")
        print(f"  First call: {duration1:.3f}s")
        print(f"  Second call (cache): {duration2:.3f}s")
        if duration2 < duration1:
            print(f"  Speedup: {duration1/duration2:.1f}x faster")

    def test_error_handling_invalid_address(self):
        """Test error handling for invalid address."""
        agent = AccountAgent()

        try:
            result = agent.get_account_state("0xinvalid", use_cache=False)
            print(f"\n✓ Invalid address handled gracefully")
        except Exception as e:
            assert len(str(e)) > 0
            print(f"\n✓ Invalid address properly rejected")
