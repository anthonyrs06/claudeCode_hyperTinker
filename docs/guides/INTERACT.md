# How to Interact with Your Multi-Agent System

## 🎯 Three Ways to Use the System

### 1. Interactive Demo (Recommended for Exploration)
```bash
python demo.py
```

This launches an interactive shell where you can:
- Type natural language queries
- View routing statistics with `stats`
- Check routing history with `history`
- Monitor performance with `metrics`
- View circuit breaker states with `circuits`
- Type `quit` to exit

**Example Session:**
```
🤖 Query: BTC price
✓ SUCCESS
Agent: price_book
Result: $113,801.50

🤖 Query: history
Last 10 routing decisions:
1. BTC price
   Intent: price, Agent: price_book
   Time: 81ms, Success: True

🤖 Query: quit
👋 Goodbye!
```

### 2. Single Query Mode
```bash
# Just ask a question
python demo.py "What is BTC price?"

# Or any other query
python demo.py "Show me ETH 1h candles"
python demo.py "list all coins"
```

### 3. Programmatic Usage (For Building Applications)
```python
from agents.orchestrator.orchestrator_agent import OrchestratorAgent

# Initialize once
orchestrator = OrchestratorAgent()

# Make queries
result = orchestrator.route_request("BTC price")
if result["success"]:
    print(f"Price: {result['result']['price']}")
```

## 📋 Quick Reference: What Can You Ask?

### Price Queries 💰
```python
"What is BTC price?"
"Show me ETH price"
"Get SOL price"
"Show all prices"
"List all coin prices"
```

### Order Book Queries 📊
```python
"BTC orderbook"
"Show ETH order book"
"BTC spread"
"What's the SOL spread?"
```

### Historical Candles 📈
```python
"BTC 1h candles"
"ETH 4h candles"
"SOL daily candles"
"Show me BTC 15m candles"
```
**Supported intervals:** 1m, 5m, 15m, 1h, 4h, 1d

### Account Queries 👤 (Requires Address)
```python
"Show my account 0x1234..."
"Account summary for 0x1234..."
"Show positions for 0x1234..."
"Risk metrics for 0x1234..."
```

### Trade Queries 💱 (Requires Address)
```python
"Show my fills 0x1234..."
"Trade history for 0x1234..."
"Show open orders 0x1234..."
```

### Metadata Queries ℹ️
```python
"list coins"
"show all available coins"
"meta info"
"show metadata"
```

## 🔧 Configuration Options

### Enable Claude-Powered Routing

1. **Set your API key:**
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

2. **Verify it's enabled:**
```python
orchestrator = OrchestratorAgent()
print(f"Claude routing: {orchestrator.use_claude_routing}")
# Output: Claude routing: True
```

**When to use Claude routing:**
- Complex, ambiguous queries
- Need parameter extraction
- Want intelligent intent classification

**When to use pattern matching (default):**
- Simple, clear queries (90%+ of use cases)
- Zero cost, <10ms latency
- No API key required

### Disable Memory Tracking
```python
# Don't track this query in routing history
result = orchestrator.route_request("BTC price", track_memory=False)
```

### Provide Context
```python
context = {
    "coin": "BTC",
    "user_address": "0x...",
    "timeframe": "1h"
}
result = orchestrator.route_request("Show me the data", context=context)
```

## 📊 Monitoring Your System

### View Routing History
```python
history = orchestrator.get_routing_history(limit=10)
for entry in history:
    print(f"{entry['request']} → {entry['routed_to']} ({entry['response_time_ms']:.0f}ms)")
```

### Check Performance Metrics
```python
metrics = orchestrator.get_performance_metrics()
print(f"Total requests: {metrics['total_requests']}")
print(f"Avg response: {metrics['avg_response_ms']:.0f}ms")

for agent, stats in metrics['agents'].items():
    print(f"{agent}: {stats['uptime']*100:.1f}% uptime")
```

### Analyze Routing Patterns
```python
analysis = orchestrator.analyze_routing_patterns()
print(f"Most common intent: {analysis['most_common_intent']}")
print(f"Agent utilization: {analysis['agent_utilization']}")
```

### Monitor Circuit Breakers
```python
states = orchestrator.circuit_breakers.get_all_states()
for agent, state in states.items():
    print(f"{agent}: {state['state']} (failures: {state['failure_count']})")
```

## 🚀 Run the Examples

### Basic Usage Examples
```bash
python examples/basic_usage.py
```

Demonstrates:
- ✅ Price queries (specific coin & all coins)
- ✅ Order book queries (L2 book & spread)
- ✅ Historical candles with stats
- ✅ Metadata queries
- ✅ Monitoring & metrics
- ✅ Error handling

