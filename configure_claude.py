#!/usr/bin/env python3
"""
Interactive Claude Configuration Script
========================================
Helps you set up Claude-powered routing with your Anthropic API key.
"""

import os
import sys
from pathlib import Path


def main():
    print("="*60)
    print("CLAUDE-POWERED ROUTING CONFIGURATION")
    print("="*60)
    print()

    # Check if .env exists
    env_file = Path(".env")
    if not env_file.exists():
        print("⚠️  No .env file found.")
        create = input("Create .env file from .env.example? (y/n): ").strip().lower()
        if create == 'y':
            if Path(".env.example").exists():
                import shutil
                shutil.copy(".env.example", ".env")
                print("✅ Created .env file")
            else:
                print("❌ .env.example not found")
                return
        else:
            print("❌ Cannot proceed without .env file")
            return

    print()
    print("📝 Current configuration:")
    print()

    # Check current status
    from core.config import ANTHROPIC_API_KEY, ENABLE_CLAUDE_ROUTING

    api_key_set = bool(ANTHROPIC_API_KEY and ANTHROPIC_API_KEY != "your_api_key_here")

    print(f"  API Key: {'✅ Configured' if api_key_set else '❌ Not set'}")
    if api_key_set:
        print(f"  Key prefix: {ANTHROPIC_API_KEY[:15]}...")
    print(f"  Claude routing enabled: {'✅' if ENABLE_CLAUDE_ROUTING else '❌'}")

    # Check anthropic library
    try:
        import anthropic
        print(f"  anthropic library: ✅ Installed")
    except ImportError:
        print(f"  anthropic library: ❌ Not installed")
        install = input("\nInstall anthropic library? (y/n): ").strip().lower()
        if install == 'y':
            os.system("pip install anthropic")
            print("✅ Installed anthropic")

    print()

    if api_key_set:
        print("✅ Your API key is already configured!")
        print()
        update = input("Do you want to update it? (y/n): ").strip().lower()
        if update != 'y':
            test_system()
            return

    # Prompt for API key
    print()
    print("To get your Anthropic API key:")
    print("  1. Go to https://console.anthropic.com/")
    print("  2. Sign in or create an account")
    print("  3. Navigate to API Keys")
    print("  4. Create a new key")
    print("  5. Copy the key (starts with 'sk-ant-')")
    print()

    api_key = input("Enter your Anthropic API key (or 'skip' to skip): ").strip()

    if api_key.lower() == 'skip':
        print("\n⚠️  Skipped API key configuration")
        print("Claude routing will use pattern matching (no Claude API calls)")
        return

    if not api_key.startswith('sk-ant-'):
        print("\n⚠️  Warning: API key should start with 'sk-ant-'")
        cont = input("Continue anyway? (y/n): ").strip().lower()
        if cont != 'y':
            return

    # Update .env file
    print("\n📝 Updating .env file...")

    with open(".env", "r") as f:
        lines = f.readlines()

    with open(".env", "w") as f:
        for line in lines:
            if line.startswith("ANTHROPIC_API_KEY="):
                f.write(f"ANTHROPIC_API_KEY={api_key}\n")
            else:
                f.write(line)

    print("✅ API key saved to .env")

    # Test the configuration
    test_system()


def test_system():
    """Test that Claude routing is working."""
    print()
    print("="*60)
    print("TESTING CONFIGURATION")
    print("="*60)
    print()

    try:
        # Reload config to pick up new API key
        import importlib
        import core.config
        importlib.reload(core.config)

        from core.config import ANTHROPIC_API_KEY, ENABLE_CLAUDE_ROUTING

        api_key_set = bool(ANTHROPIC_API_KEY and ANTHROPIC_API_KEY != "your_api_key_here")

        print("Configuration check:")
        print(f"  ✅ API key: {'Set' if api_key_set else 'Not set'}")
        print(f"  ✅ Claude routing: {'Enabled' if ENABLE_CLAUDE_ROUTING else 'Disabled'}")

        # Try to create orchestrator
        print()
        print("Initializing orchestrator...")

        from agents.orchestrator.orchestrator_agent import OrchestratorAgent
        orchestrator = OrchestratorAgent()

        print(f"  ✅ Orchestrator initialized")
        print(f"  {'✅' if orchestrator.use_claude_routing else '❌'} Claude routing: {'enabled' if orchestrator.use_claude_routing else 'disabled'}")
        print(f"  {'✅' if orchestrator.claude_client else '❌'} Claude client: {'available' if orchestrator.claude_client else 'not available'}")

        print()
        print("="*60)
        if orchestrator.use_claude_routing:
            print("✅ SUCCESS! Claude-powered routing is enabled!")
        else:
            print("⚠️  Claude routing is disabled")
            print("   System will use pattern matching (no Claude API calls)")
        print("="*60)

        print()
        print("Next steps:")
        print("  • Test it: python demo.py")
        print("  • Read guide: CLAUDE_SETUP.md")
        print("  • Documentation: QUICKSTART.md")

    except Exception as e:
        print(f"❌ Error: {e}")
        print()
        print("Troubleshooting:")
        print("  1. Make sure your API key is correct")
        print("  2. Check that 'anthropic' library is installed")
        print("  3. Read CLAUDE_SETUP.md for detailed help")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Configuration cancelled")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
