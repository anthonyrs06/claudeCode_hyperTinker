"""
Orchestrator Agent
==================
Routes user requests to specialized agents based on intent analysis.

Design Principle:
- Starts with pattern matching routing (Phase 3)
- Can be upgraded to Claude-powered routing with Memory Tool (Phase 4)
- Delegates all data fetching to specialized agents
- Aggregates results from multiple agents when needed
- Token budget: 20K-40K per orchestration cycle (future LLM-powered version)

Architecture:
    User Request
        ↓
    Orchestrator (this file - routing logic)
        ↓
    Specialized Agents (Price, Trades, Candles, Account, Error Recovery)
        ↓
    Skills (hyperliquid-fetch-and-cache)
        ↓
    Hyperliquid API + Memory Cache
"""

from typing import Dict, Any, List, Optional, Callable
import re
import time
from datetime import datetime
from agents.base_agent import BaseAgent
from agents.price_book.price_book_agent import PriceBookAgent
from agents.trades_fills.trades_fills_agent import TradesFillsAgent
from agents.candles.candles_agent import CandlesAgent
from agents.account.account_agent import AccountAgent
from agents.error_recovery.error_recovery_agent import ErrorRecoveryAgent
from core.memory_manager import get_memory_manager
from core.circuit_breaker import CircuitBreakerManager
from core.config import (
    ANTHROPIC_API_KEY,
    ORCHESTRATOR_MODEL,
    ENABLE_CLAUDE_ROUTING,
    CLAUDE_ROUTING_CONFIDENCE_THRESHOLD,
    CIRCUIT_BREAKER_CONFIG
)

# Conditional import of Anthropic (for Phase 5)
try:
    import anthropic
    ANTHROPIC_AVAILABLE = bool(ANTHROPIC_API_KEY)
except ImportError:
    ANTHROPIC_AVAILABLE = False


