"""
Price & Book Agent
==================
Lightweight wrapper for real-time price data and order books.

Design Principle:
- Agent is ~20 lines (just method stubs)
- All heavy lifting delegated to hyperliquid-fetch-and-cache skill
- Skill handles: HTTP calls, caching, validation, rate limiting
- Token usage: ~2K per request (just coordination, not execution)

Architecture:
    User Request
        ↓
    Price & Book Agent (this file - lightweight)
        ↓
    invoke_skill("hyperliquid-fetch-and-cache", params)
        ↓
    Skill Script (executed outside context - 0 tokens)
        ↓
    Hyperliquid API + Memory Cache
"""

from typing import Dict, Any, List, Optional
from agents.base_agent import BaseAgent


class PriceBookAgent(BaseAgent):
    """
    Fetches real-time price data and order books via Skills.

    This agent is SIMPLE - just invokes skills.
    Heavy lifting in scripts (executed outside context).
    """

    def __init__(self):
        super().__init__(agent_name="price_book_agent")
        self.skill_name = "hyperliquid-fetch-and-cache"

    def get_all_mids(self, use_cache: bool = True, ttl_seconds: Optional[int] = None, force_refresh: bool = False) -> Dict[str, str]:
        """
        Get mid prices for all coins.

        Args:
            use_cache: Whether to use cached data (default: True)
            ttl_seconds: Cache TTL override (uses config default if not specified)
            force_refresh: Force bypass cache and get fresh data (default: False)

        Returns:
            Dict mapping coin symbols to mid prices
            Example: {"BTC": "111000.5", "ETH": "3959.25", ...}

        Token usage: ~2K (just skill invocation, skill execution is 0 tokens)

        Note: Cache TTL defaults from core/config.py: CACHE_TTL["all_mids"] = 5 seconds
        """
        cache_config = {"enabled": use_cache and not force_refresh}
        if ttl_seconds is not None:
            cache_config["ttl_seconds"] = ttl_seconds
        if force_refresh or not use_cache:
            cache_config["force_refresh"] = True

        result = self.invoke_skill(self.skill_name, {
            "endpoint": "allMids",
            "params": {},
            "cache_config": cache_config
        })

        self.validate_response(result)

        if not result["success"]:
            raise Exception(f"Failed to fetch all mids: {result.get('error')}")

        return result["data"]

    def get_price(self, coin: str, use_cache: bool = True, force_refresh: bool = False) -> float:
        """
        Get price for a specific coin.

        Args:
            coin: Coin symbol (e.g., "BTC", "ETH")
            use_cache: Whether to use cached data (default: True)
            force_refresh: Force bypass cache and get fresh data (default: False)

        Returns:
            Price as float

        Raises:
            KeyError: If coin not found
        """
        all_mids = self.get_all_mids(use_cache=use_cache, force_refresh=force_refresh)

        if coin not in all_mids:
            raise KeyError(f"Coin '{coin}' not found in market data")

        return float(all_mids[coin])

    def get_l2_book(self, coin: str, use_cache: bool = True, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get L2 order book for specific coin.

        Args:
            coin: Coin symbol (e.g., "BTC")
            use_cache: Whether to use cached data (default: True)
            force_refresh: Force bypass cache and get fresh data (default: False)

        Returns:
            Order book with structure:
            {
                "coin": "BTC",
                "time": 1698765432000,
                "levels": [
                    [{"px": "45000", "sz": "1.5", "n": 3}, ...],  # Bids
                    [{"px": "45100", "sz": "2.0", "n": 5}, ...]   # Asks
                ]
            }

        Note: Cache TTL defaults from core/config.py: CACHE_TTL["l2_book"] = 3 seconds
        """
        cache_config = {"enabled": use_cache and not force_refresh}
        if force_refresh or not use_cache:
            cache_config["force_refresh"] = True

        result = self.invoke_skill(self.skill_name, {
            "endpoint": "l2Book",
            "params": {"coin": coin},
            "cache_config": cache_config
        })

        self.validate_response(result)

        if not result["success"]:
            raise Exception(f"Failed to fetch order book: {result.get('error')}")

        return result["data"]

    def get_spread(self, coin: str, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Calculate bid-ask spread for a coin.

        Args:
            coin: Coin symbol (e.g., "BTC")
            force_refresh: Force bypass cache and get fresh data (default: False)

        Returns:
            {
                "coin": "BTC",
                "best_bid": 45000.0,
                "best_ask": 45001.0,
                "spread": 1.0,
                "spread_bps": 0.22  # basis points
            }
        """
        book = self.get_l2_book(coin, force_refresh=force_refresh)

        bids = book["levels"][0]  # Bids
        asks = book["levels"][1]  # Asks

        if not bids or not asks:
            raise ValueError(f"No liquidity for {coin}")

        best_bid = float(bids[0]["px"])
        best_ask = float(asks[0]["px"])
        spread = best_ask - best_bid
        spread_bps = (spread / best_bid) * 10000

        return {
            "coin": coin,
            "best_bid": best_bid,
            "best_ask": best_ask,
            "spread": spread,
            "spread_bps": round(spread_bps, 2)
        }

    def get_meta(self, use_cache: bool = True, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get asset metadata (symbols, tick sizes, max leverage, etc.).

        Args:
            use_cache: Whether to use cached data (default: True)
            force_refresh: Force bypass cache and get fresh data (default: False)

        Returns:
            {
                "universe": [
                    {
                        "name": "BTC",
                        "szDecimals": 5,
                        "maxLeverage": 50,
                        "onlyIsolated": False
                    },
                    ...
                ]
            }

        Note: Cache TTL defaults from core/config.py: CACHE_TTL["meta"] = 60 seconds
        """
        cache_config = {"enabled": use_cache and not force_refresh}
        if force_refresh or not use_cache:
            cache_config["force_refresh"] = True

        result = self.invoke_skill(self.skill_name, {
            "endpoint": "meta",
            "params": {},
            "cache_config": cache_config
        })

        self.validate_response(result)

        if not result["success"]:
            raise Exception(f"Failed to fetch metadata: {result.get('error')}")

        return result["data"]

    def get_coins_list(self, force_refresh: bool = False) -> List[str]:
        """
        Get list of all tradable coins.

        Args:
            force_refresh: Force bypass cache and get fresh data (default: False)

        Returns:
            List of coin symbols
        """
        meta = self.get_meta(use_cache=True, force_refresh=force_refresh)
        return [coin["name"] for coin in meta["universe"]]
