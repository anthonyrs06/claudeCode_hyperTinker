# Interactive Demo: Hyperliquid Fetch Skill

This guide shows you how to interact with the Phase 1 implementation.

## Quick Start

All commands should be run from the project root directory.

### 1. Get All Mid Prices (Most Popular)

```bash
echo '{"endpoint": "allMids", "params": {}}' | \
  ./venv/bin/python3 skills/hyperliquid-fetch-and-cache/scripts/fetch_hyperliquid.py | \
  python3 -m json.tool | head -50
```

### 2. Get Specific Coin Prices

```bash
# Get all prices, filter for BTC/ETH/SOL
echo '{"endpoint": "allMids", "params": {}}' | \
  ./venv/bin/python3 skills/hyperliquid-fetch-and-cache/scripts/fetch_hyperliquid.py | \
  python3 -c "import sys, json; data = json.load(sys.stdin); print(f\"BTC: \${data['data']['BTC']}\"); print(f\"ETH: \${data['data']['ETH']}\"); print(f\"SOL: \${data['data']['SOL']}\")"
```

### 3. Get Order Book for BTC

```bash
echo '{"endpoint": "l2Book", "params": {"coin": "BTC"}}' | \
  ./venv/bin/python3 skills/hyperliquid-fetch-and-cache/scripts/fetch_hyperliquid.py | \
  python3 -m json.tool | head -80
```

### 4. Get Exchange Metadata

```bash
echo '{"endpoint": "meta", "params": {}}' | \
  ./venv/bin/python3 skills/hyperliquid-fetch-and-cache/scripts/fetch_hyperliquid.py | \
  python3 -m json.tool | head -100
```

### 5. Get Recent Trades for ETH

```bash
echo '{"endpoint": "trades", "params": {"coin": "ETH"}}' | \
  ./venv/bin/python3 skills/hyperliquid-fetch-and-cache/scripts/fetch_hyperliquid.py | \
  python3 -m json.tool | head -80
```

### 6. Test Cache Behavior

```bash
# First call - hits API
echo "=== First call (should be from API) ===" && \
echo '{"endpoint": "allMids", "params": {}}' | \
  ./venv/bin/python3 skills/hyperliquid-fetch-and-cache/scripts/fetch_hyperliquid.py | \
  python3 -c "import sys, json; data = json.load(sys.stdin); print(f\"Source: {data['metadata']['source']}\"); print(f\"Latency: {data['metadata'].get('api_latency_ms', 'N/A')}ms\")"

echo ""
sleep 1

# Second call - hits cache
echo "=== Second call (should be from cache) ===" && \
echo '{"endpoint": "allMids", "params": {}}' | \
  ./venv/bin/python3 skills/hyperliquid-fetch-and-cache/scripts/fetch_hyperliquid.py | \
  python3 -c "import sys, json; data = json.load(sys.stdin); print(f\"Source: {data['metadata']['source']}\"); print(f\"Cached until: {data['metadata'].get('cached_until', 'N/A')}\")"
```

### 7. Force Refresh (Bypass Cache)

```bash
echo '{"endpoint": "allMids", "params": {}, "cache_config": {"force_refresh": true}}' | \
  ./venv/bin/python3 skills/hyperliquid-fetch-and-cache/scripts/fetch_hyperliquid.py | \
  python3 -c "import sys, json; data = json.load(sys.stdin); print(f\"Source: {data['metadata']['source']} (forced refresh)\")"
```

### 8. Disable Cache

```bash
echo '{"endpoint": "allMids", "params": {}, "cache_config": {"enabled": false}}' | \
  ./venv/bin/python3 skills/hyperliquid-fetch-and-cache/scripts/fetch_hyperliquid.py | \
  python3 -c "import sys, json; data = json.load(sys.stdin); print(f\"Source: {data['metadata']['source']} (cache disabled)\")"
```

### 9. Custom TTL (Cache for 10 seconds)

```bash
echo '{"endpoint": "allMids", "params": {}, "cache_config": {"ttl_seconds": 10}}' | \
  ./venv/bin/python3 skills/hyperliquid-fetch-and-cache/scripts/fetch_hyperliquid.py | \
  python3 -c "import sys, json; data = json.load(sys.stdin); print(f\"Cached until: {data['metadata'].get('cached_until', 'N/A')}\")"
```

## Advanced Interactions

### View Cache Files

```bash
# List cached data
ls -lh memories/market_data/

# View a cache file
cat memories/market_data/allMids_*.json | python3 -m json.tool | head -50
```

### Check Rate Limit State

```bash
cat memories/shared/rate_limit_state.json | python3 -m json.tool
```

### View Endpoint Whitelist

```bash
cat memories/validation/endpoint_whitelist.json | python3 -m json.tool
```

### Test Security (Should Fail)

This will demonstrate endpoint validation:

