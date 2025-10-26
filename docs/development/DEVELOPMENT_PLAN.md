# Hyperliquid Multi-Agent System - Development Plan
## Step-by-Step Implementation Guide

**Status:** Ready to Execute
**Estimated Duration:** 5 weeks (can be compressed or extended based on resources)
**Approach:** Incremental, test-driven, fail-fast

---

## Development Principles

1. **Build → Test → Validate → Commit** (every step)
2. **Start simple, add complexity incrementally**
3. **Test in isolation before integration**
4. **Validate assumptions early** (especially Skills network calls)
5. **Keep working code at all times** (no big-bang integration)
6. **Document as you go** (no catch-up documentation at end)

---

## Phase 0: Project Setup (Day 1)

### Step 0.1: Initialize Project Structure
```bash
cd /Users/anthony.sadarangani/source/claudeCode_hyperTinker

# Create directory structure
mkdir -p {skills,agents,core,tests,scripts,memories}
mkdir -p skills/{hyperliquid-fetch-and-cache,hyperliquid-market-analyzer,hyperliquid-backfill-candles,hyperliquid-cache-optimizer,hyperliquid-data-formatter}
mkdir -p memories/{orchestrator,market_data,errors,shared}
mkdir -p tests/{unit,integration,load}

# Initialize git (if not already)
git init
git add .
git commit -m "Initial project structure"
```

**Validation:**
```bash
tree -L 2
# Verify all directories exist
```

---

### Step 0.2: Set Up Python Environment
```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Create requirements.txt
cat > requirements.txt << 'EOF'
# Anthropic SDK
anthropic==0.18.0

# HTTP & API
requests==2.31.0
httpx==0.27.0

# Data processing
pandas==2.2.0
numpy==1.26.0

# Validation
jsonschema==4.21.0

# Utilities
python-dotenv==1.0.0
pydantic==2.6.0

# Testing
pytest==8.0.0
pytest-asyncio==0.23.0
pytest-mock==3.12.0
responses==0.25.0  # Mock HTTP responses

# Monitoring (Phase 2+)
prometheus-client==0.19.0
opentelemetry-api==1.22.0
opentelemetry-sdk==1.22.0
EOF

pip install -r requirements.txt
```

**Validation:**
```bash
python -c "import anthropic; print(anthropic.__version__)"
python -c "import requests; print(requests.__version__)"
```

---

### Step 0.3: Configuration Setup
```bash
# Create .env file
cat > .env << 'EOF'
# Anthropic API
ANTHROPIC_API_KEY=your_key_here

# Hyperliquid endpoints (official only)
HYPERLIQUID_MAINNET_URL=https://api.hyperliquid.xyz
HYPERLIQUID_TESTNET_URL=https://api.hyperliquid-testnet.xyz

# Memory paths
MEMORY_BASE_PATH=/Users/anthony.sadarangani/source/claudeCode_hyperTinker/memories

# Agent configuration
AGENT_POOL_MIN=5
AGENT_POOL_MAX=50
ORCHESTRATOR_MODEL=claude-sonnet-4.5-20250929
AGENT_MODEL=claude-haiku-4.5-20250929

# Beta feature flags
ENABLE_MEMORY_TOOL=true
ENABLE_SKILLS=true
ENABLE_CONTEXT_CACHING=true
EOF

# Create core config module
cat > core/config.py << 'EOF'
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# API Configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Official Hyperliquid Endpoints (immutable)
OFFICIAL_ENDPOINTS = {
    "mainnet": os.getenv("HYPERLIQUID_MAINNET_URL"),
    "testnet": os.getenv("HYPERLIQUID_TESTNET_URL")
}

# Memory Configuration
MEMORY_BASE_PATH = Path(os.getenv("MEMORY_BASE_PATH"))

# Model Configuration
ORCHESTRATOR_MODEL = os.getenv("ORCHESTRATOR_MODEL")
AGENT_MODEL = os.getenv("AGENT_MODEL")

# Beta Headers
BETA_HEADERS = {
    "anthropic-beta": "context-management-2025-06-27,code-execution-2025-08-25,files-api-2025-04-14,skills-2025-10-02"
}

# Cache TTLs
CACHE_TTLS = {
    "allMids": 300,        # 5 minutes
    "l2Book": 60,          # 1 minute
    "candleSnapshot": None,  # Immutable
    "userFills": 300,
    "portfolio": 600,
    "meta": 86400          # 24 hours
}
EOF
```

