"""
Basic Usage Examples
====================
Simple examples of using the Hyperliquid Multi-Agent System.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.orchestrator.orchestrator_agent import OrchestratorAgent


def example_price_queries():
    """Example: Price queries"""
    print("\n" + "="*60)
    print("EXAMPLE 1: Price Queries")
    print("="*60)

    orchestrator = OrchestratorAgent()

    # Get specific coin price
    print("\n1. Get BTC price:")
    result = orchestrator.route_request("What is BTC price?")
    if result["success"]:
        price = result["result"]["price"]
        print(f"   BTC: ${price:,.2f}")

    # Get all prices
    print("\n2. Get all prices:")
    result = orchestrator.route_request("Show all prices")
    if result["success"]:
        prices = result["result"]
        print(f"   Found {len(prices)} coins")
        for coin, price in list(prices.items())[:3]:
            try:
                price_val = float(price) if isinstance(price, str) else price
                print(f"   {coin}: ${price_val:,.2f}")
            except (ValueError, TypeError):
                print(f"   {coin}: {price}")
        print(f"   ... and {len(prices) - 3} more")


def example_orderbook_queries():
    """Example: Order book queries"""
    print("\n" + "="*60)
    print("EXAMPLE 2: Order Book Queries")
    print("="*60)

    orchestrator = OrchestratorAgent()

    # Get order book
    print("\n1. Get BTC order book:")
    result = orchestrator.route_request("BTC orderbook")
    if result["success"]:
        book = result["result"]
        bids = book["levels"][0][:3]
        asks = book["levels"][1][:3]

        print("\n   Top 3 Bids:")
        for level in bids:
            print(f"     {level['px']} @ {level['sz']}")

        print("\n   Top 3 Asks:")
        for level in asks:
            print(f"     {level['px']} @ {level['sz']}")

    # Get spread
    print("\n2. Get BTC spread:")
    result = orchestrator.route_request("BTC spread")
    if result["success"]:
        spread = result["result"]
        print(f"   Bid: ${spread.get('bid', 0):,.2f}")
        print(f"   Ask: ${spread.get('ask', 0):,.2f}")
        print(f"   Spread: ${spread.get('spread', 0):,.2f} ({spread.get('spread_pct', 0):.3f}%)")


def example_candles_queries():
    """Example: Historical candles"""
    print("\n" + "="*60)
    print("EXAMPLE 3: Historical Candles")
    print("="*60)

    orchestrator = OrchestratorAgent()

    # Get candles
    print("\n1. Get BTC 1h candles:")
    result = orchestrator.route_request("BTC 1h candles")
    if result["success"]:
        candles = result["result"]["candles"]
        stats = result["result"]["stats"]

        print(f"   Received {len(candles)} candles")
        if stats.get('high'):
            print(f"   High: ${stats['high']:,.2f}")
        if stats.get('low'):
            print(f"   Low: ${stats['low']:,.2f}")
        if stats.get('avg'):
            print(f"   Avg: ${stats['avg']:,.2f}")
        if stats.get('total_volume'):
            print(f"   Total volume: {stats['total_volume']:,.0f}")

        # Show last candle
        if candles:
            last = candles[-1]
            print(f"\n   Latest candle:")
            print(f"     Open: ${float(last['o']):,.2f}")
            print(f"     High: ${float(last['h']):,.2f}")
            print(f"     Low: ${float(last['l']):,.2f}")
            print(f"     Close: ${float(last['c']):,.2f}")
            print(f"     Volume: {float(last['v']):,.0f}")


def example_meta_queries():
    """Example: Metadata queries"""
    print("\n" + "="*60)
    print("EXAMPLE 4: Metadata Queries")
    print("="*60)

    orchestrator = OrchestratorAgent()

    # List coins
    print("\n1. List all coins:")
    result = orchestrator.route_request("list coins")
    if result["success"]:
        coins = result["result"]
        print(f"   Found {len(coins)} coins:")
        print(f"   {', '.join(coins[:10])}")
        print(f"   ... and {len(coins) - 10} more")


def example_monitoring():
    """Example: Monitoring and metrics"""
    print("\n" + "="*60)
    print("EXAMPLE 5: Monitoring & Metrics")
    print("="*60)

    orchestrator = OrchestratorAgent()

    # Make some requests
    print("\n1. Making several requests...")
    queries = [
        "BTC price",
        "ETH price",
        "SOL price",
        "BTC orderbook",
        "list coins"
    ]

    for query in queries:
        orchestrator.route_request(query, track_memory=True)
        print(f"   ✓ {query}")

    # View routing history
    print("\n2. Routing History:")
    history = orchestrator.get_routing_history(limit=5)
    for i, entry in enumerate(history[-5:], 1):
        print(f"   {i}. {entry['request']}")
        print(f"      → {entry['routed_to']} ({entry['response_time_ms']:.0f}ms)")

    # View performance metrics
    print("\n3. Performance Metrics:")
    metrics = orchestrator.get_performance_metrics()
    print(f"   Total requests: {metrics['total_requests']}")
    print(f"   Avg response: {metrics['avg_response_ms']:.0f}ms")

    print("\n   Per-agent metrics:")
    for agent, stats in metrics['agents'].items():
        if stats['total_requests'] > 0:
            print(f"     {agent}:")
            print(f"       Requests: {stats['total_requests']}")
            print(f"       Avg time: {stats['avg_response_ms']:.0f}ms")
            print(f"       Uptime: {stats['uptime']*100:.1f}%")

    # Analyze patterns
    print("\n4. Routing Pattern Analysis:")
    analysis = orchestrator.analyze_routing_patterns()
    print(f"   Most common intent: {analysis['most_common_intent']}")
    print(f"   Agent utilization:")
    for agent, util in analysis['agent_utilization'].items():
        print(f"     {agent}: {util*100:.1f}%")


def example_error_handling():
    """Example: Error handling"""
    print("\n" + "="*60)
    print("EXAMPLE 6: Error Handling")
    print("="*60)

    orchestrator = OrchestratorAgent()

    # Missing address
    print("\n1. Query without required address:")
    result = orchestrator.route_request("Show my account")
    if not result["success"]:
        print(f"   ✗ Error: {result['error']}")
        print(f"   Suggestion: {result['suggestion']}")

    # Unknown intent
    print("\n2. Unknown query type:")
    result = orchestrator.route_request("What's the weather?")
    if not result["success"]:
        print(f"   ✗ Error: {result['error']}")
        if result.get("suggestion"):
            print(f"   Suggestion: {result['suggestion']}")


def main():
    """Run all examples"""
    print("\n" + "="*60)
    print("HYPERLIQUID MULTI-AGENT SYSTEM - BASIC USAGE EXAMPLES")
    print("="*60)

    try:
        example_price_queries()
        example_orderbook_queries()
        example_candles_queries()
        example_meta_queries()
        example_monitoring()
        example_error_handling()

        print("\n" + "="*60)
        print("✓ All examples completed!")
        print("="*60)
        print("\nNext steps:")
        print("  • Try the interactive demo: python demo.py")
        print("  • Read the quick start guide: QUICKSTART.md")
        print("  • Build your own queries using the orchestrator")

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
