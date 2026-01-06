"""
CSV parsing functions for loading gear, minis, and stats data.
Handles both modern and legacy CSV formats.
"""

import csv
import os
from ..core.constants import SCRIPT_DIR
from ..core.stats_calculator import build_base_stats_from_config
from ..core.utils import cfg_to_dict, safe_int, empty_stats
from .models import WarnOnce

# Global warning instance
WARN_ONCE = WarnOnce()


def resolve_stats_csv(paths, filename):
    """
    Resolve Gears/Minis CSV relative to SCRIPT_DIR or Stats.csv folder.

    Args:
        paths: Path configuration dict
        filename: Name of CSV file (e.g., "Gears.csv")

    Returns:
        str: Resolved path to CSV file
    """
    csv_path = os.path.join(SCRIPT_DIR, filename)
    if not os.path.exists(csv_path):
        stats_loc = paths.get("Stats", "")
        if stats_loc:
            csv_path = os.path.join(os.path.dirname(stats_loc), filename)
    return csv_path


def _build_row_map(row, header_lower):
    """
    Build a mapping from header keys to row values for CSV parsing.

    Args:
        row: CSV row data
        header_lower: Lowercase header names

    Returns:
        dict: Mapping of header keys to values
    """
    mapped = {}
    for idx, col in enumerate(header_lower):
        key = col or f"col_{idx}"
        mapped.setdefault(key, []).append(row[idx].strip() if idx < len(row) else "")
    return mapped


def _first_val(row_map, keys):
    """
    Return the first non-empty value from row_map matching any of the keys.

    Args:
        row_map: Dictionary from _build_row_map
        keys: Tuple of possible key names

    Returns:
        str: First matching value or empty string
    """
    for key in keys:
        for val in row_map.get(key, []):
            v = str(val).strip() if val is not None else ""
            if v:
                return v
    return ""


def parse_gear_rows(filepath):
    """
    Parse Gears.csv into a list of gear dicts.
    Supports both modern and legacy CSV formats.

    Args:
        filepath: Path to Gears.csv file

    Returns:
        list: List of gear dictionaries with stats
    """
    gear_list = []
    if not os.path.exists(filepath):
        return gear_list
    try:
        with open(filepath, "r", encoding="utf-8-sig", newline="") as f:
            rows = list(csv.reader(f))

        if not rows:
            return gear_list

        header = [h.strip() for h in rows[0]]
        header_lower = [h.lower() for h in header]

        modern_format = "type" in header_lower and any(name in header_lower for name in ("gear name", "name", "gear"))

        if modern_format:
            for row in rows[1:]:
                if not any((c or "").strip() for c in row):
                    continue
                row_map = _build_row_map(row, header_lower)
                name = _first_val(row_map, ("gear name", "name", "gear"))
                if not name:
                    continue
                slot = _first_val(row_map, ("type", "slot", "category")) or "Hat"
                stats = {
                    "Name": name,
                    "type": slot,
                    "Chill": safe_int(_first_val(row_map, ("chill",))),
                    "Flow": safe_int(_first_val(row_map, ("flow",))),
                    "Rush": safe_int(_first_val(row_map, ("rush",))),
                    "Beat": safe_int(_first_val(row_map, ("beat",))),
                    "Vibe": safe_int(_first_val(row_map, ("vibe",))),
                    "Perfect Points": safe_int(_first_val(row_map, ("ppoint", "perfect points", "pp", "ppoints"))),
                    "Combo Multiplier": safe_int(_first_val(row_map, ("cmult", "cbmlt", "combo multiplier", "combo"))),
                    "Fever Multiplier": safe_int(_first_val(row_map, ("fmult", "fmlt", "fever multiplier"))),
                }
                # IMPORTANT: Perfect Time (often stored as "PTime") is a
                # completely different mechanic from Fever Time and must
                # NEVER be treated as Fever Time. Do not fall back to
                # any "ptime" column here; only true Fever Time fields
                # ("time" / "fever time" / "ft") are allowed.
                time_val = _first_val(row_map, ("time", "fever time", "ft"))
                stats["Fever Time"] = safe_int(time_val)
                stats["Fever Fill Rate"] = safe_int(
                    _first_val(row_map, ("fill", "fvfil", "fever fill rate", "fever fill"))
                )
                gear_list.append(stats)
        else:
            # Legacy format
            current_category = "Hat"
            known_slots = ["Neck", "Face", "Shirt", "Back", "Pants"]
            for row in rows[1:]:
                if not row:
                    continue
                potential_cat = row[0].strip()
                if potential_cat in known_slots:
                    current_category = potential_cat
                    continue
                if len(row) < 11:
                    continue
                name = row[0].strip()
                if not name:
                    continue
                stats = {
                    "Name": name,
                    "type": current_category,
                    "Chill": safe_int(row[1]),
                    "Flow": safe_int(row[2]),
                    "Rush": safe_int(row[3]),
                    "Beat": safe_int(row[4]),
                    "Vibe": safe_int(row[5]),
                    "Perfect Points": safe_int(row[6]),
                    "Combo Multiplier": safe_int(row[7]),
                    "Fever Multiplier": safe_int(row[8]),
                    "Fever Time": safe_int(row[9]),
                    "Fever Fill Rate": safe_int(row[10]),
                }
                gear_list.append(stats)
    except Exception as exc:
        WARN_ONCE.warn("gear-csv", f"Failed to parse gear CSV {filepath}: {exc}")
    return gear_list