**Validation:**
```bash
python -c "from core.config import OFFICIAL_ENDPOINTS; print(OFFICIAL_ENDPOINTS)"
```

---

## Phase 1: Core Skill Development (Days 2-4)

### Step 1.1: Build hyperliquid-fetch-and-cache Skill (Foundation)

**Why this first:** This is the PRIMARY data collector. Everything depends on it working.

```bash
cd skills/hyperliquid-fetch-and-cache

# Create SKILL.md
cat > SKILL.md << 'EOF'
---
name: hyperliquid-fetch-and-cache
description: >
  Fetches data from official Hyperliquid API (api.hyperliquid.xyz),
  validates against schemas, caches in Memory Tool, and returns result.

  Handles cache checking, API calls, validation, Memory updates, and
  rate limit coordination. Use this skill for ANY Hyperliquid data request.

  Supported endpoints: allMids, l2Book, candleSnapshot, userFills,
  historicalOrders, openOrders, portfolio, meta
---

# Hyperliquid Fetch and Cache

## Usage

Invoke with:
```json
{
  "endpoint": "allMids",
  "params": {}
}
```

## Workflow

1. Check Memory cache for fresh data
2. If cache miss: fetch from https://api.hyperliquid.xyz/info
3. Validate response against schema
4. Write to Memory cache
5. Return data

## Official Endpoints Only

This skill ONLY calls:
- https://api.hyperliquid.xyz (mainnet)
- https://api.hyperliquid-testnet.xyz (fallback)

Any other endpoint is REJECTED.
EOF

# Create directory structure
mkdir -p {scripts,resources/schemas}
touch scripts/__init__.py
```

**Validation:**
```bash
ls -la skills/hyperliquid-fetch-and-cache/
# Verify SKILL.md and directories exist
```

---

### Step 1.2: Implement Fetch Script (Core Logic)

