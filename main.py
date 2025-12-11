#!/usr/bin/env python3
"""
Gear Optimizer - Main Entry Point

Refactored to use GearOptimizerApp.
"""
import multiprocessing
import sys
from gear_optimizer.app import GearOptimizerApp

if __name__ == "__main__":
    multiprocessing.freeze_support()
    try:
        app = GearOptimizerApp()
        app.run()
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print(f"Fatal Error: {e}")
        sys.exit(1)
