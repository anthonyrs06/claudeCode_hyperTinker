#!/usr/bin/env python3
"""
Hyperliquid Fetch and Cache Script
==================================
Network-enabled skill script that fetches market data from official Hyperliquid API,
validates against schemas, caches in Memory Tool, and returns results.

This script is executed OUTSIDE Claude's context (0 tokens for execution).
Only input/output cross the context boundary (~500 tokens).

Official Endpoints:
- Mainnet: https://api.hyperliquid.xyz
- Testnet: https://api.hyperliquid-testnet.xyz
"""

import json
import sys
import os
import time
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple

try:
    import requests
    from requests.adapters import HTTPAdapter
    from requests.packages.urllib3.util.retry import Retry
except ImportError:
    print(json.dumps({
        "success": False,
        "error": "requests library not installed. Run: pip install requests"
    }))
    sys.exit(1)

# Import schema validation (local module)
try:
    from schemas import validate_response, ValidationError
except ImportError:
    # If schemas module not found, disable validation
    def validate_response(endpoint, data, strict=True):
        return True, ""
    class ValidationError(Exception):
        pass


# ============================================================================
# CONFIGURATION
# ============================================================================

# Get base path (project root)
BASE_PATH = Path(__file__).parent.parent.parent.parent

# Official Hyperliquid endpoints (immutable whitelist)
OFFICIAL_ENDPOINTS = {
    "mainnet": "https://api.hyperliquid.xyz",
    "testnet": "https://api.hyperliquid-testnet.xyz"
}

# Cache configuration
MEMORY_BASE_PATH = BASE_PATH / "memories"
CACHE_PATH = MEMORY_BASE_PATH / "market_data"
SHARED_PATH = MEMORY_BASE_PATH / "shared"
VALIDATION_PATH = MEMORY_BASE_PATH / "validation"

# Load cache TTL configuration from core/config.py
try:
    sys.path.insert(0, str(BASE_PATH))
    from core.config import CACHE_TTL, CACHE_ENABLED

    # Map Hyperliquid endpoint names to config keys
    DEFAULT_TTLS = {
        "allMids": CACHE_TTL.get("all_mids", 5),
        "meta": CACHE_TTL.get("meta", 60),
        "metaAndAssetCtxs": CACHE_TTL.get("meta", 60),
        "l2Book": CACHE_TTL.get("l2_book", 3),
        "trades": CACHE_TTL.get("default", 30),
        "candleSnapshot": CACHE_TTL.get("candle_snapshot", 300),
        "userState": CACHE_TTL.get("user_state", 30),
        "userFills": CACHE_TTL.get("user_fills", 10),
        "userFunding": CACHE_TTL.get("user_funding", 60),
        "openOrders": CACHE_TTL.get("open_orders", 5),
        "frontendOpenOrders": CACHE_TTL.get("open_orders", 5),
        "userRateLimit": CACHE_TTL.get("default", 30)
    }
    GLOBAL_CACHE_ENABLED = CACHE_ENABLED
except ImportError:
    # Fallback to hardcoded values if config import fails
    DEFAULT_TTLS = {
        "allMids": 5,
        "meta": 60,
        "metaAndAssetCtxs": 60,
        "l2Book": 3,
        "trades": 30,
        "candleSnapshot": 300,
        "userState": 30,
        "userFills": 10,
        "userFunding": 60,
        "openOrders": 5,
        "frontendOpenOrders": 5,
        "userRateLimit": 30
    }
    GLOBAL_CACHE_ENABLED = True

# Rate limiting
RATE_LIMIT_PER_MINUTE = 500
RATE_LIMIT_BURST = 50

# HTTP configuration
REQUEST_TIMEOUT = 10  # seconds
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 0.3  # 0.3, 0.6, 1.2 seconds


# ============================================================================
# ENDPOINT VALIDATION (Security-Critical)
# ============================================================================

def load_endpoint_whitelist() -> Dict[str, Any]:
    """Load the immutable endpoint whitelist from Memory."""
    whitelist_file = VALIDATION_PATH / "endpoint_whitelist.json"

    if not whitelist_file.exists():
        raise FileNotFoundError(
            f"Endpoint whitelist not found: {whitelist_file}. "
            "This is a security-critical file. Ensure it exists."
        )

    with open(whitelist_file, 'r') as f:
        whitelist = json.load(f)

    if not whitelist.get("immutable", False):
        raise SecurityError("Endpoint whitelist must be marked immutable")

    return whitelist


