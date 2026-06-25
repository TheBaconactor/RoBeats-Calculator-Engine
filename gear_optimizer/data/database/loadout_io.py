"""
Loadout (gear + minis) compaction, expansion, and hashing helpers.
"""
import re
from typing import Any, List


def _compact_gear_for_db(gear_list):
    """
    Convert gear list to compact storage format (names only).
    Handles both dicts and strings.
    Args:
        gear_list: List of gear items (dicts or strings)
    Returns:
        list: List of gear names
    """
    if not gear_list:
        return []
    result = []
    for g in gear_list:
        if isinstance(g, dict):
            name = g.get("Name", "")
        else:
            name = str(g) if g else ""
        if name:
            result.append(name)
    return result


def _compact_minis_for_db(mini_list):
    """
    Convert mini list to compact storage format (names only).
    Handles:
    - dicts: {"Name": ...}
    - strings: "Electroman"
    - nested variant groups: [["A","B"], ["C"], ...] (takes a representative per slot)
    Args:
        mini_list: List of mini items (dicts or strings)
    Returns:
        list: List of mini names
    """
    if not mini_list:
        return []

    def _first_name(v: Any) -> str:
        if v is None:
            return ""
        if isinstance(v, dict):
            return str(v.get("Name", "") or "").strip()
        if isinstance(v, (list, tuple)):
            for it in v:
                name = _first_name(it)
                if name:
                    return name
            return ""
        if isinstance(v, str):
            s = v.strip()
            if s.startswith("[") and s.endswith("]"):
                match = re.search(r"[\"']([^\"']+)[\"']", s)
                if match:
                    return match.group(1).strip()
            return s
        return str(v).strip()

    result = []
    for m in mini_list:
        name = _first_name(m)
        if name:
            result.append(name)
    return result


def _expand_gear_from_db(gear_names, gears_by_name):
    """
    Expand gear names back to full stat dictionaries.
    Args:
        gear_names: List of gear names
        gears_by_name: Lookup dict mapping names to full gear dicts
    Returns:
        list: List of full gear dictionaries
    """
    if not gear_names or not gears_by_name:
        return []
    return [gears_by_name.get(name, {"Name": name}) for name in gear_names]


def _expand_minis_from_db(mini_names, minis_by_name):
    """
    Expand mini names back to full stat dictionaries.
    Args:
        mini_names: List of mini names
        minis_by_name: Lookup dict mapping names to full mini dicts
    Returns:
        list: List of full mini dictionaries
    """
    if not mini_names or not minis_by_name:
        return []
    return [minis_by_name.get(name, {"Name": name}) for name in mini_names]


def _loadout_hash_from_names(gear_names: list[str], mini_names: list[str]) -> str:
    from ...helpers.song_helpers.loadout_hashing import loadout_hash_from_names
    return loadout_hash_from_names(gear_names, mini_names)


def get_loadout_hash(gear_list: List[Any], mini_list: List[Any]) -> str:
    """
    Generate a unique hash for a loadout (gear + minis).
    Sorts items by name to ensure consistent hashing regardless of order.
    Handles both dicts (with 'Name' key) and plain strings.
    Args:
        gear_list: List of gear items (dicts or strings)
        mini_list: List of mini items (dicts or strings)
    Returns:
        str: MD5 hash of the loadout
    """
    # Route through the package facade so a monkeypatch of
    # `gear_optimizer.data.database._loadout_hash_from_names` is honored at call
    # time, exactly as in the pre-split monolith where this was a module-level name.
    from gear_optimizer.data import database as _db
    gear_names = _compact_gear_for_db(gear_list)
    mini_names = _compact_minis_for_db(mini_list)
    return _db._loadout_hash_from_names(gear_names, mini_names)
