# Hyperliquid Multi-Agent Market Data System
## Distinguished Architecture Plan

## Executive Summary

This architecture leverages Claude's multi-agent orchestration, Haiku models for cost efficiency, Memory Tool for state persistence, Claude Skills with executable scripts for end-to-end data pipelines, and context engineering best practices to create a robust, scalable system for gathering official Hyperliquid market data.

**Key Design Principles:**
- Role-based agent specialization (agents as lightweight orchestrators)
- Context scoping to minimize token usage (scripts execute outside context)
- Official SDK/endpoint validation layers (enforced in Skills scripts)
- Cost optimization through strategic Haiku deployment + Skills execution
- Fault tolerance and data validation (built into Skills)
- Persistent memory for cross-session learning and state management
- **Claude Skills as PRIMARY data collectors** (network-enabled via executable scripts)

---

## 1. Agent Architecture

### 1.1 Agent Hierarchy

```
Orchestrator Agent (Sonnet 4.5) + Memory + Skills
│   Skills: hyperliquid-cache-optimizer
│   Role: Strategic routing (lightweight orchestrator)
│   Token usage: ~2K per request
│
├── Market Data Agents (Haiku 4.5) [Pool of 3-5] + Memory + Skills
│   │   Role: Invoke Skills (minimal agent logic)
│   │   Token usage: ~2K per request (Skills do heavy lifting)
│   │
│   ├── Price & Book Agent
│   │   Skills: hyperliquid-fetch-and-cache, hyperliquid-market-analyzer
│   │
│   ├── Trades & Fills Agent
│   │   Skills: hyperliquid-fetch-and-cache, hyperliquid-data-formatter
│   │
│   └── Candles & Historical Agent
│       Skills: hyperliquid-fetch-and-cache, hyperliquid-backfill-candles
│
├── Account Monitor Agent (Haiku 4.5) + Memory + Skills
│   Skills: hyperliquid-fetch-and-cache, hyperliquid-data-formatter
│
└── Error Recovery Agent (Haiku 4.5) + Memory + Skills
    Skills: (uses error patterns from Memory)

NOTE: Data Validation Agent REMOVED (validation now in Skills)

/memories/ (Persistent Storage)
    ├── orchestrator/
    │   ├── routing_history.json
    │   ├── learned_patterns.json
    │   └── task_performance.json
    ├── validation/
    │   ├── endpoint_whitelist.json
    │   ├── failed_validations.log
    │   └── anomaly_patterns.json
    ├── market_data/
    │   ├── price_cache.json
    │   ├── asset_metadata.json
    │   └── last_fetch_timestamps.json
    ├── errors/
    │   ├── error_patterns.json
    │   ├── recovery_strategies.json
    │   └── rate_limit_state.json
    └── shared/
        ├── hyperliquid_schemas.json
        └── system_health.json

/skills/ (Network-Enabled Executable Pipelines)
    ├── hyperliquid-fetch-and-cache/          ★ PRIMARY DATA COLLECTOR
    │   ├── SKILL.md                          "Fetch, validate, cache pipeline"
    │   ├── scripts/
    │   │   ├── fetch_hyperliquid.py          ← Makes HTTP calls to api.hyperliquid.xyz
    │   │   ├── validate_schema.py            ← Schema validation
    │   │   ├── cache_manager.py              ← Memory Tool interface
    │   │   └── rate_limit_coordinator.py     ← Rate limiting
    │   ├── resources/
    │   │   ├── schemas/*.json                ← Official Hyperliquid schemas
    │   │   ├── endpoints.json                ← Endpoint whitelist
    │   │   └── cache_ttls.json               ← TTL configuration
    │   └── requirements.txt                  (requests, jsonschema, fcntl)
    │
    ├── hyperliquid-market-analyzer/
    │   ├── SKILL.md
    │   ├── scripts/
    │   │   ├── analyze_orderbook.py          ← NumPy/Pandas analysis
    │   │   └── analyze_candles.py            ← Trend/volatility detection
    │   └── resources/indicators/*.json
    │
    ├── hyperliquid-backfill-candles/         ★ MULTI-SESSION BACKFILL
    │   ├── SKILL.md                          "Stateful historical data collector"
    │   ├── scripts/
    │   │   └── backfill.py                   ← Makes HTTP calls + resumes from checkpoint
    │   └── resources/progress_schema.json
    │
    ├── hyperliquid-cache-optimizer/
    │   ├── SKILL.md
    │   └── scripts/analyze_cache_patterns.py ← Reads Memory access logs
    │
    └── hyperliquid-data-formatter/
        ├── SKILL.md
        ├── scripts/
        │   ├── format_to_excel.py
        │   └── format_to_pdf.py
        └── resources/templates/*.html

KEY CHANGE: Skills now make network calls via executable scripts
           (not just post-processing - they ARE the data collectors)
```

### 1.2 Agent Responsibilities

#### **Orchestrator Agent (Sonnet 4.5)**
- **Role**: Strategic planning, task routing, complex decision-making
- **Why Sonnet**: Handles complex routing logic, multi-step planning, ambiguous requests
- **Context Scope**: High-level task definitions, agent capabilities, routing rules
- **Token Budget**: 20K-40K per orchestration cycle
- **Memory Usage**:
  - `/memories/orchestrator/routing_history.json` - Learn optimal routing patterns
  - `/memories/orchestrator/learned_patterns.json` - User preference patterns
  - `/memories/orchestrator/task_performance.json` - Agent performance metrics
- **Responsibilities**:
  - Parse user requests into atomic data collection tasks
  - Route tasks to specialized agents based on learned patterns
  - Aggregate results from multiple agents
  - Handle complex error scenarios requiring reasoning
  - Validate that all data sources are official Hyperliquid endpoints
  - **Learn from routing decisions**: Track which agents handle which tasks most efficiently

#### **Price & Book Agent (Haiku 4.5)** - REVISED TO SKILLS-CENTRIC
- **Role**: Invoke Skills to fetch real-time price data and order books
- **Why Haiku**: Lightweight agent that delegates to Skills (minimal token usage)
- **Token Budget**: 2K-3K per request (down from 8K - Skills do heavy lifting)
- **Primary Skill**: `hyperliquid-fetch-and-cache`
- **Secondary Skill**: `hyperliquid-market-analyzer` (for analysis)
- **Agent Code** (simplified):
  ```python
  async def get_all_mids(self):
      # Single skill invocation (all logic in script)
      result = await invoke_skill("hyperliquid-fetch-and-cache", {
          "endpoint": "allMids",
          "params": {}
      })
      return result['data']
  ```
- **What Skill Does** (executed OUTSIDE context = 0 tokens):
  - Checks `/memories/market_data/price_cache.json`
  - If cache miss: HTTP POST to `https://api.hyperliquid.xyz/info`
  - Validates response against schema
  - Writes to Memory cache
  - Returns data to agent

#### **Trades & Fills Agent (Haiku 4.5)** - REVISED TO SKILLS-CENTRIC
- **Role**: Invoke Skills to fetch trade history and user fills
- **Token Budget**: 2K-3K per request (down from 8K)
- **Primary Skill**: `hyperliquid-fetch-and-cache`
- **Secondary Skill**: `hyperliquid-data-formatter` (for exports)
- **Agent Code** (simplified):
  ```python
  async def get_user_fills(self, user_address):
      result = await invoke_skill("hyperliquid-fetch-and-cache", {
          "endpoint": "userFills",
          "params": {"user": user_address}
      })
      return result['data']
  ```
