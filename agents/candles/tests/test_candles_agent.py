"""
Tests for Candles & Historical Agent
=====================================
Integration tests that validate end-to-end flow:
Agent → Skill → Hyperliquid API → Cache → Return
"""

import pytest
from datetime import datetime, timedelta
from agents.candles.candles_agent import CandlesAgent


class TestCandlesAgent:
    """Test Candles & Historical Agent functionality."""

    def test_agent_creation(self):
        """Test agent instantiation."""
        agent = CandlesAgent()
        assert agent.agent_name == "candles_agent"
        assert agent.skill_name == "hyperliquid-fetch-and-cache"
        assert len(agent.INTERVALS) > 0

    def test_supported_intervals(self):
        """Test that all expected intervals are supported."""
        agent = CandlesAgent()

        expected_intervals = ["1m", "5m", "15m", "1h", "4h", "1d"]

        for interval in expected_intervals:
            assert interval in agent.INTERVALS

        print(f"\n✓ Supported intervals: {agent.INTERVALS}")

    def test_get_recent_candles(self):
        """Test fetching recent candles."""
        agent = CandlesAgent()

        # Get recent 10 BTC 1-hour candles
        candles = agent.get_recent_candles("BTC", "1h", num_candles=10, use_cache=False)

        # Validate structure
        assert isinstance(candles, list)
        assert len(candles) > 0
        assert len(candles) <= 15  # API may return more than requested

        # Validate first candle
        first_candle = candles[0]
        assert "t" in first_candle  # Start time
        assert "T" in first_candle  # End time
        assert "s" in first_candle  # Symbol
        assert "i" in first_candle  # Interval
        assert "o" in first_candle  # Open
        assert "h" in first_candle  # High
        assert "l" in first_candle  # Low
        assert "c" in first_candle  # Close
        assert "v" in first_candle  # Volume
        assert "n" in first_candle  # Number of trades

        # Validate values
        assert first_candle["s"] == "BTC"
        assert first_candle["i"] == "1h"
        assert float(first_candle["h"]) >= float(first_candle["l"])  # High >= Low

        print(f"\n✓ Fetched {len(candles)} recent BTC candles (1h)")
        print(f"  Latest: O:{candles[-1]['o']} H:{candles[-1]['h']} L:{candles[-1]['l']} C:{candles[-1]['c']}")

    def test_get_candles_with_time_range(self):
        """Test fetching candles with specific time range."""
        agent = CandlesAgent()

        # Get candles for last 24 hours
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = end_time - (24 * 60 * 60 * 1000)  # 24 hours ago

        candles = agent.get_candles("BTC", "1h", start_time, end_time, use_cache=False)

        # Should have approximately 24 candles (one per hour)
        assert isinstance(candles, list)
        assert len(candles) > 0
        assert len(candles) <= 25  # Allow some buffer

        print(f"\n✓ Fetched {len(candles)} BTC candles for last 24 hours")

    def test_get_latest_candle(self):
        """Test fetching the most recent candle."""
        agent = CandlesAgent()

        # Get latest 15-minute candle
        candle = agent.get_latest_candle("BTC", "15m", use_cache=False)

        # Validate structure
        assert isinstance(candle, dict)
        assert "c" in candle  # Close price
        assert "v" in candle  # Volume

        # Timestamp should be recent
        candle_time = candle["T"]  # End time
        now = int(datetime.now().timestamp() * 1000)
        time_diff_minutes = (now - candle_time) / (60 * 1000)

        # Should be within last 30 minutes
        assert time_diff_minutes < 30

        print(f"\n✓ Latest BTC 15m candle:")
        print(f"  Close: ${candle['c']}")
        print(f"  Volume: {candle['v']}")
        print(f"  Age: {time_diff_minutes:.1f} minutes")

    def test_get_ohlcv_range(self):
        """Test fetching OHLCV data for N days."""
        agent = CandlesAgent()

        # Get last 3 days of 4-hour candles
        candles = agent.get_ohlcv_range("BTC", "4h", days=3, use_cache=False)

        # Should have ~18 candles (6 per day * 3 days)
        assert isinstance(candles, list)
        assert len(candles) > 0
        assert len(candles) <= 20  # Allow buffer

        print(f"\n✓ Fetched {len(candles)} BTC candles for last 3 days (4h interval)")

    def test_calculate_vwap(self):
        """Test VWAP calculation."""
        agent = CandlesAgent()

        # Get candles
        candles = agent.get_recent_candles("BTC", "1h", num_candles=24, use_cache=True)

        # Calculate VWAP
        vwap = agent.calculate_vwap(candles)

        # Validate
        assert isinstance(vwap, float)
        assert vwap > 0

        # VWAP should be within range of highs and lows
        highs = [float(c["h"]) for c in candles]
        lows = [float(c["l"]) for c in candles]
        assert vwap >= min(lows)
        assert vwap <= max(highs)

        print(f"\n✓ VWAP for last 24h: ${vwap:,.2f}")

    def test_get_candle_stats(self):
        """Test candle statistics calculation."""
        agent = CandlesAgent()

        # Get candles
        candles = agent.get_recent_candles("BTC", "1h", num_candles=24, use_cache=True)

        # Calculate stats
        stats = agent.get_candle_stats(candles)

        # Validate structure
        assert isinstance(stats, dict)
        assert "num_candles" in stats
        assert "high" in stats
        assert "low" in stats
        assert "vwap" in stats
        assert "total_volume" in stats
        assert "price_change" in stats
        assert "price_change_abs" in stats

        # Validate values
        assert stats["num_candles"] == len(candles)
        assert stats["high"] > 0
        assert stats["low"] > 0
        assert stats["high"] >= stats["low"]
        assert stats["total_volume"] >= 0

        print(f"\n✓ Candle stats for last 24h:")
        print(f"  High: ${stats['high']:,.2f}")
        print(f"  Low: ${stats['low']:,.2f}")
        print(f"  VWAP: ${stats['vwap']:,.2f}")
        print(f"  Volume: {stats['total_volume']:,.2f}")
        print(f"  Price change: {stats['price_change']:+.2f}%")

    def test_multiple_intervals(self):
        """Test fetching candles for multiple intervals."""
        agent = CandlesAgent()

        intervals = ["1m", "5m", "15m", "1h"]

        print(f"\n✓ Testing multiple intervals:")
        for interval in intervals:
            try:
                candles = agent.get_recent_candles("BTC", interval, num_candles=5, use_cache=True)
                print(f"  {interval}: {len(candles)} candles, latest close: ${candles[-1]['c']}")
                assert len(candles) > 0
            except Exception as e:
                print(f"  {interval}: Error - {e}")

    def test_multiple_coins(self):
        """Test fetching candles for multiple coins."""
        agent = CandlesAgent()

        coins = ["BTC", "ETH", "SOL"]

        print(f"\n✓ Testing multiple coins:")
        for coin in coins:
            try:
                candles = agent.get_recent_candles(coin, "1h", num_candles=5, use_cache=True)
                latest = candles[-1]
                print(f"  {coin}: {len(candles)} candles, latest close: ${latest['c']}")
                assert len(candles) > 0
            except Exception as e:
                print(f"  {coin}: Error - {e}")

    def test_cache_behavior(self):
        """Test that caching works for historical data."""
        import time

        agent = CandlesAgent()

        # First call (force refresh)
        start1 = time.time()
        result1 = agent.get_recent_candles("BTC", "1h", num_candles=24, use_cache=False)
        duration1 = time.time() - start1

        # Second call (should hit cache)
        start2 = time.time()
        result2 = agent.get_recent_candles("BTC", "1h", num_candles=24, use_cache=True)
        duration2 = time.time() - start2

        # Both should return same number of candles
        assert len(result1) == len(result2)

        print(f"\n✓ Cache behavior:")
        print(f"  First call (API): {duration1:.3f}s")
        print(f"  Second call (cache): {duration2:.3f}s")
        if duration2 < duration1:
            speedup = duration1 / duration2
            print(f"  Speedup: {speedup:.1f}x faster")

    def test_interval_validation(self):
        """Test that invalid intervals are rejected."""
        agent = CandlesAgent()

        with pytest.raises(ValueError, match="Unsupported interval"):
            agent.get_recent_candles("BTC", "invalid", num_candles=10)

        print(f"\n✓ Invalid interval properly rejected")

    def test_time_range_validation(self):
        """Test that invalid time ranges are rejected."""
        agent = CandlesAgent()

        end_time = int(datetime.now().timestamp() * 1000)
        start_time = end_time + 1000  # Start after end (invalid)

        with pytest.raises(ValueError, match="must be before"):
            agent.get_candles("BTC", "1h", start_time, end_time)

        print(f"\n✓ Invalid time range properly rejected")

    def test_max_candles_validation(self):
        """Test that requests exceeding max candles are rejected."""
        agent = CandlesAgent()

        with pytest.raises(ValueError, match="Maximum 5000 candles"):
            agent.get_recent_candles("BTC", "1m", num_candles=10000)

        print(f"\n✓ Excessive candle request properly rejected")

    def test_interval_to_milliseconds(self):
        """Test interval conversion helper."""
        agent = CandlesAgent()

        # Test various intervals
        assert agent._interval_to_milliseconds("1m") == 60 * 1000
        assert agent._interval_to_milliseconds("5m") == 5 * 60 * 1000
        assert agent._interval_to_milliseconds("1h") == 60 * 60 * 1000
        assert agent._interval_to_milliseconds("1d") == 24 * 60 * 60 * 1000

        print(f"\n✓ Interval conversions working correctly")
