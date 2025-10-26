"""
Trades & Fills Agent
====================
Lightweight wrapper for trade history and order fills.

Design Principle:
- Agent is ~20 lines per method (just method stubs)
- All heavy lifting delegated to hyperliquid-fetch-and-cache skill
- Skill handles: HTTP calls, caching, validation, rate limiting
- Token usage: ~2K per request (just coordination, not execution)

Architecture:
    User Request
        ↓
    Trades & Fills Agent (this file - lightweight)
        ↓
    invoke_skill("hyperliquid-fetch-and-cache", params)
        ↓
    Skill Script (executed outside context - 0 tokens)
        ↓
    Hyperliquid API + Memory Cache
"""

from typing import Dict, Any, List, Optional
from agents.base_agent import BaseAgent


class TradesFillsAgent(BaseAgent):
    """
    Fetches trade history and order fills via Skills.

    This agent is SIMPLE - just invokes skills.
    Heavy lifting in scripts (executed outside context).
    """

    def __init__(self):
        super().__init__(agent_name="trades_fills_agent")
        self.skill_name = "hyperliquid-fetch-and-cache"

    def get_user_fills(self, user_address: str, use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        Get filled orders for a user.

        Args:
            user_address: Hyperliquid user address (0x...)
            use_cache: Whether to use cached data (TTL: 60s)

        Returns:
            List of fill records:
            [
                {
                    "coin": "BTC",
                    "px": "45000.0",
                    "sz": "0.1",
                    "side": "B",  # B=Buy, A=Ask/Sell
                    "time": 1698765432000,
                    "startPosition": "0",
                    "dir": "Open Long",
                    "closedPnl": "0",
                    "hash": "0x...",
                    "oid": 123456,
                    "crossed": true,
                    "fee": "2.25",
                    "tid": 789012,
                    "feeToken": "USDC"
                },
                ...
            ]

        Token usage: ~2K (just skill invocation)
        """
        cache_config = {"enabled": use_cache, "ttl_seconds": 60}
        if not use_cache:
            cache_config["force_refresh"] = True

        result = self.invoke_skill(self.skill_name, {
            "endpoint": "userFills",
            "params": {"user": user_address},
            "cache_config": cache_config
        })

        self.validate_response(result)

        if not result["success"]:
            raise Exception(f"Failed to fetch user fills: {result.get('error')}")

        return result["data"]

    # Note: Hyperliquid API does not provide a public "recent trades" endpoint
    # for market trades. Available endpoints focus on user-specific data:
    # - userFills (user's filled orders)
    # - openOrders (user's open orders)
    # - userFunding (user's funding payments)

    def get_open_orders(self, user_address: str, use_cache: bool = False) -> List[Dict[str, Any]]:
        """
        Get open orders for a user.

        Args:
            user_address: Hyperliquid user address (0x...)
            use_cache: Whether to use cached data (TTL: 30s, typically disabled)

        Returns:
            List of open orders:
            [
                {
                    "coin": "BTC",
                    "side": "B",  # B=Buy, A=Ask/Sell
                    "limitPx": "44000.0",
                    "sz": "0.1",
                    "oid": 123456,
                    "timestamp": 1698765432000,
                    "origSz": "0.1"
                },
                ...
            ]

        Token usage: ~2K
        """
        cache_config = {"enabled": use_cache, "ttl_seconds": 30}
        if not use_cache:
            cache_config["force_refresh"] = True

        result = self.invoke_skill(self.skill_name, {
            "endpoint": "openOrders",
            "params": {"user": user_address},
            "cache_config": cache_config
        })

        self.validate_response(result)

        if not result["success"]:
            raise Exception(f"Failed to fetch open orders: {result.get('error')}")

        return result["data"]

    def get_user_funding(self, user_address: str, use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        Get funding payments for a user.

        Args:
            user_address: Hyperliquid user address (0x...)
            use_cache: Whether to use cached data (TTL: 300s)

        Returns:
            List of funding payment records (same structure as fills)

        Token usage: ~2K
        """
        cache_config = {"enabled": use_cache, "ttl_seconds": 300}
        if not use_cache:
            cache_config["force_refresh"] = True

        result = self.invoke_skill(self.skill_name, {
            "endpoint": "userFunding",
            "params": {"user": user_address},
            "cache_config": cache_config
        })

        self.validate_response(result)

        if not result["success"]:
            raise Exception(f"Failed to fetch user funding: {result.get('error')}")

        return result["data"]

    def get_trade_summary(self, user_address: str) -> Dict[str, Any]:
        """
        Get summary of user's trading activity.

        Args:
            user_address: Hyperliquid user address

        Returns:
            {
                "total_fills": 150,
                "open_orders": 5,
                "recent_coins_traded": ["BTC", "ETH", "SOL"],
                "last_trade_time": 1698765432000
            }

        Token usage: ~2K (reuses cached fills)
        """
        fills = self.get_user_fills(user_address, use_cache=True)
        open_orders = self.get_open_orders(user_address, use_cache=False)

        # Extract unique coins
        coins_traded = list(set(fill["coin"] for fill in fills))

        # Get last trade time
        last_trade_time = max((fill["time"] for fill in fills), default=0)

        return {
            "total_fills": len(fills),
            "open_orders": len(open_orders),
            "recent_coins_traded": coins_traded,
            "last_trade_time": last_trade_time
        }

    def get_fills_by_coin(self, user_address: str, coin: str) -> List[Dict[str, Any]]:
        """
        Get user fills filtered by coin.

        Args:
            user_address: Hyperliquid user address
            coin: Coin symbol to filter by

        Returns:
            List of fills for the specific coin

        Token usage: ~2K (reuses cached fills)
        """
        fills = self.get_user_fills(user_address, use_cache=True)
        return [fill for fill in fills if fill["coin"] == coin]

    def get_pnl_summary(self, user_address: str) -> Dict[str, Any]:
        """
        Calculate PnL summary from user fills.

        Args:
            user_address: Hyperliquid user address

        Returns:
            {
                "total_closed_pnl": 1234.56,
                "total_fees": 45.67,
                "net_pnl": 1188.89,
                "num_trades": 150
            }

        Token usage: ~2K (reuses cached fills)
        """
        fills = self.get_user_fills(user_address, use_cache=True)

        total_closed_pnl = sum(
            float(fill.get("closedPnl", "0")) for fill in fills
        )

        total_fees = sum(
            float(fill.get("fee", "0")) for fill in fills
        )

        return {
            "total_closed_pnl": round(total_closed_pnl, 2),
            "total_fees": round(total_fees, 2),
            "net_pnl": round(total_closed_pnl - total_fees, 2),
            "num_trades": len(fills)
        }