def validate_endpoint_url(url: str, whitelist: Dict[str, Any]) -> None:
    """
    Validate that URL is in official whitelist.
    Raises SecurityError if validation fails.
    """
    official_endpoints = whitelist.get("official_endpoints", [])

    if url not in official_endpoints:
        raise SecurityError(
            f"REJECTED: URL '{url}' is not in official whitelist. "
            f"Only these endpoints are allowed: {official_endpoints}"
        )

    # Additional validation rules
    rules = whitelist.get("validation_rules", {})

    if rules.get("require_https", True) and not url.startswith("https://"):
        raise SecurityError(f"REJECTED: URL must use HTTPS: {url}")

    if not rules.get("allow_http", False) and url.startswith("http://"):
        raise SecurityError(f"REJECTED: HTTP not allowed (HTTPS required): {url}")


class SecurityError(Exception):
    """Raised when endpoint validation fails."""
    pass


# ============================================================================
# RATE LIMITING
# ============================================================================

def check_rate_limit() -> bool:
    """
    Check if we're within rate limits.
    Returns True if OK to proceed, False if need to wait.

    Uses shared state in Memory for coordination across agents.
    """
    rate_limit_file = SHARED_PATH / "rate_limit_state.json"

    # Ensure directory exists
    SHARED_PATH.mkdir(parents=True, exist_ok=True)

    # Initialize if doesn't exist
    if not rate_limit_file.exists():
        state = {
            "requests_this_minute": 0,
            "window_start": datetime.now().isoformat(),
            "limit_per_minute": RATE_LIMIT_PER_MINUTE
        }
        with open(rate_limit_file, 'w') as f:
            json.dump(state, f)
        return True

    # Read current state
    with open(rate_limit_file, 'r') as f:
        state = json.load(f)

    window_start = datetime.fromisoformat(state["window_start"])
    now = datetime.now()

    # Reset window if minute elapsed
    if (now - window_start).total_seconds() >= 60:
        state = {
            "requests_this_minute": 1,
            "window_start": now.isoformat(),
            "limit_per_minute": RATE_LIMIT_PER_MINUTE
        }
        with open(rate_limit_file, 'w') as f:
            json.dump(state, f)
        return True

    # Check if under limit
    if state["requests_this_minute"] < state["limit_per_minute"]:
        state["requests_this_minute"] += 1
        with open(rate_limit_file, 'w') as f:
            json.dump(state, f)
        return True

    return False  # Rate limit exceeded


def wait_for_rate_limit() -> None:
    """Wait until rate limit window resets."""
    rate_limit_file = SHARED_PATH / "rate_limit_state.json"

    with open(rate_limit_file, 'r') as f:
        state = json.load(f)

    window_start = datetime.fromisoformat(state["window_start"])
    now = datetime.now()
    elapsed = (now - window_start).total_seconds()
    wait_time = max(0, 60 - elapsed)

    if wait_time > 0:
        time.sleep(wait_time)


# ============================================================================
# CACHE OPERATIONS
# ============================================================================

def generate_cache_key(endpoint: str, params: Dict[str, Any]) -> str:
    """Generate a deterministic cache key from endpoint and params."""
    # Sort params for consistency
    params_str = json.dumps(params, sort_keys=True)
    params_hash = hashlib.sha256(params_str.encode()).hexdigest()[:16]
    return f"{endpoint}_{params_hash}"


def check_cache(cache_key: str, ttl_seconds: int) -> Optional[Dict[str, Any]]:
    """
    Check if valid cached data exists.
    Returns cached data if valid, None otherwise.
    """
    cache_file = CACHE_PATH / f"{cache_key}.json"

    if not cache_file.exists():
        return None

    try:
        with open(cache_file, 'r') as f:
            cached = json.load(f)

        # Check if expired
        cached_time = datetime.fromisoformat(cached["metadata"]["timestamp"])
        now = datetime.now()
        age_seconds = (now - cached_time).total_seconds()

        if age_seconds < ttl_seconds:
            # Still valid
            cached["metadata"]["source"] = "cache"
            cached["metadata"]["cached_until"] = (cached_time + timedelta(seconds=ttl_seconds)).isoformat()
            return cached
        else:
            # Expired
            return None

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        # Cache corrupted, ignore
        return None


def write_cache(cache_key: str, data: Dict[str, Any], endpoint: str, api_latency_ms: int) -> None:
    """
    Write data to cache using atomic operations.
    Uses temp file + rename pattern for atomicity.
    """
    # Ensure directory exists
    CACHE_PATH.mkdir(parents=True, exist_ok=True)

    cache_file = CACHE_PATH / f"{cache_key}.json"
    temp_file = CACHE_PATH / f"{cache_key}.tmp"

    cache_entry = {
        "success": True,
        "data": data,
        "metadata": {
            "source": "api",
            "timestamp": datetime.now().isoformat(),
            "endpoint": endpoint,
            "api_latency_ms": api_latency_ms
        }
    }

    # Write to temp file
    with open(temp_file, 'w') as f:
        json.dump(cache_entry, f, indent=2)

    # Atomic rename (POSIX guarantees atomicity)
    temp_file.rename(cache_file)