```bash
# Try to bypass whitelist (will fail)
# Modify the script to use an unofficial URL and see it get rejected
```

## Monitoring Performance

### Measure Latency

```bash
# Time the API call
time echo '{"endpoint": "allMids", "params": {}, "cache_config": {"force_refresh": true}}' | \
  ./venv/bin/python3 skills/hyperliquid-fetch-and-cache/scripts/fetch_hyperliquid.py > /dev/null
```

### Measure Cache Hit Performance

```bash
# Time the cached call
time echo '{"endpoint": "allMids", "params": {}}' | \
  ./venv/bin/python3 skills/hyperliquid-fetch-and-cache/scripts/fetch_hyperliquid.py > /dev/null
```

## Testing Different Endpoints

### Historical Candles

```bash
# Get 1-hour BTC candles (last 24 hours)
START_TIME=$(python3 -c "import time; print(int((time.time() - 86400) * 1000))")
END_TIME=$(python3 -c "import time; print(int(time.time() * 1000))")

echo "{\"endpoint\": \"candleSnapshot\", \"params\": {\"coin\": \"BTC\", \"interval\": \"1h\", \"startTime\": $START_TIME, \"endTime\": $END_TIME}}" | \
  ./venv/bin/python3 skills/hyperliquid-fetch-and-cache/scripts/fetch_hyperliquid.py | \
  python3 -m json.tool | head -100
```

### Multiple Coins Order Books

```bash
# BTC order book
echo "=== BTC Order Book ===" && \
echo '{"endpoint": "l2Book", "params": {"coin": "BTC"}}' | \
  ./venv/bin/python3 skills/hyperliquid-fetch-and-cache/scripts/fetch_hyperliquid.py | \
  python3 -c "import sys, json; data = json.load(sys.stdin); levels = data['data']['levels']; print(f\"Top bid: {levels[0][0]['px']}\"); print(f\"Top ask: {levels[1][0]['px']}\")"

echo ""

# ETH order book
echo "=== ETH Order Book ===" && \
echo '{"endpoint": "l2Book", "params": {"coin": "ETH"}}' | \
  ./venv/bin/python3 skills/hyperliquid-fetch-and-cache/scripts/fetch_hyperliquid.py | \
  python3 -c "import sys, json; data = json.load(sys.stdin); levels = data['data']['levels']; print(f\"Top bid: {levels[0][0]['px']}\"); print(f\"Top ask: {levels[1][0]['px']}\")"
```

## Pretty Output Examples

### Show Top 10 Coins by Price

```bash
echo '{"endpoint": "allMids", "params": {}}' | \
  ./venv/bin/python3 skills/hyperliquid-fetch-and-cache/scripts/fetch_hyperliquid.py | \
  python3 -c "
import sys, json
data = json.load(sys.stdin)
prices = [(k, float(v)) for k, v in data['data'].items() if not k.startswith('@')]
prices.sort(key=lambda x: x[1], reverse=True)
print('Top 10 Coins by Price:')
for coin, price in prices[:10]:
    print(f'{coin:8} \${price:,.2f}')
"
```

### Monitor Cache Performance

```bash
#!/bin/bash
# Save this as test_cache_performance.sh

echo "Testing cache performance..."
echo ""

# First call (API)
echo "Call 1 (API):"
time echo '{"endpoint": "allMids", "params": {}, "cache_config": {"force_refresh": true}}' | \
  ./venv/bin/python3 skills/hyperliquid-fetch-and-cache/scripts/fetch_hyperliquid.py > /dev/null 2>&1

echo ""

# Cached calls
echo "Call 2-5 (Cache):"
for i in {2..5}; do
  echo -n "  Call $i: "
  time echo '{"endpoint": "allMids", "params": {}}' | \
    ./venv/bin/python3 skills/hyperliquid-fetch-and-cache/scripts/fetch_hyperliquid.py > /dev/null 2>&1
done
```

## Troubleshooting

### Clear Cache

```bash
rm -rf memories/market_data/*.json
echo "Cache cleared!"
```

### Reset Rate Limit State

```bash
rm -f memories/shared/rate_limit_state.json
echo "Rate limit state reset!"
```

### View Error Messages

```bash
# Run with stderr visible
echo '{"endpoint": "invalid_endpoint", "params": {}}' | \
  ./venv/bin/python3 skills/hyperliquid-fetch-and-cache/scripts/fetch_hyperliquid.py 2>&1
```

## Next: Run Unit Tests

```bash
# Run all tests
./venv/bin/python -m pytest skills/hyperliquid-fetch-and-cache/tests/ -v

# Run specific test
./venv/bin/python -m pytest skills/hyperliquid-fetch-and-cache/tests/test_fetch_hyperliquid.py::test_cache_expiration -v

# Run with coverage
./venv/bin/python -m pytest skills/hyperliquid-fetch-and-cache/tests/ --cov=skills --cov-report=html
```