```bash
cat > skills/hyperliquid-fetch-and-cache/scripts/fetch_hyperliquid.py << 'EOF'
#!/usr/bin/env python3
"""
Hyperliquid data fetcher with caching and validation.
This script makes actual network calls to api.hyperliquid.xyz
"""
import json
import sys
import os
import time
import requests
from pathlib import Path
from datetime import datetime, timedelta

# Configuration
OFFICIAL_ENDPOINTS = {
    "mainnet": "https://api.hyperliquid.xyz",
    "testnet": "https://api.hyperliquid-testnet.xyz"
}

MEMORY_PATH = Path(os.getenv("MEMORY_BASE_PATH", "/tmp/memories")) / "market_data"
MEMORY_PATH.mkdir(parents=True, exist_ok=True)

CACHE_TTLS = {
    "allMids": 300,        # 5 minutes
    "l2Book": 60,          # 1 minute
    "candleSnapshot": None,  # Immutable
    "userFills": 300,
    "portfolio": 600,
    "meta": 86400          # 24 hours
}

def log(message):
    """Log to stderr (doesn't pollute stdout result)"""
    print(f"[SKILL] {message}", file=sys.stderr)

def validate_endpoint(endpoint_url):
    """Ensure we only call official Hyperliquid endpoints"""
    if endpoint_url not in OFFICIAL_ENDPOINTS.values():
        raise ValueError(f"REJECTED: {endpoint_url} is not an official Hyperliquid endpoint")
    log(f"✓ Endpoint validated: {endpoint_url}")
    return True

def check_cache(endpoint, params):
    """Check if we have fresh cached data"""
    cache_key = f"{endpoint}_{json.dumps(params, sort_keys=True)}"
    cache_file = MEMORY_PATH / f"{cache_key}.json"

    if not cache_file.exists():
        log(f"Cache MISS: {cache_key} (file doesn't exist)")
        return None

    try:
        with open(cache_file, 'r') as f:
            cached = json.load(f)

        # Check freshness
        ttl = CACHE_TTLS.get(endpoint)
        if ttl is None:  # Immutable data
            log(f"Cache HIT: {cache_key} (immutable)")
            return cached['data']

        cached_time = datetime.fromisoformat(cached['timestamp'])
        age_seconds = (datetime.now() - cached_time).total_seconds()

        if age_seconds < ttl:
            log(f"Cache HIT: {cache_key} (age: {age_seconds:.0f}s < TTL: {ttl}s)")
            return cached['data']
        else:
            log(f"Cache MISS: {cache_key} (age: {age_seconds:.0f}s > TTL: {ttl}s)")
            return None

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        log(f"Cache CORRUPTED: {cache_key} - {e}")
        return None

def fetch_from_api(endpoint, params, max_retries=3):
    """Fetch data from Hyperliquid API with retry logic"""
    url = f"{OFFICIAL_ENDPOINTS['mainnet']}/info"
    validate_endpoint(OFFICIAL_ENDPOINTS['mainnet'])

    payload = {"type": endpoint, **params}
    log(f"Fetching from API: {endpoint} with params {params}")

    for attempt in range(max_retries):
        try:
            response = requests.post(
                url,
                json=payload,
                timeout=10,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 429:  # Rate limited
                wait_time = 2 ** attempt  # Exponential backoff
                log(f"Rate limited, waiting {wait_time}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
                continue

            response.raise_for_status()
            data = response.json()
            log(f"✓ API call successful: {len(json.dumps(data))} bytes")
            return data

        except requests.RequestException as e:
            if attempt == max_retries - 1:
                # Try testnet as fallback
                log(f"Mainnet failed, trying testnet fallback...")
                try:
                    testnet_url = f"{OFFICIAL_ENDPOINTS['testnet']}/info"
                    validate_endpoint(OFFICIAL_ENDPOINTS['testnet'])
                    response = requests.post(testnet_url, json=payload, timeout=10)
                    response.raise_for_status()
                    data = response.json()
                    data['_source'] = 'testnet'  # Mark as testnet data
                    log(f"✓ Testnet fallback successful")
                    return data
                except Exception as fallback_error:
                    log(f"✗ Testnet fallback failed: {fallback_error}")
                    raise e

            log(f"API call failed (attempt {attempt + 1}/{max_retries}): {e}")
            time.sleep(1)

    raise Exception(f"Failed to fetch after {max_retries} attempts")

def write_cache(endpoint, params, data):
    """Write validated data to Memory cache (last-write-wins, no locking)"""
    cache_key = f"{endpoint}_{json.dumps(params, sort_keys=True)}"
    cache_file = MEMORY_PATH / f"{cache_key}.json"

    cache_entry = {
        "endpoint": endpoint,
        "params": params,
        "data": data,
        "timestamp": datetime.now().isoformat(),
        "source": "https://api.hyperliquid.xyz/info"
    }

    # Atomic write (write to temp file, then rename)
    temp_file = cache_file.with_suffix('.tmp')
    with open(temp_file, 'w') as f:
        json.dump(cache_entry, f, indent=2)
    temp_file.rename(cache_file)

    log(f"✓ Cache written: {cache_key}")

def main():
    """Main entry point"""
    try:
        # Read input from stdin (Claude passes parameters as JSON)
        input_data = json.loads(sys.stdin.read())

        endpoint = input_data.get('endpoint')
        params = input_data.get('params', {})

        if not endpoint:
            raise ValueError("Missing required field: endpoint")

        log(f"=== Hyperliquid Fetch: {endpoint} ===")

        # 1. Check cache first
        cached_data = check_cache(endpoint, params)
        if cached_data:
            result = {
                "success": True,
                "data": cached_data,
                "source": "cache",
                "timestamp": datetime.now().isoformat()
            }
            print(json.dumps(result))
            return

        # 2. Fetch from API
        data = fetch_from_api(endpoint, params)

        # 3. Cache (no validation for now - add in Step 1.3)
        write_cache(endpoint, params, data)

        # 4. Return result
        result = {
            "success": True,
            "data": data,
            "source": "api",
            "timestamp": datetime.now().isoformat()
        }
        print(json.dumps(result))

    except Exception as e:
        log(f"✗ Error: {e}")
        # Return error to Claude
        error_result = {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
        print(json.dumps(error_result))
        sys.exit(1)

if __name__ == "__main__":
    main()
EOF

chmod +x skills/hyperliquid-fetch-and-cache/scripts/fetch_hyperliquid.py
```

