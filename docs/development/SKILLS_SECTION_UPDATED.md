# Skills Section - Updated for Network-Enabled Architecture

This content should replace section 3.2 onwards in ARCHITECTURE.md

---

### 3.2 Core Skills for Hyperliquid (Network-Enabled)

#### **Skill 1: hyperliquid-fetch-and-cache** ★ PRIMARY DATA COLLECTOR

**Purpose:** Unified end-to-end pipeline: fetch → validate → cache → return

**Token Impact:**
- Without Skill: Agent code for cache check (500) + API call (1K) + validation (1K) + cache write (500) = **3K tokens**
- With Skill: Skill invocation (100) + result (500) = **600 tokens**
- **Savings: 80% token reduction**

**What This Skill Does (all in executable script):**
1. Reads `/memories/market_data/{endpoint}_cache.json` to check cache
2. If fresh: returns cached data (no API call)
3. If stale: coordinates rate limit via `/memories/shared/rate_limit_state.json`
4. Makes HTTP POST to `https://api.hyperliquid.xyz/info`
5. Validates response against schema in `resources/schemas/`
6. Writes validated data to Memory cache (atomic write with file locking)
7. Returns result to agent

**Script: scripts/fetch_hyperliquid.py** (200 lines - see SKILLS_NETWORK_REVISION.md for full code)

**Key Features:**
```python
# Official endpoint validation (enforced in script)
OFFICIAL_ENDPOINTS = {
    "mainnet": "https://api.hyperliquid.xyz",
    "testnet": "https://api.hyperliquid-testnet.xyz"
}

# Network call (requests library)
response = requests.post(
    f"{OFFICIAL_ENDPOINTS['mainnet']}/info",
    json={"type": endpoint, **params},
    timeout=10
)

# Validation
validate_response(endpoint, response.json())

# Memory write with file locking (prevents race conditions)
with open(cache_file, 'r+') as f:
    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
    # ... write data ...
    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
```

**Deployment:** ALL agents use this skill (universal data fetcher)

**Endpoints Supported:**
- `allMids` - All coin mid prices
- `l2Book` - Order book snapshot (20 levels)
- `candleSnapshot` - OHLCV data (up to 5000 candles)
- `userFills` - Trade history (up to 2000 fills)
- `historicalOrders` - Order history
- `openOrders` - Current open orders
- `portfolio` - Account value history
- `meta` - Asset metadata

---

#### **Skill 2: hyperliquid-market-analyzer**

**Purpose:** Analyze fetched data (order books, candles, trade flow)

**Token Impact:**
- Without Skill: NumPy/Pandas code in agent context = **2K tokens**
- With Skill: Analysis output only = **300 tokens**
- **Savings: 85% token reduction**

**What This Skill Does:**

**Order Book Analysis (script: analyze_orderbook.py):**
```python
import numpy as np

def analyze_orderbook(data):
    bids = [l for l in data['levels'] if float(l[1]) > 0]
    asks = [l for l in data['levels'] if float(l[1]) < 0]

    spread = float(asks[0][0]) - float(bids[0][0])
    bid_depth = sum(float(l[1]) for l in bids[:10])
    ask_depth = sum(abs(float(l[1])) for l in asks[:10])

    return {
        "spread_bps": (spread / float(bids[0][0])) * 10000,
        "bid_depth_10": bid_depth,
        "ask_depth_10": ask_depth,
        "imbalance": (bid_depth - ask_depth) / (bid_depth + ask_depth)
    }
```

**Candle Analysis (script: analyze_candles.py):**
```python
import pandas as pd

def analyze_candles(data):
    df = pd.DataFrame(data, columns=['t', 'o', 'h', 'l', 'c', 'v'])
    df['sma_20'] = df['c'].rolling(20).mean()
    df['volatility'] = df['c'].pct_change().std() * np.sqrt(365)

    return {
        "trend": "uptrend" if df['c'].iloc[-1] > df['sma_20'].iloc[-1] else "downtrend",
        "volatility": float(df['volatility'].iloc[-1]),
        "current_price": float(df['c'].iloc[-1])
    }
```

