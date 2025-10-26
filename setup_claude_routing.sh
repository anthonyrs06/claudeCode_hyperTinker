#!/bin/bash
# Setup Claude Routing for Hyperliquid Multi-Agent System
# =======================================================

echo "🚀 Setting up Claude-Powered Routing"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Creating from .env.example..."
    cp .env.example .env
fi

# Check if API key is set
if grep -q "your_api_key_here" .env; then
    echo "📝 Your API key needs to be configured."
    echo ""
    echo "Please do ONE of the following:"
    echo ""
    echo "Option 1: Edit .env file directly"
    echo "  1. Open .env in your editor"
    echo "  2. Replace 'your_api_key_here' with your actual API key"
    echo "  3. Save the file"
    echo ""
    echo "Option 2: Set environment variable"
    echo "  export ANTHROPIC_API_KEY='sk-ant-...'"
    echo ""
    read -p "Do you want to enter your API key now? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Enter your Anthropic API key (sk-ant-...): " api_key
        if [ ! -z "$api_key" ]; then
            # Update .env file
            if [[ "$OSTYPE" == "darwin"* ]]; then
                # macOS
                sed -i '' "s/ANTHROPIC_API_KEY=.*/ANTHROPIC_API_KEY=$api_key/" .env
            else
                # Linux
                sed -i "s/ANTHROPIC_API_KEY=.*/ANTHROPIC_API_KEY=$api_key/" .env
            fi
            echo "✅ API key saved to .env"
        fi
    fi
fi

# Check if anthropic library is installed
echo ""
echo "🔍 Checking dependencies..."
source venv/bin/activate

if ! python -c "import anthropic" 2>/dev/null; then
    echo "⚠️  anthropic library not found. Installing..."
    pip install anthropic
    echo "✅ anthropic library installed"
else
    echo "✅ anthropic library already installed"
fi

# Test the configuration
echo ""
echo "🧪 Testing Claude routing configuration..."
python -c "
from core.config import ANTHROPIC_API_KEY, ENABLE_CLAUDE_ROUTING
import os

# Load from .env
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv('ANTHROPIC_API_KEY', ANTHROPIC_API_KEY)

if api_key and api_key != 'your_api_key_here':
    print('✅ API key is configured')
    print(f'   Key: {api_key[:12]}...')
else:
    print('⚠️  API key not set')

print(f'✅ Claude routing enabled: {ENABLE_CLAUDE_ROUTING}')

try:
    import anthropic
    print('✅ anthropic library available')
except ImportError:
    print('❌ anthropic library not available')
"

echo ""
echo "🎯 Setup complete!"
echo ""
echo "To verify Claude routing is working:"
echo "  python demo.py"
echo ""
echo "You should see: 'Claude routing: enabled'"
echo ""
echo "If you see 'Claude routing: disabled', make sure:"
echo "  1. Your API key is set in .env"
echo "  2. The key starts with 'sk-ant-'"
echo "  3. ENABLE_CLAUDE_ROUTING=True in core/config.py (default)"
