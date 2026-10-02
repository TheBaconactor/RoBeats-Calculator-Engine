from tests.curves_support import synthetic_curves
import numpy as np

from gear_optimizer.rules import STAT_GEM_GAIN_NORMAL
from gear_optimizer.helpers.song_helpers.fg_candidate_stats import hydrate_fg_candidate_stats
from gear_optimizer.solver.scoring.exact_rescore import score_stats_exact, score_stats_exact_batch
from gear_optimizer.solver.taichi_gem.api import timeline as timeline_api
from tests.songs_support import make_song


def _prebuild_timeline_cache(song, curves, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("TIMELINE_FRONTIER_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("TIMELINE_FRONTIER_DISK_CACHE", "1")
    timeline_api.reset_timeline_state()
    timeline_api.build_or_load_timeline_frontier_payload(song, curves)
    timeline_api.reset_timeline_state()


def test_hydrate_fg_candidate_stats_prefers_base_stats_over_rebuilding_from_genome():
    cand = {
        "Score": 321,
        "BaseScore": 321,
        "Gear": [{"Name": "HugePP", "Perfect Points": 999}],
        "Minis": [],
        "Genome": [{"Name": "HugePP", "Perfect Points": 999}],
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

    hydrate_fg_candidate_stats([cand], selected_color="Rush")

    stats = cand["Data"]["Stats"]
    assert cand["Data"]["BaseStats"]["Perfect Points"] == 10
    assert stats["Perfect Points"] == 10 + STAT_GEM_GAIN_NORMAL


def test_hydrate_fg_candidate_stats_canonicalizes_base_score_and_preserves_raw_ga_search_score(
    tmp_path, monkeypatch
):
    song = make_song([0.0])
    curves = synthetic_curves({
        "Perfect Points": [1.0] * 161,
        "Combo Multiplier": [1.0] * 161,
        "Fever Multiplier": [1.0] * 161,
        "Fever Fill Rate": [1.0] * 161,
        "Fever Time": [1.0] * 161,
    })
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
    _prebuild_timeline_cache(song, curves, tmp_path, monkeypatch)

    hydrate_fg_candidate_stats(
        [cand],
        selected_color="Rush",
        song=song,
        curves=curves,
    )

    assert cand["RawGASearchScore"] == 999
    assert cand["Data"]["RawGASearchScore"] == 999
    assert cand["BaseScore"] == 26
    assert cand["Score"] == 26
    assert cand["Data"]["BaseScore"] == 26


def test_hydrate_fg_candidate_stats_canonicalizes_existing_stats_payload(tmp_path, monkeypatch):
    timestamps = np.linspace(0.0, 2.0, 101, dtype=np.float32)
    song = make_song(timestamps)
    curves = synthetic_curves({
        "Perfect Points": [1.0] * 161,
        "Combo Multiplier": [2.0] * 161,
        "Fever Multiplier": [4.0] * 161,
        "Fever Fill Rate": [1.0] * 161,
        "Fever Time": [1.0] * 161,
    })
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
    _prebuild_timeline_cache(song, curves, tmp_path, monkeypatch)

    hydrate_fg_candidate_stats(
        [cand],
        selected_color="Rush",
        song=song,
        curves=curves,
    )

    assert cand["RawGASearchScore"] == 999
    assert cand["BaseScore"] == 80336
    assert cand["Data"]["BaseScore"] == 80336


def test_score_stats_exact_batch_matches_scalar_timeline_frontier_authority(tmp_path, monkeypatch):
    timestamps = np.linspace(0.0, 12.0, 128, dtype=np.float32)
    song = make_song(timestamps, long_notes=4)
    curves = synthetic_curves({
        "Perfect Points": [float(1 + (i % 7) / 10.0) for i in range(161)],
        "Combo Multiplier": [float(1 + (i / 500.0)) for i in range(161)],
        "Fever Multiplier": [float(1 + (i / 400.0)) for i in range(161)],
        "Fever Fill Rate": [float(1 + (i / 300.0)) for i in range(161)],
        "Fever Time": [float(1 + (i / 250.0)) for i in range(161)],
    })
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
    _prebuild_timeline_cache(song, curves, tmp_path, monkeypatch)

    assert score_stats_exact_batch(stats_rows, song, curves) == [
        score_stats_exact(stats, song, curves) for stats in stats_rows
    ]
