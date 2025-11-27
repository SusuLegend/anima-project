

#!/usr/bin/env python3
"""
AI Virtual Assistant Launcher

This is the main entry point for the application.
It opens the settings manager where users can configure and launch the assistant.
"""

import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.ui.settings_manager import main as settings_main

if __name__ == "__main__":
    print("=" * 60)
    print("AI Virtual Assistant - Launcher")
    print("=" * 60)
    print("\nOpening Settings Manager...")
    print("Configure your assistant and click START to launch.\n")
    
    # Launch settings manager
    settings_main()