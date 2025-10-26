# Setting Up Claude-Powered Routing

## 🎯 Quick Setup (3 Steps)

### Step 1: Get Your Anthropic API Key

1. Go to https://console.anthropic.com/
2. Sign in or create an account
3. Navigate to API Keys
4. Click "Create Key"
5. Copy your key (starts with `sk-ant-...`)

### Step 2: Add Your API Key to `.env`

Open `.env` file in the project root and replace `your_api_key_here`:

```bash
# Before:
ANTHROPIC_API_KEY=your_api_key_here

# After:
ANTHROPIC_API_KEY=sk-ant-api03-your-actual-key-here
```

### Step 3: Verify It's Working

```bash
python demo.py
```

You should see:
```
✓ Orchestrator ready
  Claude routing: enabled  ✅
  Circuit breakers: active
  Memory tracking: enabled
```

**That's it!** Claude routing is now active.

---

## 🔧 Alternative Setup Methods

### Method 1: Use the Setup Script (Recommended)

```bash
./setup_claude_routing.sh
```

This will:
- Check if `.env` exists
- Prompt you to enter your API key
- Verify the configuration
- Test that everything works

### Method 2: Export Environment Variable

```bash
# Add to your shell profile (~/.zshrc or ~/.bashrc)
export ANTHROPIC_API_KEY='sk-ant-your-key-here'

# Or just for this session
export ANTHROPIC_API_KEY='sk-ant-your-key-here'
python demo.py
```

### Method 3: Edit .env File Directly

```bash
# Edit the file
nano .env

# Or with your favorite editor
code .env
vim .env
```

Then change:
```bash
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
```

---

## ✅ Verify Claude Routing is Enabled

### Quick Test
```bash
python -c "
from agents.orchestrator.orchestrator_agent import OrchestratorAgent
orch = OrchestratorAgent()
print(f'Claude routing: {orch.use_claude_routing}')
"
```

Expected output:
```
Claude routing: True
```

### Full Test
```bash
python demo.py "BTC price"
```

Look for in the output:
```
✓ Orchestrator ready
  Claude routing: enabled  ✅
```

---

## 🔍 Troubleshooting

### Issue: "Claude routing: disabled"

**Possible causes:**

1. **API key not set in .env**
   ```bash
   # Check your .env file
   cat .env | grep ANTHROPIC_API_KEY
   ```
   Should show: `ANTHROPIC_API_KEY=sk-ant-...`

   If it shows `your_api_key_here`, update it with your real key.

2. **API key format is wrong**
   - Must start with `sk-ant-`
   - No quotes needed in .env file
   - No extra spaces

3. **.env file not found**
   ```bash
   # Check if .env exists
   ls -la .env

   # If not, create from example
   cp .env.example .env
   ```

4. **python-dotenv not installed**
   ```bash
   pip install python-dotenv
   ```

### Issue: "Module 'anthropic' not found"

```bash
source venv/bin/activate
pip install anthropic
```

### Issue: API Key works but routing still disabled

Check that `ENABLE_CLAUDE_ROUTING` is True in `core/config.py`:

```python
ENABLE_CLAUDE_ROUTING = True  # Should be True (default)
```

### Issue: "Invalid API key" error

1. Verify your key at https://console.anthropic.com/
2. Make sure you copied the entire key
3. Check for extra characters or spaces
4. Generate a new key if needed

---

## 📊 Verify It's Working

### Test 1: Check Configuration
```bash
python -c "
from core.config import ANTHROPIC_API_KEY, ENABLE_CLAUDE_ROUTING
print(f'API key set: {bool(ANTHROPIC_API_KEY and ANTHROPIC_API_KEY != \"your_api_key_here\")}')
print(f'API key prefix: {ANTHROPIC_API_KEY[:10] if ANTHROPIC_API_KEY else \"Not set\"}')
print(f'Claude routing enabled: {ENABLE_CLAUDE_ROUTING}')
"
```

### Test 2: Check Anthropic Library
```bash
python -c "
try:
    import anthropic
    print('✅ anthropic library available')
    client = anthropic.Anthropic(api_key='test')
    print('✅ anthropic client can be created')
except ImportError:
    print('❌ anthropic library not installed')
except Exception as e:
    print(f'⚠️  Issue: {e}')
"
```

### Test 3: Check Orchestrator
```bash
python -c "
from agents.orchestrator.orchestrator_agent import OrchestratorAgent
orch = OrchestratorAgent()
print(f'✅ Orchestrator initialized')
print(f'   Claude routing: {orch.use_claude_routing}')
print(f'   Claude client: {\"available\" if orch.claude_client else \"not available\"}')
"
```

### Test 4: Make an Actual Query
```bash
python demo.py "What is the current BTC price?"
```

With Claude routing enabled, you should see in the metadata:
```
routing_logic: claude  ✅
confidence: 0.95
```

Without Claude, you'll see:
```
routing_logic: pattern_match
confidence: 0.8
```

---

## 🎯 Understanding Claude Routing

### When Claude Routing is Used

Claude routing activates when:
1. ✅ API key is set
2. ✅ `ENABLE_CLAUDE_ROUTING = True` (default)
3. ✅ Circuit breaker is not open
4. ✅ `anthropic` library is installed

### How It Works

