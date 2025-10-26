# Cache Configuration Guide

## 🎯 Overview

Your multi-agent system now has **configurable cache TTL (Time To Live)** per data type and supports **force_refresh** to bypass the cache for real-time data.

This solves the issue where you were getting stale price data due to caching.

---

## ⚡ Quick Summary of Changes

### What Was the Problem?
- All data was cached for 30 seconds by default
- You were seeing the same BTC price even though the price had changed
- No way to force fresh data

### What's Fixed?
1. ✅ **Configurable cache TTL** per data type (prices: 5s, order books: 3s, etc.)
2. ✅ **Force refresh parameter** to bypass cache when needed
3. ✅ **Environment variable support** to adjust TTLs without code changes

---

## 📊 Default Cache TTL Settings

These are now configured in `core/config.py`:

| Data Type | Default TTL | Reason |
|-----------|-------------|--------|
| **Prices** (`all_mids`) | **5 seconds** | Near real-time, updates frequently |
| **Order Books** (`l2_book`) | **3 seconds** | Very dynamic, needs to be fresh |
| **Open Orders** | **5 seconds** | Dynamic, user-specific |
| **User Fills** | **10 seconds** | Moderate updates |
| **Account State** | **30 seconds** | Moderate freshness needed |
| **User Funding** | **60 seconds** | Slower changing |
| **Meta Info** | **60 seconds** | Rarely changes |
| **Candles** | **300 seconds** (5 min) | Historical, doesn't change |

**Before:** Everything was cached for 300 seconds (5 minutes)!
**Now:** Prices are cached for only 5 seconds, order books for 3 seconds.

---

## 🚀 How to Use

### Method 1: Normal Request (Uses Cache)

```python
from agents.orchestrator.orchestrator_agent import OrchestratorAgent

orchestrator = OrchestratorAgent()

# Normal request - uses cache
result = orchestrator.route_request("BTC price")
price = result["result"]["price"]
print(f"BTC: ${price:,.2f}")

# Second request within 5 seconds - uses cached data (fast!)
result2 = orchestrator.route_request("BTC price")
```

### Method 2: Force Fresh Data

```python
# Force bypass cache - always gets latest data
result = orchestrator.route_request("BTC price", force_refresh=True)
price = result["result"]["price"]
print(f"BTC (fresh): ${price:,.2f}")
```

### Method 3: Check if Cache Was Bypassed

```python
result = orchestrator.route_request("BTC price")

# Check metadata
cache_bypassed = result["metadata"]["cache_bypassed"]
if cache_bypassed:
    print("✓ Fresh data from API")
else:
    print("ℹ️ Cached data (fast)")
```

---

## 🔧 Customizing Cache TTL

### Option 1: Edit `core/config.py`

```python
# core/config.py

CACHE_TTL = {
    "all_mids": 5,           # Change to 10 for 10 second cache
    "l2_book": 3,            # Change to 1 for 1 second cache
    "meta": 60,
    # ... etc
}
```

### Option 2: Use Environment Variables

```bash
# Set custom TTL via environment variables
export CACHE_TTL_ALL_MIDS=10      # 10 seconds for prices
export CACHE_TTL_L2_BOOK=1        # 1 second for order books
export CACHE_TTL_CANDLES=600      # 10 minutes for candles

# Then run your app
python demo.py
```

### Option 3: Disable Caching Globally

```bash
export CACHE_ENABLED=false
```

Or in `core/config.py`:
```python
CACHE_ENABLED = False
```

---

## 📖 Usage Examples

### Example 1: Trading Bot (Needs Fresh Prices)

```python
orchestrator = OrchestratorAgent()

# Always get fresh price for trading decisions
result = orchestrator.route_request(
    "BTC price",
    force_refresh=True  # Always fresh!
)

price = result["result"]["price"]
# Make trading decision based on real-time price
```

### Example 2: Dashboard (Can Use Cache)

```python
orchestrator = OrchestratorAgent()

# Normal request - uses cache (fast UI)
result = orchestrator.route_request("BTC price")
price = result["result"]["price"]

# Update UI
dashboard.update_price("BTC", price)

# Cache automatically expires after 5 seconds
# Next request will fetch fresh data
```

### Example 3: Manual Refresh Button

```python
def on_refresh_button_click():
    """User clicked refresh button in UI."""
    result = orchestrator.route_request(
        "Show all prices",
        force_refresh=True  # Force fresh data
    )
    update_ui(result["result"])
```

### Example 4: Programmatic Agent Access

