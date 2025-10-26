"""
Candles & Historical Agent
===========================
Lightweight wrapper for candlestick (OHLCV) data.

Design Principle:
- Agent is ~20 lines per method (just method stubs)
- All heavy lifting delegated to hyperliquid-fetch-and-cache skill
- Skill handles: HTTP calls, caching, validation, rate limiting
- Token usage: ~2K per request (just coordination, not execution)

Architecture:
    User Request
        ↓
    Candles Agent (this file - lightweight)
        ↓
    invoke_skill("hyperliquid-fetch-and-cache", params)
        ↓
    Skill Script (executed outside context - 0 tokens)
        ↓
    Hyperliquid API + Memory Cache

Supported Intervals:
    "1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "8h", "12h", "1d", "3d", "1w", "1M"

Limitations:
    - Maximum 5000 candles per request
    - Historical data cached for 24 hours (immutable)
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from agents.base_agent import BaseAgent


class CandlesAgent(BaseAgent):
    """
    Fetches candlestick (OHLCV) data via Skills.

    This agent is SIMPLE - just invokes skills.
    Heavy lifting in scripts (executed outside context).
    """

    # Supported time intervals
    INTERVALS = ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "8h", "12h", "1d", "3d", "1w", "1M"]

    def __init__(self):
        super().__init__(agent_name="candles_agent")
        self.skill_name = "hyperliquid-fetch-and-cache"

    def get_candles(
        self,
        coin: str,
        interval: str,
        start_time: int,
        end_time: int,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get candlestick data for a specific time range.

        Args:
            coin: Coin symbol (e.g., "BTC")
            interval: Time interval (1m, 5m, 15m, 1h, 4h, 1d, etc.)
            start_time: Start timestamp in milliseconds
            end_time: End timestamp in milliseconds
            use_cache: Whether to use cached data (TTL: 24h for historical)

        Returns:
            List of candles:
            [
                {
                    "t": 1698765432000,  # Start time
                    "T": 1698765492000,  # End time
                    "s": "BTC",          # Symbol
                    "i": "1m",           # Interval
                    "o": "45000.0",      # Open
                    "h": "45100.0",      # High
                    "l": "44900.0",      # Low
                    "c": "45050.0",      # Close
                    "v": "123.45",       # Volume
                    "n": 42              # Number of trades
                },
                ...
            ]

        Raises:
            ValueError: If interval not supported or time range invalid

        Token usage: ~2K (just skill invocation)
        """
        # Validate interval
        if interval not in self.INTERVALS:
            raise ValueError(f"Unsupported interval '{interval}'. Must be one of: {', '.join(self.INTERVALS)}")

        # Validate time range
        if start_time >= end_time:
            raise ValueError(f"start_time ({start_time}) must be before end_time ({end_time})")

        cache_config = {"enabled": use_cache, "ttl_seconds": 86400}  # 24 hours for historical
        if not use_cache:
            cache_config["force_refresh"] = True

        result = self.invoke_skill(self.skill_name, {
            "endpoint": "candleSnapshot",
            "params": {
                "coin": coin,
                "interval": interval,
                "startTime": start_time,
                "endTime": end_time
            },
            "cache_config": cache_config
        })

        self.validate_response(result)

        if not result["success"]:
            raise Exception(f"Failed to fetch candles: {result.get('error')}")

        return result["data"]

    def get_recent_candles(
        self,
        coin: str,
        interval: str,
        num_candles: int = 100,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get recent N candles for a coin.

        Args:
            coin: Coin symbol (e.g., "BTC")
            interval: Time interval (1m, 5m, 15m, 1h, 4h, 1d, etc.)
            num_candles: Number of recent candles to fetch (max 5000)
            use_cache: Whether to use cached data

        Returns:
            List of recent candles (most recent last)

        Token usage: ~2K
        """
        # Validate interval first
        if interval not in self.INTERVALS:
            raise ValueError(f"Unsupported interval '{interval}'. Must be one of: {', '.join(self.INTERVALS)}")

        if num_candles > 5000:
            raise ValueError("Maximum 5000 candles per request")

        # Calculate time range based on interval
        interval_ms = self._interval_to_milliseconds(interval)
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = end_time - (interval_ms * num_candles)

        return self.get_candles(coin, interval, start_time, end_time, use_cache)

    def get_latest_candle(
        self,
        coin: str,
        interval: str,
        use_cache: bool = False
    ) -> Dict[str, Any]:
        """
        Get the most recent candle for a coin.

        Args:
            coin: Coin symbol (e.g., "BTC")
            interval: Time interval (1m, 5m, 15m, 1h, 4h, 1d, etc.)
            use_cache: Whether to use cached data (typically False for latest)

        Returns:
            Single most recent candle

        Token usage: ~2K
        """
        candles = self.get_recent_candles(coin, interval, num_candles=1, use_cache=use_cache)

        if not candles:
            raise ValueError(f"No candles available for {coin}")

        return candles[-1]  # Last candle is most recent

    def get_ohlcv_range(
        self,
        coin: str,
        interval: str,
        days: int = 7,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get OHLCV data for the last N days.

        Args:
            coin: Coin symbol (e.g., "BTC")
            interval: Time interval
            days: Number of days to fetch (default: 7)
            use_cache: Whether to use cached data

        Returns:
            List of candles for the specified period

        Token usage: ~2K
        """
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = end_time - (days * 24 * 60 * 60 * 1000)

        return self.get_candles(coin, interval, start_time, end_time, use_cache)

    def calculate_vwap(self, candles: List[Dict[str, Any]]) -> float:
        """
        Calculate Volume Weighted Average Price from candles.

        Args:
            candles: List of candle objects

        Returns:
            VWAP as float

        Token usage: ~0 (local calculation)
        """
        if not candles:
            raise ValueError("Cannot calculate VWAP from empty candles")

        total_volume = 0.0
        weighted_sum = 0.0

        for candle in candles:
            # Typical price = (high + low + close) / 3
            typical_price = (
                float(candle["h"]) +
                float(candle["l"]) +
                float(candle["c"])
            ) / 3.0

            volume = float(candle["v"])

            weighted_sum += typical_price * volume
            total_volume += volume

        if total_volume == 0:
            raise ValueError("Total volume is zero, cannot calculate VWAP")

        return round(weighted_sum / total_volume, 2)

    def get_candle_stats(self, candles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate statistics from a set of candles.

        Args:
            candles: List of candle objects

        Returns:
            {
                "num_candles": 100,
                "high": 45500.0,
                "low": 44000.0,
                "vwap": 44750.0,
                "total_volume": 1234.56,
                "price_change": 2.5,  # percentage
                "price_change_abs": 1100.0  # absolute
            }

        Token usage: ~0 (local calculation)
        """
        if not candles:
            raise ValueError("Cannot calculate stats from empty candles")

        highs = [float(c["h"]) for c in candles]
        lows = [float(c["l"]) for c in candles]
        volumes = [float(c["v"]) for c in candles]

        first_open = float(candles[0]["o"])
        last_close = float(candles[-1]["c"])
        price_change_abs = last_close - first_open
        price_change_pct = (price_change_abs / first_open) * 100 if first_open != 0 else 0

        return {
            "num_candles": len(candles),
            "high": round(max(highs), 2),
            "low": round(min(lows), 2),
            "vwap": self.calculate_vwap(candles),
            "total_volume": round(sum(volumes), 2),
            "price_change": round(price_change_pct, 2),
            "price_change_abs": round(price_change_abs, 2),
            "first_open": round(first_open, 2),
            "last_close": round(last_close, 2)
        }

    def _interval_to_milliseconds(self, interval: str) -> int:
        """
        Convert interval string to milliseconds.

        Args:
            interval: Interval string (1m, 5m, 1h, 1d, etc.)

        Returns:
            Milliseconds for one interval
        """
        # Parse interval (e.g., "1m", "5m", "1h", "1d")
        if interval.endswith('m'):
            minutes = int(interval[:-1])
            return minutes * 60 * 1000
        elif interval.endswith('h'):
            hours = int(interval[:-1])
            return hours * 60 * 60 * 1000
        elif interval.endswith('d'):
            days = int(interval[:-1])
            return days * 24 * 60 * 60 * 1000
        elif interval.endswith('w'):
            weeks = int(interval[:-1])
            return weeks * 7 * 24 * 60 * 60 * 1000
        elif interval.endswith('M'):
            months = int(interval[:-1])
            return months * 30 * 24 * 60 * 60 * 1000  # Approximate
        else:
            raise ValueError(f"Cannot parse interval: {interval}")