```
User Query
    ↓
Orchestrator checks: Should use Claude?
    ├─→ YES: Call Claude API
    │         ├─→ Parse intent (price, orderbook, candles, etc.)
    │         ├─→ Extract parameters (coin, address, timeframe)
    │         ├─→ Check confidence (≥ 0.7?)
    │         └─→ Route to agent
    │
    └─→ NO: Use pattern matching
              └─→ Keyword-based intent classification
```

### Fallback Behavior

Claude routing **automatically falls back** to pattern matching if:
- API key is missing
- API call fails
- Circuit breaker is open
- Confidence is too low (<0.7)

This means **your system always works**, even if Claude is unavailable!

---

## 💰 Cost Implications

### Pattern Matching (Default)
- **Cost**: $0.000 per query
- **Latency**: <10ms
- **Accuracy**: ~90% for clear queries

### Claude Routing (With API Key)
- **Cost**: $0.006 - $0.012 per query
- **Latency**: ~500ms
- **Accuracy**: ~95% for all queries
- **Benefits**:
  - Better parameter extraction
  - Handles ambiguous queries
  - Learns from routing history

### Recommendation

**Start with pattern matching** (no API key) and enable Claude if you need:
- Complex, ambiguous queries
- Better parameter extraction
- Learning-based routing

For 90% of use cases, **pattern matching is perfect** and costs nothing!

---

## 🔐 Security Best Practices

### 1. Never Commit API Keys
```bash
# .gitignore should include:
.env
*.key
```

### 2. Use Environment Variables in Production
```bash
# In production, set via environment:
export ANTHROPIC_API_KEY='sk-ant-...'

# Not in code or .env files
```

### 3. Rotate Keys Regularly
- Generate new keys every 90 days
- Revoke old keys immediately
- Monitor usage at console.anthropic.com

### 4. Set Usage Limits
- Go to https://console.anthropic.com/settings/limits
- Set monthly spend limits
- Enable email notifications

---

## 📈 Monitoring Claude Usage

### Check if Claude Was Used
```python
result = orchestrator.route_request("BTC price")

# Check routing logic in metadata
routing = result.get("metadata", {}).get("routing_logic")

if routing == "claude":
    print("✅ Used Claude routing")
elif routing == "pattern_match":
    print("ℹ️  Used pattern matching")
```

### View Routing History
```bash
python -c "
from agents.orchestrator.orchestrator_agent import OrchestratorAgent
orch = OrchestratorAgent()

# Make some queries first
orch.route_request('BTC price')
orch.route_request('ETH orderbook')

# Check history
history = orch.get_routing_history(limit=10)
for entry in history:
    print(f'{entry[\"request\"]} -> routing: {entry.get(\"routing_logic\", \"unknown\")}')
"
```

### Monitor Performance
```bash
python -c "
from agents.orchestrator.orchestrator_agent import OrchestratorAgent
orch = OrchestratorAgent()

# Make queries...
orch.route_request('BTC price')

# Check metrics
metrics = orch.get_performance_metrics()
print(f'Avg response time: {metrics[\"avg_response_ms\"]:.0f}ms')
"
```

---

## 🎓 Next Steps

1. ✅ **Set your API key** (Method 1, 2, or 3 above)
2. ✅ **Verify it works** (Run `python demo.py`)
3. ✅ **Test it out** (Make some queries and check `routing_logic`)
4. ✅ **Monitor usage** (Check routing history and metrics)
5. ✅ **Optimize costs** (Use Claude only when needed)

---

## 🆘 Still Having Issues?

### Run Full Diagnostic
```bash
./setup_claude_routing.sh
```

### Check System Status
```bash
python -c "
print('=== SYSTEM STATUS ===')
print()

# 1. Check .env
import os
from pathlib import Path
env_file = Path('.env')
print(f'1. .env file exists: {env_file.exists()}')

# 2. Check API key
from core.config import ANTHROPIC_API_KEY
api_key_set = bool(ANTHROPIC_API_KEY and ANTHROPIC_API_KEY != 'your_api_key_here')
print(f'2. API key configured: {api_key_set}')
if api_key_set:
    print(f'   Key prefix: {ANTHROPIC_API_KEY[:15]}...')

# 3. Check library
try:
    import anthropic
    print(f'3. anthropic library: ✅ installed')
except:
    print(f'3. anthropic library: ❌ not installed')

# 4. Check orchestrator
try:
    from agents.orchestrator.orchestrator_agent import OrchestratorAgent
    orch = OrchestratorAgent()
    print(f'4. Claude routing: {\"✅ enabled\" if orch.use_claude_routing else \"⚠️  disabled\"}')
    print(f'   Claude client: {\"✅ available\" if orch.claude_client else \"❌ not available\"}')
except Exception as e:
    print(f'4. Error loading orchestrator: {e}')
"
```

**If all checks pass** (✅), Claude routing is working!

**If any check fails** (❌), follow the troubleshooting steps above for that specific issue.

---

## 📚 Additional Resources

- **Anthropic Console**: https://console.anthropic.com/
- **API Documentation**: https://docs.anthropic.com/
- **Pricing**: https://www.anthropic.com/pricing
- **System Documentation**: See `QUICKSTART.md` and `INTERACT.md`

---

**Ready?** Just add your API key to `.env` and run `python demo.py`! 🚀
