"""Regression tests for the perfect_window persistence break (commit 9c38d2d2).

The canonical persistence path (`canonicalize_and_assemble` -> `_normalize_entry_shape`)
stores a loadout's gear/minis as NAME STRINGS (the loadout hash is derived from names). The
per-tier gem re-solve, made unconditional for `perfect_window` by 9c38d2d2, calls
`_entry_loadout_items`, which needs the 6 gear + 3 minis. Before the fix that mismatch raised
"tier re-solve needs 6 gear + 3 mini stat-dicts, got 0" for every song.

These exercise the real resolver against the live Gears.csv/Minis.csv -- no monkeypatch.
"""

import pytest

from gear_optimizer.gamedata import ASCENSION_PERFECT_POINTS, Gear, SongMini, load_gears, load_minis
from gear_optimizer.helpers.song_helpers.team_buff_tiers import (
    _entry_loadout_items,
    _representative_mini_names_from_any,
)
from gear_optimizer.settings import paths
from tests.items_support import make_song_mini
from tests.songs_support import make_chart

# No mini targets this song, so every mini only gains the flat ascension Perfect Points.
_CHART = make_chart([1.0, 2.0], name="Untargeted Test Song", primary="Rush", secondary="Flow")


def _real_gear_and_mini_names():
    gears = load_gears(paths().gears_csv)
    minis = load_minis(paths().minis_csv)
    gear_names = list(gears)[:6]
    # Pick mini names whose representative resolves back into the catalog (variant-group safe).
    mini_names = []
    for name in minis:
        rep = _representative_mini_names_from_any([name])
        if len(rep) == 1 and rep[0] in minis:
            mini_names.append(name)
        if len(mini_names) == 3:
            break
    return gear_names, mini_names


def _assert_resolved(items, gear_names, mini_names):
    minis = load_minis(paths().minis_csv)
    assert len(items) == 9, "must resolve exactly 6 gear + 3 minis"
    assert all(isinstance(item, Gear) for item in items[:6])
    assert [item.name for item in items[:6]] == list(gear_names), "gear order/identity preserved"
    assert all(isinstance(item, SongMini) for item in items[6:])
    for item, name in zip(items[6:], mini_names, strict=True):
        assert item.name == name
        assert item.stats["Perfect Points"] == minis[name].stats["Perfect Points"] + ASCENSION_PERFECT_POINTS


def test_entry_loadout_items_resolves_persisted_name_strings():
    gear_names, mini_names = _real_gear_and_mini_names()
    if len(gear_names) < 6 or len(mini_names) < 3:
        pytest.skip("Gears.csv/Minis.csv not available in this environment")

    # Persistence shape: gear/minis are bare NAME STRINGS.
    entry = {"loadout_hash": "name-strings", "gear": list(gear_names), "minis": list(mini_names)}
    _assert_resolved(_entry_loadout_items(entry, _CHART), gear_names, mini_names)


def test_entry_loadout_items_fails_loud_on_unresolvable_names():
    entry = {"loadout_hash": "bad", "gear": ["__no_such_gear__"] * 6, "minis": ["__no_such_mini__"] * 3}
    with pytest.raises(ValueError):
        _entry_loadout_items(entry, _CHART)


def test_entry_loadout_items_accepts_already_expanded_items():
    """The optimizer-replay path passes entries whose gear/minis are already catalog items (custom-pool
    items included); they are used directly and the minis ascend for the chart's song."""
    gear_names, mini_names = _real_gear_and_mini_names()
    if len(gear_names) < 6 or len(mini_names) < 3:
        pytest.skip("Gears.csv/Minis.csv not available in this environment")
    gears = load_gears(paths().gears_csv)
    minis = load_minis(paths().minis_csv)
    entry = {
        "loadout_hash": "items",
        "gear": [gears[n] for n in gear_names],
        "minis": [minis[n] for n in mini_names],
    }
    _assert_resolved(_entry_loadout_items(entry, _CHART), gear_names, mini_names)


def test_entry_loadout_items_keeps_song_minis_as_they_are():
    gear_names, _mini_names = _real_gear_and_mini_names()
    if len(gear_names) < 6:
        pytest.skip("Gears.csv not available in this environment")
    gears = load_gears(paths().gears_csv)
    song_minis = [make_song_mini(f"M{i}", **{"Perfect Points": 20 + i}) for i in range(3)]
    entry = {"loadout_hash": "song-minis", "gear": [gears[n] for n in gear_names], "minis": song_minis}
    assert _entry_loadout_items(entry, _CHART)[6:] == song_minis
