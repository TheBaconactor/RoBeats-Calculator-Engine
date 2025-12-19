"""
Database Health Checker - Background CPU task to validate Stats field consistency.

Runs async without blocking GPU. Samples entries and checks for discrepancies
between stored Stats and computed Stats (from gear + minis + gems + base).
"""

import csv
import json
import os
import random
import sqlite3
from typing import Optional

from ..core.stats_calculator import build_base_stats_from_config, compute_full_stats
from ..core.constants import SKIP_ITEM_KEYS


class DBHealthChecker:
    """
    Validates database Stats field consistency.
    
    Designed to run as a background CPU task without blocking GPU work.
    Samples entries and compares stored Stats vs computed Stats.
    """
    
    def __init__(self, gears_path: str, minis_path: str, cfg_dict: dict):
        """
        Initialize the health checker.

        Args:
            gears_path: Path to Gears.csv
            minis_path: Path to Minis.csv
            cfg_dict: Config dictionary (from cfg_to_dict)
        """
        self.gears_by_name = self._load_items_from_csv(gears_path)
        self.minis_by_name = self._load_items_from_csv(minis_path)
        self.base_stats = build_base_stats_from_config(cfg_dict)
        
    def _load_items_from_csv(self, csv_path: str) -> dict:
        """Load items from CSV file with key normalization."""
        items = {}
        if not csv_path or not os.path.exists(csv_path):
            return items
        
        # Mapping for normalizing keys to internal naming
        key_map = {
            "PPoint": "Perfect Points",
            "CMult": "Combo Multiplier",
            "FMult": "Fever Multiplier",
            "Time": "Fever Time",
            "Fill": "Fever Fill Rate",
            "CbMlt": "Combo Multiplier",
            "FvMlt": "Fever Multiplier",
            "FvTim": "Fever Time",
            "FvFil": "Fever Fill Rate",
        }
            
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = row.get("Name") or row.get("Gear Name") or row.get("Mini Name")
                    if name:
                        item = {"Name": name}
                        for k, v in row.items():
                            if k in ("Name", "Gear Name", "Mini Name", "", "Type", "Star", "L1 Stats"):
                                continue
                            norm_k = key_map.get(k, k)
                            try:
                                item[norm_k] = int(v) if v else 0
                            except ValueError:
                                item[norm_k] = v
                        items[name] = item
        except Exception:
            pass
        return items

    def compute_expected_stats(self, gear_names: list, mini_names: list,
                                gem_counts: dict, selected_element: str) -> dict:
        """Compute expected Stats from gear/minis/gems."""
        return compute_full_stats(
            gear_names, mini_names, gem_counts, selected_element,
            self.gears_by_name, self.minis_by_name, self.base_stats
        )
    
    def check_sample(self, db_path: str, sample_size: int = 100) -> list:
        """
        Sample entries and check for Stats discrepancies.
        
        Args:
            db_path: Path to evolution.db
            sample_size: Number of entries to sample
            
        Returns:
            List of discrepancy tuples: (rowid, song_name, field, expected, actual)
        """
        discrepancies = []
        
        if not os.path.exists(db_path):
            return discrepancies
            
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            
            # Get total count
            total = conn.execute("SELECT COUNT(*) FROM loadouts").fetchone()[0]
            if total == 0:
                conn.close()
                return discrepancies
            
            # Sample random entries
            sample_size = min(sample_size, total)
            offsets = random.sample(range(total), sample_size)
            
            for offset in offsets:
                row = conn.execute(
                    "SELECT rowid, song_name, gear_json, minis_json, details_json "
                    "FROM loadouts LIMIT 1 OFFSET ?",
                    (offset,)
                ).fetchone()
                
                if not row:
                    continue
                    
                details = json.loads(row["details_json"]) if row["details_json"] else {}
                stored_stats = details.get("Stats", {})
                
                # Skip if no Stats field (expected for very old entries)
                if not stored_stats:
                    continue
                
                gear_names = json.loads(row["gear_json"]) if row["gear_json"] else []
                mini_names = json.loads(row["minis_json"]) if row["minis_json"] else []
                gem_counts = details.get("GemCounts", {})
                selected_element = details.get("SelectedElement") or details.get("Selected Element") or ""
                
                expected_stats = self.compute_expected_stats(
                    gear_names, mini_names, gem_counts, selected_element
                )
                
                # Compare key stats (ignore minor fields like PTime)
                key_fields = [
                    "Perfect Points", "Combo Multiplier", "Fever Multiplier",
                    "Fever Time", "Fever Fill Rate"
                ]
                
                for field in key_fields:
                    expected = expected_stats.get(field, 0)
                    actual = stored_stats.get(field, 0)
                    
                    if expected != actual:
                        discrepancies.append((
                            row["rowid"],
                            row["song_name"],
                            field,
                            expected,
                            actual
                        ))
            
            conn.close()
        except Exception as e:
            # Don't crash on health check errors
            pass
            
        return discrepancies


def run_health_check(db_path: str, gears_path: str, minis_path: str, 
                     cfg_dict: dict, sample_size: int = 100) -> Optional[str]:
    """
    Run a health check and return a warning message if issues found.
    
    Args:
        db_path: Path to evolution.db
        gears_path: Path to Gears.csv
        minis_path: Path to Minis.csv
        cfg_dict: Config dictionary
        sample_size: Number of entries to sample
        
    Returns:
        Warning message string, or None if no issues
    """
    try:
        checker = DBHealthChecker(gears_path, minis_path, cfg_dict)
        discrepancies = checker.check_sample(db_path, sample_size)
        
        if discrepancies:
            return (
                f"[DB Health] Found {len(discrepancies)} entries with Stats discrepancies. "
                f"Run 'python tools/backfill_stats.py' to fix."
            )
        return None
    except Exception as e:
        return f"[DB Health] Check failed: {e}"