### Example Queries Mode
```bash
python demo.py --example
```

Runs 10+ example queries interactively.

## 💡 Common Patterns

### Building a Price Monitor
```python
orchestrator = OrchestratorAgent()

coins = ["BTC", "ETH", "SOL", "AVAX"]
for coin in coins:
    result = orchestrator.route_request(f"{coin} price")
    if result["success"]:
        price = result["result"]["price"]
        print(f"{coin}: ${price:,.2f}")
```

### Building a Portfolio Tracker
```python
address = "0x1234567890abcdef1234567890abcdef12345678"

# Get account summary
result = orchestrator.route_request(f"Account summary for {address}")
summary = result["result"]

# Get positions
result = orchestrator.route_request(f"Show positions for {address}")
positions = result["result"]

# Get risk metrics
result = orchestrator.route_request(f"Risk metrics for {address}")
risk = result["result"]
```

### Building a Market Analysis Tool
```python
coin = "BTC"

# Get current price
price_result = orchestrator.route_request(f"{coin} price")
price = price_result["result"]["price"]

# Get order book depth
book_result = orchestrator.route_request(f"{coin} orderbook")
book = book_result["result"]

# Get historical data
candles_result = orchestrator.route_request(f"{coin} 1h candles")
candles = candles_result["result"]["candles"]
stats = candles_result["result"]["stats"]

print(f"{coin} Analysis:")
print(f"  Current: ${price:,.2f}")
print(f"  24h High: ${stats['high']:,.2f}")
print(f"  24h Low: ${stats['low']:,.2f}")
print(f"  Volume: {stats['total_volume']:,.0f}")
```

## 🔒 Security Best Practices

1. **API Keys**: Store in environment variables, never commit to code
```bash
# .env file
ANTHROPIC_API_KEY=sk-ant-...
```

2. **Addresses**: Validate format before queries
```python
import re
def is_valid_address(addr):
    return bool(re.match(r'^0x[a-fA-F0-9]{40}$', addr))
```

3. **Rate Limiting**: Use cache to avoid hitting API limits
```python
# Cache is automatically used by default
result = orchestrator.route_request("BTC price")  # Cache: 30s
```

## 🐛 Troubleshooting

### "Circuit breaker OPEN" Error
**Cause:** Agent experiencing repeated failures
**Solution:** Wait 60 seconds or reset manually
```python
orchestrator.circuit_breakers.reset_all()
```

### Slow Response Times
**Cause:** Cache miss or network latency
**Solution:** Check if subsequent requests are faster (cache hit)
```python
# First call: ~500ms (API call)
result = orchestrator.route_request("BTC price")

# Second call: <10ms (cached)
result = orchestrator.route_request("BTC price")
```

### "Unable to determine intent" Error
**Cause:** Query doesn't match known patterns
**Solution:** Use more specific keywords
```python
# ❌ "What's happening?"
# ✅ "What is BTC price?"
```

Or enable Claude routing for better intent classification.

## 📈 Performance Characteristics

| Component | Latency | Cost | Cache Duration |
|-----------|---------|------|----------------|
| Pattern Matching | <10ms | $0.000 | N/A |
| Claude Routing | ~500ms | $0.006-$0.012 | N/A |
| Price Data | ~100ms | $0.000 | 30s |
| Order Book | ~100ms | $0.000 | 30s |
| Candles | ~300ms | $0.000 | 5m |
| Account Data | ~200ms | $0.000 | 60s |

**Overall System:** 98.7% cost reduction vs baseline Claude-only

## 🎓 Learning Resources

1. **Quick Start Guide**: `QUICKSTART.md`
2. **Architecture Documentation**: `ARCHITECTURE.md`
3. **Test Files**: See `agents/*/tests/` for usage examples
4. **Memory Files**: Check `/memories/orchestrator/` for routing history

## 🤝 Getting Help

- **View stats**: Type `stats` in interactive mode
- **Check history**: Type `history` in interactive mode
- **View metrics**: Type `metrics` in interactive mode
- **Check circuits**: Type `circuits` in interactive mode

## 🎯 Next Steps

1. ✅ **Run the demo**: `python demo.py`
2. ✅ **Try examples**: `python examples/basic_usage.py`
3. ✅ **Read the quick start**: `QUICKSTART.md`
4. ✅ **Enable Claude** (optional): Set `ANTHROPIC_API_KEY`
5. ✅ **Build your application**: Use `OrchestratorAgent()` in your code

---

**Ready to start?** Run `python demo.py` and start asking questions! 🚀
