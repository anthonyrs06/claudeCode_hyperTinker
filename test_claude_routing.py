"""
Test Claude Routing Metadata
============================
Verify that metadata shows routing_logic='claude' when Claude is used.
"""

from agents.orchestrator.orchestrator_agent import OrchestratorAgent
import json

print("=" * 60)
print("TESTING CLAUDE ROUTING METADATA")
print("=" * 60)

# Initialize orchestrator
orchestrator = OrchestratorAgent()

print(f"\n📊 Configuration:")
print(f"  Claude routing enabled: {orchestrator.use_claude_routing}")
print(f"  Claude client initialized: {orchestrator.claude_client is not None}")

# Test 1: Simple price query
print("\n" + "=" * 60)
print("TEST 1: Price Query")
print("=" * 60)
result = orchestrator.route_request("BTC price", track_memory=False)

print(f"\n✅ Success: {result.get('success')}")
print(f"   Agent: {result.get('agent')}")
print(f"   Action: {result.get('action')}")

metadata = result.get("metadata", {})
print(f"\n📋 Metadata:")
print(f"   routing_logic: {metadata.get('routing_logic')}")
print(f"   confidence: {metadata.get('confidence')}")
print(f"   cache_bypassed: {metadata.get('cache_bypassed')}")

# Show price if available
if result.get("success") and "result" in result:
    res = result["result"]
    if "price" in res:
        print(f"\n💰 BTC Price: ${float(res['price']):,.2f}")

# Test 2: List coins query
print("\n" + "=" * 60)
print("TEST 2: Meta Query (list coins)")
print("=" * 60)
result2 = orchestrator.route_request("list coins", track_memory=False)

print(f"\n✅ Success: {result2.get('success')}")
print(f"   Agent: {result2.get('agent')}")
print(f"   Action: {result2.get('action')}")

metadata2 = result2.get("metadata", {})
print(f"\n📋 Metadata:")
print(f"   routing_logic: {metadata2.get('routing_logic')}")
print(f"   confidence: {metadata2.get('confidence')}")

# Show number of coins if available
if result2.get("success") and "result" in result2:
    print(f"   num_coins: {len(result2['result'])}")

print("\n" + "=" * 60)
print("✓ TESTS COMPLETE")
print("=" * 60)

# Summary
print("\n📊 Summary:")
if metadata.get('routing_logic') == 'claude':
    print("   ✅ Claude routing is working! Metadata shows 'claude'")
elif metadata.get('routing_logic') == 'pattern_match':
    print("   ℹ️  Pattern matching used (Claude may have failed or not been tried)")
elif metadata.get('routing_logic') == 'pattern_match_fallback':
    print("   ⚠️  Claude had low confidence, fell back to pattern matching")
else:
    print(f"   ❓ Unknown routing_logic: {metadata.get('routing_logic')}")