def parse_mini_rows(filepath):
    """
    Parse Minis.csv into a list of mini dicts.
    Supports both modern and legacy CSV formats.

    Args:
        filepath: Path to Minis.csv file

    Returns:
        list: List of mini dictionaries with stats
    """
    minis_list = []
    if not os.path.exists(filepath):
        return minis_list
    try:
        with open(filepath, "r", encoding="utf-8-sig", newline="") as f:
            rows = list(csv.reader(f))

        if not rows:
            return minis_list

        header = [h.strip() for h in rows[0]]
        header_lower = [h.lower() for h in header]

        modern_format = "type" in header_lower and any(name in header_lower for name in ("mini name", "name", "mini"))

        if modern_format:
            for row in rows[1:]:
                if not any((c or "").strip() for c in row):
                    continue
                row_map = _build_row_map(row, header_lower)
                name = _first_val(row_map, ("mini name", "name", "mini"))
                if not name or name == "(Empty)":
                    continue
                mini_type = _first_val(row_map, ("type",)) or "Mini"
                stats = {
                    "Name": name,
                    "type": mini_type,
                    "Chill": safe_int(_first_val(row_map, ("chill",))),
                    "Flow": safe_int(_first_val(row_map, ("flow",))),
                    "Rush": safe_int(_first_val(row_map, ("rush",))),
                    "Beat": safe_int(_first_val(row_map, ("beat",))),
                    "Vibe": safe_int(_first_val(row_map, ("vibe",))),
                    "Perfect Points": safe_int(_first_val(row_map, ("ppoint", "perfect points", "pp", "ppoints"))),
                    "Combo Multiplier": safe_int(_first_val(row_map, ("cbmlt", "cmult", "combo multiplier", "combo"))),
                    "Fever Multiplier": safe_int(_first_val(row_map, ("fmult", "fmlt", "fvmlt", "fever multiplier"))),
                    "Fever Time": safe_int(_first_val(row_map, ("fvtim", "time", "ft", "fever time"))),
                    "Fever Fill Rate": safe_int(_first_val(row_map, ("fvfil", "fill", "ff", "fever fill"))),
                }
                minis_list.append(stats)
        else:
            # Legacy format
            for row in rows[1:]:
                if len(row) < 12:
                    continue
                name = row[1].strip()
                if not name or name == "(Empty)":
                    continue
                stats = {
                    "Name": name,
                    "type": "Mini",
                    "Chill": safe_int(row[2]),
                    "Flow": safe_int(row[3]),
                    "Rush": safe_int(row[4]),
                    "Beat": safe_int(row[5]),
                    "Vibe": safe_int(row[6]),
                    "Perfect Points": safe_int(row[7]) if len(row) > 7 else 0,
                    "Combo Multiplier": safe_int(row[8]) if len(row) > 8 else 0,
                    "Fever Multiplier": safe_int(row[9]) if len(row) > 9 else 0,
                    "Fever Time": safe_int(row[10]) if len(row) > 10 else 0,
                    "Fever Fill Rate": safe_int(row[11]) if len(row) > 11 else 0,
                }
                minis_list.append(stats)
    except Exception as exc:
        WARN_ONCE.warn("mini-csv", f"Failed to parse minis CSV {filepath}: {exc}")
    return minis_list