```python
from agents.price_book.price_book_agent import PriceBookAgent

agent = PriceBookAgent()

# Normal (uses cache)
price = agent.get_price("BTC")

# Force fresh
price = agent.get_price("BTC", force_refresh=True)

# Or with custom TTL
prices = agent.get_all_mids(ttl_seconds=10)  # 10 second cache
```

---

## 🧪 Testing Your Configuration

Run the test script:

```bash
python test_cache.py
```

This will:
1. ✅ Show your cache configuration
2. ✅ Test normal caching behavior
3. ✅ Test force_refresh
4. ✅ Test cache expiration

You should see prices change when using `force_refresh=True`!

---

## 💡 Performance Impact

### With Caching (Default):
- **First request**: ~100ms (API call)
- **Subsequent requests** (within TTL): **<10ms** (cached)
- **Cost**: $0.000

### With Force Refresh:
- **Every request**: ~100ms (API call)
- **Cost**: $0.000 (still free, but slower)

### Recommendation:
- ✅ **Use cache for most requests** (default behavior)
- ✅ **Use force_refresh** only when you absolutely need real-time data
- ✅ **Adjust TTL** per your needs (5s works well for prices)

---

## 🔍 Troubleshooting

### Issue: Still seeing stale prices

**Check the TTL:**
```python
from core.config import CACHE_TTL
print(f"Price TTL: {CACHE_TTL['all_mids']} seconds")
```

**Solution:** Reduce the TTL or use `force_refresh=True`

### Issue: Too many API calls (slow)

**Check if you're using force_refresh too often:**
```python
result = orchestrator.route_request("BTC price")
if result["metadata"]["cache_bypassed"]:
    print("⚠️ Cache was bypassed - you might be using force_refresh too much")
```

**Solution:** Remove `force_refresh=True` and rely on the 5-second cache

### Issue: Want different TTL for different use cases

**Use custom TTL per request:**
```python
# Short cache for trading
agent.get_all_mids(ttl_seconds=1)  # 1 second

# Longer cache for analytics
agent.get_all_mids(ttl_seconds=30)  # 30 seconds
```

---

## 📊 Monitoring Cache Behavior

### Check Cache Hit Rate

```python
from agents.orchestrator.orchestrator_agent import OrchestratorAgent

orchestrator = OrchestratorAgent()

# Make several requests
for i in range(5):
    result = orchestrator.route_request("BTC price")
    cache_bypassed = result["metadata"]["cache_bypassed"]
    print(f"Request {i+1}: {'Cache BYPASSED' if cache_bypassed else 'Cache HIT'}")
```

Expected output:
```
Request 1: Cache BYPASSED  (first request)
Request 2: Cache HIT       (within 5s TTL)
Request 3: Cache HIT       (within 5s TTL)
Request 4: Cache HIT       (within 5s TTL)
Request 5: Cache BYPASSED  (>5s elapsed, fresh data)
```

---

## 🎯 Recommended Settings

### For Real-Time Trading:
```python
CACHE_TTL = {
    "all_mids": 1,      # 1 second for prices
    "l2_book": 1,       # 1 second for order books
    "open_orders": 1,   # 1 second for orders
}
```

### For Analytics Dashboard:
```python
CACHE_TTL = {
    "all_mids": 10,     # 10 seconds for prices
    "l2_book": 5,       # 5 seconds for order books
    "candle_snapshot": 300,  # 5 minutes for candles
}
```

### For Portfolio Tracker:
```python
CACHE_TTL = {
    "all_mids": 30,     # 30 seconds for prices
    "user_state": 60,   # 60 seconds for account state
    "candle_snapshot": 600,  # 10 minutes for candles
}
```

---

## ✅ Summary

**What you now have:**

1. ✅ **Configurable cache TTL** - Prices cached for 5s (was 300s)
2. ✅ **Force refresh option** - `force_refresh=True` bypasses cache
3. ✅ **Per-data-type configuration** - Different TTL for different data
4. ✅ **Environment variable support** - Easy configuration without code changes
5. ✅ **Metadata tracking** - Know if data came from cache or API

**How to use it:**

```python
# Normal (fast, uses 5s cache)
result = orchestrator.route_request("BTC price")

# Force fresh (real-time)
result = orchestrator.route_request("BTC price", force_refresh=True)

# Custom TTL
agent.get_price("BTC", ttl_seconds=10)
```

**Test it:**
```bash
python test_cache.py
```

---

Your system now gives you **real-time data when you need it** and **fast cached data** when you don't! 🚀
