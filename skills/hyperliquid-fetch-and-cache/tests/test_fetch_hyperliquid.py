"""
Unit Tests for Hyperliquid Fetch and Cache Skill
================================================
Tests network calls, caching, validation, and error handling.
"""

import json
import os
import sys
import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Add scripts directory to path
SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import fetch_hyperliquid
from fetch_hyperliquid import (
    generate_cache_key,
    check_cache,
    write_cache,
    validate_endpoint_url,
    SecurityError,
    load_endpoint_whitelist
)
from schemas import validate_response, ENDPOINT_SCHEMAS


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def temp_memory_dir(monkeypatch):
    """Create temporary memory directory for testing."""
    temp_dir = tempfile.mkdtemp()
    memory_path = Path(temp_dir) / "memories"
    memory_path.mkdir(parents=True)

    # Create subdirectories
    (memory_path / "market_data").mkdir()
    (memory_path / "shared").mkdir()
    (memory_path / "validation").mkdir()

    # Create whitelist
    whitelist = {
        "immutable": True,
        "official_endpoints": [
            "https://api.hyperliquid.xyz",
            "https://api.hyperliquid-testnet.xyz"
        ],
        "validation_rules": {
            "require_https": True,
            "allow_http": False
        }
    }
    with open(memory_path / "validation" / "endpoint_whitelist.json", 'w') as f:
        json.dump(whitelist, f)

    # Patch paths in fetch_hyperliquid module
    monkeypatch.setattr(fetch_hyperliquid, "MEMORY_BASE_PATH", memory_path)
    monkeypatch.setattr(fetch_hyperliquid, "CACHE_PATH", memory_path / "market_data")
    monkeypatch.setattr(fetch_hyperliquid, "SHARED_PATH", memory_path / "shared")
    monkeypatch.setattr(fetch_hyperliquid, "VALIDATION_PATH", memory_path / "validation")

    yield memory_path

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_hyperliquid_response():
    """Mock successful Hyperliquid API response."""
    return {
        "BTC": "111000.5",
        "ETH": "4000.25",
        "SOL": "200.50"
    }


# ============================================================================
# CACHE TESTS
# ============================================================================

def test_generate_cache_key():
    """Test cache key generation is deterministic."""
    key1 = generate_cache_key("allMids", {})
    key2 = generate_cache_key("allMids", {})
    assert key1 == key2

    # Different params should give different keys
    key3 = generate_cache_key("l2Book", {"coin": "BTC"})
    assert key1 != key3

    # Param order shouldn't matter
    key4 = generate_cache_key("test", {"a": 1, "b": 2})
    key5 = generate_cache_key("test", {"b": 2, "a": 1})
    assert key4 == key5


def test_write_and_read_cache(temp_memory_dir):
    """Test cache write and read operations."""
    cache_key = "test_cache_key"
    test_data = {"test": "data", "value": 123}
    endpoint = "allMids"
    latency = 150

    # Write cache
    write_cache(cache_key, test_data, endpoint, latency)

    # Verify file exists
    cache_file = temp_memory_dir / "market_data" / f"{cache_key}.json"
    assert cache_file.exists()

    # Read and verify cache
    cached_data = check_cache(cache_key, ttl_seconds=300)
    assert cached_data is not None
    assert cached_data["success"] == True
    assert cached_data["data"] == test_data
    assert cached_data["metadata"]["endpoint"] == endpoint
    assert cached_data["metadata"]["source"] == "cache"


def test_cache_expiration(temp_memory_dir):
    """Test that expired cache entries are not returned."""
    cache_key = "test_expiring_cache"
    test_data = {"test": "data"}

    # Write cache
    write_cache(cache_key, test_data, "allMids", 100)

    # Should be valid with long TTL
    cached = check_cache(cache_key, ttl_seconds=3600)
    assert cached is not None

    # Should be expired with 0 TTL
    cached = check_cache(cache_key, ttl_seconds=0)
    assert cached is None


def test_cache_corruption_handling(temp_memory_dir):
    """Test graceful handling of corrupted cache files."""
    cache_key = "corrupted_cache"
    cache_file = temp_memory_dir / "market_data" / f"{cache_key}.json"

    # Write invalid JSON
    with open(cache_file, 'w') as f:
        f.write("{invalid json")

    # Should return None for corrupted cache
    cached = check_cache(cache_key, ttl_seconds=300)
    assert cached is None


# ============================================================================
# ENDPOINT VALIDATION TESTS
# ============================================================================