- **What Skill Does**: Fetches, validates, caches (all in script outside context)

#### **Candles & Historical Agent (Haiku 4.5)** - REVISED TO SKILLS-CENTRIC
- **Role**: Invoke Skills to fetch OHLCV data and perform backfills
- **Token Budget**: 2K-3K per request (down from 10K)
- **Primary Skill**: `hyperliquid-fetch-and-cache`
- **Special Skill**: `hyperliquid-backfill-candles` (for multi-session backfills)
- **Agent Code** (simplified):
  ```python
  async def get_candles(self, coin, interval, start, end):
      # For small queries: use fetch-and-cache
      result = await invoke_skill("hyperliquid-fetch-and-cache", {
          "endpoint": "candleSnapshot",
          "params": {"coin": coin, "interval": interval}
      })
      return result['data']

  async def backfill_candles(self, coin, interval, start_date, end_date):
      # For large historical backfills: use specialized skill
      result = await invoke_skill("hyperliquid-backfill-candles", {
          "coin": coin,
          "interval": interval,
          "start_date": start_date,
          "end_date": end_date
      })
      return result
  ```
- **What backfill Skill Does**:
  - Checks `/memories/market_data/backfill_progress.json` for checkpoint
  - Resumes from last timestamp if interrupted
  - Fetches 5000 candles at a time (pagination)
  - Writes each batch to Memory (immutable cache)
  - Updates progress after each batch
  - All logic in script (0 tokens in context)

#### **Account Monitor Agent (Haiku 4.5)**
- **Role**: Portfolio tracking, subaccounts, rate limits
- **Why Haiku**: Repetitive monitoring tasks
- **Context Scope**: portfolio, userRateLimit, subAccounts methods
- **Token Budget**: 3K-7K per check
- **Memory Usage**:
  - `/memories/market_data/portfolio_history.json` - Track portfolio changes over time
  - `/memories/errors/rate_limit_state.json` - Current rate limit consumption
- **Learning Capability**: Predict when to throttle based on rate limit trends

#### **Error Recovery Agent (Haiku 4.5)**
- **Role**: Handle API errors, retries, fallback strategies
- **Why Haiku**: Well-defined error handling patterns
- **Context Scope**: Error codes, retry strategies, rate limits, fallback endpoints
- **Token Budget**: 2K-5K per recovery attempt
- **Memory Usage**:
  - `/memories/errors/error_patterns.json` - Historical error patterns by endpoint/time
  - `/memories/errors/recovery_strategies.json` - Success rates of different recovery approaches
  - `/memories/errors/circuit_breaker_state.json` - Circuit breaker status per endpoint
- **Learning Capability**: Predict failures, optimize retry timing, circuit breaker intelligence

---

## 2. Memory Tool Integration

### 2.1 Why Memory Tool is Critical