**Validation (Critical - Test Network Call):**
```bash
# Test 1: Basic invocation
echo '{"endpoint": "allMids", "params": {}}' | \
  python skills/hyperliquid-fetch-and-cache/scripts/fetch_hyperliquid.py

# Expected output: JSON with {"success": true, "data": {"BTC": "...", ...}}

# Test 2: Cache behavior (run same command twice)
echo '{"endpoint": "allMids", "params": {}}' | \
  python skills/hyperliquid-fetch-and-cache/scripts/fetch_hyperliquid.py
# First call: "source": "api"

echo '{"endpoint": "allMids", "params": {}}' | \
  python skills/hyperliquid-fetch-and-cache/scripts/fetch_hyperliquid.py
# Second call: "source": "cache" (should be instant)

# Test 3: Verify cache file exists
ls -la memories/market_data/
cat memories/market_data/allMids_*.json | jq .

# Test 4: Invalid endpoint (should reject)
echo '{"endpoint": "allMids", "params": {}}' | \
  HYPERLIQUID_MAINNET_URL=https://evil.com \
  python skills/hyperliquid-fetch-and-cache/scripts/fetch_hyperliquid.py
# Expected: Error "REJECTED: https://evil.com is not an official endpoint"
```

**CHECKPOINT:** Do NOT proceed unless all 4 tests pass. This is the foundation.

---

### Step 1.3: Add Schema Validation

```bash
# Create official Hyperliquid schemas
cat > skills/hyperliquid-fetch-and-cache/resources/schemas/allMids.json << 'EOF'
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "patternProperties": {
    "^[A-Z0-9-]+$": {
      "type": "string",
      "pattern": "^[0-9]+(\\.[0-9]+)?$"
    }
  },
  "additionalProperties": false
}
EOF

cat > skills/hyperliquid-fetch-and-cache/resources/schemas/l2Book.json << 'EOF'
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "coin": {"type": "string"},
    "levels": {
      "type": "array",
      "items": {
        "type": "array",
        "items": [
          {"type": "string"},
          {"type": "string"},
          {"type": "number"}
        ]
      }
    },
    "time": {"type": "number"}
  },
  "required": ["coin", "levels", "time"]
}
EOF

# Add validation to fetch script
# Insert after fetch_from_api() function:
cat >> skills/hyperliquid-fetch-and-cache/scripts/fetch_hyperliquid.py << 'EOF'

def validate_response(endpoint, data):
    """Validate response against schema"""
    schema_file = Path(__file__).parent.parent / f"resources/schemas/{endpoint}.json"

    if not schema_file.exists():
        log(f"⚠ No schema for {endpoint}, skipping validation")
        return True

    try:
        import jsonschema
        with open(schema_file) as f:
            schema = json.load(f)
        jsonschema.validate(instance=data, schema=schema)
        log(f"✓ Validation passed: {endpoint}")
        return True
    except jsonschema.ValidationError as e:
        log(f"✗ Validation failed: {e.message}")
        raise ValueError(f"Validation failed: {e.message}")
EOF
```

Update main() to call validate_response() after fetching.

**Validation:**
```bash
# Test validation with real data
echo '{"endpoint": "allMids", "params": {}}' | \
  python skills/hyperliquid-fetch-and-cache/scripts/fetch_hyperliquid.py

# Should see: "✓ Validation passed: allMids" in stderr
```

---

### Step 1.4: Create Unit Tests

```bash
cat > tests/unit/test_fetch_skill.py << 'EOF'
import pytest
import json
import responses
from pathlib import Path

# Import the skill script
import sys
sys.path.insert(0, 'skills/hyperliquid-fetch-and-cache/scripts')
import fetch_hyperliquid

@responses.activate
def test_fetch_from_api_success():
    """Test successful API call"""
    responses.add(
        responses.POST,
        "https://api.hyperliquid.xyz/info",
        json={"BTC": "45000.5", "ETH": "2340.2"},
        status=200
    )

    result = fetch_hyperliquid.fetch_from_api("allMids", {})
    assert "BTC" in result
    assert result["BTC"] == "45000.5"

@responses.activate
def test_fetch_with_rate_limit_retry():
    """Test retry logic on rate limit"""
    responses.add(
        responses.POST,
        "https://api.hyperliquid.xyz/info",
        json={"error": "rate limit"},
        status=429
    )
    responses.add(
        responses.POST,
        "https://api.hyperliquid.xyz/info",
        json={"BTC": "45000.5"},
        status=200
    )

    result = fetch_hyperliquid.fetch_from_api("allMids", {})
    assert "BTC" in result

def test_cache_write_and_read():
    """Test cache write/read cycle"""
    endpoint = "allMids"
    params = {}
    data = {"BTC": "45000.5"}

    # Write
    fetch_hyperliquid.write_cache(endpoint, params, data)

    # Read
    cached = fetch_hyperliquid.check_cache(endpoint, params)
    assert cached == data

def test_endpoint_validation_rejects_unofficial():
    """Test that unofficial endpoints are rejected"""
    with pytest.raises(ValueError, match="REJECTED"):
        fetch_hyperliquid.validate_endpoint("https://evil.com")

def test_endpoint_validation_accepts_official():
    """Test that official endpoints are accepted"""
    assert fetch_hyperliquid.validate_endpoint("https://api.hyperliquid.xyz")
EOF

# Run tests
pytest tests/unit/test_fetch_skill.py -v
```

