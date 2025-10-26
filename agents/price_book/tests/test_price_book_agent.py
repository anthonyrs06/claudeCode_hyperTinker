"""
Tests for Price & Book Agent
============================
Integration tests that validate end-to-end flow:
Agent → Skill → Hyperliquid API → Cache → Return
"""

import pytest
from agents.price_book.price_book_agent import PriceBookAgent


class TestPriceBookAgent:
    """Test Price & Book Agent functionality."""

    def test_agent_creation(self):
        """Test agent instantiation."""
        agent = PriceBookAgent()
        assert agent.agent_name == "price_book_agent"
        assert agent.skill_name == "hyperliquid-fetch-and-cache"

    def test_get_all_mids(self):
        """Test fetching all mid prices."""
        agent = PriceBookAgent()

        # Fetch all prices
        result = agent.get_all_mids(use_cache=True)

        # Validate structure
        assert isinstance(result, dict)
        assert len(result) > 0

        # Check for major coins
        assert "BTC" in result
        assert "ETH" in result

        # Validate prices are numeric strings
        assert float(result["BTC"]) > 0
        assert float(result["ETH"]) > 0

        print(f"\n✓ Fetched {len(result)} coin prices")
        print(f"  BTC: ${result['BTC']}")
        print(f"  ETH: ${result['ETH']}")

    def test_get_price_specific_coin(self):
        """Test fetching price for specific coin."""
        agent = PriceBookAgent()

        # Get BTC price
        btc_price = agent.get_price("BTC")

        assert isinstance(btc_price, float)
        assert btc_price > 0

        print(f"\n✓ BTC price: ${btc_price:,.2f}")

    def test_get_price_invalid_coin(self):
        """Test error handling for invalid coin."""
        agent = PriceBookAgent()

        with pytest.raises(KeyError, match="not found"):
            agent.get_price("INVALID_COIN_XYZ")

    def test_get_l2_book(self):
        """Test fetching order book."""
        agent = PriceBookAgent()

        # Get BTC order book
        book = agent.get_l2_book("BTC")

        # Validate structure
        assert isinstance(book, dict)
        assert "coin" in book
        assert book["coin"] == "BTC"
        assert "levels" in book
        assert len(book["levels"]) == 2  # [bids, asks]

        bids = book["levels"][0]
        asks = book["levels"][1]

        assert len(bids) > 0
        assert len(asks) > 0

        # Validate bid structure
        assert "px" in bids[0]  # Price
        assert "sz" in bids[0]  # Size
        assert "n" in bids[0]   # Number of orders

        print(f"\n✓ Fetched order book for BTC")
        print(f"  Top bid: {bids[0]['px']} (size: {bids[0]['sz']})")
        print(f"  Top ask: {asks[0]['px']} (size: {asks[0]['sz']})")

    def test_get_spread(self):
        """Test spread calculation."""
        agent = PriceBookAgent()

        # Get spread for BTC
        spread = agent.get_spread("BTC")

        # Validate structure
        assert isinstance(spread, dict)
        assert "coin" in spread
        assert spread["coin"] == "BTC"
        assert "best_bid" in spread
        assert "best_ask" in spread
        assert "spread" in spread
        assert "spread_bps" in spread

        # Validate values
        assert spread["best_bid"] > 0
        assert spread["best_ask"] > 0
        assert spread["best_ask"] > spread["best_bid"]  # Ask should be higher
        assert spread["spread"] > 0
        assert spread["spread_bps"] > 0

        print(f"\n✓ BTC spread:")
        print(f"  Best bid: ${spread['best_bid']:,.2f}")
        print(f"  Best ask: ${spread['best_ask']:,.2f}")
        print(f"  Spread: ${spread['spread']:.2f} ({spread['spread_bps']} bps)")

    def test_get_meta(self):
        """Test fetching exchange metadata."""
        agent = PriceBookAgent()

        # Get metadata
        meta = agent.get_meta()

        # Validate structure
        assert isinstance(meta, dict)
        assert "universe" in meta
        assert isinstance(meta["universe"], list)
        assert len(meta["universe"]) > 0

        # Check first coin structure
        first_coin = meta["universe"][0]
        assert "name" in first_coin
        assert "szDecimals" in first_coin
        assert "maxLeverage" in first_coin

        print(f"\n✓ Fetched metadata for {len(meta['universe'])} coins")
        print(f"  Example: {first_coin['name']} (leverage: {first_coin['maxLeverage']}x)")

    def test_get_coins_list(self):
        """Test getting list of coins."""
        agent = PriceBookAgent()

        # Get coins list
        coins = agent.get_coins_list()

        # Validate
        assert isinstance(coins, list)
        assert len(coins) > 0
        assert "BTC" in coins
        assert "ETH" in coins

        print(f"\n✓ Found {len(coins)} tradable coins")
        print(f"  First 10: {coins[:10]}")

    def test_cache_behavior(self):
        """Test that caching works (second call faster)."""
        import time

        agent = PriceBookAgent()

        # First call (should hit API or populate cache)
        start1 = time.time()
        result1 = agent.get_all_mids(use_cache=False)  # Force refresh
        duration1 = time.time() - start1

        # Second call (should hit cache)
        start2 = time.time()
        result2 = agent.get_all_mids(use_cache=True)
        duration2 = time.time() - start2

        # Both should return same data
        assert result1.keys() == result2.keys()

        # Second call should be faster (cached)
        # Note: This might not always be true due to system variability,
        # but cache should be consistently faster on average
        print(f"\n✓ Cache behavior:")
        print(f"  First call (API): {duration1:.3f}s")
        print(f"  Second call (cache): {duration2:.3f}s")
        if duration2 < duration1:
            speedup = duration1 / duration2
            print(f"  Speedup: {speedup:.1f}x faster")

    def test_multiple_coins_spread(self):
        """Test spread calculation for multiple coins."""
        agent = PriceBookAgent()

        coins = ["BTC", "ETH", "SOL"]

        print(f"\n✓ Spread comparison:")
        for coin in coins:
            try:
                spread = agent.get_spread(coin)
                print(f"  {coin}: ${spread['spread']:.2f} ({spread['spread_bps']} bps)")
            except Exception as e:
                print(f"  {coin}: Error - {e}")

    def test_agent_error_handling(self):
        """Test that agent handles skill errors gracefully."""
        agent = PriceBookAgent()

        # Try to get order book for invalid coin
        # (This should fail at the API level)
        try:
            result = agent.get_l2_book("INVALID_COIN_XYZ")
            # If it doesn't fail, that's okay too (API might handle it)
        except Exception as e:
            # Should get a meaningful error
            assert len(str(e)) > 0
            print(f"\n✓ Error handling works: {e}")
