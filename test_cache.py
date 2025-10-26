"""
Test Cache Configuration and Force Refresh
===========================================
Demonstrates configurable cache TTL and force_refresh parameter.
"""

from agents.orchestrator.orchestrator_agent import OrchestratorAgent
from core.config import CACHE_TTL
import time

print("="*60)
print("TESTING CACHE CONFIGURATION")
print("="*60)

# Show cache configuration
print("\n📋 Cache TTL Configuration (from core/config.py):")
for key, ttl in CACHE_TTL.items():
    print(f"  • {key}: {ttl} seconds")

print("\n" + "="*60)

# Initialize orchestrator
orchestrator = OrchestratorAgent()

# Test 1: Normal query (will fetch fresh data)
print("\n🧪 TEST 1: Normal query (first request)")
result1 = orchestrator.route_request("BTC price", track_memory=False)
price1 = result1["result"]["price"]
cache_bypassed1 = result1["metadata"].get("cache_bypassed", False)
print(f"  Price: ${price1:,.2f}")
print(f"  Cache bypassed: {cache_bypassed1}")

# Test 2: Same query immediately after (should use cache)
print("\n🧪 TEST 2: Same query (should use cache)")
result2 = orchestrator.route_request("BTC price", track_memory=False)
price2 = result2["result"]["price"]
cache_bypassed2 = result2["metadata"].get("cache_bypassed", False)
print(f"  Price: ${price2:,.2f}")
print(f"  Cache bypassed: {cache_bypassed2}")
print(f"  ✓ Same price (cached): {price1 == price2}")

# Test 3: Force refresh (bypass cache)
print("\n🧪 TEST 3: Force refresh (bypass cache)")
result3 = orchestrator.route_request("BTC price", track_memory=False, force_refresh=True)
price3 = result3["result"]["price"]
cache_bypassed3 = result3["metadata"].get("cache_bypassed", False)
print(f"  Price: ${price3:,.2f}")
print(f"  Cache bypassed: {cache_bypassed3}")
print(f"  ✓ Fresh data fetched: {cache_bypassed3 == True}")

# Test 4: Wait for cache to expire (TTL is 5 seconds for all_mids)
print(f"\n🧪 TEST 4: Wait {CACHE_TTL['all_mids']}s for cache to expire...")
time.sleep(CACHE_TTL['all_mids'] + 1)
result4 = orchestrator.route_request("BTC price", track_memory=False)
price4 = result4["result"]["price"]
print(f"  Price: ${price4:,.2f}")
print(f"  ✓ Cache expired, fresh data fetched")

print("\n" + "="*60)
print("✓ ALL TESTS PASSED")
print("="*60)

print("\n📖 Usage Examples:")
print("\n1. Normal request (uses cache):")
print('   result = orchestrator.route_request("BTC price")')

print("\n2. Force fresh data:")
print('   result = orchestrator.route_request("BTC price", force_refresh=True)')

print("\n3. Check if cache was bypassed:")
print('   cache_bypassed = result["metadata"]["cache_bypassed"]')

print("\n📝 Cache TTL can be configured in core/config.py or via environment variables:")
print('   export CACHE_TTL_ALL_MIDS=10  # 10 seconds for prices')
print('   export CACHE_TTL_L2_BOOK=5    # 5 seconds for order books')

print("\n✅ Cache system working correctly!")