**CHECKPOINT:** All tests must pass before proceeding.

---

## Phase 2: Agent Development (Days 5-7)

### Step 2.1: Create Base Agent Class

```bash
cat > agents/base_agent.py << 'EOF'
"""
Base agent class with Skills invocation capability
"""
import anthropic
from typing import Dict, Any, Optional
from core.config import ANTHROPIC_API_KEY, BETA_HEADERS, AGENT_MODEL

class BaseAgent:
    def __init__(self, model: str = AGENT_MODEL):
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self.model = model

    async def invoke_skill(self, skill_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invoke a Claude Skill and return the result

        This is the KEY method - agents just call skills
        """
        # For now, we'll simulate skill invocation by directly calling the script
        # In production, this would use Anthropic's Skills API

        import subprocess
        import json

        skill_script = f"skills/{skill_name}/scripts/fetch_hyperliquid.py"

        # Pass parameters as JSON to stdin
        result = subprocess.run(
            ["python", skill_script],
            input=json.dumps(parameters),
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise Exception(f"Skill execution failed: {result.stderr}")

        return json.loads(result.stdout)
EOF
```

---

### Step 2.2: Implement Price & Book Agent

```bash
cat > agents/price_book_agent.py << 'EOF'
"""
Price & Book Agent - Lightweight wrapper around Skills
"""
from agents.base_agent import BaseAgent
from typing import Dict, Any, Optional

class PriceBookAgent(BaseAgent):
    """
    Fetches real-time price data and order books via Skills.

    This agent is SIMPLE - just invokes skills. Heavy lifting in scripts.
    """

    async def get_all_mids(self) -> Dict[str, Any]:
        """
        Get mid prices for all coins.

        Token usage: ~2K (just skill invocation, not fetch logic)
        """
        result = await self.invoke_skill("hyperliquid-fetch-and-cache", {
            "endpoint": "allMids",
            "params": {}
        })

        if not result.get("success"):
            raise Exception(f"Failed to fetch: {result.get('error')}")

        return result['data']

    async def get_l2_book(self, coin: str) -> Dict[str, Any]:
        """
        Get L2 order book for specific coin.
        """
        result = await self.invoke_skill("hyperliquid-fetch-and-cache", {
            "endpoint": "l2Book",
            "params": {"coin": coin}
        })

        if not result.get("success"):
            raise Exception(f"Failed to fetch: {result.get('error')}")

        return result['data']

    async def get_meta(self) -> Dict[str, Any]:
        """
        Get asset metadata (symbols, tick sizes, etc.)
        """
        result = await self.invoke_skill("hyperliquid-fetch-and-cache", {
            "endpoint": "meta",
            "params": {}
        })

        if not result.get("success"):
            raise Exception(f"Failed to fetch: {result.get('error')}")

        return result['data']
EOF
```

---

### Step 2.3: Test Agent in Isolation

```bash
cat > tests/integration/test_price_agent.py << 'EOF'
import pytest
import asyncio
from agents.price_book_agent import PriceBookAgent

@pytest.mark.asyncio
async def test_get_all_mids():
    """Test fetching all mid prices"""
    agent = PriceBookAgent()

    # This should work end-to-end:
    # Agent → Skill → HTTP → Cache → Return
    result = await agent.get_all_mids()

    assert isinstance(result, dict)
    assert "BTC" in result
    assert "ETH" in result

    # Verify prices are numeric strings
    assert float(result["BTC"]) > 0

    print(f"✓ Fetched {len(result)} coin prices")

@pytest.mark.asyncio
async def test_get_l2_book():
    """Test fetching order book"""
    agent = PriceBookAgent()

    result = await agent.get_l2_book("BTC")

    assert "coin" in result
    assert result["coin"] == "BTC"
    assert "levels" in result
    assert len(result["levels"]) > 0

    print(f"✓ Fetched order book with {len(result['levels'])} levels")

@pytest.mark.asyncio
async def test_cache_behavior():
    """Test that second call uses cache"""
    agent = PriceBookAgent()

    import time

    # First call (API)
    start = time.time()
    result1 = await agent.get_all_mids()
    duration1 = time.time() - start

    # Second call (should be cached)
    start = time.time()
    result2 = await agent.get_all_mids()
    duration2 = time.time() - start

    # Cache should be significantly faster
    assert duration2 < duration1 * 0.5, "Second call should be faster (cached)"

    print(f"✓ First call: {duration1:.2f}s, Second call (cached): {duration2:.2f}s")
EOF

# Run integration tests
pytest tests/integration/test_price_agent.py -v -s
```

