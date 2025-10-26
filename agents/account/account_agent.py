"""
Account Monitor Agent
=====================
Lightweight wrapper for account and portfolio monitoring.

Design Principle:
- Agent is ~20 lines per method (just method stubs)
- All heavy lifting delegated to hyperliquid-fetch-and-cache skill
- Skill handles: HTTP calls, caching, validation, rate limiting
- Token usage: ~3K per request (just coordination, not execution)

Architecture:
    User Request
        ↓
    Account Monitor Agent (this file - lightweight)
        ↓
    invoke_skill("hyperliquid-fetch-and-cache", params)
        ↓
    Skill Script (executed outside context - 0 tokens)
        ↓
    Hyperliquid API + Memory Cache
"""

from typing import Dict, Any, List, Optional
from agents.base_agent import BaseAgent


class AccountAgent(BaseAgent):
    """
    Monitors account state and portfolio positions via Skills.

    This agent is SIMPLE - just invokes skills.
    Heavy lifting in scripts (executed outside context).
    """

    def __init__(self):
        super().__init__(agent_name="account_agent")
        self.skill_name = "hyperliquid-fetch-and-cache"

    def get_account_state(self, user_address: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Get complete account state (clearinghouse state).

        Args:
            user_address: Hyperliquid user address (0x...)
            use_cache: Whether to use cached data (TTL: 60s)

        Returns:
            Account state:
            {
                "assetPositions": [
                    {
                        "position": {
                            "coin": "BTC",
                            "szi": "0.5",  # Position size
                            "leverage": {
                                "type": "cross",
                                "value": 10
                            },
                            "entryPx": "45000.0",
                            "positionValue": "22500.0",
                            "unrealizedPnl": "500.0"
                        }
                    },
                    ...
                ],
                "crossMarginSummary": {
                    "accountValue": "10000.0",
                    "totalMarginUsed": "2250.0",
                    "totalNtlPos": "22500.0",
                    "totalRawUsd": "10000.0"
                },
                "marginSummary": {
                    "accountValue": "10000.0",
                    "totalMarginUsed": "2250.0"
                },
                "withdrawable": "7750.0",
                "time": 1698765432000
            }

        Token usage: ~3K
        """
        cache_config = {"enabled": use_cache, "ttl_seconds": 60}
        if not use_cache:
            cache_config["force_refresh"] = True

        result = self.invoke_skill(self.skill_name, {
            "endpoint": "clearinghouseState",
            "params": {"user": user_address},
            "cache_config": cache_config
        })

        self.validate_response(result)

        if not result["success"]:
            raise Exception(f"Failed to fetch account state: {result.get('error')}")

        return result["data"]

    def get_positions(self, user_address: str) -> List[Dict[str, Any]]:
        """
        Get user's open positions.

        Args:
            user_address: Hyperliquid user address

        Returns:
            List of open positions with coin, size, entry price, PnL

        Token usage: ~3K (reuses account state)
        """
        account_state = self.get_account_state(user_address, use_cache=True)

        # Extract positions from asset positions
        positions = []
        for asset_pos in account_state.get("assetPositions", []):
            position = asset_pos.get("position", {})
            if position and float(position.get("szi", "0")) != 0:
                positions.append(position)

        return positions

    def get_account_summary(self, user_address: str) -> Dict[str, Any]:
        """
        Get simplified account summary.

        Args:
            user_address: Hyperliquid user address

        Returns:
            {
                "account_value": 10000.0,
                "total_margin_used": 2250.0,
                "withdrawable": 7750.0,
                "num_positions": 3,
                "total_unrealized_pnl": 1500.0
            }

        Token usage: ~3K (reuses account state)
        """
        account_state = self.get_account_state(user_address, use_cache=True)

        # Extract summary info
        margin_summary = account_state.get("marginSummary", {})
        positions = self.get_positions(user_address)

        # Calculate total unrealized PnL
        total_pnl = sum(
            float(pos.get("unrealizedPnl", "0"))
            for pos in positions
        )

        return {
            "account_value": float(margin_summary.get("accountValue", "0")),
            "total_margin_used": float(margin_summary.get("totalMarginUsed", "0")),
            "withdrawable": float(account_state.get("withdrawable", "0")),
            "num_positions": len(positions),
            "total_unrealized_pnl": round(total_pnl, 2)
        }

    def get_position_by_coin(self, user_address: str, coin: str) -> Optional[Dict[str, Any]]:
        """
        Get position for a specific coin.

        Args:
            user_address: Hyperliquid user address
            coin: Coin symbol (e.g., "BTC")

        Returns:
            Position dict if found, None otherwise

        Token usage: ~3K (reuses account state)
        """
        positions = self.get_positions(user_address)

        for position in positions:
            if position.get("coin") == coin:
                return position

        return None

    def get_active_asset_data(
        self,
        user_address: str,
        coin: str,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Get active asset data for a specific coin.

        Args:
            user_address: Hyperliquid user address
            coin: Coin symbol (e.g., "BTC")
            use_cache: Whether to use cached data

        Returns:
            {
                "leverage": {"type": "cross", "value": 10},
                "maxTradeSzs": ["100.0", "50.0"],
                "availableToTrade": "5000.0",
                "markPx": "45000.0"
            }

        Token usage: ~3K
        """
        cache_config = {"enabled": use_cache, "ttl_seconds": 60}
        if not use_cache:
            cache_config["force_refresh"] = True

        result = self.invoke_skill(self.skill_name, {
            "endpoint": "activeAssetData",
            "params": {"user": user_address, "coin": coin},
            "cache_config": cache_config
        })

        self.validate_response(result)

        if not result["success"]:
            raise Exception(f"Failed to fetch active asset data: {result.get('error')}")

        return result["data"]

    def get_ledger_updates(
        self,
        user_address: str,
        start_time: int,
        end_time: Optional[int] = None,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get non-funding ledger updates (deposits, withdrawals, transfers).

        Args:
            user_address: Hyperliquid user address
            start_time: Start timestamp in milliseconds
            end_time: End timestamp in milliseconds (optional)
            use_cache: Whether to use cached data

        Returns:
            List of ledger updates:
            [
                {
                    "time": 1698765432000,
                    "hash": "0x...",
                    "delta": {
                        "type": "deposit",
                        "amount": "1000.0",
                        "token": "USDC"
                    }
                },
                ...
            ]

        Token usage: ~3K
        """
        cache_config = {"enabled": use_cache, "ttl_seconds": 300}
        if not use_cache:
            cache_config["force_refresh"] = True

        params = {
            "user": user_address,
            "startTime": start_time
        }
        if end_time is not None:
            params["endTime"] = end_time

        result = self.invoke_skill(self.skill_name, {
            "endpoint": "userNonFundingLedgerUpdates",
            "params": params,
            "cache_config": cache_config
        })

        self.validate_response(result)

        if not result["success"]:
            raise Exception(f"Failed to fetch ledger updates: {result.get('error')}")

        return result["data"]

    def get_portfolio_value(self, user_address: str) -> Dict[str, Any]:
        """
        Get current portfolio value breakdown.

        Args:
            user_address: Hyperliquid user address

        Returns:
            {
                "account_value": 10000.0,
                "cash_balance": 7750.0,
                "position_value": 2250.0,
                "unrealized_pnl": 500.0,
                "margin_ratio": 0.225  # margin_used / account_value
            }

        Token usage: ~3K (reuses account state)
        """
        account_state = self.get_account_state(user_address, use_cache=True)
        margin_summary = account_state.get("marginSummary", {})
        cross_margin = account_state.get("crossMarginSummary", {})

        account_value = float(margin_summary.get("accountValue", "0"))
        margin_used = float(margin_summary.get("totalMarginUsed", "0"))
        withdrawable = float(account_state.get("withdrawable", "0"))

        # Calculate total position value
        positions = self.get_positions(user_address)
        total_pos_value = sum(
            float(pos.get("positionValue", "0"))
            for pos in positions
        )

        # Calculate unrealized PnL
        total_pnl = sum(
            float(pos.get("unrealizedPnl", "0"))
            for pos in positions
        )

        # Margin ratio
        margin_ratio = (margin_used / account_value) if account_value > 0 else 0

        return {
            "account_value": round(account_value, 2),
            "cash_balance": round(withdrawable, 2),
            "position_value": round(total_pos_value, 2),
            "unrealized_pnl": round(total_pnl, 2),
            "margin_ratio": round(margin_ratio, 4)
        }

    def get_risk_metrics(self, user_address: str) -> Dict[str, Any]:
        """
        Calculate risk metrics for the account.

        Args:
            user_address: Hyperliquid user address

        Returns:
            {
                "margin_ratio": 0.225,
                "leverage": 2.25,  # total_position_value / account_value
                "num_positions": 3,
                "largest_position": "BTC",
                "largest_position_pct": 0.50  # % of account value
            }

        Token usage: ~3K (reuses account state)
        """
        account_state = self.get_account_state(user_address, use_cache=True)
        margin_summary = account_state.get("marginSummary", {})
        cross_margin = account_state.get("crossMarginSummary", {})

        account_value = float(margin_summary.get("accountValue", "0"))
        margin_used = float(margin_summary.get("totalMarginUsed", "0"))
        total_pos_value = float(cross_margin.get("totalNtlPos", "0"))

        # Get positions
        positions = self.get_positions(user_address)

        # Find largest position
        largest_coin = None
        largest_value = 0.0
        for pos in positions:
            pos_value = abs(float(pos.get("positionValue", "0")))
            if pos_value > largest_value:
                largest_value = pos_value
                largest_coin = pos.get("coin")

        # Calculate metrics
        margin_ratio = (margin_used / account_value) if account_value > 0 else 0
        leverage = (total_pos_value / account_value) if account_value > 0 else 0
        largest_pos_pct = (largest_value / account_value) if account_value > 0 else 0

        return {
            "margin_ratio": round(margin_ratio, 4),
            "leverage": round(leverage, 2),
            "num_positions": len(positions),
            "largest_position": largest_coin,
            "largest_position_pct": round(largest_pos_pct, 4)
        }
