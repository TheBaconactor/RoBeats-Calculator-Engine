#!/usr/bin/env python3
"""
GeneralMeta - Main Entry Point

Find the universal best loadout and gem allocation per elemental category.
This analyzes existing optimization results from the database and runs
cross-song gem optimization.

Usage:
    python general_meta_main.py
"""
import configparser
import multiprocessing
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

from gear_optimizer.general_meta import run_general_meta, export_general_meta_json
from gear_optimizer.core.config import load_paths_cache
from gear_optimizer.data.database import init_db


def main():
    """Main entry point for GeneralMeta."""
    multiprocessing.freeze_support()
    
    print("=" * 60)
    print("GENERAL META - Universal Loadout Finder")
    print("=" * 60)
    print()
    
    try:
        # Load config
        cfg = configparser.ConfigParser()
        cfg.read(str(REPO_ROOT / "config.ini"), encoding="utf-8-sig")
        paths = load_paths_cache()
        
        # Ensure database exists
        init_db()
        
        # Run GeneralMeta analysis
        results = run_general_meta(cfg, paths)
        
        # Export to JSON
        output_path = export_general_meta_json(results)
        
        print("\n" + "=" * 60)
        print("GENERAL META COMPLETE")
        print("=" * 60)
        print(f"\nResults exported to: {output_path}")
        print(f"Processed {len(results.get('results', {}))} elemental combinations")
        
    except KeyboardInterrupt:
        print("\nCancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nFatal Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
