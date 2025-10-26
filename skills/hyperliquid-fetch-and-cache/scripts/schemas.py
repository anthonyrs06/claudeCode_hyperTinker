"""
Hyperliquid API Response Schemas
================================
JSON schemas for validating responses from Hyperliquid API endpoints.

These schemas ensure data integrity and catch API changes early.
"""

from typing import Dict, Any


# ============================================================================
# SCHEMA DEFINITIONS
# ============================================================================

# allMids: Dictionary of coin symbol -> mid price string
SCHEMA_ALL_MIDS = {
    "type": "object",
    "additionalProperties": {
        "type": "string",
        "pattern": "^[0-9]+(\\.[0-9]+)?$"  # Numeric string
    },
    "minProperties": 1  # At least one coin
}

# meta: Exchange metadata
SCHEMA_META = {
    "type": "object",
    "properties": {
        "universe": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "szDecimals": {"type": "integer"},
                    "maxLeverage": {"type": "integer"},
                    "onlyIsolated": {"type": "boolean"}
                },
                "required": ["name"]
            }
        }
    },
    "required": ["universe"]
}

# l2Book: Level 2 order book
# Simplified schema - just check basic structure
SCHEMA_L2_BOOK = {
    "type": "object",
    "properties": {
        "coin": {"type": "string"},
        "time": {"type": "integer"},  # Unix timestamp
        "levels": {"type": "array"}  # Array of [bids, asks]
    },
    "required": ["coin", "levels"]
}

# trades: Recent trades
SCHEMA_TRADES = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "coin": {"type": "string"},
            "side": {"type": "string", "enum": ["A", "B"]},  # Ask/Bid
            "px": {"type": "string"},
            "sz": {"type": "string"},
            "time": {"type": "integer"},
            "hash": {"type": "string"}
        },
        "required": ["coin", "side", "px", "sz", "time"]
    }
}

# candleSnapshot: Historical candles
SCHEMA_CANDLE_SNAPSHOT = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "t": {"type": "integer"},   # Start time
            "T": {"type": "integer"},   # End time
            "s": {"type": "string"},    # Symbol
            "i": {"type": "string"},    # Interval
            "o": {"type": "string"},    # Open
            "h": {"type": "string"},    # High
            "l": {"type": "string"},    # Low
            "c": {"type": "string"},    # Close
            "v": {"type": "string"},    # Volume
            "n": {"type": "integer"}    # Number of trades
        },
        "required": ["t", "T", "s", "i", "o", "h", "l", "c", "v", "n"]
    }
}

# userFills: User fills/trades
SCHEMA_USER_FILLS = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "coin": {"type": "string"},
            "px": {"type": "string"},
            "sz": {"type": "string"},
            "side": {"type": "string"},
            "time": {"type": "integer"},
            "startPosition": {"type": "string"},
            "dir": {"type": "string"},
            "closedPnl": {"type": "string"},
            "hash": {"type": "string"},
            "oid": {"type": "integer"},
            "crossed": {"type": "boolean"},
            "fee": {"type": "string"},
            "tid": {"type": "integer"},
            "feeToken": {"type": "string"}
        },
        "required": ["coin", "px", "sz", "side", "time"]
    }
}

# openOrders: Open orders
SCHEMA_OPEN_ORDERS = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "coin": {"type": "string"},
            "side": {"type": "string"},
            "limitPx": {"type": "string"},
            "sz": {"type": "string"},
            "oid": {"type": "integer"},
            "timestamp": {"type": "integer"},
            "origSz": {"type": "string"},
            "cloid": {}  # Optional client order ID
        },
        "required": ["coin", "side", "limitPx", "sz", "oid", "timestamp"]
    }
}

# metaAndAssetCtxs: Meta + asset contexts (combined)
SCHEMA_META_AND_ASSET_CTXS = {
    "type": "array",
    "minItems": 2,
    "maxItems": 2,
    "items": [
        SCHEMA_META,  # First element is meta
        {
            "type": "array",  # Second element is asset contexts
            "items": {
                "type": "object",
                "properties": {
                    "dayNtlVlm": {"type": "string"},
                    "funding": {"type": "string"},
                    "openInterest": {"type": "string"},
                    "prevDayPx": {"type": "string"},
                    "markPx": {"type": "string"},
                    "midPx": {"type": "string"},
                    "impactPxs": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                }
            }
        }
    ]
}


# ============================================================================
# SCHEMA REGISTRY
# ============================================================================

# Map endpoint names to their schemas
ENDPOINT_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "allMids": SCHEMA_ALL_MIDS,
    "meta": SCHEMA_META,
    "metaAndAssetCtxs": SCHEMA_META_AND_ASSET_CTXS,
    "l2Book": SCHEMA_L2_BOOK,
    "trades": SCHEMA_TRADES,
    "candleSnapshot": SCHEMA_CANDLE_SNAPSHOT,
    "userFills": SCHEMA_USER_FILLS,
    "userFunding": SCHEMA_USER_FILLS,  # Same schema as userFills
    "openOrders": SCHEMA_OPEN_ORDERS,
    "frontendOpenOrders": SCHEMA_OPEN_ORDERS,  # Same schema as openOrders

    # Note: userRateLimit schema is flexible (varies by user state)
    # We'll use basic validation for it
    "userRateLimit": {
        "type": "object",
        "additionalProperties": True
    }
}


# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================

def get_schema_for_endpoint(endpoint: str) -> Dict[str, Any]:
    """
    Get JSON schema for a given endpoint.
    Returns None if no schema defined (validation disabled for that endpoint).
    """
    return ENDPOINT_SCHEMAS.get(endpoint)


def validate_response(endpoint: str, data: Any, strict: bool = True) -> tuple[bool, str]:
    """
    Validate API response against schema.

    Args:
        endpoint: The endpoint name
        data: The response data to validate
        strict: If True, raise exception on validation failure
                If False, return (False, error_message) on failure

    Returns:
        (is_valid, error_message)
        - (True, "") if valid
        - (False, error_msg) if invalid

    Raises:
        ValidationError if strict=True and validation fails
    """
    schema = get_schema_for_endpoint(endpoint)

    if schema is None:
        # No schema defined - skip validation
        return True, ""

    try:
        import jsonschema
        jsonschema.validate(instance=data, schema=schema)
        return True, ""
    except jsonschema.ValidationError as e:
        error_msg = f"Schema validation failed for endpoint '{endpoint}': {str(e)}"
        if strict:
            raise ValidationError(error_msg)
        return False, error_msg
    except jsonschema.SchemaError as e:
        error_msg = f"Invalid schema definition for endpoint '{endpoint}': {str(e)}"
        if strict:
            raise ValidationError(error_msg)
        return False, error_msg


class ValidationError(Exception):
    """Raised when response schema validation fails."""
    pass


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_supported_endpoints() -> list[str]:
    """Get list of all supported endpoints with schemas."""
    return list(ENDPOINT_SCHEMAS.keys())


def has_schema(endpoint: str) -> bool:
    """Check if an endpoint has a validation schema defined."""
    return endpoint in ENDPOINT_SCHEMAS