**Deployment:** Price & Book Agent, Candles Agent

---

#### **Skill 3: hyperliquid-backfill-candles** ★ STATEFUL MULTI-SESSION

**Purpose:** Backfill historical candles with automatic resume capability

**Token Impact:**
- Without Skill: Backfill logic (5K) + pagination (1K) + state management (1K) = **7K tokens**
- With Skill: Invocation + progress updates = **500 tokens**
- **Savings: 93% token reduction**

**What This Skill Does (scripts/backfill.py):**

1. **Check for existing progress:**
```python
progress_file = Path("/memories/market_data/backfill_progress.json")
if progress_file.exists():
    progress = json.load(open(progress_file))
    start_timestamp = progress[f"{coin}_{interval}"]["current_progress"]
    # Resume from checkpoint
```

2. **Fetch in batches (5000 candle limit):**
```python
while current_ms < end_ms:
    batch_end_ms = min(current_ms + batch_size_ms, end_ms)

    # Network call to Hyperliquid
    candles = requests.post(
        "https://api.hyperliquid.xyz/info",
        json={
            "type": "candleSnapshot",
            "req": {"coin": coin, "interval": interval, "startTime": current_ms}
        }
    ).json()

    # Write batch to Memory (immutable cache)
    write_candles_to_cache(coin, interval, candles)

    # Update progress
    save_progress(coin, interval, current_ms, percent_complete)

    current_ms = batch_end_ms
```

3. **If interrupted:** Next invocation resumes automatically from checkpoint

**Example Usage:**
```python
# Agent invokes skill for large backfill
result = await invoke_skill("hyperliquid-backfill-candles", {
    "coin": "BTC",
    "interval": "1h",
    "start_date": "2024-01-01",
    "end_date": "2025-01-01"
})

# If crashes halfway through, next invocation resumes:
# "Resuming from 2024-06-15" (50% complete)
```

**Deployment:** Candles & Historical Agent

---

#### **Skill 4: hyperliquid-cache-optimizer**

**Purpose:** Analyze Memory cache patterns and optimize TTL values

**Token Impact:**
- Without Skill: Analysis logic in agent = **2K tokens**
- With Skill: Recommendations only = **400 tokens**
- **Savings: 80% token reduction**

**What This Skill Does (scripts/analyze_cache_patterns.py):**

```python
def analyze_cache_access(access_logs):
    # Read Memory access logs
    logs = read_memory("/memories/shared/access_logs.json")

    # Per-coin analysis
    hit_rates = {}
    for coin in unique_coins:
        hits = sum(1 for log in logs if log['coin'] == coin and log['cache_hit'])
        total = sum(1 for log in logs if log['coin'] == coin)
        hit_rates[coin] = hits / total

    # TTL recommendations
    recommendations = {}
    for coin, hit_rate in hit_rates.items():
        if hit_rate > 0.8:
            recommendations[coin] = {"ttl": 300, "reason": "High hit rate"}
        elif hit_rate < 0.5:
            recommendations[coin] = {"ttl": 60, "reason": "Low hit rate, reduce TTL"}

    return recommendations
```

**Deployment:** Orchestrator Agent (runs periodically to tune cache)

---

#### **Skill 5: hyperliquid-data-formatter**

**Purpose:** Transform Hyperliquid data into Excel, PDF, CSV

**Token Impact:**
- Without Skill: Formatting logic (pandas, openpyxl) = **3K tokens**
- With Skill: File reference only = **200 tokens**
- **Savings: 93% token reduction**

**What This Skill Does:**

**Excel Export (scripts/format_to_excel.py):**
```python
import pandas as pd
from openpyxl import Workbook

def format_candles_to_excel(candles, output_path):
    df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

    wb = Workbook()
    ws = wb.active
    ws.title = "Hyperliquid Data"

    # Write data with formatting
    for r_idx, row in enumerate(df.itertuples(index=False), start=1):
        for c_idx, value in enumerate(row, start=1):
            ws.cell(row=r_idx, column=c_idx, value=value)

    # Bold headers
    for cell in ws[1]:
        cell.font = Font(bold=True)

    wb.save(output_path)
    return {"file": output_path}
```

