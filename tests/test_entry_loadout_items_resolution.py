"""Regression tests for the perfect_window persistence break (commit 9c38d2d2).

The canonical persistence path (`canonicalize_and_assemble` -> `_normalize_entry_shape`)
stores a loadout's gear/minis as NAME STRINGS (the loadout hash is derived from names). The
per-tier gem re-solve, made unconditional for `perfect_window` by 9c38d2d2, calls
`_entry_loadout_items`, which needs the 6 gear + 3 mini pre-gem STAT-DICTS. Before the fix that
mismatch raised "tier re-solve needs 6 gear + 3 mini stat-dicts, got 0" for every song.

These exercise the real resolver against the live Gears.csv/Minis.csv maps -- no monkeypatch.
"""

import pytest

from gear_optimizer.data.loadout_equivalence import (
    get_gears_by_name_cached,
    get_minis_by_name_cached,
)
from gear_optimizer.helpers.song_helpers.team_buff_tiers import (
    _entry_loadout_items,
    _representative_mini_names_from_any,
)


def _real_gear_and_mini_names():
    gears_by_name = get_gears_by_name_cached()
    minis_by_name = get_minis_by_name_cached()
    gear_names = list(gears_by_name.keys())[:6]
    # Pick mini names whose representative resolves back into the map (variant-group safe).
    mini_names = []
    for name in minis_by_name.keys():
        rep = _representative_mini_names_from_any([name])
        if len(rep) == 1 and rep[0] in minis_by_name:
            mini_names.append(name)
        if len(mini_names) == 3:
            break
    return gear_names, mini_names


def _has_real_stats(item):
    return isinstance(item, dict) and any(k not in ("Name", "type") for k in item.keys())


def test_entry_loadout_items_resolves_persisted_name_strings():
    gear_names, mini_names = _real_gear_and_mini_names()
    if len(gear_names) < 6 or len(mini_names) < 3:
        pytest.skip("Gears.csv/Minis.csv not available in this environment")

    # Persistence shape: gear/minis are bare NAME STRINGS (not stat-dicts).
    entry = {"loadout_hash": "name-strings", "gear": list(gear_names), "minis": list(mini_names)}
    items = _entry_loadout_items(entry)

    assert len(items) == 9, "must resolve exactly 6 gear + 3 mini stat-dicts"
    assert all(_has_real_stats(it) for it in items), "names must resolve to real stat-dicts, not bare {'Name': ...}"
    assert [it.get("Name") for it in items[:6]] == list(gear_names), "gear order/identity preserved"


def test_entry_loadout_items_fails_loud_on_unresolvable_names():
    entry = {"loadout_hash": "bad", "gear": ["__no_such_gear__"] * 6, "minis": ["__no_such_mini__"] * 3}
    with pytest.raises(ValueError):
        _entry_loadout_items(entry)


def test_entry_loadout_items_accepts_already_expanded_stat_dicts():
    """The on-demand serving path passes entries whose gear/minis are already stat-dicts;
    they must be used directly (the resolver handles both shapes)."""
    gear_names, mini_names = _real_gear_and_mini_names()
    if len(gear_names) < 6 or len(mini_names) < 3:
        pytest.skip("Gears.csv/Minis.csv not available in this environment")
    gears_by_name = get_gears_by_name_cached()
    minis_by_name = get_minis_by_name_cached()
    entry = {
        "loadout_hash": "stat-dicts",
        "gear": [dict(gears_by_name[n]) for n in gear_names],
        "minis": [dict(minis_by_name[n]) for n in mini_names],
    }
    items = _entry_loadout_items(entry)
    assert len(items) == 9
    assert all(_has_real_stats(it) for it in items)
