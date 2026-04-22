import numpy as np

from gear_optimizer.core.constants import TOTAL_ROWS
from gear_optimizer.solver.fever_timeline import calculate_non_fever_sections
from gear_optimizer.solver.scoring.stats_scoring import (
    _FG_BASELINE_CACHE,
    _FG_BASELINE_GRID_CACHE,
    _FG_BASELINE_POINT_MISS_COUNT,
    fg_baseline_params,
)
from gear_optimizer.solver.scoring_core import lookup_reference_py


def test_fg_baseline_params_grid_matches_non_fever_sections(monkeypatch):
    monkeypatch.setenv("FG_BASELINE_GRID", "1")
    monkeypatch.setenv("FG_BASELINE_GRID_AUTO_THRESHOLD", "0")
    _FG_BASELINE_GRID_CACHE.clear()
    _FG_BASELINE_CACHE.clear()
    _FG_BASELINE_POINT_MISS_COUNT.clear()

    timestamps = np.linspace(0.0, 120.0, 1000, dtype=np.float32)
    calc_song = {
        "metadata": {
            "Song Name": "pytest_fg_baseline_grid",
            "Difficulty": "Hard",
            "Long Notes": 0,
            "Last Note Time": float(timestamps[-1]),
            "HumanHitSimSeed": 0,
        },
        "song_data": {"timestamps": timestamps, "fg_timestamps": timestamps},
    }
    ref_arrays = {
        "Fever Time": np.linspace(1.0, 2.5, TOTAL_ROWS + 1, dtype=np.float32),
        "Fever Fill Rate": np.linspace(1.0, 2.0, TOTAL_ROWS + 1, dtype=np.float32),
    }

    total_notes = int(timestamps.shape[0])
    long_notes = 0
    last_note_time = float(timestamps[-1])

    combos = [
        (0, 0),
        (1, 3),
        (20, 50),
        (80, 100),
        (160, 160),
    ]
    for ft_stat, ff_stat in combos:
        stats = {"Fever Time": int(ft_stat), "Fever Fill Rate": int(ff_stat)}
        got_sections, got_base = fg_baseline_params(stats, calc_song, ref_arrays)

        fever_fill_rate = lookup_reference_py(ff_stat, ref_arrays["Fever Fill Rate"], TOTAL_ROWS)
        fever_time_stat = lookup_reference_py(ft_stat, ref_arrays["Fever Time"], TOTAL_ROWS)
        exp_sections, exp_base = calculate_non_fever_sections(
            timestamps,
            total_notes,
            fever_fill_rate,
            fever_time_stat,
            long_notes,
            last_note_time,
        )
        assert int(got_sections) == int(exp_sections)
        assert int(got_base) == int(exp_base)

    assert _FG_BASELINE_GRID_CACHE, "Expected fg_baseline_params to populate the per-song baseline grid cache"


def test_fg_baseline_params_auto_defers_grid_for_small_lookup_count(monkeypatch):
    monkeypatch.setenv("FG_BASELINE_GRID", "1")
    monkeypatch.setenv("FG_BASELINE_GRID_AUTO_THRESHOLD", "16")
    _FG_BASELINE_GRID_CACHE.clear()
    _FG_BASELINE_CACHE.clear()
    _FG_BASELINE_POINT_MISS_COUNT.clear()

    timestamps = np.linspace(0.0, 60.0, 256, dtype=np.float32)
    calc_song = {
        "metadata": {
            "Song Name": "pytest_fg_baseline_point_first",
            "Difficulty": "Hard",
            "Long Notes": 0,
            "Last Note Time": float(timestamps[-1]),
            "HumanHitSimSeed": 0,
        },
        "song_data": {"timestamps": timestamps, "fg_timestamps": timestamps},
    }
    ref_arrays = {
        "Fever Time": np.linspace(1.0, 2.0, TOTAL_ROWS + 1, dtype=np.float32),
        "Fever Fill Rate": np.linspace(1.0, 2.0, TOTAL_ROWS + 1, dtype=np.float32),
    }
    stats = {"Fever Time": 5, "Fever Fill Rate": 7}

    got_sections, got_base = fg_baseline_params(stats, calc_song, ref_arrays)

    fever_fill_rate = lookup_reference_py(stats["Fever Fill Rate"], ref_arrays["Fever Fill Rate"], TOTAL_ROWS)
    fever_time_stat = lookup_reference_py(stats["Fever Time"], ref_arrays["Fever Time"], TOTAL_ROWS)
    exp_sections, exp_base = calculate_non_fever_sections(
        timestamps,
        int(timestamps.shape[0]),
        fever_fill_rate,
        fever_time_stat,
        0,
        float(timestamps[-1]),
    )

    assert int(got_sections) == int(exp_sections)
    assert int(got_base) == int(exp_base)
    assert not _FG_BASELINE_GRID_CACHE
