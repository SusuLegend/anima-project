#!/usr/bin/env python3
"""
AI Virtual Assistant Launcher

This is the main entry point for the application.
It opens the settings manager where users can configure and launch the assistant.
"""

import sys
from pathlib import Path

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.resolve()

# Add project root to Python path if not already there
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Verify required directories exist
REQUIRED_DIRS = ['src', 'assets']
for dir_name in REQUIRED_DIRS:
    if not (PROJECT_ROOT / dir_name).exists():
        print(f"Warning: Required directory '{dir_name}' not found in {PROJECT_ROOT}")

from src.ui.settings_manager import main as settings_main

if __name__ == "__main__":
    print("=" * 60)
    print("AI Virtual Assistant - Launcher")
    print("=" * 60)
    print(f"\nProject root: {PROJECT_ROOT}")
    print("\nOpening Settings Manager...")
    print("Configure your assistant and click START to launch.\n")
    
    # Launch settings manager
    settings_main()