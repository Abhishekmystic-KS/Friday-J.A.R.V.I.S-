#!/usr/bin/env python3
"""
Test script to demonstrate chat widget functionality.
Run this and click the 💬 button to see the chat panel expand.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from jarvis.ui.robo_popup import main

if __name__ == "__main__":
    print("=" * 60)
    print("ROBO POPUP + CHAT WIDGET DEMO")
    print("=" * 60)
    print("\n📌 What to see:")
    print("  1. Small window appears on right side with robo animation")
    print("  2. Below animation: 💬 button (bright green)")
    print("  3. Click 💬 → Chat panel expands below")
    print("  4. Type queries and press Enter or click Send")
    print("  5. Without RAG setup: See warning message")
    print("  6. Click 💬 again → Chat collapses")
    print("\n🚀 Starting...\n")
    
    main()
