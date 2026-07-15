import numpy as np

from gear_optimizer.core.constants import GEM_SCALE_NORMAL
from gear_optimizer.helpers.song_helpers.fg_candidate_stats import hydrate_fg_candidate_stats
from gear_optimizer.solver.scoring.exact_rescore import score_stats_exact, score_stats_exact_batch
from gear_optimizer.solver.taichi_gem.api import timeline as timeline_api
from gear_optimizer.solver.timing_envelope import apply_timing_envelope


def _prebuild_timeline_cache(calc_song, ref_arrays, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("TIMELINE_FRONTIER_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("TIMELINE_FRONTIER_DISK_CACHE", "1")
    timeline_api.reset_timeline_state()
    apply_timing_envelope(calc_song)
    timeline_api.build_or_load_timeline_frontier_payload(calc_song, ref_arrays)
    timeline_api.reset_timeline_state()


def test_hydrate_fg_candidate_stats_uses_base_fixed_to_avoid_double_counting_user_gems():
    # base_stats_fixed includes "user fixed" gems already (a common non-auto-mode setup).
    # cfg_data tells us how many gems were embedded so we can subtract them before re-applying
    # the candidate's chosen allocation.
    user_pp = 7
    base_stats_fixed = {
        "Perfect Points": user_pp * GEM_SCALE_NORMAL,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Time": 0,
        "Fever Fill Rate": 0,
        "Beat": 0,
        "Vibe": 0,
        "Rush": 0,
        "Flow": 0,
        "Chill": 0,
    }
    cfg_data = {
        "user_pp": user_pp,
        "user_cm": 0,
        "user_fm": 0,
        "user_ft": 0,
        "user_ff": 0,
        "static_elem_input": 0,
        "selected_color": "Rush",
    }

    cand = {
        "Score": 123,
        "BaseScore": 123,
        "Gear": [],
        "Minis": [],
        "Loadout": [],
        "Data": {
            "FT": 0,
            "FF": 0,
            "GemCounts": {"Perfect Points": user_pp, "Combo Multiplier": 0, "Fever Multiplier": 0, "Element": 0},
            "Selected Element": "Rush",
        },
    }
    hydrate_fg_candidate_stats([cand], base_stats_fixed=base_stats_fixed, selected_color="Rush", cfg_data=cfg_data)

    stats = cand["Data"]["Stats"]
    # If we double-counted, this would be 2x. Correct behavior: it stays at the original embedded total.
    assert stats["Perfect Points"] == user_pp * GEM_SCALE_NORMAL


def test_hydrate_fg_candidate_stats_prefers_base_stats_over_rebuilding_from_loadout():
    cand = {
        "Score": 321,
        "BaseScore": 321,
        "Gear": [{"Name": "HugePP", "Perfect Points": 999}],
        "Minis": [],
        "Loadout": [{"Name": "HugePP", "Perfect Points": 999}],
        "Data": {
            "BaseStats": {
                "Perfect Points": 10,
                "Combo Multiplier": 0,
                "Fever Multiplier": 0,
                "Fever Time": 0,
                "Fever Fill Rate": 0,
                "Beat": 0,
                "Vibe": 0,
                "Rush": 0,
                "Flow": 0,
                "Chill": 0,
            },
            "FT": 0,
            "FF": 0,
            "GemCounts": {"Perfect Points": 1, "Combo Multiplier": 0, "Fever Multiplier": 0, "Element": 0},
            "Selected Element": "Rush",
        },
    }

    hydrate_fg_candidate_stats([cand], base_stats_fixed={}, selected_color="Rush", cfg_data={"selected_color": "Rush"})

    stats = cand["Data"]["Stats"]
    assert cand["Data"]["BaseStats"]["Perfect Points"] == 10
    assert stats["Perfect Points"] == 10 + GEM_SCALE_NORMAL


def test_hydrate_fg_candidate_stats_canonicalizes_base_score_and_preserves_raw_base_search_score(
    tmp_path, monkeypatch
):
    calc_song = {
        "metadata": {
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": 0.0,
        },
        "song_data": {"timestamps": [0.0], "note_types": [1], "lanes": [0]},
    }
    ref_arrays = {
        "Perfect Points": [1.0] * 161,
        "Combo Multiplier": [1.0] * 161,
        "Fever Multiplier": [1.0] * 161,
        "Fever Fill Rate": [1.0] * 161,
        "Fever Time": [1.0] * 161,
    }
    cand = {
        "Score": 999,
        "BaseScore": 999,
        "Data": {
            "BaseStats": {
                "Perfect Points": 0,
                "Combo Multiplier": 0,
                "Fever Multiplier": 0,
                "Fever Time": 0,
                "Fever Fill Rate": 0,
                "Beat": 0,
                "Vibe": 0,
                "Rush": 10,
                "Flow": 5,
                "Chill": 0,
            },
            "FT": 0,
            "FF": 0,
            "GemCounts": {"Perfect Points": 0, "Combo Multiplier": 0, "Fever Multiplier": 0, "Element": 0},
            "Selected Element": "Rush",
        },
    }
    _prebuild_timeline_cache(calc_song, ref_arrays, tmp_path, monkeypatch)

    hydrate_fg_candidate_stats(
        [cand],
        base_stats_fixed={},
        selected_color="Rush",
        cfg_data={"selected_color": "Rush"},
        calc_song=calc_song,
        ref_arrays=ref_arrays,
    )

    assert cand["RawBaseSearchScore"] == 999
    assert cand["Data"]["RawBaseSearchScore"] == 999
    assert cand["BaseScore"] == 26
    assert cand["Score"] == 26
    assert cand["Data"]["BaseScore"] == 26


def test_hydrate_fg_candidate_stats_canonicalizes_existing_stats_payload(tmp_path, monkeypatch):
    timestamps = np.linspace(0.0, 2.0, 101, dtype=np.float32)
    calc_song = {
        "metadata": {
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": float(timestamps[-1]),
        },
        "song_data": {
            "timestamps": timestamps,
            "note_types": np.ones(int(timestamps.shape[0]), dtype=np.int16),
            "lanes": np.zeros(int(timestamps.shape[0]), dtype=np.int16),
        },
    }
    ref_arrays = {
        "Perfect Points": [1.0] * 161,
        "Combo Multiplier": [2.0] * 161,
        "Fever Multiplier": [4.0] * 161,
        "Fever Fill Rate": [1.0] * 161,
        "Fever Time": [1.0] * 161,
    }
    stats = {
        "Perfect Points": 0,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Rush": 100,
        "Flow": 50,
    }
    cand = {
        "Score": 999,
        "BaseScore": 999,
        "Data": {
            "Stats": dict(stats),
            "BaseStats": dict(stats),
            "FT": 0,
            "FF": 0,
            "GemCounts": {"Perfect Points": 0, "Combo Multiplier": 0, "Fever Multiplier": 0, "Element": 0},
            "Selected Element": "Rush",
        },
    }
    _prebuild_timeline_cache(calc_song, ref_arrays, tmp_path, monkeypatch)

    hydrate_fg_candidate_stats(
        [cand],
        base_stats_fixed={},
        selected_color="Rush",
        cfg_data={"selected_color": "Rush"},
        calc_song=calc_song,
        ref_arrays=ref_arrays,
    )

    assert cand["RawBaseSearchScore"] == 999
    expected_score = score_stats_exact(stats, calc_song, ref_arrays)
    assert cand["BaseScore"] == expected_score
    assert cand["Data"]["BaseScore"] == expected_score


def test_score_stats_exact_batch_matches_scalar_timeline_frontier_authority(tmp_path, monkeypatch):
    timestamps = np.linspace(0.0, 12.0, 128, dtype=np.float32)
    calc_song = {
        "metadata": {
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 4,
            "Last Note Time": float(timestamps[-1]),
        },
        "song_data": {
            "timestamps": timestamps,
            "note_types": np.ones(int(timestamps.shape[0]), dtype=np.int16),
            "lanes": np.zeros(int(timestamps.shape[0]), dtype=np.int16),
        },
    }
    ref_arrays = {
        "Perfect Points": [float(1 + (i % 7) / 10.0) for i in range(161)],
        "Combo Multiplier": [float(1 + (i / 500.0)) for i in range(161)],
        "Fever Multiplier": [float(1 + (i / 400.0)) for i in range(161)],
        "Fever Fill Rate": [float(1 + (i / 300.0)) for i in range(161)],
        "Fever Time": [float(1 + (i / 250.0)) for i in range(161)],
    }
    stats_rows = [
        {
            "Perfect Points": 10 + i,
            "Combo Multiplier": 20 + i,
            "Fever Multiplier": 30 + i,
            "Fever Fill Rate": 40 + i,
            "Fever Time": 50 + i,
            "Rush": 100 + (i * 3),
            "Flow": 70 + (i * 2),
        }
        for i in range(5)
    ]
    _prebuild_timeline_cache(calc_song, ref_arrays, tmp_path, monkeypatch)

    assert score_stats_exact_batch(stats_rows, calc_song, ref_arrays) == [
        score_stats_exact(stats, calc_song, ref_arrays) for stats in stats_rows
    ]