**PDF Report (scripts/format_to_pdf.py):**
- Uses Anthropic's pre-built PDF skill
- Generates professional market reports
- Includes charts and tables

**Deployment:** Trades & Fills Agent, Account Monitor Agent

---

### 3.3 Skills Workflow Architecture (Updated)

```
USER REQUEST: "Get BTC price"
       ↓
┌─────────────────────────────────────────────────────────────┐
│ ORCHESTRATOR AGENT (Sonnet 4.5)                            │
│ - Reads Memory: /memories/orchestrator/learned_patterns    │
│ - Routes to: Price & Book Agent                            │
│ Token usage: ~2K                                           │
└────────────────┬────────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────────────┐
│ PRICE & BOOK AGENT (Haiku 4.5)                             │
│                                                             │
│ Agent code (5 lines):                                       │
│   result = await invoke_skill("hyperliquid-fetch-and-cache", {
│       "endpoint": "allMids",                                │
│       "params": {}                                          │
│   })                                                        │
│   return result['data']                                     │
│                                                             │
│ Token usage: ~2K (just skill invocation)                   │
└────────────────┬────────────────────────────────────────────┘
                 ↓
         ┌───────────────────────────────────────┐
         │ SKILL: hyperliquid-fetch-and-cache   │
         │ (Executed OUTSIDE context = 0 tokens)│
         ├───────────────────────────────────────┤
         │ 1. Read Memory cache                 │
         │    /memories/market_data/allMids.json│
         │    → Cache HIT (data from 2 min ago) │
         │    → Return cached data               │
         │                                       │
         │ (If cache miss:)                      │
         │ 2. HTTP POST to api.hyperliquid.xyz  │
         │ 3. Validate response                  │
         │ 4. Write to Memory (with lock)        │
         │ 5. Return fresh data                  │
         └───────────────┬───────────────────────┘
                         ↓
                Result: {"BTC": "45123.50", ...}
                (~500 tokens enters context)
                         ↓
            Return to Orchestrator → User

TOTAL TOKEN USAGE: ~4.5K (vs 15K without Skills = 70% reduction)
```

**Key Points:**
- Agent code is trivial (5-line wrapper)
- Heavy lifting in scripts (cache, HTTP, validate, write)
- Scripts execute OUTSIDE context (0 tokens)
- Only result enters context
- 70% token reduction vs agent-centric approach

---

### 3.4 Skills API Configuration (Updated)

```python
# config.py
BETA_HEADERS = {
    "context-management-2025-06-27",  # Memory Tool
    "code-execution-2025-08-25",      # Skills script execution
    "files-api-2025-04-14",           # File handling
    "skills-2025-10-02"               # Skills API
}

# Skills registration (network-enabled)
AGENT_SKILLS_MAP = {
    "orchestrator": [
        "hyperliquid-cache-optimizer"  # Periodic cache tuning
    ],
    "price_book": [
        "hyperliquid-fetch-and-cache",    # PRIMARY: Fetches price data
        "hyperliquid-market-analyzer"     # SECONDARY: Analyzes data
    ],
    "trades_fills": [
        "hyperliquid-fetch-and-cache",    # PRIMARY: Fetches trade data
        "hyperliquid-data-formatter"      # SECONDARY: Exports to Excel/PDF
    ],
    "candles": [
        "hyperliquid-fetch-and-cache",    # PRIMARY: Fetches candles
        "hyperliquid-backfill-candles",   # SPECIAL: Large historical backfills
        "hyperliquid-market-analyzer"     # SECONDARY: Trend analysis
    ],
    "account_monitor": [
        "hyperliquid-fetch-and-cache",    # PRIMARY: Fetches portfolio data
        "hyperliquid-data-formatter"      # SECONDARY: Reports
    ],
    "error_recovery": []                  # No skills (uses Memory patterns)
}
```