class OrchestratorAgent(BaseAgent):
    """
    Routes user requests to appropriate specialized agents.

    Phase 3: Simple pattern matching
    Phase 4: Claude-powered routing with Memory Tool learning
    """

    def __init__(self):
        super().__init__(agent_name="orchestrator_agent")

        # Initialize specialized agents
        self.price_agent = PriceBookAgent()
        self.trades_agent = TradesFillsAgent()
        self.candles_agent = CandlesAgent()
        self.account_agent = AccountAgent()
        self.error_recovery_agent = ErrorRecoveryAgent()

        # Initialize memory manager (Phase 4)
        self.memory = get_memory_manager()

        # Initialize circuit breakers (Phase 5)
        self.circuit_breakers = CircuitBreakerManager(
            failure_threshold=CIRCUIT_BREAKER_CONFIG["failure_threshold"],
            timeout_seconds=CIRCUIT_BREAKER_CONFIG["timeout_seconds"],
            half_open_max_calls=CIRCUIT_BREAKER_CONFIG["half_open_max_calls"]
        )

        # Initialize Anthropic client (Phase 5)
        if ANTHROPIC_AVAILABLE and ENABLE_CLAUDE_ROUTING:
            self.claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            self.use_claude_routing = True
        else:
            self.claude_client = None
            self.use_claude_routing = False

        # Routing patterns (pattern matching fallback)
        self.routing_patterns = {
            "price": ["price", "mid", "quote", "cost", "value"],
            "book": ["book", "orderbook", "order book", "depth", "liquidity"],
            "spread": ["spread", "bid-ask", "bid ask"],
            "trades": ["trade", "fill", "order", "execution"],
            "candles": ["candle", "ohlc", "bar", "chart", "historical price"],
            "account": ["account", "portfolio", "position", "balance", "pnl"],
            "meta": ["meta", "coin list", "list coins", "list", "available", "universe", "symbols"]
        }

        # Initialize memory structures
        self._init_memory()

    def route_request(self, user_request: str, context: Optional[Dict[str, Any]] = None, track_memory: bool = True, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Route user request to appropriate agent.

        Args:
            user_request: Natural language request from user
            context: Optional context (user address, coin, etc.)
            track_memory: Whether to track routing decision in memory (Phase 4)
            force_refresh: Force bypass cache and get fresh data (default: False)

        Returns:
            {
                "agent": "price_book",
                "action": "get_all_mids",
                "result": {...},
                "metadata": {
                    "routing_logic": "pattern_match",
                    "confidence": 0.95,
                    "cache_bypassed": True  # if force_refresh=True
                }
            }

        Token usage (Phase 3): ~0 (pattern matching)
        Token usage (Phase 4): ~20K-40K (Claude-powered routing)

        Note: force_refresh bypasses all caching for real-time data
        """
        context = context or {}
        context["force_refresh"] = force_refresh  # Pass through to agents
        request_lower = user_request.lower()
        start_time = time.time()  # Track response time
        intent = "unknown"
        routed_to = "none"
        success = False
        error_msg = None

        try:
            # Extract coin symbol if present (common parameter)
            coin = self._extract_coin(user_request)
            if coin:
                context["coin"] = coin

            # Extract user address if present
            address = self._extract_address(user_request)
            if address:
                context["user_address"] = address

            # Route based on intent (Phase 5: Use Claude when available)
            routing_logic = "pattern_match"
            confidence = 0.8
            claude_result = None

            if self._should_use_claude_routing():
                # Try Claude-powered routing
                claude_result = self._classify_intent_with_claude(user_request, context)
                confidence = claude_result.get("confidence", 0.5)

                # Use Claude result if confidence is high enough
                if confidence >= CLAUDE_ROUTING_CONFIDENCE_THRESHOLD:
                    intent = claude_result.get("intent", "unknown")
                    routing_logic = "claude"

                    # Use extracted parameters from Claude
                    extracted_params = claude_result.get("extracted_params", {})
                    if extracted_params.get("coin"):
                        context["coin"] = extracted_params["coin"]
                    if extracted_params.get("address"):
                        context["user_address"] = extracted_params["address"]
                else:
                    # Low confidence, fall back to pattern matching
                    intent = self._classify_intent(request_lower)
                    routing_logic = "pattern_match_fallback"
            else:
                # Claude not available, use pattern matching
                intent = self._classify_intent(request_lower)

            # Pass routing metadata to context for downstream methods
            context["routing_logic"] = routing_logic
            context["routing_confidence"] = confidence

            # Route to appropriate agent
            result = None
            if intent == "price":
                result = self._route_to_price_agent(request_lower, context)
                routed_to = "price_book"
            elif intent == "book":
                result = self._route_to_book_agent(request_lower, context)
                routed_to = "price_book"
            elif intent == "spread":
                result = self._route_to_spread_agent(request_lower, context)
                routed_to = "price_book"
            elif intent == "trades":
                result = self._route_to_trades_agent(request_lower, context)
                routed_to = "trades_fills"
            elif intent == "candles":
                result = self._route_to_candles_agent(request_lower, context)
                routed_to = "candles"
            elif intent == "account":
                result = self._route_to_account_agent(request_lower, context)
                routed_to = "account"
            elif intent == "meta":
                result = self._route_to_meta_agent(request_lower, context)
                routed_to = "price_book"
            else:
                result = {
                    "success": False,
                    "error": "Unable to determine intent from request",
                    "request": user_request,
                    "suggestion": "Try asking about prices, order books, candles, trades, or account info"
                }

            # Track success
            success = result.get("success", False)

            # Track routing decision in memory (Phase 4)
            if track_memory:
                response_time_ms = (time.time() - start_time) * 1000
                self._track_routing_decision(
                    user_request=user_request,
                    intent=intent,
                    routed_to=routed_to,
                    response_time_ms=response_time_ms,
                    success=success,
                    error=result.get("error") if not success else None
                )

            return result

        except Exception as e:
            # Use error recovery agent to analyze
            analysis = self.error_recovery_agent.analyze_error(e, {
                "request": user_request,
                "context": context
            })

            # Track error
            if track_memory:
                response_time_ms = (time.time() - start_time) * 1000
                self._track_routing_decision(
                    user_request=user_request,
                    intent=intent,
                    routed_to="error_recovery",
                    response_time_ms=response_time_ms,
                    success=False,
                    error=str(e)
                )

            return {
                "success": False,
                "error": str(e),
                "error_analysis": analysis,
                "request": user_request
            }

    def _classify_intent(self, request_lower: str) -> str:
        """Classify user intent based on keywords."""
        # Check each intent category
        for intent, keywords in self.routing_patterns.items():
            if any(keyword in request_lower for keyword in keywords):
                return intent

        return "unknown"

    def _extract_coin(self, request: str) -> Optional[str]:
        """Extract coin symbol from request (e.g., BTC, ETH)."""
        # Look for 3-4 uppercase letters
        match = re.search(r'\b([A-Z]{3,4})\b', request)
        return match.group(1) if match else None

    def _extract_address(self, request: str) -> Optional[str]:
        """Extract Ethereum address from request."""
        # Look for 0x followed by 40 hex characters
        match = re.search(r'0x[a-fA-F0-9]{40}', request)
        return match.group(0) if match else None

    def _route_to_price_agent(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Route to Price & Book Agent for price queries (with circuit breaker protection)."""
        coin = context.get("coin")
        force_refresh = context.get("force_refresh", False)
        routing_logic = context.get("routing_logic", "pattern_match")
        routing_confidence = context.get("routing_confidence", 0.95)

        if coin:
            # Get specific coin price with circuit breaker
            price = self._call_agent_with_breaker(
                "price_book",
                self.price_agent.get_price,
                coin,
                use_cache=True,
                force_refresh=force_refresh
            )

            # Check if circuit breaker returned error response
            if isinstance(price, dict) and not price.get("success", True):
                return price

            return {
                "success": True,
                "agent": "price_book",
                "action": "get_price",
                "result": {
                    "coin": coin,
                    "price": price
                },
                "metadata": {
                    "routing_logic": routing_logic,
                    "confidence": routing_confidence,
                    "cache_bypassed": force_refresh
                }
            }
        else:
            # Get all prices with circuit breaker
            prices = self._call_agent_with_breaker(
                "price_book",
                self.price_agent.get_all_mids,
                use_cache=True,
                force_refresh=force_refresh
            )

            # Check if circuit breaker returned error response
            if isinstance(prices, dict) and not prices.get("success", True):
                return prices

            return {
                "success": True,
                "agent": "price_book",
                "action": "get_all_mids",
                "result": prices,
                "metadata": {
                    "routing_logic": routing_logic,
                    "confidence": routing_confidence,
                    "num_coins": len(prices),
                    "cache_bypassed": force_refresh
                }
            }

    def _route_to_book_agent(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Route to Price & Book Agent for order book queries (with circuit breaker)."""
        coin = context.get("coin", "BTC")  # Default to BTC
        force_refresh = context.get("force_refresh", False)
        routing_logic = context.get("routing_logic", "pattern_match")
        routing_confidence = context.get("routing_confidence", 0.95)

        book = self._call_agent_with_breaker(
            "price_book",
            self.price_agent.get_l2_book,
            coin,
            use_cache=True,
            force_refresh=force_refresh
        )

        if isinstance(book, dict) and not book.get("success", True):
            return book

        return {
            "success": True,
            "agent": "price_book",
            "action": "get_l2_book",
            "result": book,
            "metadata": {
                "routing_logic": routing_logic,
                "confidence": routing_confidence,
                "cache_bypassed": force_refresh
            }
        }

    def _route_to_spread_agent(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Route to Price & Book Agent for spread queries (with circuit breaker)."""
        coin = context.get("coin", "BTC")
        force_refresh = context.get("force_refresh", False)
        routing_logic = context.get("routing_logic", "pattern_match")
        routing_confidence = context.get("routing_confidence", 0.95)

        spread = self._call_agent_with_breaker(
            "price_book",
            self.price_agent.get_spread,
            coin,
            force_refresh=force_refresh
        )

        if isinstance(spread, dict) and not spread.get("success", True):
            return spread

        return {
            "success": True,
            "agent": "price_book",
            "action": "get_spread",
            "result": spread,
            "metadata": {
                "routing_logic": routing_logic,
                "confidence": routing_confidence,
                "cache_bypassed": force_refresh
            }
        }

    def _route_to_trades_agent(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Route to Trades & Fills Agent (with circuit breaker)."""
        user_address = context.get("user_address")
        routing_logic = context.get("routing_logic", "pattern_match")
        routing_confidence = context.get("routing_confidence", 0.95)

        if not user_address:
            return {
                "success": False,
                "error": "User address required for trade queries",
                "suggestion": "Please provide a user address (0x...)"
            }

        # Determine specific action
        if "fill" in request or "filled" in request:
            fills = self._call_agent_with_breaker(
                "trades_fills",
                self.trades_agent.get_user_fills,
                user_address,
                use_cache=True
            )

            if isinstance(fills, dict) and not fills.get("success", True):
                return fills

            return {
                "success": True,
                "agent": "trades_fills",
                "action": "get_user_fills",
                "result": fills,
                "metadata": {
                    "routing_logic": routing_logic,
                    "confidence": routing_confidence,
                    "num_fills": len(fills)
                }
            }
        elif "open" in request:
            orders = self._call_agent_with_breaker(
                "trades_fills",
                self.trades_agent.get_open_orders,
                user_address,
                use_cache=False
            )

            if isinstance(orders, dict) and not orders.get("success", True):
                return orders

            return {
                "success": True,
                "agent": "trades_fills",
                "action": "get_open_orders",
                "result": orders,
                "metadata": {
                    "routing_logic": routing_logic,
                    "confidence": routing_confidence,
                    "num_orders": len(orders)
                }
            }
        else:
            # Default to trade summary
            summary = self._call_agent_with_breaker(
                "trades_fills",
                self.trades_agent.get_trade_summary,
                user_address
            )

            if isinstance(summary, dict) and not summary.get("success", True):
                return summary

            return {
                "success": True,
                "agent": "trades_fills",
                "action": "get_trade_summary",
                "result": summary,
                "metadata": {
                    "routing_logic": routing_logic,
                    "confidence": routing_confidence
                }
            }

    def _route_to_candles_agent(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Route to Candles & Historical Agent (with circuit breaker)."""
        coin = context.get("coin", "BTC")
        routing_logic = context.get("routing_logic", "pattern_match")
        routing_confidence = context.get("routing_confidence", 0.95)

        # Determine interval (default 1h)
        interval = "1h"
        if "1m" in request or "minute" in request:
            interval = "1m"
        elif "5m" in request:
            interval = "5m"
        elif "15m" in request:
            interval = "15m"
        elif "4h" in request:
            interval = "4h"
        elif "1d" in request or "day" in request or "daily" in request:
            interval = "1d"

        # Get recent candles with circuit breaker
        candles = self._call_agent_with_breaker(
            "candles",
            self.candles_agent.get_recent_candles,
            coin,
            interval,
            num_candles=100,
            use_cache=True
        )

        if isinstance(candles, dict) and not candles.get("success", True):
            return candles

        # Calculate stats
        stats = self.candles_agent.get_candle_stats(candles)

        return {
            "success": True,
            "agent": "candles",
            "action": "get_recent_candles",
            "result": {
                "candles": candles,
                "stats": stats
            },
            "metadata": {
                "routing_logic": routing_logic,
                "confidence": routing_confidence,
                "interval": interval,
                "num_candles": len(candles)
            }
        }

    def _route_to_account_agent(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Route to Account Monitor Agent (with circuit breaker)."""
        user_address = context.get("user_address")
        routing_logic = context.get("routing_logic", "pattern_match")
        routing_confidence = context.get("routing_confidence", 0.95)

        if not user_address:
            return {
                "success": False,
                "error": "User address required for account queries",
                "suggestion": "Please provide a user address (0x...)"
            }

        # Determine specific action
        if "position" in request:
            positions = self._call_agent_with_breaker(
                "account",
                self.account_agent.get_positions,
                user_address
            )

            if isinstance(positions, dict) and not positions.get("success", True):
                return positions

            return {
                "success": True,
                "agent": "account",
                "action": "get_positions",
                "result": positions,
                "metadata": {
                    "routing_logic": routing_logic,
                    "confidence": routing_confidence,
                    "num_positions": len(positions)
                }
            }
        elif "risk" in request:
            risk = self._call_agent_with_breaker(
                "account",
                self.account_agent.get_risk_metrics,
                user_address
            )

            if isinstance(risk, dict) and not risk.get("success", True):
                return risk

            return {
                "success": True,
                "agent": "account",
                "action": "get_risk_metrics",
                "result": risk,
                "metadata": {
                    "routing_logic": routing_logic,
                    "confidence": routing_confidence
                }
            }
        else:
            # Default to account summary
            summary = self._call_agent_with_breaker(
                "account",
                self.account_agent.get_account_summary,
                user_address
            )

            if isinstance(summary, dict) and not summary.get("success", True):
                return summary

            return {
                "success": True,
                "agent": "account",
                "action": "get_account_summary",
                "result": summary,
                "metadata": {
                    "routing_logic": routing_logic,
                    "confidence": routing_confidence
                }
            }

    def _route_to_meta_agent(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Route to Price & Book Agent for metadata queries (with circuit breaker)."""
        force_refresh = context.get("force_refresh", False)
        routing_logic = context.get("routing_logic", "pattern_match")
        routing_confidence = context.get("routing_confidence", 0.95)

        if "list" in request or "coins" in request:
            coins = self._call_agent_with_breaker(
                "price_book",
                self.price_agent.get_coins_list,
                force_refresh=force_refresh
            )

            if isinstance(coins, dict) and not coins.get("success", True):
                return coins

            return {
                "success": True,
                "agent": "price_book",
                "action": "get_coins_list",
                "result": coins,
                "metadata": {
                    "routing_logic": routing_logic,
                    "confidence": routing_confidence,
                    "num_coins": len(coins),
                    "cache_bypassed": force_refresh
                }
            }
        else:
            meta = self._call_agent_with_breaker(
                "price_book",
                self.price_agent.get_meta,
                use_cache=True,
                force_refresh=force_refresh
            )

            if isinstance(meta, dict) and not meta.get("success", True):
                return meta

            return {
                "success": True,
                "agent": "price_book",
                "action": "get_meta",
                "result": meta,
                "metadata": {
                    "routing_logic": routing_logic,
                    "confidence": routing_confidence,
                    "cache_bypassed": force_refresh
                }
            }

    def get_routing_stats(self) -> Dict[str, Any]:
        """Get statistics about routing patterns (for debugging)."""
        return {
            "available_agents": ["price_book", "trades_fills", "candles", "account", "error_recovery"],
            "routing_patterns": self.routing_patterns,
            "routing_logic": "pattern_match (Phase 3)",
            "upgrade_path": "Claude-powered with Memory Tool (Phase 4)"
        }

    # ========================================================================
    # PHASE 4: MEMORY TOOL INTEGRATION
    # ========================================================================

    def _init_memory(self):
        """Initialize memory structures for routing history and learning."""
        # Initialize routing history if it doesn't exist
        history = self.memory.read("orchestrator", "routing_history.json", default=[])
        if not history:
            self.memory.write("orchestrator", "routing_history.json", [])

        # Initialize learned patterns
        patterns = self.memory.read("orchestrator", "learned_patterns.json", default={})
        if not patterns:
            initial_patterns = {
                "version": "1.0",
                "last_updated": datetime.now().isoformat(),
                "intent_to_agent": {},
                "common_requests": {}
            }
            self.memory.write("orchestrator", "learned_patterns.json", initial_patterns)

        # Initialize performance metrics
        performance = self.memory.read("orchestrator", "task_performance.json", default={})
        if not performance:
            initial_performance = {
                "version": "1.0",
                "agents": {
                    "price_book": {"total_requests": 0, "total_time_ms": 0, "errors": 0},
                    "trades_fills": {"total_requests": 0, "total_time_ms": 0, "errors": 0},
                    "candles": {"total_requests": 0, "total_time_ms": 0, "errors": 0},
                    "account": {"total_requests": 0, "total_time_ms": 0, "errors": 0},
                    "error_recovery": {"total_requests": 0, "total_time_ms": 0, "errors": 0}
                }
            }
            self.memory.write("orchestrator", "task_performance.json", initial_performance)

    def _track_routing_decision(
        self,
        user_request: str,
        intent: str,
        routed_to: str,
        response_time_ms: float,
        success: bool,
        error: Optional[str] = None
    ):
        """
        Track routing decision to memory for learning.

        Args:
            user_request: Original user request
            intent: Classified intent
            routed_to: Agent that handled request
            response_time_ms: Response time in milliseconds
            success: Whether request succeeded
            error: Error message if failed
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "request": user_request[:100],  # Truncate long requests
            "intent": intent,
            "routed_to": routed_to,
            "response_time_ms": round(response_time_ms, 2),
            "success": success
        }

        if error:
            entry["error"] = str(error)[:200]  # Truncate long errors

        # Append to routing history (max 1000 entries)
        self.memory.append("orchestrator", "routing_history.json", entry, max_entries=1000)

        # Update performance metrics
        self._update_performance_metrics(routed_to, response_time_ms, success)

    def _update_performance_metrics(self, agent: str, response_time_ms: float, success: bool):
        """Update agent performance metrics in memory."""
        performance = self.memory.read("orchestrator", "task_performance.json", default={})

        if "agents" not in performance:
            performance["agents"] = {}

        if agent not in performance["agents"]:
            performance["agents"][agent] = {
                "total_requests": 0,
                "total_time_ms": 0,
                "errors": 0
            }

        performance["agents"][agent]["total_requests"] += 1
        performance["agents"][agent]["total_time_ms"] += response_time_ms

        if not success:
            performance["agents"][agent]["errors"] += 1

        performance["last_updated"] = datetime.now().isoformat()

        self.memory.write("orchestrator", "task_performance.json", performance)

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics for all agents.

        Returns:
            {
                "agents": {
                    "price_book": {
                        "total_requests": 100,
                        "avg_response_ms": 245.5,
                        "error_rate": 0.02,
                        "uptime": 0.98
                    },
                    ...
                },
                "total_requests": 500,
                "avg_response_ms": 300.2
            }
        """
        performance = self.memory.read("orchestrator", "task_performance.json", default={})

        if "agents" not in performance:
            return {"agents": {}, "total_requests": 0, "avg_response_ms": 0}

        # Calculate derived metrics
        result = {"agents": {}}
        total_requests = 0
        total_time = 0

        for agent, metrics in performance["agents"].items():
            total_reqs = metrics["total_requests"]
            total_ms = metrics["total_time_ms"]
            errors = metrics["errors"]

            if total_reqs > 0:
                avg_ms = total_ms / total_reqs
                error_rate = errors / total_reqs
                uptime = 1.0 - error_rate
            else:
                avg_ms = 0
                error_rate = 0
                uptime = 1.0

            result["agents"][agent] = {
                "total_requests": total_reqs,
                "avg_response_ms": round(avg_ms, 2),
                "error_rate": round(error_rate, 4),
                "uptime": round(uptime, 4)
            }

            total_requests += total_reqs
            total_time += total_ms

        result["total_requests"] = total_requests
        result["avg_response_ms"] = round(total_time / total_requests, 2) if total_requests > 0 else 0

        return result

    def get_routing_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent routing history.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of recent routing decisions
        """
        history = self.memory.read("orchestrator", "routing_history.json", default=[])
        return history[-limit:]  # Return most recent

    def analyze_routing_patterns(self) -> Dict[str, Any]:
        """
        Analyze routing patterns from history.

        Returns:
            {
                "most_common_intent": "price",
                "intent_distribution": {"price": 45, "candles": 30, ...},
                "agent_utilization": {"price_book": 0.60, "candles": 0.25, ...},
                "avg_response_time_by_agent": {...},
                "peak_usage_hours": [9, 10, 14, 15]
            }
        """
        history = self.memory.read("orchestrator", "routing_history.json", default=[])

        if not history:
            return {
                "most_common_intent": None,
                "intent_distribution": {},
                "agent_utilization": {},
                "avg_response_time_by_agent": {}
            }

        # Count intents
        intent_counts = {}
        agent_counts = {}
        agent_times = {}

        for entry in history:
            intent = entry.get("intent", "unknown")
            agent = entry.get("routed_to", "unknown")
            resp_time = entry.get("response_time_ms", 0)

            intent_counts[intent] = intent_counts.get(intent, 0) + 1
            agent_counts[agent] = agent_counts.get(agent, 0) + 1

            if agent not in agent_times:
                agent_times[agent] = []
            agent_times[agent].append(resp_time)

        # Calculate metrics
        total_requests = len(history)
        most_common_intent = max(intent_counts, key=intent_counts.get) if intent_counts else None

        agent_utilization = {
            agent: round(count / total_requests, 2)
            for agent, count in agent_counts.items()
        }

        avg_response_times = {
            agent: round(sum(times) / len(times), 2)
            for agent, times in agent_times.items()
            if times
        }

        return {
            "most_common_intent": most_common_intent,
            "intent_distribution": intent_counts,
            "agent_utilization": agent_utilization,
            "avg_response_time_by_agent": avg_response_times,
            "total_requests": total_requests
        }

    # ====================================================================
    # PHASE 5: CLAUDE-POWERED ROUTING
    # ====================================================================

    def _get_learned_patterns(self) -> str:
        """
        Get insights from routing history to inform Claude.

        Returns:
            String summary of learned patterns
        """
        patterns = self.analyze_routing_patterns()

        if not patterns.get("total_requests"):
            return "No routing history available yet."

        summary = f"""Based on {patterns['total_requests']} historical routing decisions:

Most Common Intent: {patterns.get('most_common_intent', 'N/A')}

Intent Distribution:
{chr(10).join(f'  - {intent}: {count} requests' for intent, count in patterns.get('intent_distribution', {}).items())}

Agent Performance:
{chr(10).join(f'  - {agent}: {patterns["avg_response_time_by_agent"].get(agent, 0):.0f}ms avg' for agent in patterns.get('agent_utilization', {}).keys())}
"""
        return summary

    def _classify_intent_with_claude(self, user_request: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Use Claude to classify intent with learned patterns.

        Args:
            user_request: User's natural language request
            context: Optional context (address, timeframe, etc.)

        Returns:
            {
                "intent": "price",
                "confidence": 0.95,
                "reasoning": "User asking for current price...",
                "suggested_agent": "price_book",
                "extracted_params": {"coin": "BTC"}
            }
        """
        if not self.use_claude_routing:
            # Fallback to pattern matching
            return {
                "intent": self._classify_intent(user_request.lower()),
                "confidence": 0.5,
                "reasoning": "Using pattern matching (Claude unavailable)",
                "suggested_agent": None,
                "extracted_params": {}
            }

        # Get learned patterns for context
        learned_patterns = self._get_learned_patterns()

        # Build prompt for Claude
        prompt = f"""You are an intelligent routing system for a Hyperliquid market data API.

Your job is to classify user requests and route them to the appropriate specialized agent.

Available Agents:
1. price_book: Current prices, order books, bid/ask spreads, market depth
2. candles: Historical candles (OHLCV), price history, chart data
3. account: Account info, positions, balances, margin, PnL (requires address)
4. trades: Recent trades, fills, trade history (requires address for user trades)
5. meta: Metadata like coin lists, universe info, available symbols

Historical Context:
{learned_patterns}

User Request: "{user_request}"
Additional Context: {context or "None"}

Analyze this request and respond with:
1. The most appropriate intent (price, orderbook, candles, account, trades, or meta)
2. Confidence level (0.0-1.0)
3. Brief reasoning
4. Suggested agent to route to
5. Any extracted parameters (coin symbol, address, timeframe, etc.)

Respond in JSON format:
{{
    "intent": "price",
    "confidence": 0.95,
    "reasoning": "...",
    "suggested_agent": "price_book",
    "extracted_params": {{"coin": "BTC"}}
}}"""

        try:
            # Call Claude API with circuit breaker protection
            def claude_call():
                response = self.claude_client.messages.create(
                    model=ORCHESTRATOR_MODEL,
                    max_tokens=1000,
                    messages=[{"role": "user", "content": prompt}]
                )
                # Extract text from response
                if hasattr(response, 'content') and len(response.content) > 0:
                    content_block = response.content[0]
                    if hasattr(content_block, 'text'):
                        return content_block.text
                    else:
                        # content_block might be a dict
                        return content_block.get('text', str(content_block))
                else:
                    raise ValueError(f"Unexpected response format: {response}")

            # Use circuit breaker
            response_text = self.circuit_breakers.call("claude_routing", claude_call)

            # Parse JSON response (handle markdown code blocks)
            import json
            import re

            # Remove markdown code blocks if present (```json ... ```)
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(1)

            result = json.loads(response_text)

            return result

        except json.JSONDecodeError as e:
            # JSON parsing error - log the response text for debugging
            print(f"Claude routing JSON parse error: {e}. Response was: {response_text[:200] if 'response_text' in locals() else 'N/A'}. Falling back to pattern matching.")
            return {
                "intent": self._classify_intent(user_request.lower()),
                "confidence": 0.5,
                "reasoning": f"Fallback to pattern matching (JSON error: {str(e)[:50]})",
                "suggested_agent": None,
                "extracted_params": {}
            }
        except Exception as e:
            # Circuit breaker or API error - fallback to pattern matching
            print(f"Claude routing failed: {e}. Falling back to pattern matching.")
            return {
                "intent": self._classify_intent(user_request.lower()),
                "confidence": 0.5,
                "reasoning": f"Fallback to pattern matching (Claude error: {str(e)[:50]})",
                "suggested_agent": None,
                "extracted_params": {}
            }

    def _should_use_claude_routing(self, confidence_threshold: float = None) -> bool:
        """
        Determine if Claude routing should be used.

        Args:
            confidence_threshold: Minimum confidence required

        Returns:
            True if Claude should be used
        """
        if not self.use_claude_routing:
            return False

        # Check circuit breaker state
        breaker = self.circuit_breakers.get_breaker("claude_routing")
        if breaker.state.value == "open":
            return False

        return True

    def _call_agent_with_breaker(self, agent_name: str, func: Callable, *args, **kwargs) -> Any:
        """
        Call agent method with circuit breaker protection.

        Args:
            agent_name: Name of agent (for circuit breaker tracking)
            func: Agent method to call
            *args, **kwargs: Arguments to pass to method

        Returns:
            Method result

        Raises:
            Exception: If circuit breaker is open or method fails
        """
        try:
            return self.circuit_breakers.call(agent_name, func, *args, **kwargs)
        except Exception as e:
            # Circuit breaker exception - agent is failing
            breaker_state = self.circuit_breakers.get_breaker(agent_name).get_state()
            if breaker_state["state"] == "open":
                return {
                    "success": False,
                    "error": f"Agent {agent_name} is temporarily unavailable (circuit breaker open)",
                    "circuit_breaker_state": breaker_state,
                    "retry_after": f"{CIRCUIT_BREAKER_CONFIG['timeout_seconds']}s"
                }
            raise