# ============================================================================
# HTTP CLIENT
# ============================================================================

def create_http_session() -> requests.Session:
    """Create HTTP session with retry logic."""
    session = requests.Session()

    retry_strategy = Retry(
        total=MAX_RETRIES,
        backoff_factor=RETRY_BACKOFF_FACTOR,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST"]
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    return session


def fetch_from_api(
    endpoint: str,
    params: Dict[str, Any],
    environment: str = "mainnet"
) -> Tuple[Dict[str, Any], int]:
    """
    Fetch data from Hyperliquid API.
    Returns (data, latency_ms).
    """
    # Get base URL
    base_url = OFFICIAL_ENDPOINTS[environment]
    url = f"{base_url}/info"

    # Construct payload
    payload = {"type": endpoint}
    if params:
        # candleSnapshot endpoint requires params wrapped in "req" field
        if endpoint == "candleSnapshot":
            payload["req"] = params
        else:
            payload.update(params)

    # Make request
    session = create_http_session()
    start_time = time.time()

    try:
        response = session.post(
            url,
            json=payload,
            timeout=REQUEST_TIMEOUT,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()

        latency_ms = int((time.time() - start_time) * 1000)
        data = response.json()

        # Validate response against schema
        is_valid, error_msg = validate_response(endpoint, data, strict=False)
        if not is_valid:
            # Log warning but don't fail (graceful degradation)
            import sys
            print(f"WARNING: Schema validation failed: {error_msg}", file=sys.stderr)

        return data, latency_ms

    except requests.exceptions.HTTPError as e:
        raise Exception(f"HTTP error: {e.response.status_code} - {e.response.text}")
    except requests.exceptions.Timeout:
        raise Exception(f"Request timeout after {REQUEST_TIMEOUT} seconds")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Request failed: {str(e)}")
    except json.JSONDecodeError:
        raise Exception("Invalid JSON response from API")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main entry point for the skill script."""

    try:
        # Read input from stdin
        input_data = json.loads(sys.stdin.read())

        # Extract parameters
        endpoint = input_data.get("endpoint")
        params = input_data.get("params", {})
        cache_config = input_data.get("cache_config", {})

        cache_enabled = cache_config.get("enabled", GLOBAL_CACHE_ENABLED)
        ttl_seconds = cache_config.get("ttl_seconds", DEFAULT_TTLS.get(endpoint, 30))
        force_refresh = cache_config.get("force_refresh", False)
        environment = input_data.get("environment", "mainnet")

        # Validate endpoint
        if not endpoint:
            raise ValueError("Missing required parameter: endpoint")

        # Load and validate against whitelist
        whitelist = load_endpoint_whitelist()
        base_url = OFFICIAL_ENDPOINTS[environment]
        validate_endpoint_url(base_url, whitelist)

        # Generate cache key
        cache_key = generate_cache_key(endpoint, params)

        # Check cache (if enabled and not force refresh)
        if cache_enabled and not force_refresh:
            cached_data = check_cache(cache_key, ttl_seconds)
            if cached_data is not None:
                # Cache hit
                print(json.dumps(cached_data))
                return

        # Cache miss or disabled - fetch from API
        # Check rate limit
        if not check_rate_limit():
            wait_for_rate_limit()
            # Try again after waiting
            if not check_rate_limit():
                raise Exception("Rate limit exceeded even after waiting")

        # Fetch from API
        data, latency_ms = fetch_from_api(endpoint, params, environment)

        # Write to cache (if enabled)
        if cache_enabled:
            write_cache(cache_key, data, endpoint, latency_ms)

        # Return result
        result = {
            "success": True,
            "data": data,
            "metadata": {
                "source": "api",
                "timestamp": datetime.now().isoformat(),
                "endpoint": endpoint,
                "api_latency_ms": latency_ms
            }
        }

        print(json.dumps(result))

    except SecurityError as e:
        # Security violation - critical error
        error_result = {
            "success": False,
            "error": f"SECURITY ERROR: {str(e)}",
            "error_type": "security_violation"
        }
        print(json.dumps(error_result))
        sys.exit(1)

    except Exception as e:
        # Other errors
        error_result = {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }
        print(json.dumps(error_result))
        sys.exit(1)


if __name__ == "__main__":
    main()
