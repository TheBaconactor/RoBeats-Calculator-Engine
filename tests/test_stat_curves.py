from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest

from gear_optimizer.gamedata import CURVE_STATS, StatCurves, load_stat_curves, read_curves
from gear_optimizer.rules import MAX_STAT

_GAME = load_stat_curves(Path(__file__).resolve().parents[1] / "Data" / "Gear" / "Stats.txt")


def _write_stats_txt(path, rows: int = MAX_STAT + 1, columns: int = 5, multipliers=None) -> None:
    # Stats.txt: one header line, then rows from stat value MAX_STAT down to 0. Row r holds r + column, but the combo
    # and fever multipliers (columns 1 and 2) must be the game's curve values.
    multipliers = multipliers or {stat: _GAME.f64[stat] for stat in ("Combo Multiplier", "Fever Multiplier")}
    lines = []
    for row in range(rows):
        values = [float(row + col) for col in range(columns)]
        for col, stat in ((1, "Combo Multiplier"), (2, "Fever Multiplier")):
            if col < columns:
                values[col] = float(multipliers[stat][MAX_STAT - row])
        lines.append(" ".join(repr(value) for value in values))
    path.write_text("header\n" + "\n".join(lines) + "\n")


def test_read_curves_rejects_a_short_table(tmp_path) -> None:
    path = tmp_path / "Stats.txt"
    _write_stats_txt(path, rows=MAX_STAT)
    with pytest.raises(ValueError, match="expected 161 rows of 5 values"):
        read_curves(path)


def test_read_curves_rejects_short_rows(tmp_path) -> None:
    path = tmp_path / "Stats.txt"
    _write_stats_txt(path, columns=4)
    with pytest.raises(ValueError, match="expected 161 rows of 5 values"):
        read_curves(path)


def test_read_curves_reverses_the_file_rows_onto_the_stat_axis(tmp_path) -> None:
    path = tmp_path / "Stats.txt"
    _write_stats_txt(path)
    curves = read_curves(path)
    # The file's first data row is stat value MAX_STAT.
    assert curves.f64["Perfect Points"][MAX_STAT] == 0.0
    assert curves.f64["Perfect Points"][0] == float(MAX_STAT)
    assert curves.f64["Fever Time"][MAX_STAT] == 4.0
    assert curves.f64["Combo Multiplier"].tobytes() == _GAME.f64["Combo Multiplier"].tobytes()


def test_read_curves_rejects_a_multiplier_off_the_games_curve(tmp_path) -> None:
    combo = _GAME.f64["Combo Multiplier"].copy()
    combo[80] += 1e-6
    path = tmp_path / "Stats.txt"
    _write_stats_txt(path, multipliers={"Combo Multiplier": combo, "Fever Multiplier": _GAME.f64["Fever Multiplier"]})
    with pytest.raises(ValueError, match=r"Combo Multiplier 80 is 2\.600001\d*, the game's curve gives 2\.6"):
        read_curves(path)


def test_float32_view_is_the_float64_values_rounded() -> None:
    curves = StatCurves.from_mapping({stat: np.linspace(0.1, 3.7, MAX_STAT + 1) for stat in CURVE_STATS})
    for stat in CURVE_STATS:
        assert curves.f64[stat].dtype == np.float64
        assert curves.f32[stat].dtype == np.float32
        assert curves.f32[stat].tobytes() == curves.f64[stat].astype(np.float32).tobytes()
    assert curves.factor("Combo Multiplier", 999) == float(curves.f64["Combo Multiplier"][MAX_STAT])
    assert curves.factor("Combo Multiplier", -3) == float(curves.f64["Combo Multiplier"][0])


def test_from_mapping_requires_every_curve_at_full_length() -> None:
    values = {stat: np.ones(MAX_STAT + 1) for stat in CURVE_STATS}
    del values["Fever Time"]
    with pytest.raises(KeyError):
        StatCurves.from_mapping(values)
    values["Fever Time"] = np.ones(MAX_STAT)
    with pytest.raises(ValueError, match="Fever Time curve needs 161 values"):
        StatCurves.from_mapping(values)


def test_load_stat_curves_reloads_after_the_file_changes(tmp_path) -> None:
    path = tmp_path / "Stats.txt"
    _write_stats_txt(path)
    first = load_stat_curves(path)
    assert load_stat_curves(path) is first
    header, first, rest = path.read_text().split("\n", 2)
    path.write_text("\n".join((header, "9.0" + first[len("0.0"):], rest)))
    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))
    second = load_stat_curves(path)
    assert second is not first
    assert second.f64["Perfect Points"][MAX_STAT] == 9.0