**CHECKPOINT:** Integration tests must pass. This validates end-to-end flow.

---

## Phase 3: Orchestrator & Multi-Agent Coordination (Days 8-10)

### Step 3.1: Implement Simple Orchestrator

```bash
cat > agents/orchestrator_agent.py << 'EOF'
"""
Orchestrator Agent - Routes requests to specialized agents
"""
import anthropic
from typing import Dict, Any
from agents.price_book_agent import PriceBookAgent
from core.config import ANTHROPIC_API_KEY, ORCHESTRATOR_MODEL

class OrchestratorAgent:
    """
    Sonnet 4.5-powered orchestrator that routes requests.

    Starts simple (pattern matching), learns patterns over time (Phase 4).
    """

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self.model = ORCHESTRATOR_MODEL

        # Initialize specialized agents
        self.price_book_agent = PriceBookAgent()
        # Add more agents in later steps

    async def process_request(self, user_request: str) -> Dict[str, Any]:
        """
        Process user request and route to appropriate agent.

        For now: Simple pattern matching
        Later: Claude-powered intelligent routing with Memory
        """
        request_lower = user_request.lower()

        # Simple routing logic (upgrade to Claude-powered in Phase 4)
        if any(keyword in request_lower for keyword in ["price", "mid", "quote"]):
            # Route to Price & Book Agent
            if "orderbook" in request_lower or "book" in request_lower:
                # Extract coin (simple regex for now)
                import re
                coin_match = re.search(r'\b([A-Z]{3,4})\b', user_request)
                coin = coin_match.group(1) if coin_match else "BTC"

                result = await self.price_book_agent.get_l2_book(coin)
                return {
                    "agent": "price_book",
                    "action": "get_l2_book",
                    "result": result
                }
            else:
                result = await self.price_book_agent.get_all_mids()
                return {
                    "agent": "price_book",
                    "action": "get_all_mids",
                    "result": result
                }

        # Default: return error
        return {
            "error": "Unable to route request",
            "request": user_request
        }
EOF
```

---

### Step 3.2: Test Orchestrator

```bash
cat > tests/integration/test_orchestrator.py << 'EOF'
import pytest
import asyncio
from agents.orchestrator_agent import OrchestratorAgent

@pytest.mark.asyncio
async def test_orchestrator_routes_price_request():
    """Test orchestrator routes price request to correct agent"""
    orchestrator = OrchestratorAgent()

    result = await orchestrator.process_request("Get BTC price")

    assert result["agent"] == "price_book"
    assert "result" in result
    assert "BTC" in result["result"]

    print(f"✓ Orchestrator routed to price_book agent successfully")

@pytest.mark.asyncio
async def test_orchestrator_routes_orderbook_request():
    """Test orchestrator routes orderbook request"""
    orchestrator = OrchestratorAgent()

    result = await orchestrator.process_request("Show me ETH orderbook")

    assert result["agent"] == "price_book"
    assert result["action"] == "get_l2_book"
    assert result["result"]["coin"] == "ETH"

    print(f"✓ Orchestrator routed orderbook request correctly")
EOF

pytest tests/integration/test_orchestrator.py -v -s
```

---

## Phase 4: Memory Tool Integration (Days 11-13)

### Step 4.1: Add Memory-Powered Routing

