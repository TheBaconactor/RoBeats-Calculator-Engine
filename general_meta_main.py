#!/usr/bin/env python3
"""
GeneralMeta - Main Entry Point

Find the universal best loadout and gem allocation per elemental category.
This analyzes existing optimization results from the database and runs
cross-song gem optimization.

Usage:
    python general_meta_main.py
"""

import multiprocessing
from pathlib import Path
import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

from general_meta import export_general_meta_json, run_general_meta
from gear_optimizer.core.config import find_and_cache_paths, get_config_path, load_config, load_paths_cache
from gear_optimizer.data.database import init_db


def sync_optimizer_csvs_from_exported_data(repo_root: Path) -> None:
    """
    Refresh Data/Gear CSVs from exported_game_data.json before GeneralMeta.

    This keeps mini/gear catalogs aligned with the latest game-data export and
    prevents silent drift where winners reference names missing from stale CSVs.
    """
    exporter = repo_root / "tools" / "data" / "export_game_data_gear_minis.py"
    exported_data = repo_root / "Data" / "exported_game_data.json"
    gears_out = repo_root / "Data" / "Gear" / "Gears.csv"
    minis_out = repo_root / "Data" / "Gear" / "Minis.csv"

    if not exporter.exists():
        raise FileNotFoundError(f"Missing exporter script: {exporter}")
    if not exported_data.exists():
        raise FileNotFoundError(f"Missing exported game data: {exported_data}")

    cmd = [
        sys.executable,
        str(exporter),
        "--input",
        str(exported_data),
        "--gears-out",
        str(gears_out),
        "--minis-out",
        str(minis_out),
    ]
    print("Syncing optimizer gear/mini CSVs from exported_game_data.json ...")
    subprocess.run(cmd, check=True, cwd=str(repo_root))


def main():
    """Main entry point for GeneralMeta."""
    multiprocessing.freeze_support()

    print("=" * 60)
    print("GENERAL META - Universal Loadout Finder")
    print("=" * 60)
    print()

    try:
        sync_optimizer_csvs_from_exported_data(REPO_ROOT)
        # Rebuild path cache so subsequent loaders use current CSV paths.
        find_and_cache_paths()

        # Load config
        cfg = load_config(get_config_path(str(REPO_ROOT / "config.ini")))
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
