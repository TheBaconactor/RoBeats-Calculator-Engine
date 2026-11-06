"""The items a solve picks from, read from the game export."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from gear_optimizer.chart import read_header
from gear_optimizer.data.game_export import custom_catalog, game_song_names, load_catalog, read_catalog
from gear_optimizer.gamedata import ASCENSION_PERFECT_POINTS, song_minis
from gear_optimizer.settings import DIFFICULTIES

_NO_POOL = {"customGear": [], "customMinis": [], "excludeGear": [], "excludeMinis": []}
_GEAR_STATS = dict.fromkeys(
    ("ColorBlue", "ColorPurple", "ColorRed", "ColorOrange", "ColorGreen", "PerfectPoints", "ComboMultiplier",
     "FeverMultiplier", "FeverTime", "FeverFillRate", "PerfectTime"), 0)
_MINI_STATS = {key: 0 for key in _GEAR_STATS if key not in ("PerfectPoints", "PerfectTime")}


def _mini(name: str, targets: tuple[int, ...] = (), **stats: int) -> dict:
    return {"name": name, "stats": _MINI_STATS | stats, "ascension_songs": [{"song_id": song} for song in targets]}


def _export(path: Path, *, gears: tuple = (), minis: tuple = (), songs: tuple = ()) -> Path:
    path.write_text(json.dumps({
        "gears": {"1": {"gears": list(gears)}},
        "minis": {"1": {"minis": list(minis)}},
        "songs": {"1": {"songs": [
            {"songid": song_id, "displayname": title, "artist": "Artist"} for song_id, title in songs
        ]}},
    }), encoding="utf-8")
    return path


def test_a_gear_keeps_its_stats_and_perfect_time_apart(tmp_path):
    raw = {"name": " Goggles ", "slot": 3, "stats": _GEAR_STATS | {
        "ColorPurple": 6, "ColorRed": 13, "ComboMultiplier": 6, "PerfectTime": 40,
    }}
    gear = read_catalog(_export(tmp_path / "export.json", gears=(raw,))).gears["Goggles"]
    assert gear.slot == "Hat"
    assert (gear.stats["Flow"], gear.stats["Rush"], gear.stats["Combo Multiplier"]) == (6, 13, 6)
    # Perfect Time moves the hit windows; it is not Fever Time and no score reads it.
    assert gear.perfect_time == 40
    assert gear.stats["Fever Time"] == 0


def test_a_mini_export_holds_level_one_stats(tmp_path):
    minis = (_mini("Ringmaster Roxie", (7,), ColorRed=7, ColorGreen=13, FeverFillRate=8),)
    mini = read_catalog(_export(tmp_path / "e.json", minis=minis, songs=((7, "Clouds in the Blue (Hard)"),))).minis["Ringmaster Roxie"]
    assert mini.element == "Vibe"
    assert (mini.stats["Rush"], mini.stats["Vibe"], mini.stats["Fever Fill Rate"]) == (35, 65, 32)
    assert mini.stats["Perfect Points"] == 0
    assert dict(mini.level1_elements) == {"Rush": 7, "Vibe": 13}
    assert mini.song_targets == frozenset({"Clouds in the Blue (Hard) by Artist"})


@pytest.mark.parametrize(("export", "message"), [
    ({"minis": (_mini("A", (9,), ColorRed=1),)}, "unknown song_id 9"),
    ({"minis": (_mini("A", (1, 1), ColorRed=1),), "songs": ((1, "S"),)}, "twice"),
    ({"minis": (_mini("A"), _mini("A"))}, "duplicate mini"),
    ({"gears": ({"name": " ", "slot": 1, "stats": _GEAR_STATS},)}, "no name"),
    ({"songs": ((1, "S"), (1, "T"))}, "duplicate song id"),
    ({"songs": ((1, "S"), (2, "S"))}, "duplicate song"),
])
def test_a_bad_export_stops_the_read(tmp_path, export, message):
    with pytest.raises(ValueError, match=message):
        read_catalog(_export(tmp_path / "export.json", **export))


def test_a_custom_mini_gains_only_the_flat_ascension_perfect_points(tmp_path):
    catalog = read_catalog(_export(
        tmp_path / "e.json", minis=(_mini("Real Mini", (1,), ColorRed=10, ColorPurple=4),), songs=((1, "Target Song"),),
    ))
    pool = _NO_POOL | {"customMinis": [{"name": "My Custom Mini", "type": "Rush", "rush": 90, "flow": 30, "cbmlt": 12,
                                        "chill": 0, "beat": 0, "vibe": 0, "fvmlt": 0, "fvtim": 0, "fvfil": 0}]}
    minis = custom_catalog(catalog, pool).minis
    custom = minis["My Custom Mini"]
    assert custom.level1_elements == {} and custom.song_targets == frozenset()
    ascended = {m.name: m for m in song_minis(minis.values(), "Target Song by Artist", "Rush", "Flow")}
    assert ascended["My Custom Mini"].targets_song is False
    assert ascended["My Custom Mini"].stats == {**custom.stats, "Perfect Points": ASCENSION_PERFECT_POINTS}
    assert ascended["Real Mini"].targets_song is True
    assert ascended["Real Mini"].stats["Rush"] > minis["Real Mini"].stats["Rush"]


def test_a_pool_excludes_by_name_whatever_the_case_and_leaves_the_catalog_alone(tmp_path):
    gears = [{"name": name, "slot": 3, "stats": _GEAR_STATS} for name in ("Keep", "Drop")]
    catalog = read_catalog(_export(tmp_path / "e.json", gears=gears, minis=(_mini("Mini"),)))
    solve_catalog = custom_catalog(catalog, _NO_POOL | {"excludeGear": ["DROP", "not in the catalog"], "excludeMinis": ["mini"]})
    assert list(solve_catalog.gears) == ["Keep"] and list(solve_catalog.minis) == []
    assert list(catalog.gears) == ["Keep", "Drop"]


def test_song_minis_keeps_export_order_and_needs_a_song_name(tmp_path):
    minis = read_catalog(_export(tmp_path / "e.json", minis=[_mini(name, ColorBlue=2) for name in ("B", "A", "C")])).minis
    assert [m.name for m in song_minis(minis.values(), "Song", "Chill", "Chill")] == ["B", "A", "C"]
    with pytest.raises(ValueError, match="song name"):
        song_minis(minis.values(), "  ", "Chill", "")


def test_the_catalog_reloads_when_the_file_changes(tmp_path):
    path = _export(tmp_path / "export.json", minis=(_mini("First"),))
    first = load_catalog(path)
    assert load_catalog(path) is first
    _export(path, minis=(_mini("Second!"),))
    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))
    assert list(load_catalog(path).minis) == ["Second!"]


def test_every_checked_in_mini_target_has_a_chart():
    data = Path(__file__).resolve().parents[1] / "Data"
    export = data / "exported_game_data.json"
    charts = {read_header(chart)["Song Name"] for difficulty in DIFFICULTIES for chart in (data / difficulty).glob("*.txt")}
    targets = {target for mini in read_catalog(export).minis.values() for target in mini.song_targets}
    assert targets and targets <= charts
    assert targets <= game_song_names(export)