```bash
cat > core/memory_manager.py << 'EOF'
"""
Memory Manager - Interface to Memory Tool storage
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from core.config import MEMORY_BASE_PATH

class MemoryManager:
    """Manages reading/writing to Memory Tool storage"""

    def __init__(self):
        self.base_path = MEMORY_BASE_PATH
        self.base_path.mkdir(parents=True, exist_ok=True)

    def read(self, path: str) -> Optional[Dict[str, Any]]:
        """Read from Memory (returns None if doesn't exist)"""
        full_path = self.base_path / path

        if not full_path.exists():
            return None

        try:
            with open(full_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return None

    def write(self, path: str, data: Dict[str, Any]):
        """Write to Memory (last-write-wins, no locking)"""
        full_path = self.base_path / path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Atomic write
        temp_path = full_path.with_suffix('.tmp')
        with open(temp_path, 'w') as f:
            json.dump(data, f, indent=2)
        temp_path.rename(full_path)

    def append_log(self, path: str, entry: Dict[str, Any]):
        """Append to log file (for routing history, etc.)"""
        full_path = self.base_path / path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        entry['timestamp'] = datetime.now().isoformat()

        with open(full_path, 'a') as f:
            f.write(json.dumps(entry) + '\n')
EOF
```

---

### Step 4.2: Upgrade Orchestrator with Memory

```python
# Update orchestrator_agent.py to use Memory
from core.memory_manager import MemoryManager

class OrchestratorAgent:
    def __init__(self):
        # ... existing code ...
        self.memory = MemoryManager()

    async def process_request(self, user_request: str) -> Dict[str, Any]:
        """Process request with Memory-powered routing"""

        # 1. Check learned patterns
        patterns = self.memory.read("orchestrator/learned_patterns.json")
        if patterns:
            # Use learned routing (implement logic)
            pass

        # 2. Route using current logic
        result = await self._route_request(user_request)

        # 3. Log routing decision to Memory
        self.memory.append_log("orchestrator/routing_history.jsonl", {
            "request": user_request,
            "routed_to": result.get("agent"),
            "action": result.get("action"),
            "success": "error" not in result
        })

        return result
```

---

## Phase 5: Additional Skills & Agents (Days 14-18)

### Step 5.1: Implement Remaining Agents

Follow same pattern:
1. Create agent class (5-10 lines)
2. Invoke appropriate skill
3. Write unit tests
4. Write integration tests
5. Add to orchestrator routing

**Agents to implement:**
- Trades & Fills Agent
- Candles & Historical Agent
- Account Monitor Agent
- Error Recovery Agent

---

### Step 5.2: Build Additional Skills

**Priority order:**
1. `hyperliquid-market-analyzer` (analysis logic)
2. `hyperliquid-backfill-candles` (multi-session backfills)
3. `hyperliquid-cache-optimizer` (TTL tuning)
4. `hyperliquid-data-formatter` (Excel/PDF exports)

Each skill follows same pattern as Step 1.

---

## Phase 6: Testing & Optimization (Days 19-22)

### Step 6.1: Load Testing

```bash
cat > tests/load/test_load.py << 'EOF'
import pytest
import asyncio
import time
from agents.orchestrator_agent import OrchestratorAgent

@pytest.mark.asyncio
async def test_concurrent_requests():
    """Test system under concurrent load"""
    orchestrator = OrchestratorAgent()

    requests = [
        "Get BTC price",
        "Show ETH orderbook",
        "Get all prices",
        "BTC price please"
    ] * 25  # 100 total requests

    start = time.time()
    tasks = [orchestrator.process_request(req) for req in requests]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    duration = time.time() - start

    # Check results
    errors = [r for r in results if isinstance(r, Exception)]
    successes = [r for r in results if not isinstance(r, Exception)]

    print(f"\n=== Load Test Results ===")
    print(f"Total requests: {len(requests)}")
    print(f"Successes: {len(successes)}")
    print(f"Errors: {len(errors)}")
    print(f"Duration: {duration:.2f}s")
    print(f"Requests/sec: {len(requests)/duration:.2f}")

    # Should handle 100 requests with >95% success rate
    assert len(successes) / len(requests) > 0.95
EOF

pytest tests/load/test_load.py -v -s
```

---

### Step 6.2: Token Usage Measurement

```python
# Add token tracking to agents
class BaseAgent:
    def __init__(self):
        self.token_usage = []

    async def invoke_skill(self, ...):
        # Track tokens before/after
        start_usage = self.get_token_usage()
        result = await actual_invoke()
        end_usage = self.get_token_usage()

        self.token_usage.append({
            "skill": skill_name,
            "tokens": end_usage - start_usage
        })

        return result
```