def test_load_endpoint_whitelist(temp_memory_dir):
    """Test loading endpoint whitelist."""
    whitelist = load_endpoint_whitelist()
    assert whitelist is not None
    assert whitelist["immutable"] == True
    assert "https://api.hyperliquid.xyz" in whitelist["official_endpoints"]


def test_validate_official_endpoint(temp_memory_dir):
    """Test validation of official endpoints."""
    whitelist = load_endpoint_whitelist()

    # Should pass for official mainnet
    validate_endpoint_url("https://api.hyperliquid.xyz", whitelist)

    # Should pass for official testnet
    validate_endpoint_url("https://api.hyperliquid-testnet.xyz", whitelist)


def test_reject_unofficial_endpoint(temp_memory_dir):
    """Test rejection of unofficial endpoints."""
    whitelist = load_endpoint_whitelist()

    # Should fail for unofficial endpoint
    with pytest.raises(SecurityError):
        validate_endpoint_url("https://malicious-site.com", whitelist)


def test_reject_http_endpoint(temp_memory_dir):
    """Test rejection of HTTP (non-HTTPS) endpoints."""
    whitelist = load_endpoint_whitelist()

    # Should fail for HTTP
    with pytest.raises(SecurityError):
        validate_endpoint_url("http://api.hyperliquid.xyz", whitelist)


# ============================================================================
# SCHEMA VALIDATION TESTS
# ============================================================================

def test_validate_allmids_response():
    """Test validation of allMids response."""
    # Valid response
    valid_data = {
        "BTC": "111000.5",
        "ETH": "4000.25",
        "SOL": "200.50"
    }
    is_valid, error = validate_response("allMids", valid_data, strict=False)
    assert is_valid == True
    assert error == ""

    # Invalid response (non-string price)
    invalid_data = {
        "BTC": 111000.5  # Should be string, not number
    }
    is_valid, error = validate_response("allMids", invalid_data, strict=False)
    assert is_valid == False


def test_validate_l2book_response():
    """Test validation of l2Book response."""
    valid_data = {
        "coin": "BTC",
        "time": 1698765432000,
        "levels": [
            [{"px": "45000", "sz": "1.5", "n": 3}],
            [{"px": "44999", "sz": "2.0", "n": 5}]
        ]
    }
    is_valid, error = validate_response("l2Book", valid_data, strict=False)
    assert is_valid == True

    # Missing required field
    invalid_data = {
        "coin": "BTC"
        # Missing "levels" field
    }
    is_valid, error = validate_response("l2Book", invalid_data, strict=False)
    assert is_valid == False


def test_validate_candle_snapshot_response():
    """Test validation of candleSnapshot response."""
    valid_data = [
        {
            "t": 1698700000000,
            "T": 1698703600000,
            "s": "BTC",
            "i": "1h",
            "o": "44500.0",
            "h": "45000.0",
            "l": "44400.0",
            "c": "44900.0",
            "v": "1234.56",
            "n": 567
        }
    ]
    is_valid, error = validate_response("candleSnapshot", valid_data, strict=False)
    assert is_valid == True


# ============================================================================
# INTEGRATION TESTS (Require Network Access)
# ============================================================================

@pytest.mark.integration
def test_fetch_allmids_from_api(temp_memory_dir):
    """Test actual network call to Hyperliquid API."""
    from fetch_hyperliquid import fetch_from_api

    # Fetch allMids
    data, latency_ms = fetch_from_api("allMids", {}, environment="mainnet")

    # Verify response structure
    assert isinstance(data, dict)
    assert len(data) > 0  # Should have multiple coins
    assert "BTC" in data or "@1" in data  # Should have at least some coin
    assert latency_ms > 0  # Should have positive latency


@pytest.mark.integration
def test_full_fetch_and_cache_flow(temp_memory_dir):
    """Test complete fetch → cache → read flow."""
    from fetch_hyperliquid import fetch_from_api

    cache_key = generate_cache_key("allMids", {})

    # First call - should fetch from API
    data1, latency1 = fetch_from_api("allMids", {}, environment="mainnet")
    write_cache(cache_key, data1, "allMids", latency1)

    # Second call - should hit cache
    cached_data = check_cache(cache_key, ttl_seconds=300)
    assert cached_data is not None
    assert cached_data["data"] == data1
    assert cached_data["metadata"]["source"] == "cache"


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

