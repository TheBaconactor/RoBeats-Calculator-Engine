import numpy as np

from gear_optimizer.core.constants import TOTAL_ROWS
from gear_optimizer.solver.fever_timeline import SONG_TIMELINE_GRIDS, SongTimelineGrid
from gear_optimizer.solver.scoring import GEM_SOLVER_CACHE, solve_best_fever_combination


def _mock_song(*, n_notes: int = 64, duration: float = 120.0) -> dict:
    timestamps = np.linspace(0.0, float(duration), int(n_notes), dtype=np.float32)
    return {
        "metadata": {
            "Song Name": "Topology Bucket Song",
            "Difficulty": "Hard",
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": float(timestamps[-1]),
            "Total Notes": int(timestamps.shape[0]),
        },
        "song_data": {"timestamps": timestamps},
    }


def _ref_arrays(rows: int) -> dict:
    return {
        "Perfect Points": np.linspace(1.0, 2.0, rows, dtype=np.float32),
        "Combo Multiplier": np.linspace(1.0, 3.0, rows, dtype=np.float32),
        "Fever Multiplier": np.linspace(1.0, 5.0, rows, dtype=np.float32),
        "Fever Fill Rate": np.linspace(1.0, 2.0, rows, dtype=np.float32),
        "Fever Time": np.linspace(1.0, 2.5, rows, dtype=np.float32),
    }


def _base_stats() -> dict:
    return {
        "Perfect Points": 100,
        "Combo Multiplier": 95,
        "Fever Multiplier": 90,
        "Fever Fill Rate": 80,
        "Fever Time": 85,
        "Rush": 140,
        "Flow": 120,
        "Beat": 60,
        "Vibe": 60,
        "Chill": 60,
    }


def _cfg_data() -> dict:
    return {
        "selected_color": "Rush",
        "user_ft": 0,
        "user_ff": 0,
        "user_pp": 0,
        "user_cm": 0,
        "user_fm": 0,
        "static_elem_input": 0,
        "use_gpu": False,
    }


def _clear_timeline_caches() -> None:
    SONG_TIMELINE_GRIDS.clear()
    GEM_SOLVER_CACHE.clear()


def test_exact_signature_bucket_mode_preserves_timeline_entries(monkeypatch) -> None:
    calc_song = _mock_song(n_notes=48, duration=96.0)
    ref_arrays = _ref_arrays(TOTAL_ROWS + 1)
    sample_pairs = [(0, 0), (2, 5), (11, 7), (27, 13), (80, 40)]

    monkeypatch.setenv("TIMELINE_BUCKET_MODE", "off")
    _clear_timeline_caches()
    grid_off = SongTimelineGrid(calc_song, ref_arrays)
    timelines_off = {pair: grid_off.get_timeline(*pair) for pair in sample_pairs}

    monkeypatch.setenv("TIMELINE_BUCKET_MODE", "a")
    _clear_timeline_caches()
    grid_sig = SongTimelineGrid(calc_song, ref_arrays)

    for pair in sample_pairs:
        timeline_off = timelines_off[pair]
        timeline_sig = grid_sig.get_timeline(*pair)

        assert np.array_equal(
            np.asarray(timeline_off[0], dtype=np.bool_),
            np.asarray(timeline_sig[0], dtype=np.bool_),
        )
        assert int(timeline_off[1]) == int(timeline_sig[1])
        assert int(timeline_off[2]) == int(timeline_sig[2])
        assert int(timeline_off[3]) == int(timeline_sig[3])
        assert int(timeline_off[4]) == int(timeline_sig[4])


def test_exact_signature_bucket_mode_preserves_solver_output(monkeypatch) -> None:
    calc_song = _mock_song(n_notes=72, duration=144.0)
    ref_arrays = _ref_arrays(TOTAL_ROWS + 1)
    base_stats = _base_stats()
    cfg_data = _cfg_data()

    monkeypatch.setenv("TIMELINE_BUCKET_MODE", "off")
    _clear_timeline_caches()
    result_off = solve_best_fever_combination(
        cfg=None,
        initial_stats=base_stats.copy(),
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        silent=True,
        override_cfg=cfg_data,
    )

    monkeypatch.setenv("TIMELINE_BUCKET_MODE", "a")
    _clear_timeline_caches()
    result_sig = solve_best_fever_combination(
        cfg=None,
        initial_stats=base_stats.copy(),
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        silent=True,
        override_cfg=cfg_data,
    )

    assert int(result_off["Score"]) == int(result_sig["Score"])
    assert int(result_off["FT"]) == int(result_sig["FT"])
    assert int(result_off["FF"]) == int(result_sig["FF"])
    assert result_off["GemCounts"] == result_sig["GemCounts"]
    assert result_off["Stats"] == result_sig["Stats"]
    assert result_off["Selected Element"] == result_sig["Selected Element"]
