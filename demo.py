"""
Hyperliquid Multi-Agent System - Interactive Demo
==================================================
Demonstrates how to interact with the orchestrator and agents.

Usage:
    python demo.py                    # Interactive mode
    python demo.py "BTC price"        # Single query
    python demo.py --example          # Run example queries
"""

import sys
import json
from agents.orchestrator.orchestrator_agent import OrchestratorAgent


def print_result(result: dict, verbose: bool = False):
    """Pretty print orchestrator result."""
    print("\n" + "="*60)

    if result.get("success"):
        print(f"✓ SUCCESS")
        print(f"Agent: {result.get('agent', 'unknown')}")
        print(f"Action: {result.get('action', 'unknown')}")

        # Print metadata
        if result.get("metadata"):
            meta = result["metadata"]
            print(f"\nMetadata:")
            for key, value in meta.items():
                print(f"  {key}: {value}")

        # Print result data
        print(f"\nResult:")
        if verbose:
            print(json.dumps(result.get("result", {}), indent=2))
        else:
            # Abbreviated output
            res = result.get("result", {})
            if isinstance(res, dict):
                # Show first few keys
                for i, (key, value) in enumerate(res.items()):
                    if i < 3:
                        print(f"  {key}: {value}")
                    else:
                        print(f"  ... ({len(res) - 3} more fields)")
                        break
            elif isinstance(res, list):
                print(f"  {len(res)} items")
                if len(res) > 0:
                    print(f"  First item: {res[0]}")
            else:
                print(f"  {res}")
    else:
        print(f"✗ ERROR")
        print(f"Error: {result.get('error', 'Unknown error')}")
        if result.get("suggestion"):
            print(f"Suggestion: {result['suggestion']}")

    print("="*60)


def run_example_queries(orchestrator: OrchestratorAgent):
    """Run a series of example queries."""
    examples = [
        # Price queries
        ("What is the BTC price?", "Get current Bitcoin price"),
        ("Show me ETH price", "Get Ethereum price"),
        ("Show all prices", "Get all coin prices"),

        # Order book queries
        ("BTC orderbook", "Get Bitcoin order book"),
        ("What's the SOL spread?", "Get Solana bid-ask spread"),

        # Candles queries
        ("BTC 1h candles", "Get Bitcoin 1-hour candles"),
        ("Show me ETH daily candles", "Get Ethereum daily candles"),

        # Meta queries
        ("List all coins", "Get list of available coins"),
        ("Show meta info", "Get market metadata"),

        # Account queries (will error without address)
        ("Show my account", "Account query (needs address)"),
    ]

    print("\n" + "="*60)
    print("RUNNING EXAMPLE QUERIES")
    print("="*60)

    for query, description in examples:
        print(f"\n📝 Query: {query}")
        print(f"   ({description})")

        result = orchestrator.route_request(query, track_memory=True)
        print_result(result, verbose=False)

        input("\nPress Enter to continue...")


def run_interactive_mode(orchestrator: OrchestratorAgent):
    """Run interactive query mode."""
    print("\n" + "="*60)
    print("HYPERLIQUID MULTI-AGENT SYSTEM - INTERACTIVE MODE")
    print("="*60)
    print("\nAvailable query types:")
    print("  • Prices: 'BTC price', 'show all prices'")
    print("  • Order Books: 'BTC orderbook', 'ETH spread'")
    print("  • Candles: 'BTC 1h candles', 'ETH daily candles'")
    print("  • Account: 'my account 0x...' (requires address)")
    print("  • Trades: 'my trades 0x...' (requires address)")
    print("  • Meta: 'list coins', 'meta info'")
    print("\nCommands:")
    print("  • 'stats' - Show routing statistics")
    print("  • 'history' - Show routing history")
    print("  • 'metrics' - Show performance metrics")
    print("  • 'circuits' - Show circuit breaker states")
    print("  • 'quit' or 'exit' - Exit")
    print("="*60)

    while True:
        try:
            query = input("\n🤖 Query: ").strip()

            if not query:
                continue

            if query.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!")
                break

            # Handle special commands
            if query.lower() == 'stats':
                stats = orchestrator.get_routing_stats()
                print(json.dumps(stats, indent=2))
                continue

            if query.lower() == 'history':
                history = orchestrator.get_routing_history(limit=10)
                print(f"\nLast {len(history)} routing decisions:")
                for i, entry in enumerate(history[-10:]):
                    print(f"\n{i+1}. {entry['request']}")
                    print(f"   Intent: {entry['intent']}, Agent: {entry['routed_to']}")
                    print(f"   Time: {entry['response_time_ms']:.0f}ms, Success: {entry['success']}")
                continue

            if query.lower() == 'metrics':
                metrics = orchestrator.get_performance_metrics()
                print(json.dumps(metrics, indent=2))
                continue

            if query.lower() == 'circuits':
                states = orchestrator.circuit_breakers.get_all_states()
                if not states:
                    print("\n  No circuit breakers active yet")
                else:
                    print("\nCircuit Breaker States:")
                    for agent, state in states.items():
                        print(f"\n  {agent}:")
                        print(f"    State: {state['state']}")
                        print(f"    Failures: {state['failure_count']}")
                        print(f"    Successes: {state['success_count']}")
                continue

            # Route the query
            result = orchestrator.route_request(query, track_memory=True)
            print_result(result, verbose=False)

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")


def main():
    """Main entry point."""
    # Initialize orchestrator
    print("🚀 Initializing Hyperliquid Multi-Agent System...")
    orchestrator = OrchestratorAgent()
    print("✓ Orchestrator ready")
    print(f"  Claude routing: {'enabled' if orchestrator.use_claude_routing else 'disabled'}")
    print(f"  Circuit breakers: active")
    print(f"  Memory tracking: enabled")

    # Check command line arguments
    if len(sys.argv) > 1:
        arg = sys.argv[1]

        if arg == "--example":
            run_example_queries(orchestrator)
        else:
            # Single query mode
            query = " ".join(sys.argv[1:])
            print(f"\n📝 Query: {query}")
            result = orchestrator.route_request(query, track_memory=True)
            print_result(result, verbose=True)
    else:
        # Interactive mode
        run_interactive_mode(orchestrator)


if __name__ == "__main__":
    main()
