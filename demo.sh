#!/bin/bash
# Interactive Demo Script for Hyperliquid Fetch Skill
# Phase 1 Testing

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

SKILL_SCRIPT="./venv/bin/python3 skills/hyperliquid-fetch-and-cache/scripts/fetch_hyperliquid.py"

echo "=========================================="
echo "Hyperliquid Fetch Skill - Interactive Demo"
echo "=========================================="
echo ""

# Helper function to call the skill
call_skill() {
    echo "$1" | $SKILL_SCRIPT
}

# Main menu
while true; do
    echo ""
    echo "Choose an option:"
    echo ""
    echo "  1) Get BTC/ETH/SOL prices"
    echo "  2) Get all mid prices (464 coins)"
    echo "  3) Get BTC order book (top 10 levels)"
    echo "  4) Get ETH recent trades"
    echo "  5) Test cache (2 calls - API then cache)"
    echo "  6) View cache files"
    echo "  7) View rate limit state"
    echo "  8) Clear cache"
    echo "  9) Run unit tests"
    echo "  0) Exit"
    echo ""
    read -p "Enter choice [0-9]: " choice

    case $choice in
        1)
            echo ""
            echo "=== Fetching BTC/ETH/SOL prices ==="
            call_skill '{"endpoint": "allMids", "params": {}}' | \
                python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data['success']:
        print(f\"Source: {data['metadata']['source']}\")
        print(f\"BTC: \\\${data['data']['BTC']}\")
        print(f\"ETH: \\\${data['data']['ETH']}\")
        print(f\"SOL: \\\${data['data']['SOL']}\")
    else:
        print(f\"Error: {data['error']}\")
except Exception as e:
    print(f\"Error parsing response: {e}\")
"
            ;;
        2)
            echo ""
            echo "=== All Mid Prices (Top 20 by price) ==="
            call_skill '{"endpoint": "allMids", "params": {}}' | \
                python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data['success']:
        print(f\"Source: {data['metadata']['source']}\")
        print(f\"Total coins: {len(data['data'])}\")
        print(\"\\nTop 20 by price:\")
        prices = [(k, float(v)) for k, v in data['data'].items() if not k.startswith('@')]
        prices.sort(key=lambda x: x[1], reverse=True)
        for i, (coin, price) in enumerate(prices[:20], 1):
            print(f\"{i:2}. {coin:8} \\\${price:>12,.2f}\")
    else:
        print(f\"Error: {data['error']}\")
except Exception as e:
    print(f\"Error: {e}\")
"
            ;;
        3)
            echo ""
            echo "=== BTC Order Book (Top 10 Bids/Asks) ==="
            call_skill '{"endpoint": "l2Book", "params": {"coin": "BTC"}}' | \
                python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data['success']:
        print(f\"Source: {data['metadata']['source']}\")
        levels = data['data']['levels']
        bids = levels[0][:10]
        asks = levels[1][:10]

        print(\"\\n   BIDS (Buy Orders)          |          ASKS (Sell Orders)\")
        print(\"   Price         Size    #     |     Price         Size    #\")
        print(\"   \" + \"-\"*60)

        for i in range(10):
            bid_str = f\"{bids[i]['px']:>10} {bids[i]['sz']:>8} {bids[i]['n']:>3}\" if i < len(bids) else \" \"*25
            ask_str = f\"{asks[i]['px']:>10} {asks[i]['sz']:>8} {asks[i]['n']:>3}\" if i < len(asks) else \" \"*25
            print(f\"   {bid_str}   |   {ask_str}\")
    else:
        print(f\"Error: {data['error']}\")
except Exception as e:
    print(f\"Error: {e}\")
"
            ;;
        4)
            echo ""
            echo "=== ETH Recent Trades (Last 10) ==="
            call_skill '{"endpoint": "trades", "params": {"coin": "ETH"}}' | \
                python3 -c "
import sys, json
from datetime import datetime
try:
    data = json.load(sys.stdin)
    if data['success']:
        print(f\"Source: {data['metadata']['source']}\")
        trades = data['data'][:10]
        print(f\"\\nLast {len(trades)} trades:\")
        print(\"\\n   Time                    Side    Price       Size\")
        print(\"   \" + \"-\"*55)
        for trade in trades:
            ts = datetime.fromtimestamp(trade['time']/1000).strftime('%Y-%m-%d %H:%M:%S')
            side = 'BUY ' if trade['side'] == 'B' else 'SELL'
            print(f\"   {ts}   {side}   {trade['px']:>10}   {trade['sz']:>8}\")
    else:
        print(f\"Error: {data['error']}\")
except Exception as e:
    print(f\"Error: {e}\")
"
            ;;
        5)
            echo ""
            echo "=== Testing Cache Behavior ==="
            echo ""
            echo "Call 1 (forcing refresh - should hit API):"
            START=$(python3 -c "import time; print(time.time())")
            call_skill '{"endpoint": "allMids", "params": {}, "cache_config": {"force_refresh": true}}' | \
                python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f\"  Source: {data['metadata']['source']}\")
print(f\"  Latency: {data['metadata'].get('api_latency_ms', 'N/A')}ms\")
print(f\"  Coins: {len(data['data'])}\")
"
            END=$(python3 -c "import time; print(time.time())")
            ELAPSED=$(python3 -c "print(f'{($END - $START)*1000:.0f}')")
            echo "  Total time: ${ELAPSED}ms"

            echo ""
            sleep 1

            echo "Call 2 (should hit cache):"
            START=$(python3 -c "import time; print(time.time())")
            call_skill '{"endpoint": "allMids", "params": {}}' | \
                python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f\"  Source: {data['metadata']['source']}\")
print(f\"  Cached until: {data['metadata'].get('cached_until', 'N/A')}\")
"
            END=$(python3 -c "import time; print(time.time())")
            ELAPSED=$(python3 -c "print(f'{($END - $START)*1000:.0f}')")
            echo "  Total time: ${ELAPSED}ms"

            echo ""
            echo "Notice: Cache is much faster! (~10-50ms vs ~500-1000ms)"
            ;;
        6)
            echo ""
            echo "=== Cache Files ==="
            if [ -d "memories/market_data" ] && [ "$(ls -A memories/market_data)" ]; then
                ls -lh memories/market_data/
                echo ""
                echo "Total cache files: $(ls memories/market_data/*.json 2>/dev/null | wc -l | xargs)"
            else
                echo "No cache files found."
            fi
            ;;
        7)
            echo ""
            echo "=== Rate Limit State ==="
            if [ -f "memories/shared/rate_limit_state.json" ]; then
                cat memories/shared/rate_limit_state.json | python3 -m json.tool
            else
                echo "No rate limit state file found."
            fi
            ;;
        8)
            echo ""
            read -p "Are you sure you want to clear the cache? (y/n): " confirm
            if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
                rm -f memories/market_data/*.json
                echo "Cache cleared!"
            else
                echo "Cancelled."
            fi
            ;;
        9)
            echo ""
            echo "=== Running Unit Tests ==="
            ./venv/bin/python -m pytest skills/hyperliquid-fetch-and-cache/tests/test_fetch_hyperliquid.py -v -m "not integration" --tb=short
            ;;
        0)
            echo ""
            echo "Exiting demo. Thanks for testing!"
            exit 0
            ;;
        *)
            echo ""
            echo "Invalid choice. Please enter 0-9."
            ;;
    esac

    echo ""
    read -p "Press Enter to continue..."
done
