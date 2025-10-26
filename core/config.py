"""
Configuration for the multi-agent system
=========================================
API keys, model settings, and system configuration.
"""

import os
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Load .env from project root
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(dotenv_path=env_path)
except ImportError:
    # dotenv not installed, will use system environment variables only
    pass

# ========================================================================
# API CONFIGURATION
# ========================================================================

# Anthropic API Key (for Claude-powered routing in Phase 5)
# Set via environment variable: ANTHROPIC_API_KEY
# Or in .env file: ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# ========================================================================
# MODEL CONFIGURATION
# ========================================================================

# Orchestrator model (Phase 5: Claude-powered routing)
ORCHESTRATOR_MODEL = "claude-sonnet-4-20250514"  # Sonnet 4.5

# Specialized agent model (for future Claude-powered agents)
AGENT_MODEL = "claude-haiku-4-20250611"  # Haiku 4.5

# ========================================================================
# ROUTING CONFIGURATION
# ========================================================================

# Enable Claude-powered routing (Phase 5)
# If False, falls back to pattern matching (Phase 3)
ENABLE_CLAUDE_ROUTING = True

# Claude routing confidence threshold
# Below this threshold, fall back to pattern matching
CLAUDE_ROUTING_CONFIDENCE_THRESHOLD = 0.7

# ========================================================================
# CIRCUIT BREAKER CONFIGURATION
# ========================================================================

# Circuit breaker settings per agent
CIRCUIT_BREAKER_CONFIG = {
    "failure_threshold": 5,  # Number of failures before opening circuit
    "timeout_seconds": 60,  # How long circuit stays open
    "half_open_max_calls": 3  # Max calls in half-open state before closing
}

# ========================================================================
# RATE LIMITING
# ========================================================================

# Rate limit settings
RATE_LIMIT_ENABLED = True
RATE_LIMIT_MAX_REQUESTS_PER_MINUTE = 50
RATE_LIMIT_MAX_TOKENS_PER_MINUTE = 50000

# ========================================================================
# MEMORY CONFIGURATION
# ========================================================================

# Memory base path
PROJECT_ROOT = Path(__file__).parent.parent
MEMORY_BASE_PATH = PROJECT_ROOT / "memories"

# Memory cleanup settings
MEMORY_CLEANUP_ENABLED = True
MEMORY_MAX_AGE_DAYS = 30
MEMORY_MAX_ENTRIES = 1000

# ========================================================================
# HYPERLIQUID API
# ========================================================================

# Official Hyperliquid endpoints
HYPERLIQUID_MAINNET = "https://api.hyperliquid.xyz"
HYPERLIQUID_TESTNET = "https://api.hyperliquid-testnet.xyz"

# Default environment
HYPERLIQUID_ENV = "mainnet"

# ========================================================================
# CACHE CONFIGURATION (Per Data Type)
# ========================================================================

# Cache TTL (Time To Live) settings in seconds
# Adjust these based on how fresh you need each data type to be
CACHE_TTL = {
    # Real-time market data (needs to be very fresh)
    "all_mids": int(os.environ.get("CACHE_TTL_ALL_MIDS", "5")),           # All coin prices: 5 seconds
    "l2_book": int(os.environ.get("CACHE_TTL_L2_BOOK", "3")),             # Order book: 3 seconds
    "meta": int(os.environ.get("CACHE_TTL_META", "60")),                  # Meta info: 60 seconds

    # Historical data (can be cached longer)
    "candle_snapshot": int(os.environ.get("CACHE_TTL_CANDLES", "300")),   # Candles: 5 minutes

    # User-specific data (moderate freshness)
    "user_state": int(os.environ.get("CACHE_TTL_USER_STATE", "30")),      # Account state: 30 seconds
    "user_fills": int(os.environ.get("CACHE_TTL_USER_FILLS", "10")),      # Trade fills: 10 seconds
    "open_orders": int(os.environ.get("CACHE_TTL_OPEN_ORDERS", "5")),     # Open orders: 5 seconds
    "user_funding": int(os.environ.get("CACHE_TTL_USER_FUNDING", "60")),  # Funding: 60 seconds

    # Default for any other endpoint
    "default": int(os.environ.get("CACHE_TTL_DEFAULT", "30"))              # Default: 30 seconds
}

# Enable/disable caching globally
CACHE_ENABLED = os.environ.get("CACHE_ENABLED", "true").lower() == "true"

# ========================================================================
# LOGGING
# ========================================================================

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
