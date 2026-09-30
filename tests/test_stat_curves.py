from __future__ import annotations

import os

import numpy as np
import pytest

from gear_optimizer.gamedata import CURVE_STATS, StatCurves, load_stat_curves, read_curves
from gear_optimizer.rules import MAX_STAT


def _write_stats_txt(path, rows: int = MAX_STAT + 1, columns: int = 5) -> None:
    # Stats.txt: one header line, then rows from stat value MAX_STAT down to 0.
    body = "\n".join(" ".join(str(float(row + col)) for col in range(columns)) for row in range(rows))
    path.write_text("header\n" + body + "\n")


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
    body = path.read_text().replace("0.0 1.0 2.0 3.0 4.0", "9.0 1.0 2.0 3.0 4.0", 1)
    path.write_text(body)
    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))
    second = load_stat_curves(path)
    assert second is not first
    assert second.f64["Perfect Points"][MAX_STAT] == 9.0