@patch('fetch_hyperliquid.create_http_session')
def test_handle_network_timeout(mock_session, temp_memory_dir):
    """Test handling of network timeouts."""
    import requests
    from fetch_hyperliquid import fetch_from_api

    # Mock timeout
    mock_response = Mock()
    mock_response.post.side_effect = requests.exceptions.Timeout()
    mock_session.return_value = mock_response

    # Should raise exception with timeout message
    with pytest.raises(Exception) as exc_info:
        fetch_from_api("allMids", {}, environment="mainnet")
    assert "timeout" in str(exc_info.value).lower()


@patch('fetch_hyperliquid.create_http_session')
def test_handle_http_error(mock_session, temp_memory_dir):
    """Test handling of HTTP errors."""
    import requests
    from fetch_hyperliquid import fetch_from_api

    # Mock HTTP 500 error
    mock_response = Mock()
    mock_post = Mock()
    mock_post.raise_for_status.side_effect = requests.exceptions.HTTPError(
        response=Mock(status_code=500, text="Internal Server Error")
    )
    mock_response.post.return_value = mock_post
    mock_session.return_value = mock_response

    # Should raise exception with HTTP error message
    with pytest.raises(Exception) as exc_info:
        fetch_from_api("allMids", {}, environment="mainnet")
    assert "HTTP error" in str(exc_info.value)


# ============================================================================
# RATE LIMITING TESTS
# ============================================================================

def test_rate_limit_initialization(temp_memory_dir):
    """Test rate limit state initialization."""
    from fetch_hyperliquid import check_rate_limit

    # First call should initialize state file
    result = check_rate_limit()
    assert result == True

    # Verify state file created
    state_file = temp_memory_dir / "shared" / "rate_limit_state.json"
    assert state_file.exists()

    # Verify state structure
    with open(state_file, 'r') as f:
        state = json.load(f)
    assert "requests_this_minute" in state
    assert "window_start" in state
    assert "limit_per_minute" in state


def test_rate_limit_enforcement(temp_memory_dir):
    """Test rate limit enforcement."""
    from fetch_hyperliquid import check_rate_limit, RATE_LIMIT_PER_MINUTE

    # Should allow requests under limit
    for i in range(10):
        assert check_rate_limit() == True

    # Manually set state to limit
    state_file = temp_memory_dir / "shared" / "rate_limit_state.json"
    with open(state_file, 'w') as f:
        json.dump({
            "requests_this_minute": RATE_LIMIT_PER_MINUTE,
            "window_start": datetime.now().isoformat(),
            "limit_per_minute": RATE_LIMIT_PER_MINUTE
        }, f)

    # Should deny request when at limit
    assert check_rate_limit() == False


# ============================================================================
# COMMAND-LINE TESTS
# ============================================================================

def test_main_success(temp_memory_dir, mock_hyperliquid_response, monkeypatch):
    """Test main() function with successful API call."""
    import io
    from fetch_hyperliquid import main

    # Mock stdin with valid input
    input_data = {
        "endpoint": "allMids",
        "params": {},
        "cache_config": {
            "enabled": True,
            "force_refresh": True
        }
    }
    monkeypatch.setattr('sys.stdin', io.StringIO(json.dumps(input_data)))

    # Mock fetch_from_api
    with patch('fetch_hyperliquid.fetch_from_api') as mock_fetch:
        mock_fetch.return_value = (mock_hyperliquid_response, 150)

        # Capture stdout
        captured_output = io.StringIO()
        monkeypatch.setattr('sys.stdout', captured_output)

        # Run main
        main()

        # Verify output
        output = json.loads(captured_output.getvalue())
        assert output["success"] == True
        assert output["data"] == mock_hyperliquid_response
        assert output["metadata"]["source"] == "api"


def test_main_security_error(temp_memory_dir, monkeypatch):
    """Test main() function with security violation."""
    import io
    from fetch_hyperliquid import main

    # Mock stdin with valid input
    input_data = {
        "endpoint": "allMids",
        "params": {}
    }
    monkeypatch.setattr('sys.stdin', io.StringIO(json.dumps(input_data)))

    # Mock the whitelist to reject the official endpoint (force security error)
    def mock_validate_endpoint(url, whitelist):
        raise fetch_hyperliquid.SecurityError(f"REJECTED: {url}")

    monkeypatch.setattr('fetch_hyperliquid.validate_endpoint_url', mock_validate_endpoint)

    # Capture stdout
    captured_output = io.StringIO()
    monkeypatch.setattr('sys.stdout', captured_output)

    # Run main (should exit with error)
    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1

    # Verify error output
    output = json.loads(captured_output.getvalue())
    assert output["success"] == False
    assert "SECURITY ERROR" in output["error"]
    assert output["error_type"] == "security_violation"
