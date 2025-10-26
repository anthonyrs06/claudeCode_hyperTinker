# Enable Claude-Powered Routing

## ⚡ Quick Start (30 seconds)

### Method 1: Interactive Setup (Easiest)
```bash
python configure_claude.py
```

Follow the prompts to enter your API key. Done! ✅

### Method 2: Manual Setup
```bash
# 1. Edit .env file
nano .env

# 2. Replace this line:
ANTHROPIC_API_KEY=your_api_key_here

# 3. With your actual key:
ANTHROPIC_API_KEY=sk-ant-api03-...your-actual-key...

# 4. Save and test:
python demo.py
```

You should see:
```
✓ Orchestrator ready
  Claude routing: enabled  ✅
```

## 🔑 Get Your API Key

1. Visit: https://console.anthropic.com/
2. Sign in / Create account
3. Go to: **API Keys**
4. Click: **Create Key**
5. Copy your key (starts with `sk-ant-`)

## ✅ Verify It's Working

```bash
# Quick test
python demo.py

# Should show:
# Claude routing: enabled ✅
```

## 💰 Cost Information

| Routing Type | Cost per Query | Speed | When to Use |
|--------------|---------------|-------|-------------|
| **Pattern Match** (no key) | $0.000 | <10ms | 90% of queries - default |
| **Claude** (with key) | $0.006-$0.012 | ~500ms | Complex/ambiguous queries |

**You choose:** Pattern matching works great and costs nothing! Enable Claude when you need smarter routing.

## 🆘 Having Issues?

### Claude routing shows "disabled"?

**Check your .env file:**
```bash
cat .env | grep ANTHROPIC_API_KEY
```

Should show your actual key, not `your_api_key_here`.

**Fix it:**
```bash
python configure_claude.py
```

### Need more help?

Read the detailed guide:
```bash
cat CLAUDE_SETUP.md
```

## 📊 What Changes?

### Without API Key (Default)
- Uses pattern matching
- 0 tokens, 0 cost
- Fast (<10ms)
- Works great for clear queries

### With API Key (Optional)
- Uses Claude for intent classification
- Better parameter extraction
- Handles ambiguous queries
- Learns from routing history
- ~$0.01 per query

**Both modes work perfectly!** Choose based on your needs.

## 🎯 Already Configured?

Your API key is saved in `.env` and will be used automatically.

**Test it:**
```bash
python demo.py "What is BTC price?"
```

Look for `routing_logic: claude` in the output.

---

**That's it!** Claude routing is now enabled by default when you have an API key. 🚀

For detailed documentation, see: `CLAUDE_SETUP.md`
