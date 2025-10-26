# Hyperliquid Fetch and Cache Skill

## Overview

This skill fetches market data from official Hyperliquid API endpoints, validates the data against schemas, caches results in the Memory Tool, and returns the data to the calling agent.

**Key Features:**
- Network calls to official Hyperliquid endpoints only (api.hyperliquid.xyz)
- Endpoint whitelist validation (security-critical)
- Intelligent caching with TTL-based expiration
- Rate limit coordination across concurrent agents
- Schema validation for data integrity
- Atomic file operations (last-write-wins for price data)

## Usage

```json
{
  "endpoint": "allMids",
  "params": {},
  "cache_config": {
    "enabled": true,
    "ttl_seconds": 300,
    "force_refresh": false
  }
}
```

## Supported Endpoints

### Market Data Endpoints
- `allMids` - Current mid prices for all markets
- `meta` - Exchange metadata (coins, universe)
- `metaAndAssetCtxs` - Metadata + asset contexts
- `l2Book` - Level 2 order book (requires `params.coin`)
- `trades` - Recent trades (requires `params.coin`)
- `candleSnapshot` - Historical candles (requires `params.coin`, `params.interval`, `params.startTime`, `params.endTime`)
- `userFills` - User fills (requires `params.user`)
- `userFunding` - User funding payments (requires `params.user`)
- `openOrders` - Open orders (requires `params.user`)
- `frontendOpenOrders` - Frontend open orders (requires `params.user`)
- `userRateLimit` - User rate limit info (requires `params.user`)

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "endpoint": {
      "type": "string",
      "enum": ["allMids", "meta", "metaAndAssetCtxs", "l2Book", "trades", "candleSnapshot", "userFills", "userFunding", "openOrders", "frontendOpenOrders", "userRateLimit"],
      "description": "Hyperliquid API endpoint to call"
    },
    "params": {
      "type": "object",
      "description": "Endpoint-specific parameters",
      "additionalProperties": true
    },
    "cache_config": {
      "type": "object",
      "properties": {
        "enabled": {
          "type": "boolean",
          "default": true,
          "description": "Whether to use caching"
        },
        "ttl_seconds": {
          "type": "integer",
          "default": 300,
          "description": "Cache time-to-live in seconds"
        },
        "force_refresh": {
          "type": "boolean",
          "default": false,
          "description": "Force refresh from API (ignore cache)"
        }
      }
    }
  },
  "required": ["endpoint"]
}
```

## Output Schema

```json
{
  "type": "object",
  "properties": {
    "success": {
      "type": "boolean",
      "description": "Whether the operation succeeded"
    },
    "data": {
      "type": "object",
      "description": "The fetched market data"
    },
    "metadata": {
      "type": "object",
      "properties": {
        "source": {
          "type": "string",
          "enum": ["cache", "api"],
          "description": "Where the data came from"
        },
        "timestamp": {
          "type": "string",
          "format": "date-time",
          "description": "When the data was fetched"
        },
        "endpoint": {
          "type": "string",
          "description": "The endpoint that was called"
        },
        "cached_until": {
          "type": "string",
          "format": "date-time",
          "description": "When the cache entry expires (if from cache)"
        },
        "api_latency_ms": {
          "type": "integer",
          "description": "API call latency in milliseconds (if from API)"
        }
      }
    },
    "error": {
      "type": "string",
      "description": "Error message if success=false"
    }
  },
  "required": ["success"]
}
```

## Examples

### Example 1: Get All Mid Prices
```json
// Input
{
  "endpoint": "allMids",
  "params": {}
}

// Output
{
  "success": true,
  "data": {
    "BTC": "45000.5",
    "ETH": "2500.25",
    "SOL": "100.50"
  },
  "metadata": {
    "source": "api",
    "timestamp": "2025-10-25T14:30:00.123Z",
    "endpoint": "allMids",
    "api_latency_ms": 150
  }
}
```

### Example 2: Get Order Book (with caching)
```json
// Input
{
  "endpoint": "l2Book",
  "params": {
    "coin": "BTC"
  },
  "cache_config": {
    "enabled": true,
    "ttl_seconds": 60
  }
}

// Output
{
  "success": true,
  "data": {
    "coin": "BTC",
    "time": 1698765432000,
    "levels": [
      [{"px": "45000", "sz": "1.5", "n": 3}],
      [{"px": "44999", "sz": "2.0", "n": 5}]
    ]
  },
  "metadata": {
    "source": "cache",
    "timestamp": "2025-10-25T14:29:30.000Z",
    "endpoint": "l2Book",
    "cached_until": "2025-10-25T14:30:30.000Z"
  }
}
```

### Example 3: Get Historical Candles
```json
// Input
{
  "endpoint": "candleSnapshot",
  "params": {
    "coin": "BTC",
    "interval": "1h",
    "startTime": 1698700000000,
    "endTime": 1698786400000
  },
  "cache_config": {
    "enabled": true,
    "ttl_seconds": 86400  // 24 hours (immutable historical data)
  }
}

// Output
{
  "success": true,
  "data": [
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
  ],
  "metadata": {
    "source": "api",
    "timestamp": "2025-10-25T14:30:00.000Z",
    "endpoint": "candleSnapshot",
    "cached_until": "2025-10-26T14:30:00.000Z"
  }
}
```

## Error Handling

The skill handles the following error scenarios:

1. **Invalid Endpoint**: Returns error if endpoint not in whitelist
2. **Network Errors**: Retries with exponential backoff (3 attempts)
3. **Rate Limits**: Coordinates with other agents via shared state
4. **Schema Validation Failures**: Returns error with validation details
5. **Cache Corruption**: Falls back to API call
6. **Timeout**: Returns error after 10 seconds

## Implementation Notes

- **Endpoint Validation**: All URLs validated against `/memories/validation/endpoint_whitelist.json`
- **Concurrency Strategy**: Last-write-wins for price data (acceptable for ephemeral data)
- **Rate Limiting**: Centralized coordination via `/memories/shared/rate_limit_state.json`
- **Cache Storage**: `/memories/market_data/{endpoint}_{params_hash}.json`
- **Atomic Writes**: Uses temp file + rename pattern for atomicity

## Security

- ✅ Only official Hyperliquid endpoints allowed
- ✅ HTTPS required (HTTP rejected)
- ✅ Endpoint whitelist immutable (alerts on modification)
- ✅ Input validation before network calls
- ✅ Script sandboxing via RestrictedPython

## Performance

- **Cache hit rate target**: >70%
- **API call reduction target**: >80%
- **Typical latency**: <200ms (cache), <500ms (API)
- **Token cost**: ~100 tokens (skill invocation only, execution is 0 tokens)

## Related Documentation

- [ARCHITECTURE.md](../../ARCHITECTURE.md) - Overall system architecture
- [SKILLS_NETWORK_REVISION.md](../../SKILLS_NETWORK_REVISION.md) - Skills-centric approach
- [MEMORY_CONCURRENCY_ANALYSIS.md](../../MEMORY_CONCURRENCY_ANALYSIS.md) - Concurrency strategy