The Memory tool (Anthropic's `context-management-2025-06-27` beta) enables our multi-agent system to:

1. **Cross-Session Learning**: Agents improve over time without manual retraining
2. **State Persistence**: Resume long-running operations (e.g., multi-day backfills)
3. **Cost Optimization**: Reduce repeated API calls by caching immutable data
4. **Intelligent Routing**: Orchestrator learns optimal agent routing patterns
5. **Error Intelligence**: Error Recovery Agent learns failure patterns and optimal strategies
6. **Validation Hardening**: Track and block emerging attack patterns

### 2.2 Memory Architecture

#### **Memory Directory Structure**

```
/memories/
├── orchestrator/
│   ├── routing_history.json          # Historical routing decisions & outcomes
│   ├── learned_patterns.json         # User request patterns & preferences
│   └── task_performance.json         # Agent performance metrics over time
├── validation/
│   ├── endpoint_whitelist.json       # Official Hyperliquid endpoints (source of truth)
│   ├── failed_validations.log        # Attempted unofficial endpoint usage
│   └── anomaly_patterns.json         # Learned suspicious patterns
├── market_data/
│   ├── price_cache.json              # Recent price data (5min TTL)
│   ├── asset_metadata.json           # Persistent metadata from /meta endpoint
│   ├── last_fetch_timestamps.json    # Track fetch frequency per coin
│   ├── user_trade_state.json         # Last processed trade timestamp per user
│   ├── pagination_state.json         # Resume interrupted pagination
│   ├── candle_cache.json             # Immutable historical candle data
│   ├── backfill_progress.json        # Multi-session backfill tracking
│   └── portfolio_history.json        # Portfolio changes over time
├── errors/
│   ├── error_patterns.json           # Historical errors by endpoint/time
│   ├── recovery_strategies.json      # Success rates of recovery approaches
│   ├── circuit_breaker_state.json    # Circuit breaker status per endpoint
│   └── rate_limit_state.json         # Current rate limit consumption
└── shared/
    ├── hyperliquid_schemas.json      # Cached API response schemas
    └── system_health.json            # Overall system health metrics
```

#### **Memory Access Patterns**

| Agent Type | Read Frequency | Write Frequency | Memory Impact |
|------------|---------------|-----------------|---------------|
| Orchestrator | Per request | Per request | High - learns patterns |
| Validation | Per request | On failure | Low - mostly reads whitelist |
| Price & Book | Per request | Every 5 min | Medium - time-based cache |
| Trades & Fills | Per request | On state change | Medium - tracks watermarks |
| Candles & Historical | Per request | On new data | High - caches immutable data |
| Account Monitor | Per check | Per check | Low - metrics only |
| Error Recovery | On error | On error | Medium - learns patterns |

### 2.3 Memory Schemas

#### **Orchestrator Routing History**
```json
// /memories/orchestrator/routing_history.json
{
  "version": "1.0",
  "last_updated": "2025-10-25T12:00:00Z",
  "routing_decisions": [
    {
      "timestamp": "2025-10-25T12:00:00Z",
      "user_request": "Get BTC price",
      "routed_to": "price_book_agent",
      "response_time_ms": 245,
      "success": true,
      "cost_usd": 0.00125
    }
  ],
  "learned_patterns": {
    "price_requests": "price_book_agent",
    "historical_data": "candles_historical_agent",
    "trade_history": "trades_fills_agent"
  },
  "performance_summary": {
    "avg_response_time_ms": 312,
    "success_rate": 0.998,
    "total_requests": 45231
  }
}
```

#### **Validation Endpoint Whitelist**
```json
// /memories/validation/endpoint_whitelist.json
{
  "version": "1.0",
  "immutable": true,
  "official_endpoints": [
    {
      "url": "https://api.hyperliquid.xyz",
      "environment": "mainnet",
      "verified": true,
      "verification_date": "2025-10-25"
    },
    {
      "url": "https://api.hyperliquid-testnet.xyz",
      "environment": "testnet",
      "verified": true,
      "verification_date": "2025-10-25"
    }
  ],
  "official_sdks": [
    "github.com/hyperliquid-dex/hyperliquid-python-sdk",
    "github.com/hyperliquid-dex/hyperliquid-rust-sdk"
  ],
  "blocked_patterns": [
    "*.proxy.*",
    "*.aggregator.*",
    "*third-party*"
  ]
}
```

#### **Market Data Price Cache**
```json
// /memories/market_data/price_cache.json
{
  "version": "1.0",
  "ttl_seconds": 300,
  "last_updated": "2025-10-25T12:05:00Z",
  "prices": {
    "BTC": {
      "mid": "45123.50",
      "timestamp": "2025-10-25T12:05:00Z",
      "source": "https://api.hyperliquid.xyz/info",
      "method": "allMids"
    },
    "ETH": {
      "mid": "2341.20",
      "timestamp": "2025-10-25T12:05:00Z",
      "source": "https://api.hyperliquid.xyz/info",
      "method": "allMids"
    }
  },
  "cache_stats": {
    "hits": 1234,
    "misses": 156,
    "hit_rate": 0.888
  }
}
```

#### **Error Patterns & Recovery**
```json
// /memories/errors/error_patterns.json
{
  "version": "1.0",
  "patterns": [
    {
      "error_type": "rate_limit",
      "endpoint": "https://api.hyperliquid.xyz/info",
      "occurrences": 23,
      "time_of_day_pattern": [14, 15, 16],
      "successful_recovery": "exponential_backoff_3s",
      "recovery_success_rate": 0.956
    },
    {
      "error_type": "network_timeout",
      "endpoint": "https://api.hyperliquid.xyz/info",
      "occurrences": 8,
      "successful_recovery": "retry_with_testnet_fallback",
      "recovery_success_rate": 1.0
    }
  ],
  "learned_strategies": {
    "rate_limit": "back_off_during_14_16_utc",
    "network_timeout": "immediate_fallback_to_testnet"
  }
}
```

#### **Candle Cache (Immutable Data)**
```json
// /memories/market_data/candle_cache.json
{
  "version": "1.0",
  "note": "Historical candles are immutable - never refetch",
  "cached_ranges": {
    "BTC_1h": {
      "start": "2025-01-01T00:00:00Z",
      "end": "2025-10-24T23:59:59Z",
      "candle_count": 7104,
      "storage_location": "s3://hyperliquid-cache/BTC_1h.parquet",
      "never_refetch": true
    }
  },
  "backfill_state": {
    "BTC_1m": {
      "target_start": "2024-01-01T00:00:00Z",
      "current_progress": "2024-06-15T00:00:00Z",
      "percent_complete": 42.3,
      "resume_token": "2024-06-15T00:00:00Z"
    }
  }
}
```

### 2.4 Memory-Driven Optimizations

#### **Optimization 1: Eliminate Redundant API Calls**
```python
# Without memory
def get_btc_price():
    response = call_hyperliquid_api("allMids")  # Every call hits API
    return response["BTC"]

# With memory
def get_btc_price():
    cache = read_memory("/memories/market_data/price_cache.json")
    if cache["BTC"]["timestamp"] > now() - 300:  # 5min TTL
        return cache["BTC"]["mid"]  # Cache hit - no API call

    # Cache miss - fetch and update
    response = call_hyperliquid_api("allMids")
    update_memory("/memories/market_data/price_cache.json", response)
    return response["BTC"]

# Impact: 80-95% reduction in API calls for price data
```

#### **Optimization 2: Intelligent Routing**
```python
# Without memory
def route_request(user_request):
    # Static routing logic
    if "price" in user_request:
        return "price_book_agent"

# With memory
def route_request(user_request):
    history = read_memory("/memories/orchestrator/routing_history.json")
    learned = history["learned_patterns"]

    # Use learned patterns
    for pattern, agent in learned.items():
        if pattern in user_request:
            # Check if this agent has good performance
            perf = history["performance_summary"][agent]
            if perf["success_rate"] > 0.95:
                return agent

    # Fallback to static logic
    return default_routing(user_request)

# Impact: Faster routing, better agent utilization
```

#### **Optimization 3: Predictive Error Handling**
```python
# Without memory
def fetch_data(endpoint):
    try:
        return call_api(endpoint)
    except RateLimitError:
        time.sleep(1)  # Generic backoff
        return call_api(endpoint)

# With memory
def fetch_data(endpoint):
    errors = read_memory("/memories/errors/error_patterns.json")

    # Predict rate limits during peak hours
    if is_peak_hour() and errors["patterns"]["rate_limit"]:
        time.sleep(5)  # Proactive throttling

    try:
        return call_api(endpoint)
    except RateLimitError as e:
        # Use learned optimal strategy
        strategy = errors["learned_strategies"]["rate_limit"]
        return apply_strategy(strategy, endpoint)

# Impact: 40% reduction in failed requests
```

### 2.5 Memory Tool Implementation

#### **Configuration**
```python
# config.py
import anthropic

# Enable memory tool beta
client = anthropic.Anthropic()
BETA_HEADERS = {"context-management-2025-06-27"}

# Memory tool configuration
MEMORY_TOOL = {
    "name": "memory",
    "type": "file_editor",
    "base_path": "/memories"
}

# Supported models
ORCHESTRATOR_MODEL = "claude-sonnet-4.5"  # Supports memory tool
AGENT_MODEL = "claude-haiku-4.5"  # Supports memory tool
```

#### **Agent System Prompt with Memory Instructions**
```python
AGENT_SYSTEM_PROMPT = """
You are a {agent_type} for Hyperliquid market data collection.

CRITICAL MEMORY PROTOCOL:
1. ALWAYS VIEW your memory directory BEFORE doing anything else
2. CHECK for cached data before making API calls
3. UPDATE memory files as work progresses
4. REMOVE stale entries (older than TTL)

Your memory directory: /memories/{agent_dir}/
Your memory files:
{memory_files}

WORKFLOW:
1. View memory: Check for cached data or state
2. Validate: Ensure cache is not stale
3. Act: Use cached data OR fetch fresh data
4. Update: Write results to memory
5. Clean: Remove expired entries

Official Hyperliquid endpoint: https://api.hyperliquid.xyz/info
NEVER use unofficial endpoints.
"""
```

#### **Example: Price Agent with Memory**
```python
# agents/market_data/price_book.py
import anthropic
from datetime import datetime, timedelta

class PriceBookAgentWithMemory:
    def __init__(self):
        self.client = anthropic.Anthropic()
        self.model = "claude-haiku-4.5"
        self.memory_path = "/memories/market_data"

    async def get_all_mids(self):
        """Fetch mid prices with memory-based caching"""

        message = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=[
                {
                    "type": "text",
                    "text": AGENT_SYSTEM_PROMPT.format(
                        agent_type="Price & Book Agent",
                        agent_dir="market_data",
                        memory_files="price_cache.json, asset_metadata.json"
                    ),
                    "cache_control": {"type": "ephemeral"}
                }
            ],
            tools=[
                {"name": "memory", "type": "file_editor"},
                {"name": "fetch_hyperliquid_data"}
            ],
            messages=[
                {
                    "role": "user",
                    "content": """
                    Get all mid prices for coins.

                    1. First, VIEW /memories/market_data/price_cache.json
                    2. Check if cache is fresh (< 5min old)
                    3. If fresh: return cached data
                    4. If stale: fetch from https://api.hyperliquid.xyz/info with type=allMids
                    5. UPDATE cache with new data
                    """
                }
            ]
        )

        # Claude will use memory tool automatically
        return self._parse_response(message)
```

### 2.6 Memory Lifecycle Management

#### **Cache TTL Strategy**
```python
MEMORY_TTL_CONFIG = {
    "/memories/market_data/price_cache.json": 300,  # 5 minutes
    "/memories/market_data/asset_metadata.json": 86400,  # 24 hours (rarely changes)
    "/memories/market_data/candle_cache.json": None,  # Immutable - never expire
    "/memories/orchestrator/routing_history.json": None,  # Keep forever
    "/memories/errors/error_patterns.json": None,  # Keep forever
    "/memories/validation/endpoint_whitelist.json": None,  # Immutable
}
```

#### **Memory Cleanup Policy**
```python
# Automated cleanup job
def cleanup_stale_memory():
    """Remove expired cache entries"""
    for memory_file, ttl in MEMORY_TTL_CONFIG.items():
        if ttl is None:
            continue  # Never expire

        data = read_memory(memory_file)
        cutoff = datetime.now() - timedelta(seconds=ttl)

        # Remove stale entries
        cleaned = {
            k: v for k, v in data.items()
            if parse_timestamp(v["timestamp"]) > cutoff
        }

        write_memory(memory_file, cleaned)

# Run cleanup every hour
schedule.every(1).hours.do(cleanup_stale_memory)
```

### 2.7 Memory Security

#### **Path Validation**
```python
def validate_memory_path(path: str) -> bool:
    """Prevent directory traversal attacks"""
    import os

    # Canonical path resolution
    canonical = os.path.realpath(path)
    base = os.path.realpath("/memories")

    # Must start with /memories/
    if not canonical.startswith(base):
        raise SecurityError(f"Invalid memory path: {path}")

    # Reject traversal sequences
    if ".." in path or path.startswith("/"):
        raise SecurityError(f"Directory traversal attempt: {path}")

    return True
```

#### **Sensitive Data Filtering**
```python
def sanitize_before_storage(data: dict) -> dict:
    """Remove sensitive data before writing to memory"""
    SENSITIVE_KEYS = ["api_key", "private_key", "secret", "password"]

    cleaned = {}
    for key, value in data.items():
        if any(sensitive in key.lower() for sensitive in SENSITIVE_KEYS):
            continue  # Skip sensitive fields
        cleaned[key] = value

    return cleaned
```

---

## 3. Claude Skills Integration (NETWORK-ENABLED)

### 3.1 Why Skills are Critical - REVISED UNDERSTANDING

Claude Skills provide **executable end-to-end data pipelines** via Python/shell scripts:

| Capability | Memory Tool | Claude Skills (Network-Enabled) | Combined Benefit |
|------------|-------------|----------------------------------|------------------|
| **Token Efficiency** | Store data | Execute code (0 tokens) | Minimize context usage |
| **Domain Expertise** | Learn patterns | Encode expertise | Consistent logic |
| **Reusability** | Shared state | Shared code | DRY principle |
| **Processing** | Store results | Transform data | Complete pipeline |
| **Network Calls** | N/A | **HTTP requests in scripts** | **Direct API access** |

**KEY INSIGHT (UPDATED):** Skills = PRIMARY data collectors (not just processors)

**How It Works:**
```
SKILL.md → Claude reads instructions
         → Claude executes scripts/fetch_hyperliquid.py
         → Script makes HTTP POST to https://api.hyperliquid.xyz
         → Script validates, caches in Memory
         → Script returns result to Claude
         → Only result enters context (~500 tokens)
```

**PREVIOUS MISUNDERSTANDING:** "Skills can't make network calls"
**CORRECTED:** Skills **CAN** make network calls via executable scripts (Python requests, curl, etc.)

### 3.2 Core Skills for Hyperliquid (Network-Enabled)

#### **Skill 1: hyperliquid-fetch-and-cache** ★ PRIMARY DATA COLLECTOR
**Purpose:** Unified pipeline for fetching, validating, and caching Hyperliquid data

**Token Impact:**
- Without: 1.5K tokens for schemas + 1K tokens for validation logic = 2.5K per request
- With Skill: 100 tokens metadata + script execution (0 tokens) = **95% token reduction**

**Deployment:** ALL agents (universal validation)

**Key Files:**
- `SKILL.md`: Validation instructions
- `scripts/validate_schema.py`: JSONSchema validation (NumPy/Pandas)
- `resources/schemas/`: Official Hyperliquid response schemas

**Usage Pattern:**
```python
# Agent fetches data
data = await fetch_hyperliquid("allMids")

# Skill validates (script runs, output only in context)
validation = await invoke_skill("hyperliquid-data-validator", data)

if validation["valid"]:
    write_memory("/memories/market_data/price_cache.json", data)
```

#### **Skill 2: hyperliquid-market-analyzer**
**Purpose:** Analyze market data patterns, order books, candles

**Token Impact:**
- Without: 2K tokens for analysis formulas = 2K per request
- With Skill: 100 tokens + script output (200 tokens) = **85% token reduction**

**Deployment:** Price & Book Agent, Candles Agent

**Key Files:**
- `scripts/analyze_orderbook.py`: Bid/ask spread, liquidity depth, imbalance
- `scripts/analyze_candles.py`: Trend detection, volatility, patterns
- `resources/indicators/`: Technical indicator definitions

**Analysis Capabilities:**
- Order book: Spread, depth, imbalance, support/resistance
- Candles: Trend (up/down/sideways), volatility (ATR), volume profile
- Trade flow: Buy/sell pressure, whale detection

#### **Skill 3: hyperliquid-cache-optimizer**
**Purpose:** Optimize Memory Tool caching strategies based on usage patterns

**Token Impact:**
- Without: Manual analysis + tuning
- With Skill: Automated recommendations = **time savings**

**Deployment:** Orchestrator Agent (runs periodically)

**Key Files:**
- `scripts/analyze_cache_patterns.py`: Access pattern analysis, TTL recommendations

**Optimization Outputs:**
- Per-coin TTL recommendations based on hit rates
- Peak hour analysis for proactive throttling
- Storage growth predictions

#### **Skill 4: hyperliquid-data-formatter**
**Purpose:** Transform Hyperliquid data into CSV, Excel, PDF reports

**Token Impact:**
- Without: 3K+ tokens for formatting logic
- With Skill: Leverages Anthropic's pre-built docx/xlsx/pdf skills = **90% token reduction**

**Deployment:** Trades & Fills Agent, Account Monitor Agent

**Key Files:**
- `scripts/format_to_excel.py`: Professional Excel workbooks with charts
- `scripts/format_to_pdf.py`: Branded PDF reports
- `resources/templates/`: HTML templates for reports

#### **Skill 5: hyperliquid-strategy-executor**
**Purpose:** Backtest trading strategies on Hyperliquid data (read-only analysis)

**Token Impact:**
- Without: 5K+ tokens for strategy logic + metrics
- With Skill: 100 tokens + script output = **98% token reduction**

**Deployment:** Candles Agent (advanced use case)

**Key Files:**
- `scripts/backtest_strategy.py`: Mean reversion, trend following, arbitrage
- `scripts/calculate_metrics.py`: Sharpe ratio, max drawdown, win rate

**Safety Note:** Read-only backtesting. No actual trade execution.

### 3.3 Skills Workflow Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: Agent fetches from Hyperliquid (Memory check first)    │
├─────────────────────────────────────────────────────────────────┤
│ price_cache = read_memory("/memories/market_data/price_cache") │
│ if cache_fresh: return cache                                    │
│ else: data = fetch("https://api.hyperliquid.xyz/info")         │
└────────────────────────────┬────────────────────────────────────┘
                             │ Raw data
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: Skill validates data (executable, not in context)      │
├─────────────────────────────────────────────────────────────────┤
│ validation = invoke_skill("hyperliquid-data-validator", data)  │
│ → SKILL.md loaded (~3K tokens, once)                            │
│ → scripts/validate_schema.py executes (0 tokens)               │
│ → Output: {"valid": true} (50 tokens)                          │
└────────────────────────────┬────────────────────────────────────┘
                             │ Validated data
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: Skill analyzes data (optional, for insights)           │
├─────────────────────────────────────────────────────────────────┤
│ analysis = invoke_skill("hyperliquid-market-analyzer", data)   │
│ → scripts/analyze_orderbook.py executes (0 tokens)             │
│ → Output: {"spread_bps": 2.5, "imbalance": 0.12} (200 tokens)  │
└────────────────────────────┬────────────────────────────────────┘
                             │ Analyzed data
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 4: Write to Memory Tool                                   │
├─────────────────────────────────────────────────────────────────┤
│ write_memory("/memories/market_data/price_cache.json", {       │
│   "data": validated_data,                                       │
│   "analysis": analysis,                                         │
│   "timestamp": now()                                            │
│ })                                                              │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
                      [ Return to user ]
```

**Token Breakdown:**
- Without Skills: 11.5K tokens (system + schemas + logic + data)
- With Skills: 7.3K tokens (system + metadata + data + outputs)
- **Savings: 36% per request**

### 3.4 Skills API Configuration

#### **Beta Headers Required**
```python
BETA_HEADERS = {
    "context-management-2025-06-27",  # Memory Tool
    "code-execution-2025-08-25",      # Skills execution
    "files-api-2025-04-14",           # File handling
    "skills-2025-10-02"               # Skills API
}
```

#### **Skills Registration per Agent**
```python
AGENT_SKILLS_MAP = {
    "orchestrator": [
        "hyperliquid-cache-optimizer"
    ],
    "validation": [
        "hyperliquid-data-validator"
    ],
    "price_book": [
        "hyperliquid-data-validator",
        "hyperliquid-market-analyzer"
    ],
    "trades_fills": [
        "hyperliquid-data-validator",
        "hyperliquid-data-formatter"
    ],
    "candles": [
        "hyperliquid-data-validator",
        "hyperliquid-strategy-executor"
    ],
    "account_monitor": [
        "hyperliquid-data-formatter"
    ],
    "error_recovery": []
}
```

### 3.5 Token & Cost Impact

#### **Token Usage Comparison**

| Task | Without Skills | With Skills | Savings |
|------|----------------|-------------|---------|
| Validate API response | 2.5K tokens | 150 tokens | **94%** |
| Analyze order book | 2K tokens | 300 tokens | **85%** |
| Format to Excel | 3K tokens | 200 tokens | **93%** |
| Backtest strategy | 5K tokens | 400 tokens | **92%** |
| **Average** | **3.1K tokens** | **260 tokens** | **92%** |

#### **Cost Impact (per 1000 requests/day)**

**Original (Haiku + Memory):**
- $450/month

**With Skills:**
- Base agent cost: $350/month (20% reduction from token savings)
- Skills overhead: ~$20/month (amortized script execution)
- **Total: $370/month**

**Additional Savings: $80/month = $960/year**

**Combined Total Savings:**
- Baseline: $2.7K-13.5K/month
- With Haiku + Memory + Skills: **$370/month**
- **Total Savings: 86-97% reduction**

### 3.6 Skills Deployment Roadmap

#### **Week 2: Core Validation**
```bash
# Deploy hyperliquid-data-validator to all agents
claude-skills deploy hyperliquid-data-validator/
# → All agents automatically discover and use for validation
```

#### **Week 3: Analysis & Optimization**
```bash
# Deploy analysis and optimization skills
claude-skills deploy hyperliquid-market-analyzer/
claude-skills deploy hyperliquid-cache-optimizer/
```

#### **Week 4: Formatting & Reporting**
```bash
# Deploy formatting skill (uses Anthropic's xlsx/pdf skills)
claude-skills deploy hyperliquid-data-formatter/
```

#### **Week 5: Advanced Strategies**
```bash
# Deploy backtesting skill for power users
claude-skills deploy hyperliquid-strategy-executor/
```

### 3.7 Skills vs Memory: Complementary Roles

| Aspect | Memory Tool | Claude Skills |
|--------|-------------|---------------|
| **Purpose** | Data persistence | Code execution |
| **Content** | JSON, logs, state | Python/JS scripts |
| **Token Cost** | Variable (data size) | ~100 (metadata) |
| **Execution** | Read/write files | Run scripts |
| **Learning** | Store over time | Encode expertise |
| **Network** | N/A | ❌ No external calls |
| **Use Case** | "Remember BTC price" | "Validate BTC price" |

**Together:** Memory stores data, Skills process data

**Example Synergy:**
```
1. Memory: Cache "BTC price: 45000 @ 14:00"
2. Skills: Validate schema, analyze spread
3. Memory: Store "validated + analyzed @ 14:00"
4. Skills: Format to PDF report
5. Memory: Store "report_id: xyz @ 14:05"
```

---

## 4. Context Engineering Strategy

### 4.1 Context Scoping Principles

Following Anthropic's context management best practices:

#### **Principle 1: Minimal Viable Context**
Each agent receives ONLY the context necessary for its specific task:

```python
# BAD - Sending full API documentation to every agent
context = {
    "full_api_docs": load_entire_docs(),  # 50K+ tokens
    "task": "get BTC price"
}

# GOOD - Scoped context for Price Agent
context = {
    "endpoint": "https://api.hyperliquid.xyz/info",
    "method": "POST",
    "payload": {"type": "allMids"},
    "expected_response": {"BTC": "45000.5", ...},
    "task": "get BTC price"
}  # ~500 tokens
```

#### **Principle 2: Structured Prompts with Tool Use**
Agents use Claude's tool use capabilities to ensure structured output:

```python
tools = [
    {
        "name": "fetch_hyperliquid_data",
        "description": "Fetch data from official Hyperliquid API",
        "input_schema": {
            "type": "object",
            "properties": {
                "endpoint": {"type": "string", "enum": ["https://api.hyperliquid.xyz/info"]},
                "payload": {"type": "object"},
                "validation_required": {"type": "boolean", "default": True}
            },
            "required": ["endpoint", "payload"]
        }
    }
]
```

#### **Principle 3: Prompt Caching for Repeated Context**
Cache static context that doesn't change across requests:

```python
# Cacheable context (marked for prompt caching)
STATIC_CONTEXT = """
Official Hyperliquid API Endpoints:
- Mainnet: https://api.hyperliquid.xyz
- Testnet: https://api.hyperliquid-testnet.xyz

Never use:
- Unofficial APIs
- Third-party aggregators
- Proxy services
"""

# Dynamic context (changes per request)
dynamic_context = {
    "coin": user_requested_coin,
    "timeframe": user_requested_timeframe
}
```

### 2.2 Context Templates Per Agent

#### **Orchestrator Context Template**
```yaml
system_prompt: |
  You are the Orchestrator Agent for Hyperliquid market data collection.
  Route tasks to specialized agents based on data type required.

  Available Agents:
  - price_book_agent: Real-time prices, order books
  - trades_fills_agent: Trade history, user fills
  - candles_historical_agent: OHLCV data
  - account_monitor_agent: Portfolio, rate limits

  CRITICAL: All data must come from official Hyperliquid endpoints.
  Validate all responses through the data_validation_agent.

tools:
  - route_to_agent
  - validate_data_source
  - aggregate_results
```

#### **Haiku Agent Context Template**
```yaml
system_prompt: |
  You are a specialized data collection agent.
  Your ONLY job is to fetch data from: https://api.hyperliquid.xyz/info

  Method: {agent_specific_method}
  Parameters: {agent_specific_params}
  Expected Response: {response_schema}

  If any error occurs, delegate to error_recovery_agent.
  Never use unofficial endpoints.

tools:
  - make_api_request
  - parse_response
  - report_error
```

---

## 3. Cost Optimization Strategy

### 3.1 Token Usage Breakdown

| Agent Type | Model | Avg Tokens/Request | Cost per 1M Tokens | Cost/Request |
|------------|-------|-------------------|-------------------|--------------|
| Orchestrator | Sonnet 4.5 | 30,000 | $3.00 input / $15.00 output | $0.09-$0.45 |
| Data Agents | Haiku 3.5 | 5,000 | $0.25 input / $1.25 output | $0.00125-$0.00625 |
| Validator | Haiku 3.5 | 2,000 | $0.25 input / $1.25 output | $0.0005-$0.0025 |

**Estimated Cost for 1000 Market Data Requests:**
- Without optimization: ~$90-450 (all Sonnet)
- With this architecture: ~$5-20 (Orchestrator + Haiku pool)
- **Cost Reduction: 80-95%**

### 3.2 Optimization Techniques

#### **Batching Requests**
Group similar requests to amortize orchestration overhead:
```python
# Instead of 100 individual requests
for coin in coins:
    get_price(coin)  # 100 orchestration calls

# Batch into single orchestration
get_all_prices(coins)  # 1 orchestration + parallel Haiku calls
```

#### **Prompt Caching**
Cache static context across agent invocations:
- Official endpoint URLs (500 tokens) → 90% discount on cache hits
- API method schemas (1000 tokens) → 90% discount
- Error handling patterns (800 tokens) → 90% discount

**Savings Example:**
- First request: 5000 tokens @ $0.25 = $0.00125
- Cached requests: 2700 fresh + 2300 cached @ $0.025 = $0.000675 + $0.0000575 = $0.0007325
- **42% cost reduction per cached request**

#### **Response Streaming**
For time-sensitive data, stream responses to reduce latency:
```python
async def stream_market_data():
    async for chunk in haiku_agent.stream():
        yield process_chunk(chunk)
        # User gets data as it arrives
```

---

## 4. Data Validation & Reliability

### 4.1 Validation Layers

#### **Layer 1: Pre-flight Validation (Data Validation Agent)**
```python
def validate_request(request):
    """Ensure request targets official endpoints only"""
    assert request.url in OFFICIAL_ENDPOINTS, \
        f"Rejected: {request.url} is not an official Hyperliquid endpoint"
    assert request.method == "POST", \
        "Hyperliquid Info API only accepts POST requests"
    assert "type" in request.payload, \
        "Missing required 'type' parameter"
    return True
```

#### **Layer 2: Response Validation**
```python
def validate_response(response, expected_schema):
    """Validate response structure matches Hyperliquid schema"""
    # Check for official error format
    if "error" in response:
        return handle_official_error(response["error"])

    # Schema validation
    validate_schema(response, expected_schema)

    # Data sanity checks
    if "price" in response:
        assert response["price"] > 0, "Invalid price"

    return True
```

#### **Layer 3: Cross-Validation**
```python
def cross_validate_data(data_sources):
    """Compare data from multiple endpoints for consistency"""
    prices = [source.get_price("BTC") for source in data_sources]
    variance = calculate_variance(prices)

    if variance > THRESHOLD:
        log_warning("Price variance detected", variance)
        # Use median or most recent

    return select_best_value(prices)
```

### 4.2 Error Handling Strategy

#### **Retry Logic with Exponential Backoff**
```python
async def fetch_with_retry(endpoint, payload, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = await call_api(endpoint, payload)
            return response
        except RateLimitError:
            wait_time = 2 ** attempt  # 1s, 2s, 4s
            await asyncio.sleep(wait_time)
        except NetworkError as e:
            if attempt == max_retries - 1:
                raise
            log_error(f"Attempt {attempt + 1} failed", e)

    raise MaxRetriesExceeded()
```

#### **Fallback Strategies**
```python
FALLBACK_CHAIN = [
    "https://api.hyperliquid.xyz/info",  # Primary
    "https://api.hyperliquid-testnet.xyz/info",  # Testnet fallback
    # No third-party fallbacks - testnet data better than unofficial data
]
```

---

## 5. Implementation Roadmap

### Phase 1: Core Infrastructure (Week 1)
- [ ] **Initialize Memory Tool infrastructure**
  - [ ] Create `/memories/` directory structure
  - [ ] Implement path validation and security checks
  - [ ] Set up beta header: `context-management-2025-06-27`
- [ ] **Set up Orchestrator Agent with Sonnet 4.5**
  - [ ] Configure with Memory Tool access
  - [ ] Initialize `/memories/orchestrator/` memory files
- [ ] **Implement Data Validation Agent (Haiku 4.5)**
  - [ ] Configure with Memory Tool access
  - [ ] Create `/memories/validation/endpoint_whitelist.json` (immutable)
- [ ] Create base agent communication protocol
- [ ] Establish official endpoint validation system
- [ ] Set up prompt caching infrastructure

**Validation Checkpoint:**
- All API calls validated against official endpoints
- Orchestrator successfully routes to validation agent
- Prompt caching reduces token usage by >40%
- **Memory Tool**: All agents can read/write to `/memories/`
- **Memory Tool**: Endpoint whitelist properly initialized

### Phase 2: Specialized Data Agents (Week 2)
- [ ] **Implement Price & Book Agent (Haiku 4.5)**
  - [ ] Configure Memory Tool access
  - [ ] Initialize `/memories/market_data/price_cache.json`
  - [ ] Initialize `/memories/market_data/asset_metadata.json`
  - [ ] Implement 5-minute TTL caching logic
- [ ] **Implement Trades & Fills Agent (Haiku 4.5)**
  - [ ] Configure Memory Tool access
  - [ ] Initialize `/memories/market_data/user_trade_state.json`
  - [ ] Initialize `/memories/market_data/pagination_state.json`
  - [ ] Implement pagination watermark tracking
- [ ] **Implement Candles & Historical Agent (Haiku 4.5)**
  - [ ] Configure Memory Tool access
  - [ ] Initialize `/memories/market_data/candle_cache.json`
  - [ ] Initialize `/memories/market_data/backfill_progress.json`
  - [ ] Implement immutable data caching (never refetch historical candles)
- [ ] Create agent pool management system
- [ ] Add response schema validation
- [ ] **Implement memory cleanup scheduler**

**Validation Checkpoint:**
- Each agent successfully fetches data from official endpoints
- Response schemas match Hyperliquid documentation
- Error handling delegates to Error Recovery Agent
- **Memory Tool**: Price cache reduces API calls by >80%
- **Memory Tool**: Candle agent never refetches immutable historical data
- **Memory Tool**: Pagination resumes correctly after interruption

### Phase 3: Account & Monitoring (Week 3)
- [ ] **Implement Account Monitor Agent (Haiku 4.5)**
  - [ ] Configure Memory Tool access
  - [ ] Initialize `/memories/market_data/portfolio_history.json`
  - [ ] Initialize `/memories/errors/rate_limit_state.json`
  - [ ] Implement rate limit prediction logic
- [ ] **Implement Error Recovery Agent (Haiku 4.5)**
  - [ ] Configure Memory Tool access
  - [ ] Initialize `/memories/errors/error_patterns.json`
  - [ ] Initialize `/memories/errors/recovery_strategies.json`
  - [ ] Initialize `/memories/errors/circuit_breaker_state.json`
  - [ ] Implement learning-based retry strategies
- [ ] Add retry logic with exponential backoff
- [ ] Create cross-validation system
- [ ] Set up logging and observability
- [ ] **Implement shared memory for system health**
  - [ ] Initialize `/memories/shared/system_health.json`
  - [ ] Initialize `/memories/shared/hyperliquid_schemas.json`

**Validation Checkpoint:**
- Account data correctly fetched for test users
- Error recovery handles all common API errors
- Cross-validation detects anomalies
- **Memory Tool**: Error Recovery Agent learns optimal retry strategies
- **Memory Tool**: Circuit breakers activate based on learned patterns
- **Memory Tool**: Rate limit predictions prevent throttling

### Phase 4: Optimization & Testing (Week 4)
- [ ] Implement request batching
- [ ] Optimize prompt caching strategy
- [ ] **Analyze memory tool effectiveness**
  - [ ] Measure cache hit rates across all agents
  - [ ] Analyze learning curves (routing, error recovery)
  - [ ] Optimize TTL values based on actual usage patterns
  - [ ] Profile memory storage growth
- [ ] Load testing with 10K requests
- [ ] **Memory stress testing**
  - [ ] Test concurrent memory access across agent pool
  - [ ] Validate memory cleanup under high load
  - [ ] Test backfill resume after system restart
- [ ] Cost analysis and optimization
  - [ ] Calculate cost savings from memory-based caching
  - [ ] Measure reduction in redundant API calls
- [ ] Create runbooks for common scenarios

**Validation Checkpoint:**
- System handles 1000 req/min without issues
- Cost reduction >80% vs all-Sonnet baseline
- 99.9% of data from official endpoints
- **Memory Tool**: Cache hit rate >70% for price data
- **Memory Tool**: Zero refetches of immutable historical data
- **Memory Tool**: Orchestrator routing improves over 1000+ requests

### Phase 5: Production Hardening (Week 5)
- [ ] Add rate limit monitoring (using memory-based predictions)
- [ ] Implement circuit breakers (using learned patterns)
- [ ] Create data quality dashboards
- [ ] Set up alerting for unofficial endpoint attempts
- [ ] **Memory monitoring & alerting**
  - [ ] Alert on failed memory writes
  - [ ] Monitor memory storage growth
  - [ ] Dashboard for cache hit rates
  - [ ] Alert on endpoint whitelist modifications
- [ ] **Memory backup & recovery**
  - [ ] Implement memory backup strategy
  - [ ] Test restoration from backups
  - [ ] Document disaster recovery procedures
- [ ] Documentation and handoff
  - [ ] Document memory schemas
  - [ ] Create memory management runbooks
  - [ ] Train team on memory tool usage

**Validation Checkpoint:**
- Zero unofficial endpoint calls in 48hr test
- All error scenarios handled gracefully
- Team trained on architecture
- **Memory Tool**: Backup/restore procedures validated
- **Memory Tool**: Monitoring dashboards operational
- **Memory Tool**: 7-day continuous operation without memory issues

---

## 6. Monitoring & Observability

### 6.1 Key Metrics

#### **Data Quality Metrics**
- `official_endpoint_ratio`: % of calls to official endpoints (target: 100%)
- `validation_pass_rate`: % of responses passing validation (target: >99%)
- `data_consistency_score`: Cross-validation consistency (target: >95%)

#### **Performance Metrics**
- `p50_latency`: Median response time (target: <500ms)
- `p99_latency`: 99th percentile response time (target: <2s)
- `request_success_rate`: % of successful requests (target: >99.5%)

#### **Cost Metrics**
- `cost_per_request`: Average cost per data fetch (target: <$0.01)
- `token_usage_per_agent`: Token consumption by agent type
- `cache_hit_rate`: Prompt cache hit rate (target: >60%)

#### **Memory Tool Metrics**
- `memory_cache_hit_rate`: % of requests served from memory cache (target: >70%)
- `memory_api_call_reduction`: % reduction in API calls due to caching (target: >80%)
- `memory_storage_size_mb`: Total memory storage size (alert: >1GB)
- `memory_write_latency_ms`: Time to write to memory (target: <50ms)
- `memory_read_latency_ms`: Time to read from memory (target: <10ms)
- `immutable_data_refetch_count`: Refetches of historical data (target: 0)
- `orchestrator_learning_trend`: Improvement in routing decisions over time
- `error_recovery_success_rate_trend`: Improvement in error recovery over time

### 6.2 Alerting Rules

```yaml
alerts:
  - name: unofficial_endpoint_detected
    condition: official_endpoint_ratio < 1.0
    severity: CRITICAL
    action: immediate_page

  - name: validation_failure_spike
    condition: validation_pass_rate < 0.95
    severity: HIGH
    action: notify_on_call

  - name: memory_storage_bloat
    condition: memory_storage_size_mb > 1000
    severity: MEDIUM
    action: review_cleanup_policy

  - name: immutable_data_refetch
    condition: immutable_data_refetch_count > 0
    severity: HIGH
    action: investigate_cache_bug

  - name: memory_write_failure
    condition: memory_write_errors > 0
    severity: HIGH
    action: check_filesystem_health

  - name: low_cache_hit_rate
    condition: memory_cache_hit_rate < 0.5
    severity: HIGH
    action: notify_on_call

  - name: cost_anomaly
    condition: cost_per_request > 0.05
    severity: MEDIUM
    action: investigate

  - name: high_error_rate
    condition: request_success_rate < 0.99
    severity: HIGH
    action: check_api_status
```

---

## 7. Security Considerations

### 7.1 API Key Management
- Store API keys in environment variables, never in code
- Use separate keys for testnet vs mainnet
- Rotate keys every 90 days
- Monitor for unusual API usage patterns

### 7.2 Endpoint Whitelisting
```python
ENDPOINT_WHITELIST = {
    "https://api.hyperliquid.xyz",
    "https://api.hyperliquid-testnet.xyz"
}

def is_official_endpoint(url):
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    return base_url in ENDPOINT_WHITELIST
```

### 7.3 Rate Limit Management
- Track WebSocket connections (max 1000/IP)
- Implement request queue to stay under limits
- Use multiple IPs if needed for high-volume scenarios

---

## 8. Code Structure

### 8.1 Project Layout
```
claudeCode_hyperTinker/
├── agents/
│   ├── orchestrator.py          # Sonnet 4.5 orchestrator
│   ├── validators.py            # Data validation agent
│   ├── market_data/
│   │   ├── price_book.py        # Price & Book Agent
│   │   ├── trades_fills.py      # Trades & Fills Agent
│   │   └── candles.py           # Candles & Historical Agent
│   ├── account_monitor.py       # Account Monitor Agent
│   └── error_recovery.py        # Error Recovery Agent
├── core/
│   ├── config.py                # Official endpoints config
│   ├── schemas.py               # Response schemas
│   ├── validation.py            # Validation logic
│   └── caching.py               # Prompt caching utilities
├── utils/
│   ├── api_client.py            # HTTP client for Hyperliquid
│   ├── retry.py                 # Retry logic
│   └── monitoring.py            # Metrics and logging
├── tests/
│   ├── test_validators.py
│   ├── test_agents.py
│   └── test_integration.py
├── ARCHITECTURE.md              # This file
└── README.md
```

### 8.2 Example Agent Implementation

```python
# agents/market_data/price_book.py
import anthropic
from core.config import OFFICIAL_ENDPOINTS, HAIKU_MODEL
from core.validation import validate_endpoint
from utils.api_client import HyperliquidClient

class PriceBookAgent:
    def __init__(self):
        self.client = anthropic.Anthropic()
        self.hl_client = HyperliquidClient()
        self.model = HAIKU_MODEL

        # Cacheable system prompt (static context)
        self.system_prompt = """
        You are a Price & Book Agent for Hyperliquid market data.

        Official Endpoint: https://api.hyperliquid.xyz/info

        Available Methods:
        1. allMids - Get mid prices for all coins
        2. l2Book - Get L2 order book for specific coin
        3. meta - Get metadata for all assets

        Response Format:
        {
          "success": true,
          "data": <fetched_data>,
          "endpoint_used": "https://api.hyperliquid.xyz/info"
        }

        If any error occurs, return:
        {
          "success": false,
          "error": <error_message>,
          "delegate_to": "error_recovery_agent"
        }

        CRITICAL: Only use official Hyperliquid endpoints.
        """

    async def get_all_mids(self) -> dict:
        """Fetch mid prices for all coins"""
        # Validate endpoint before making request
        endpoint = OFFICIAL_ENDPOINTS["mainnet"]
        validate_endpoint(endpoint)

        # Prepare request
        payload = {"type": "allMids"}

        # Use Claude to structure the request and parse response
        message = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=[
                {
                    "type": "text",
                    "text": self.system_prompt,
                    "cache_control": {"type": "ephemeral"}  # Cache static prompt
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": f"Fetch all mid prices using endpoint {endpoint} and payload {payload}"
                }
            ]
        )

        # Parse Claude's response and make actual API call
        response = await self.hl_client.post(endpoint, payload)

        return {
            "success": True,
            "data": response,
            "endpoint_used": endpoint
        }
```

---

## 9. Cost-Benefit Analysis

### 9.1 Baseline (All Sonnet 4.5)
- 1000 requests/day
- 30K tokens average per request
- Cost: $90-450/day = $2.7K-13.5K/month

### 9.2 Proposed Architecture
- 1000 requests/day
- Orchestrator: 100 calls/day @ 30K tokens = ~$10/day
- Haiku agents: 900 calls/day @ 5K tokens = ~$5/day
- Total: ~$15/day = **$450/month**

### 9.3 Savings
- Monthly: $2,250 - $13,050 (83-97% reduction)
- Annual: $27K - $156K saved

### 9.4 Additional Benefits
- **Reliability**: Multi-layer validation ensures official data sources
- **Scalability**: Agent pool can scale horizontally
- **Maintainability**: Specialized agents easier to debug and update
- **Observability**: Fine-grained metrics per agent type

---

## 10. Critical Success Factors

1. **100% Official Endpoint Usage**
   - Data Validation Agent reviews every request
   - Endpoint whitelist strictly enforced
   - Alerts fire on any unofficial endpoint attempt

2. **Cost Efficiency**
   - Haiku for 80%+ of requests
   - Prompt caching for repeated context
   - Batching to reduce orchestration overhead

3. **Reliability**
   - Multi-layer validation
   - Exponential backoff retries
   - Cross-validation for data quality

4. **Observability**
   - Real-time metrics dashboards
   - Alerting on anomalies
   - Cost tracking per agent type

5. **Maintainability**
   - Clear separation of concerns
   - Comprehensive testing
   - Documentation for each agent

---

## Appendix A: Official Hyperliquid Endpoints Reference

### Info Endpoint Methods (All POST to https://api.hyperliquid.xyz/info)

| Method | Purpose | Response Limit | Use Case |
|--------|---------|----------------|----------|
| `allMids` | All coin mid prices | N/A | Real-time price data |
| `l2Book` | Order book snapshot | 20 levels/side | Market depth |
| `candleSnapshot` | OHLCV data | 5000 candles | Historical analysis |
| `userFills` | User trade history | 2000 records | Trade tracking |
| `userFillsByTime` | Time-range fills | 500 elements | Historical fills |
| `historicalOrders` | Order history | 2000 records | Order tracking |
| `openOrders` | Current open orders | N/A | Active order monitoring |
| `frontendOpenOrders` | UI-formatted orders | N/A | Display purposes |
| `orderStatus` | Single order status | N/A | Order verification |
| `portfolio` | Account value history | N/A | Performance tracking |
| `userRateLimit` | Rate limit status | N/A | Quota monitoring |
| `subAccounts` | Subaccount margins | N/A | Multi-account management |
| `meta` | Asset metadata | N/A | Symbol/tick size info |

### WebSocket Subscriptions
- Endpoint: `wss://api.hyperliquid.xyz/ws`
- Max connections: 1000/IP
- Subscription types: trades, l2Book, userEvents, candle

---

## Appendix B: Token Usage Optimization Checklist

- [ ] Use Haiku for all deterministic data fetching
- [ ] Reserve Sonnet for complex routing and reasoning
- [ ] Cache static context (endpoint URLs, schemas, rules)
- [ ] Batch similar requests to amortize orchestration
- [ ] Use streaming for time-sensitive data
- [ ] Implement response pagination to avoid large payloads
- [ ] Minimize context window with scoped prompts
- [ ] Use structured output (JSON) to reduce token variance
- [ ] Profile token usage per agent weekly
- [ ] Set token budgets and alerts per agent type

---

## Appendix C: Testing Strategy

### Unit Tests
- Each agent method tested in isolation
- Mock Hyperliquid API responses
- Validate endpoint whitelisting logic

### Integration Tests
- End-to-end request routing
- Multi-agent coordination
- Error recovery workflows

### Load Tests
- 1000 req/min sustained load
- Agent pool scaling behavior
- Rate limit handling

### Validation Tests
- Reject unofficial endpoints
- Schema validation for all responses
- Cross-validation accuracy

### Cost Tests
- Measure actual token usage vs projections
- Verify prompt caching effectiveness
- Track cost per request type

---

**Document Version**: 1.0
**Last Updated**: 2025-10-25
**Author**: Distinguished Applied AI Engineer
**Stakeholders**: Engineering Team, Finance, Operations