---

### 3.5 Token & Cost Impact (Updated with Network-Enabled Skills)

#### **Token Usage Comparison**

| Task | Agent-Centric (Old) | Skills-Centric (New) | Savings |
|------|---------------------|----------------------|---------|
| Fetch & cache price | 3K tokens | 600 tokens | **80%** |
| Fetch & analyze orderbook | 5K tokens | 900 tokens | **82%** |
| Backfill candles (1000+) | 7K tokens × 200 batches | 500 tokens total | **99.6%** |
| Format to Excel | 3K tokens | 200 tokens | **93%** |
| **Average across tasks** | **4.5K tokens** | **1.1K tokens** | **76%** |

#### **Cost Impact (per 1000 requests/day)**

**Agent-Centric (Old Approach):**
- Avg tokens per request: 4.5K
- Haiku cost: $0.25 per 1M input tokens
- Cost per request: 4.5K × $0.25 / 1M = $0.001125
- Daily: $1.125
- **Monthly: $34**

**Skills-Centric (New Approach):**
- Avg tokens per request: 1.1K
- Haiku cost: $0.25 per 1M input tokens
- Cost per request: 1.1K × $0.25 / 1M = $0.000275
- Daily: $0.275
- **Monthly: $8.25**

**Additional Savings: $25.75/month per 1000 req/day**

**For 30,000 req/day (enterprise scale):**
- Agent-centric: $1,020/month
- **Skills-centric: $247.50/month**
- **Savings: $772.50/month = $9,270/year**

#### **Combined Total Savings**

```
Baseline (all Sonnet):              $2,700-13,500/month
With Haiku agents:                  $480/month (83-97% savings)
With Haiku + Memory:                $400/month (85-97% savings)
With Haiku + Memory + Skills:       $247.50/month (91-98% savings)

TOTAL ARCHITECTURE SAVINGS: 91-98% vs naive baseline
```

---

### 3.6 Skills Deployment Roadmap (Updated)

#### **Week 1: Core Infrastructure**
```bash
# 1. Build hyperliquid-fetch-and-cache skill
/skills/hyperliquid-fetch-and-cache/
├── SKILL.md
├── scripts/fetch_hyperliquid.py  # 200 lines with HTTP, validation, caching
├── resources/schemas/*.json      # Official Hyperliquid response schemas
└── requirements.txt              # requests, jsonschema, fcntl

# 2. Test network calls
python scripts/fetch_hyperliquid.py << EOF
{"endpoint": "allMids", "params": {}}
EOF
# Expected: {"success": true, "data": {"BTC": "45000", ...}, "source": "api"}

# 3. Test Memory read/write
# Verify script can read/write /memories/market_data/

# 4. Test rate limiting
# Verify coordination via /memories/shared/rate_limit_state.json
```

#### **Week 2: Agent Simplification**
```python
# Refactor agents to be thin wrappers

# BEFORE (50 lines of agent code):
class PriceBookAgent:
    async def get_all_mids(self):
        cache = read_memory(...)  # 10 lines
        if cache_fresh: return cache  # 5 lines
        response = await fetch_api(...)  # 15 lines
        validate(response)  # 10 lines
        write_memory(...)  # 10 lines
        return response

# AFTER (5 lines of agent code):
class PriceBookAgent:
    async def get_all_mids(self):
        result = await invoke_skill("hyperliquid-fetch-and-cache", {
            "endpoint": "allMids", "params": {}
        })
        return result['data']
```

#### **Week 3: Additional Skills**
```bash
# Deploy analysis and backfill skills
/skills/hyperliquid-market-analyzer/
/skills/hyperliquid-backfill-candles/
/skills/hyperliquid-cache-optimizer/
```

#### **Week 4: Validation & Testing**
- End-to-end: User request → Orchestrator → Agent → Skill → API → Memory → Response
- Load test: 1000 req/min
- Token usage validation: Expect 70-80% reduction
- Cost validation: Expect $247/month (vs $480 before)