---

## Phase 7: Production Deployment (Days 23-25)

### Step 7.1: Create Deployment Script

```bash
cat > scripts/deploy.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Hyperliquid Multi-Agent System Deployment ==="

# 1. Environment check
echo "Checking environment..."
python -c "import anthropic; print(f'Anthropic SDK: {anthropic.__version__}')"

# 2. Run tests
echo "Running tests..."
pytest tests/ -v

# 3. Initialize Memory structure
echo "Initializing Memory..."
python scripts/init_memory.py

# 4. Pre-warm cache
echo "Pre-warming cache..."
python scripts/prewarm_cache.py

# 5. Start system
echo "Starting orchestrator..."
python main.py

echo "✓ Deployment complete!"
EOF

chmod +x scripts/deploy.sh
```

---

### Step 7.2: Monitoring Setup

```python
# Add Prometheus metrics
from prometheus_client import Counter, Histogram, start_http_server

request_counter = Counter('hyperliquid_requests_total', 'Total requests', ['agent'])
request_duration = Histogram('hyperliquid_request_duration_seconds', 'Request duration')
cache_hits = Counter('hyperliquid_cache_hits_total', 'Cache hits')
cache_misses = Counter('hyperliquid_cache_misses_total', 'Cache misses')

# Start metrics server
start_http_server(8000)
```

---

## Development Checklist

### Phase 0: Setup ✅
- [ ] Project structure created
- [ ] Python environment configured
- [ ] Configuration files set up
- [ ] Git initialized

### Phase 1: Core Skill ✅
- [ ] Skill structure created
- [ ] Fetch script implemented
- [ ] Network calls tested
- [ ] Cache working
- [ ] Schema validation added
- [ ] Unit tests pass

### Phase 2: Agents ✅
- [ ] Base agent class created
- [ ] Price & Book Agent implemented
- [ ] Integration tests pass
- [ ] Cache behavior validated

### Phase 3: Orchestrator ✅
- [ ] Simple orchestrator working
- [ ] Routing tests pass
- [ ] End-to-end flow validated

### Phase 4: Memory ✅
- [ ] Memory manager created
- [ ] Routing history logged
- [ ] Learned patterns readable

### Phase 5: Additional Components ✅
- [ ] All agents implemented
- [ ] All skills built
- [ ] Integration tests pass

### Phase 6: Testing ✅
- [ ] Load tests pass (>95% success at 100 req)
- [ ] Token usage measured (<5K per request)
- [ ] Cache hit rate >70%

### Phase 7: Production ✅
- [ ] Deployment script ready
- [ ] Monitoring configured
- [ ] Documentation complete
- [ ] Team trained

---

## Success Criteria (Final Validation)

Before declaring "DONE":

1. **Functionality:**
   - [ ] Can fetch BTC price (orchestrator → agent → skill → API)
   - [ ] Second request uses cache (< 100ms)
   - [ ] All 8+ Hyperliquid endpoints working
   - [ ] Skills return valid data 100% of time

2. **Performance:**
   - [ ] Token usage: <5K per request ✅
   - [ ] Cache hit rate: >70% ✅
   - [ ] API call reduction: >80% ✅
   - [ ] P99 latency: <2s ✅

3. **Reliability:**
   - [ ] 100 concurrent requests: >95% success ✅
   - [ ] Memory files not corrupted ✅
   - [ ] Official endpoints enforced (100%) ✅
   - [ ] Error handling graceful ✅

4. **Cost:**
   - [ ] Monthly cost: <$1,100 for 30K req/day ✅
   - [ ] Token usage tracked and logged ✅
   - [ ] No unexpected API usage spikes ✅

---

## Daily Standup Questions

Ask yourself every day:

1. **What did I complete yesterday?** (check off items)
2. **What am I working on today?** (focus on 1-2 steps)
3. **Am I blocked?** (if yes, document and resolve)
4. **Are tests passing?** (never proceed with failing tests)
5. **Is the working code committed?** (commit at end of each day)

---

## Emergency Rollback Plan

If something breaks:

1. **Identify what changed** (git diff)
2. **Revert last commit** (git revert HEAD)
3. **Re-run tests** (pytest tests/)
4. **Document issue** (add to ISSUES.md)
5. **Fix in isolated branch** (git checkout -b fix/issue-name)

---

**Ready to start with Step 0.1? Let's build this system one validated step at a time!** 🚀