def load_csv_db(filepath, db_type="gear"):
    """
    Load CSV file into a lookup dictionary.

    Args:
        filepath: Path to CSV file
        db_type: Type of database ("gear" or "mini")

    Returns:
        dict: Mapping of item names to stat dictionaries
    """
    db = {}
    if not os.path.exists(filepath):
        return db
    try:
        if db_type == "gear":
            gears = parse_gear_rows(filepath)
            db = {g["Name"]: g for g in gears}
        elif db_type == "mini":
            minis = parse_mini_rows(filepath)
            db = {m["Name"]: m for m in minis}
    except Exception as exc:
        WARN_ONCE.warn(
            "csv-db",
            f"Failed to build {db_type} CSV db from {filepath}: {exc}",
        )
    return db


def load_all_minis_list(paths):
    """
    Load all minis from CSV file.

    Args:
        paths: Path configuration

    Returns:
        list: List of all mini dictionaries
    """
    return parse_mini_rows(resolve_stats_csv(paths, "Minis.csv"))


def load_all_gears_list(paths):
    """
    Load all gears from CSV file.

    Args:
        paths: Path configuration

    Returns:
        list: List of all gear dictionaries
    """
    return parse_gear_rows(resolve_stats_csv(paths, "Gears.csv"))


def get_fixed_stats(cfg):
    """
    Calculate fixed stats from gems and team buffs in config.

    Args:
        cfg: ConfigParser instance

    Returns:
        dict: Stats dictionary with gem and team buff contributions
    """
    return build_base_stats_from_config(cfg_to_dict(cfg))


def get_config_gear_stats(cfg, paths, gears_db=None):
    """
    Load gear stats from config.ini.

    Args:
        cfg: ConfigParser instance
        paths: Path configuration
        gears_db: Optional preloaded gear database

    Returns:
        tuple: (gear_stats_dict, gear_list)
    """
    if gears_db is None:
        gears_db = load_csv_db(resolve_stats_csv(paths, "Gears.csv"), "gear")

    gear_stats = empty_stats()
    gear_list = []
    gear_slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
    for slot in gear_slots:
        key = "Pant" if slot == "Pants" else slot
        item_name = cfg.get("Gear", key, fallback=cfg.get("Gear", slot, fallback="")).strip().strip(" .")
        if item_name in gears_db:
            item_data = gears_db[item_name]
            if item_data.get("type", "Hat") == slot:
                gear_list.append(item_data)
                for k in gear_stats:
                    if k in item_data:
                        gear_stats[k] += item_data.get(k, 0)
        else:
            gear_list.append({"Name": "(Empty)", "type": slot})
    return gear_stats, gear_list


def get_config_mini_stats(cfg, paths, minis_db=None):
    """
    Load mini stats from config.ini.

    Args:
        cfg: ConfigParser instance
        paths: Path configuration
        minis_db: Optional preloaded mini database

    Returns:
        tuple: (mini_stats_dict, mini_list)
    """
    if minis_db is None:
        minis_db = load_csv_db(resolve_stats_csv(paths, "Minis.csv"), "mini")

    mini_stats = empty_stats()
    mini_list = []
    for i in range(1, 4):
        item_name = cfg.get("Minis", str(i), fallback="").strip().strip(" .")
        if item_name in minis_db:
            item_data = minis_db[item_name]
            mini_list.append(item_data)
            for k in mini_stats:
                if k in item_data:
                    mini_stats[k] += item_data.get(k, 0)
        else:
            mini_list.append({"Name": "(Empty)", "type": "Mini"})
    return mini_stats, mini_list


def read_table(fp):
    """
    Read stats reference table from a CSV file.

    Args:
        fp: File path to stats table CSV

    Returns:
        list: Table data as list of lists of floats, or empty list if file not found
    """
    if not fp or not os.path.exists(fp):
        return []
    try:
        # Explicit UTF-8-SIG to match other data files and avoid Windows 'charmap' decode issues
        with open(fp, "r", encoding="utf-8-sig") as f:
            lines = f.read().splitlines()
        if not lines:
            return []
        table = []
        for line in lines[1:]:
            parts = line.split()
            if parts:
                try:
                    row = [float(x) for x in parts]
                    table.append(row)
                except Exception as exc:
                    WARN_ONCE.warn(
                        "stats-table-row",
                        f"Malformed stats row in {fp}: {parts!r} ({exc})",
                    )
        return table
    except Exception as exc:
        WARN_ONCE.warn("stats-table", f"Failed to read stats table {fp}: {exc}")
        return []