---

### 3.7 Skills Security (Critical Updates)

#### **Endpoint Whitelisting (Enforced in Script)**

```python
# scripts/fetch_hyperliquid.py

OFFICIAL_ENDPOINTS = {
    "mainnet": "https://api.hyperliquid.xyz",
    "testnet": "https://api.hyperliquid-testnet.xyz"
}

def validate_endpoint(url):
    """Only allow official Hyperliquid endpoints"""
    if url not in OFFICIAL_ENDPOINTS.values():
        raise SecurityError(f"REJECTED: {url} is not an official endpoint")
    return True

# Before every HTTP call:
validate_endpoint(endpoint_url)
response = requests.post(endpoint_url, ...)
```

**This maintains 100% official endpoint guarantee (just enforced in scripts instead of agents).**

#### **Script Sandboxing**

```python
# Option 1: RestrictedPython (lightweight)
from RestrictedPython import compile_restricted

safe_globals = {
    '__builtins__': {
        'requests': requests,  # Allow HTTP
        'json': json,
        'Path': Path,
        # Deny: os.system, subprocess, socket (beyond whitelisted)
    }
}

exec(compile_restricted(script_code), safe_globals)

# Option 2: Docker container per execution (heavier but more secure)
docker run --rm \
  --network=none \  # No network (skill controls when to allow)
  --read-only \
  -v /skills:/skills:ro \
  -v /memories:/memories:rw \
  python:3.11 python /skills/hyperliquid-fetch-and-cache/scripts/fetch.py
```

**Recommendation:** Start with Option 1 (RestrictedPython), upgrade to Option 2 if needed.

#### **Memory Access Control (File Locking)**

```python
import fcntl

def write_memory_safe(path, data):
    """Thread-safe Memory writes"""
    with open(path, 'r+') as f:
        # Acquire exclusive lock
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)

        existing = json.load(f)
        existing.update(data)
        f.seek(0)
        f.truncate()
        json.dump(existing, f)

        # Release lock
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
```

**This resolves the race condition issue from the architecture review.**

---

### 3.8 Skills vs Memory: Complementary Roles (Updated)

| Aspect | Memory Tool | Claude Skills (Network-Enabled) |
|--------|-------------|----------------------------------|
| **Purpose** | Data persistence & state | End-to-end data pipelines |
| **Content** | JSON, logs, cache | Python scripts, HTTP calls |
| **Token Cost** | Variable (data size) | ~100 (metadata) |
| **Execution** | Read/write files | **Run Python, make HTTP calls** |
| **Learning** | Store patterns over time | Encode expertise in scripts |
| **Network** | N/A | **HTTP requests to api.hyperliquid.xyz** |
| **Use Case** | "Remember BTC price" | **"Fetch, validate, cache BTC price"** |

**Together:** Memory stores state, Skills execute pipelines (including network I/O)

**Example Workflow:**
```
1. User: "Get BTC price"
2. Agent invokes hyperliquid-fetch-and-cache skill
3. Skill script:
   a. Reads Memory: /memories/market_data/allMids.json
   b. Cache miss (stale data)
   c. HTTP POST to https://api.hyperliquid.xyz/info
   d. Validates response
   e. Writes Memory: /memories/market_data/allMids.json
4. Skill returns data to agent
5. Agent returns to user
```

---

## Summary of Skills Integration (Network-Enabled)

✅ **Skills are PRIMARY data collectors** (not just processors)
✅ **Executable Python scripts** make HTTP calls to `api.hyperliquid.xyz`
✅ **70-80% token reduction** (heavy lifting outside context)
✅ **91-98% cost reduction** vs naive baseline
✅ **Security maintained** (endpoint validation in scripts)
✅ **Memory Tool integration** (scripts read/write Memory directly)
✅ **Agents become simple** (5-line wrappers)
✅ **Skills are reusable** (one fetch skill, all agents use it)

**This is the final, optimized architecture leveraging all of Claude's capabilities.**

---

**End of Skills Section Update**
