import csv
import os

import pytest

from gear_optimizer.gamedata import ASCENSION_PERFECT_POINTS, load_minis, read_gears, read_minis, song_minis

# The exported Minis.csv layout: max-level stats, then an "L1 Stats" block repeating the columns.
_MINI_HEADER = [
    "Type", "Star", "Mini Name", "Chill", "Flow", "Rush", "Beat", "Vibe", "", "CbMlt", "FvMlt", "FvTim", "FvFil",
    "L1 Stats", "Chill", "Flow", "Rush", "Beat", "Vibe", "", "CbMlt", "FvMlt", "FvTim", "FvFil", "Song Target",
]
_GEAR_HEADER = ["Type", "Gear Name", "Chill", "Flow", "Rush", "Beat", "Vibe", "PPoint", "CMult", "FMult", "Time", "Fill", "PTime"]


def _mini_row(name, element, main, level1=None, targets=""):
    """A Minis.csv row: `main`/`level1` map a column header to its value within that block."""
    split = _MINI_HEADER.index("L1 Stats")
    row = [""] * len(_MINI_HEADER)
    row[0], row[1], row[2] = element, "1", name
    for index, column in enumerate(_MINI_HEADER[:split]):
        if column in main:
            row[index] = str(main[column])
    for index, column in enumerate(_MINI_HEADER[split + 1 : -1], start=split + 1):
        if column in (level1 or {}):
            row[index] = str(level1[column])
    row[-1] = targets
    return row


def _write(path, header, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def test_read_minis_reads_the_max_level_block_and_the_level1_colors(tmp_path):
    path = tmp_path / "Minis.csv"
    _write(path, _MINI_HEADER, [
        _mini_row(
            "Ringmaster Roxie", "Vibe", {"Rush": 35, "Vibe": 65}, {"Rush": 7, "Vibe": 13, "FvFil": 8},
            '["Clouds in the Blue (Hard) by Camellia"]',
        ),
    ])
    mini = read_minis(path)["Ringmaster Roxie"]
    assert mini.element == "Vibe"
    assert (mini.stats["Rush"], mini.stats["Vibe"]) == (35, 65)
    # The level-1 block never feeds the stats: its FvFil stays out of Fever Fill Rate.
    assert mini.stats["Fever Fill Rate"] == 0
    assert mini.stats["Perfect Points"] == 0
    assert dict(mini.level1_elements) == {"Rush": 7, "Vibe": 13}
    assert mini.song_targets == frozenset({"Clouds in the Blue (Hard) by Camellia"})


def test_a_targeted_mini_needs_level1_colors(tmp_path):
    path = tmp_path / "Minis.csv"
    _write(path, _MINI_HEADER, [_mini_row("No L1", "Rush", {"Rush": 40}, {}, '["Some Song"]')])
    with pytest.raises(ValueError, match="no level-1 value"):
        read_minis(path)


def test_a_custom_pool_mini_reads_and_only_gains_the_flat_ascension_perfect_points(tmp_path):
    # robeatsmeta_service._append_custom_pool_rows leaves the level-1 block and Song Target blank.
    path = tmp_path / "Minis.csv"
    _write(path, _MINI_HEADER, [
        _mini_row("Real Mini", "Rush", {"Rush": 50, "Flow": 20}, {"Rush": 10, "Flow": 4}, '["Target Song"]'),
        _mini_row("My Custom Mini", "Rush", {"Rush": 90, "Flow": 30, "CbMlt": 12}),
    ])
    minis = read_minis(path)
    custom = minis["My Custom Mini"]
    assert custom.level1_elements == {} and custom.song_targets == frozenset()

    ascended = {m.name: m for m in song_minis(minis.values(), "Target Song", "Rush", "Flow")}
    assert ascended["My Custom Mini"].targets_song is False
    assert ascended["My Custom Mini"].stats == {
        **custom.stats, "Perfect Points": ASCENSION_PERFECT_POINTS,
    }
    assert ascended["Real Mini"].targets_song is True
    assert ascended["Real Mini"].stats["Rush"] > minis["Real Mini"].stats["Rush"]


def test_song_minis_keeps_file_order_and_needs_a_song_name(tmp_path):
    path = tmp_path / "Minis.csv"
    _write(path, _MINI_HEADER, [_mini_row(name, "Chill", {"Chill": 10}) for name in ("B", "A", "C")])
    minis = read_minis(path)
    assert [m.name for m in song_minis(minis.values(), "Song", "Chill", "Chill")] == ["B", "A", "C"]
    with pytest.raises(ValueError, match="song name"):
        song_minis(minis.values(), "  ", "Chill", "")


def test_load_minis_reloads_when_the_file_changes(tmp_path):
    path = tmp_path / "Minis.csv"
    _write(path, _MINI_HEADER, [_mini_row("First", "Chill", {"Chill": 10})])
    first = load_minis(path)
    assert load_minis(path) is first
    _write(path, _MINI_HEADER, [_mini_row("Second", "Chill", {"Chill": 12})])
    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))
    assert list(load_minis(path)) == ["Second"]


def test_read_gears_maps_the_gear_columns_and_ignores_perfect_time(tmp_path):
    path = tmp_path / "Gears.csv"
    _write(path, _GEAR_HEADER, [["Hat", "Goggles", "", "6", "13", "", "", "", "6", "", "", "", "40"]])
    gear = read_gears(path)["Goggles"]
    assert gear.slot == "Hat"
    assert (gear.stats["Flow"], gear.stats["Rush"], gear.stats["Combo Multiplier"]) == (6, 13, 6)
    # PTime (Perfect Time) is a different mechanic from Fever Time.
    assert gear.stats["Fever Time"] == 0
