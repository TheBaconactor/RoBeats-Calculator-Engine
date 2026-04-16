import numpy as np
import pytest

pytestmark = pytest.mark.gpu


def _mock_song(*, name: str, n_notes: int = 16, duration: float = 60.0) -> dict:
    timestamps = np.linspace(0.0, float(duration), int(n_notes), dtype=np.float32)
    return {
        "metadata": {
            "Song Name": name,
            "Difficulty": "Hard",
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": float(timestamps[-1]),
            "Total Notes": int(timestamps.shape[0]),
        },
        "song_data": {"timestamps": timestamps, "note_types": np.ones(int(timestamps.shape[0]), dtype=np.int16)},
    }


def _ref_arrays(rows: int) -> dict:
    # Force a sharp breakpoint on Perfect Points so tier deltas can reorder entries.
    pp = np.zeros(rows, dtype=np.float64)
    pp[110:] = 1000.0
    return {
        "Perfect Points": pp,
        "Combo Multiplier": np.ones(rows, dtype=np.float64),
        "Fever Multiplier": np.ones(rows, dtype=np.float64),
        "Fever Fill Rate": np.ones(rows, dtype=np.float64),
        "Fever Time": np.ones(rows, dtype=np.float64),
    }


def test_team_buff_tier_postprocess_reorders_top_entries_across_tiers():
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.helpers.song_helpers.team_buff_tiers import compute_team_buff_tier_leaderboards

    calc_song = _mock_song(name="pytest_team_buff_tiers", n_notes=12)
    ref_arrays = _ref_arrays(TOTAL_ROWS + 1)
    cfg_dict = {"TeamContributionBuffConstant": {"TeamBuff": "T5", "TeamColor": "Rush"}}

    # Stats here are assumed to already include the base TeamBuff=T5.
    # Under T20, PP decreases by 10 vs T5, pushing Entry A below the PP breakpoint
    # while keeping Entry B at/above it, which should flip the ordering.
    stats_a = {
        "Perfect Points": 119,  # T20 => 109 (below breakpoint), T5 => 119 (above)
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Rush": 200,
        "Flow": 0,
        "Beat": 0,
        "Vibe": 0,
        "Chill": 0,
    }
    stats_b = {
        "Perfect Points": 120,  # T20 => 110 (at breakpoint), T5 => 120 (above)
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Rush": 199,
        "Flow": 0,
        "Beat": 0,
        "Vibe": 0,
        "Chill": 0,
    }

    entry_a = {
        "score": 1,
        "fg_score": 1,
        "gear": ["A1", "A2", "A3", "A4", "A5", "A6"],
        "minis": ["A7", "A8", "A9"],
        "details": {"Stats": stats_a},
        "force": {
            "details": {
                "Stats": stats_a,
                "ForceGreats": {"mode": "manual", "config": {"NonFever1": 1}},
            }
        },
    }
    entry_b = {
        "score": 1,
        "fg_score": 1,
        "gear": ["B1", "B2", "B3", "B4", "B5", "B6"],
        "minis": ["B7", "B8", "B9"],
        "details": {"Stats": stats_b},
        "force": None,
    }

    out = compute_team_buff_tier_leaderboards(
        entries=[entry_a, entry_b], calc_song=calc_song, ref_arrays=ref_arrays, cfg_dict=cfg_dict
    )
    tiers = out["tiers"]

    assert "NONE" in tiers
    assert tiers["T5"]["base_top51"][0]["gear"] == entry_a["gear"]
    assert tiers["T20"]["base_top51"][0]["gear"] == entry_b["gear"]


def test_team_buff_tiers_auto_mode_uses_primary_color_and_t5_base():
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.helpers.song_helpers.team_buff_tiers import compute_team_buff_tier_leaderboards

    # Primary/secondary determine scoring contribution; TeamColor should follow Primary in auto mode.
    calc_song = {
        "metadata": {
            "Song Name": "pytest_team_buff_auto_mode",
            "Difficulty": "Hard",
            "Primary Color": "Vibe",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": 10.0,
            "Total Notes": 12,
        },
        "song_data": {
            "timestamps": np.linspace(0.0, 10.0, 12, dtype=np.float32),
            "note_types": np.ones(12, dtype=np.int16),
        },
    }
    ref_arrays = _ref_arrays(TOTAL_ROWS + 1)

    # NOTE: cfg_dict intentionally lies about TeamBuff/TeamColor. In runtime auto mode, we override to:
    # - TeamBuff=T5
    # - TeamColor=Primary Color
    cfg_dict = {
        "IterationEngine": {"AutoSelectBuffAndColor": "true"},
        "TeamContributionBuffConstant": {"TeamBuff": "T20", "TeamColor": "Rush"},
    }

    # Stats represent the base run under auto TeamBuff=T5 + TeamColor=Vibe already applied.
    # Under T1 (vs base T5), Vibe should increase by +5 which should increase score.
    stats = {
        "Perfect Points": 25,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Vibe": 130,
        "Flow": 10,
    }
    entry = {
        "score": 0,
        "fg_score": 0,
        "gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
        "minis": ["M1", "M2", "M3"],
        "details": {"Stats": stats},
        "force": None,
    }

    out = compute_team_buff_tier_leaderboards(
        entries=[entry],
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        cfg_dict=cfg_dict,
        tiers=("T5", "T1"),
    )
    assert out["meta"]["team_color"] == "Vibe"
    assert out["meta"]["base_team_buff"] == "T5"

    t5_score = out["tiers"]["T5"]["base_top51"][0]["score"]
    t1_score = out["tiers"]["T1"]["base_top51"][0]["score"]
    assert t1_score > t5_score


def test_build_team_buff_tier_db_batches_preserves_identity_and_repairs_corrupt_minis():
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.helpers.song_helpers.team_buff_tiers import build_team_buff_tier_db_batches

    calc_song = _mock_song(name="pytest_team_buff_batches", n_notes=12)
    ref_arrays = _ref_arrays(TOTAL_ROWS + 1)
    cfg_dict = {"TeamContributionBuffConstant": {"TeamBuff": "T5", "TeamColor": "Rush"}}

    stats = {
        "Perfect Points": 120,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Rush": 200,
        "Flow": 0,
        "Beat": 0,
        "Vibe": 0,
        "Chill": 0,
    }

    entry = {
        "score": 1,
        "fg_score": 0,
        "gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
        # Corrupted minis sometimes show up as strings like "['Name']" inside persisted mini variant groups.
        "minis": [["['M1']"], ["M2"], ["M3"]],
        "details": {"Stats": stats},
        "force": None,
    }

    batches = build_team_buff_tier_db_batches(
        entries=[entry],
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        cfg_dict=cfg_dict,
        limit=1,
        tiers=("T5",),
    )

    assert "T5" in batches
    assert len(batches["T5"]) == 1
    out = batches["T5"][0]
    assert out["gear"] == entry["gear"]
    assert out["minis"] == ["M1", "M2", "M3"]


def test_team_buff_tiers_handle_stats_missing_base_team_buff_without_negative_pp():
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.helpers.song_helpers.team_buff_tiers import build_team_buff_tier_db_batches

    calc_song = _mock_song(name="pytest_team_buff_missing_base_effect", n_notes=12)
    ref_arrays = _ref_arrays(TOTAL_ROWS + 1)

    # Auto mode => base TeamBuff is T5 + TeamColor follows Primary (Rush).
    cfg_dict = {"IterationEngine": {"AutoSelectBuffAndColor": "true"}}

    # Stats here are intentionally loadout-only (missing base T5 effect).
    stats = {
        "Perfect Points": 0,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Rush": 10,
        "Flow": 0,
        "Beat": 0,
        "Vibe": 0,
        "Chill": 0,
    }

    entry = {
        "score": 1,
        "fg_score": 2,
        "gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
        "minis": ["M1", "M2", "M3"],
        "details": {"Stats": stats},
        # Flat force payload as stored in DB; BaseStats also missing base effect to emulate repaired rows.
        "force": {"BaseStats": stats, "GemCounts": {"Perfect Points": 0}, "ForceGreats": {"config": {"NonFever1": 1}}},
    }

    batches = build_team_buff_tier_db_batches(
        entries=[entry],
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        cfg_dict=cfg_dict,
        limit=1,
        tiers=("NONE", "T5", "T10", "T20", "T50", "T51"),
    )

    # All produced Stats should be non-negative PP.
    for tier in ("NONE", "T5", "T10", "T20", "T50", "T51"):
        out = batches[tier][0]
        pp = out["details"]["Stats"]["Perfect Points"]
        assert pp >= 0


def test_team_buff_tiers_support_target_team_color_overrides():
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.helpers.song_helpers.team_buff_tiers import build_team_buff_tier_db_batches

    calc_song = _mock_song(name="pytest_team_color_modes", n_notes=12)
    ref_arrays = _ref_arrays(TOTAL_ROWS + 1)
    cfg_dict = {"TeamContributionBuffConstant": {"TeamBuff": "T5", "TeamColor": "Rush"}}

    # Baseline row already includes T5 + Primary(Rush) effect.
    stats = {
        "Perfect Points": 25,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Rush": 130,  # includes +30 from T5 primary buff
        "Flow": 10,
        "Beat": 0,
        "Vibe": 0,
        "Chill": 0,
    }
    entry = {
        "score": 0,
        "fg_score": 0,
        "gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
        "minis": ["M1", "M2", "M3"],
        "details": {"Stats": stats},
        "force": None,
    }

    primary_batches = build_team_buff_tier_db_batches(
        entries=[entry],
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        cfg_dict=cfg_dict,
        tiers=("T5",),
    )
    secondary_batches = build_team_buff_tier_db_batches(
        entries=[entry],
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        cfg_dict=cfg_dict,
        tiers=("T5",),
        target_team_color_override="Flow",
    )
    none_batches = build_team_buff_tier_db_batches(
        entries=[entry],
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        cfg_dict=cfg_dict,
        tiers=("T5",),
        target_team_color_override="",
    )

    p = primary_batches["T5"][0]
    s = secondary_batches["T5"][0]
    n = none_batches["T5"][0]

    assert p["score"] > s["score"] > n["score"]

    s_stats = s["details"]["Stats"]
    n_stats = n["details"]["Stats"]
    assert s_stats["Rush"] == 100
    assert s_stats["Flow"] == 40
    assert n_stats["Rush"] == 100
    assert n_stats["Flow"] == 10


def test_team_buff_tiers_apply_tier_deltas_to_fg_score():
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.helpers.song_helpers.team_buff_tiers import compute_team_buff_tier_leaderboards

    calc_song = _mock_song(name="pytest_team_buff_fg_tiered", n_notes=24)
    ref_arrays = _ref_arrays(TOTAL_ROWS + 1)
    cfg_dict = {"TeamContributionBuffConstant": {"TeamBuff": "T5", "TeamColor": "Rush"}}

    stats = {
        "Perfect Points": 120,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Rush": 200,
        "Flow": 0,
        "Beat": 0,
        "Vibe": 0,
        "Chill": 0,
    }
    entry = {
        "score": 0,
        "fg_score": 0,
        "gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
        "minis": ["M1", "M2", "M3"],
        "details": {"Stats": stats},
        "force": {"BaseStats": stats, "GemCounts": {"Perfect Points": 0}, "ForceGreats": {"config": {"NonFever1": 1}}},
    }

    out = compute_team_buff_tier_leaderboards(
        entries=[entry],
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        cfg_dict=cfg_dict,
        tiers=("T5", "T51"),
    )

    t5 = out["tiers"]["T5"]["base_top51"][0]
    t51 = out["tiers"]["T51"]["base_top51"][0]

    assert t5["score"] != t51["score"]
    assert t5["fg_score"] != t51["fg_score"]


def test_team_buff_tier_postprocess_uses_source_fg_base_score_for_fg_inclusion(monkeypatch):
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.helpers.song_helpers.team_buff_tiers import compute_team_buff_tier_leaderboards

    calc_song = _mock_song(name="pytest_team_buff_fg_base_context", n_notes=12)
    ref_arrays = _ref_arrays(TOTAL_ROWS + 1)
    cfg_dict = {"TeamContributionBuffConstant": {"TeamBuff": "T5", "TeamColor": "Rush"}}

    stats = {
        "Perfect Points": 100,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Rush": 150,
        "Flow": 0,
        "Beat": 0,
        "Vibe": 0,
        "Chill": 0,
    }
    entry = {
        "score": 100,
        "fg_score": 95,
        "fg_base_score": 90,
        "gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
        "minis": ["M1", "M2", "M3"],
        "details": {"Stats": dict(stats)},
        "force": {
            "Stats": dict(stats),
            "ForceGreats": {"config": {"NonFever1": 1}},
        },
    }

    def _fake_score_fixed_stats_gpu(base_inputs, _group_song, *, ref_arrays=None):
        assert len(base_inputs) == 1
        return np.asarray([110], dtype=np.int32)

    def _fake_solve_force_greats_finder_gpu(
        genomes,
        timestamps,
        great_timestamps,
        long_notes,
        last_note_time,
        counts,
        offsets,
        **kwargs,
    ):
        assert len(genomes) == 1
        assert counts
        return {"final_score": np.asarray([95], dtype=np.int32)}

    monkeypatch.setattr(
        "gear_optimizer.solver.taichi_gem.api.fixed_scoring.score_fixed_stats_gpu",
        _fake_score_fixed_stats_gpu,
    )
    monkeypatch.setattr(
        "gear_optimizer.solver.taichi_gem.force_greats.api.solve_force_greats_finder_gpu",
        _fake_solve_force_greats_finder_gpu,
    )

    out = compute_team_buff_tier_leaderboards(
        entries=[entry],
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        cfg_dict=cfg_dict,
        tiers=("T5",),
        limit=1,
    )

    tier = out["tiers"]["T5"]
    assert tier["base_top51"][0]["score"] == 110
    assert tier["base_top51"][0]["fg_score"] == 95
    assert len(tier["fg_top51"]) == 1
    assert tier["fg_top51"][0]["fg_score"] == 95
    assert tier["fg_top51"][0]["fg_base_score"] == 90
    assert tier["fg_top51"][0]["score"] == 110


@pytest.mark.parametrize("tier_name", ["NONE", "T1", "T10", "T20", "T50", "T51"])
def test_team_buff_tier_postprocess_derived_tier_fg_visibility_uses_replayed_base_score(monkeypatch, tier_name: str):
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.helpers.song_helpers.team_buff_tiers import compute_team_buff_tier_leaderboards

    calc_song = _mock_song(name=f"pytest_team_buff_derived_fg_visibility_{tier_name}", n_notes=12)
    ref_arrays = _ref_arrays(TOTAL_ROWS + 1)
    cfg_dict = {"TeamContributionBuffConstant": {"TeamBuff": "T5", "TeamColor": "Rush"}}

    stats = {
        "Perfect Points": 100,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Rush": 150,
        "Flow": 0,
        "Beat": 0,
        "Vibe": 0,
        "Chill": 0,
    }
    entry = {
        "score": 100,
        "fg_score": 95,
        "fg_base_score": 130,
        "gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
        "minis": ["M1", "M2", "M3"],
        "details": {"Stats": dict(stats)},
        "force": {
            "Stats": dict(stats),
            "ForceGreats": {"config": {"NonFever1": 1}},
        },
    }

    def _fake_score_fixed_stats_gpu(base_inputs, _group_song, *, ref_arrays=None):
        assert len(base_inputs) == 1
        return np.asarray([110], dtype=np.int32)

    def _fake_solve_force_greats_finder_gpu(
        genomes,
        timestamps,
        great_timestamps,
        long_notes,
        last_note_time,
        counts,
        offsets,
        **kwargs,
    ):
        assert len(genomes) == 1
        assert counts
        return {"final_score": np.asarray([120], dtype=np.int32)}

    monkeypatch.setattr(
        "gear_optimizer.solver.taichi_gem.api.fixed_scoring.score_fixed_stats_gpu",
        _fake_score_fixed_stats_gpu,
    )
    monkeypatch.setattr(
        "gear_optimizer.solver.taichi_gem.force_greats.api.solve_force_greats_finder_gpu",
        _fake_solve_force_greats_finder_gpu,
    )

    out = compute_team_buff_tier_leaderboards(
        entries=[entry],
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        cfg_dict=cfg_dict,
        tiers=(tier_name,),
        limit=1,
    )

    tier = out["tiers"][tier_name]
    assert tier["base_top51"][0]["score"] == 110
    assert tier["base_top51"][0]["fg_score"] == 120
    assert len(tier["fg_top51"]) == 1
    assert tier["fg_top51"][0]["fg_score"] == 120
    assert tier["fg_top51"][0]["fg_base_score"] == 110
    assert tier["fg_top51"][0]["source_fg_base_score"] == 130
    assert tier["fg_top51"][0]["score"] == 110


def test_team_buff_tier_postprocess_fg_scoring_matches_gpu_force_greats_kernel():
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.helpers.song_helpers.team_buff_tiers import compute_team_buff_tier_leaderboards
    from gear_optimizer.solver.scoring.gpu_solver import _GPU_LOCK
    from gear_optimizer.solver.taichi_gem.force_greats.api import solve_force_greats_finder_gpu

    calc_song = _mock_song(name="pytest_team_buff_fg_kernel_match", n_notes=24)
    ref_arrays = _ref_arrays(TOTAL_ROWS + 1)
    cfg_dict = {"TeamContributionBuffConstant": {"TeamBuff": "NONE", "TeamColor": "Rush"}}

    stats = {
        "Perfect Points": 120,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Rush": 200,
        "Flow": 0,
        "Beat": 0,
        "Vibe": 0,
        "Chill": 0,
    }
    entry = {
        "score": 0,
        "fg_score": 0,
        "gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
        "minis": ["M1", "M2", "M3"],
        "details": {"Stats": stats},
        # Flat force payload as stored in DB.
        "force": {"BaseStats": stats, "GemCounts": {"Perfect Points": 0}, "ForceGreats": {"config": {"NonFever1": 1}}},
    }

    out = compute_team_buff_tier_leaderboards(
        entries=[entry],
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        cfg_dict=cfg_dict,
        tiers=("NONE",),
    )
    got = int(out["tiers"]["NONE"]["base_top51"][0]["fg_score"])

    timestamps_np = calc_song["song_data"]["timestamps"]
    meta = calc_song["metadata"]
    with _GPU_LOCK:
        expected_raw = solve_force_greats_finder_gpu(
            [
                {
                    "base_pp": int(stats["Perfect Points"]),
                    "base_cm": int(stats["Combo Multiplier"]),
                    "base_fm": int(stats["Fever Multiplier"]),
                    "base_ft_stat": int(stats["Fever Time"]),
                    "base_ff_stat": int(stats["Fever Fill Rate"]),
                    "base_p_val": int(stats["Rush"]),
                    "base_s_val": int(stats["Flow"]),
                }
            ],
            timestamps_np,
            None,
            int(meta.get("Long Notes", 0) or 0),
            float(meta.get("Last Note Time", float(timestamps_np[-1]))),
            [(1,)],
            [(0, 0)],
            n_sections=1,
            is_p_ft=0,
            is_s_ft=0,
            is_p_ff=0,
            is_s_ff=0,
            is_p_pp=0,
            is_s_pp=0,
            is_p_cm=0,
            is_s_cm=0,
            is_p_fm=0,
            is_s_fm=0,
            is_p_ov=0,
            is_s_ov=0,
            ref_arrays=ref_arrays,
            total_budget=0,
            return_raw=True,
        )

    assert isinstance(expected_raw, dict)
    expected = int(expected_raw["final_score"][0])
    assert got == expected


def test_team_buff_tier_postprocess_converts_persisted_forced_counts_back_to_fp_targets():
    import math

    from gear_optimizer.app_async_db import _get_team_buff_ref_arrays_cached
    from gear_optimizer.core.constants import FEVER_FILL_BASE_RATE, TOTAL_ROWS
    from gear_optimizer.helpers.song_helpers.team_buff_tiers import compute_team_buff_tier_leaderboards
    from gear_optimizer.solver.scoring.gpu_solver import _GPU_LOCK
    from gear_optimizer.solver.scoring_core import lookup_reference_py
    from gear_optimizer.solver.taichi_gem.force_greats.api import solve_force_greats_finder_gpu

    ref_arrays = _get_team_buff_ref_arrays_cached()
    assert isinstance(ref_arrays, dict) and ref_arrays

    timestamps = np.linspace(0.0, 192.01, 1631, dtype=np.float32)
    calc_song = {
        "metadata": {
            "Song Name": "pytest_team_buff_forced_counts_fp_targets",
            "Difficulty": "18",
            "Primary Color": "Beat",
            "Secondary Color": "Beat",
            "Long Notes": 364,
            "Last Note Time": float(timestamps[-1]),
            "Total Notes": int(timestamps.shape[0]),
        },
        "song_data": {
            "timestamps": timestamps,
            "note_types": np.ones(int(timestamps.shape[0]), dtype=np.int16),
        },
    }
    stats = {
        "Perfect Points": 25,
        "Combo Multiplier": 52,
        "Fever Multiplier": 68,
        "Fever Fill Rate": 53,
        "Fever Time": 40,
        "Beat": 769,
        "Vibe": 71,
        "Rush": 12,
        "Flow": 83,
        "Chill": 0,
    }
    forced_counts = (0, 2, 0)
    entry = {
        "score": 0,
        "fg_score": 0,
        "gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
        "minis": ["M1", "M2", "M3"],
        "details": {"Stats": dict(stats)},
        "force": {
            "Stats": dict(stats),
            "ForceGreats": {"config": {"NonFever1": 0, "NonFever2": 2, "NonFever3": 0}},
        },
    }

    out = compute_team_buff_tier_leaderboards(
        entries=[entry],
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        cfg_dict={"TeamContributionBuffConstant": {"TeamBuff": "T5", "TeamColor": "Beat"}},
        tiers=("T5",),
        limit=1,
    )
    got = int(out["tiers"]["T5"]["base_top51"][0]["fg_score"])

    raw_fill = max(0.0, float(int(timestamps.shape[0]) - 364) * float(FEVER_FILL_BASE_RATE)) * float(
        lookup_reference_py(int(stats["Fever Fill Rate"]), ref_arrays["Fever Fill Rate"], TOTAL_ROWS)
    )
    fp_targets = tuple(
        max(0, int(math.ceil(raw_fill + (int(forced) * 0.5)) - math.ceil(raw_fill))) for forced in forced_counts
    )

    genome = [
        {
            "base_pp": int(stats["Perfect Points"]),
            "base_cm": int(stats["Combo Multiplier"]),
            "base_fm": int(stats["Fever Multiplier"]),
            "base_ft_stat": int(stats["Fever Time"]),
            "base_ff_stat": int(stats["Fever Fill Rate"]),
            "base_p_val": int(stats["Beat"]),
            "base_s_val": int(stats["Beat"]),
        }
    ]
    with _GPU_LOCK:
        expected_raw = solve_force_greats_finder_gpu(
            genome,
            timestamps,
            None,
            int(calc_song["metadata"]["Long Notes"]),
            float(calc_song["metadata"]["Last Note Time"]),
            [forced_counts],
            [(0, 0)],
            n_sections=3,
            is_p_ft=0,
            is_s_ft=0,
            is_p_ff=0,
            is_s_ff=0,
            is_p_pp=0,
            is_s_pp=0,
            is_p_cm=0,
            is_s_cm=0,
            is_p_fm=0,
            is_s_fm=0,
            is_p_ov=0,
            is_s_ov=0,
            ref_arrays=ref_arrays,
            total_budget=0,
            return_raw=True,
        )
        expected_fp = solve_force_greats_finder_gpu(
            genome,
            timestamps,
            None,
            int(calc_song["metadata"]["Long Notes"]),
            float(calc_song["metadata"]["Last Note Time"]),
            [fp_targets],
            [(0, 0)],
            n_sections=3,
            is_p_ft=0,
            is_s_ft=0,
            is_p_ff=0,
            is_s_ff=0,
            is_p_pp=0,
            is_s_pp=0,
            is_p_cm=0,
            is_s_cm=0,
            is_p_fm=0,
            is_s_fm=0,
            is_p_ov=0,
            is_s_ov=0,
            ref_arrays=ref_arrays,
            total_budget=0,
            return_raw=True,
        )

    assert isinstance(expected_raw, dict)
    assert isinstance(expected_fp, dict)
    assert tuple(fp_targets) == (0, 1, 0)
    assert got == int(expected_fp["final_score"][0])
    assert got != int(expected_raw["final_score"][0])


def test_build_team_buff_tier_db_batches_preserves_fg_base_score_from_fg_top_rows(monkeypatch):
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.helpers.song_helpers.team_buff_tiers import build_team_buff_tier_db_batches

    calc_song = _mock_song(name="pytest_team_buff_fg_batch_ctx", n_notes=12)
    ref_arrays = _ref_arrays(TOTAL_ROWS + 1)
    cfg_dict = {"TeamContributionBuffConstant": {"TeamBuff": "T5", "TeamColor": "Rush"}}

    stats = {
        "Perfect Points": 100,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Rush": 150,
        "Flow": 0,
        "Beat": 0,
        "Vibe": 0,
        "Chill": 0,
    }
    entry = {
        "score": 100,
        "fg_score": 95,
        "fg_base_score": 90,
        "gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
        "minis": ["M1", "M2", "M3"],
        "details": {"Stats": dict(stats)},
        "force": {
            "Stats": dict(stats),
            "ForceGreats": {"config": {"NonFever1": 1}},
        },
    }

    def _fake_compute_team_buff_tier_leaderboards(**kwargs):
        return {
            "meta": {"base_team_buff": "T5", "team_color": "Rush", "primary_color": "Rush", "secondary_color": "Flow"},
            "tiers": {
                "T5": {
                    "base_top51": [
                        {
                            "gear": list(entry["gear"]),
                            "minis": list(entry["minis"]),
                            "score": 110,
                            "fg_score": 95,
                        }
                    ],
                    "fg_top51": [
                        {
                            "gear": list(entry["gear"]),
                            "minis": list(entry["minis"]),
                            "score": 110,
                            "fg_score": 95,
                            "fg_base_score": 90,
                            "force_config": {"NonFever1": 1},
                        }
                    ],
                }
            },
        }

    monkeypatch.setattr(
        "gear_optimizer.helpers.song_helpers.team_buff_tiers.compute_team_buff_tier_leaderboards",
        _fake_compute_team_buff_tier_leaderboards,
    )

    batches = build_team_buff_tier_db_batches(
        entries=[entry],
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        cfg_dict=cfg_dict,
        tiers=("T5",),
        limit=1,
    )

    row = batches["T5"][0]
    assert row["score"] == 110
    assert row["fg_score"] == 95
    assert row["fg_base_score"] == 90
    assert row["gear"] == entry["gear"]
    assert row["minis"] == entry["minis"]
    assert row["force"]["ForceGreats"]["config"] == {"NonFever1": 1}


def test_team_buff_tier_leaderboards_respects_persisted_hitsim_seed(monkeypatch):
    import gear_optimizer.solver.hit_simulation as hs
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.helpers.song_helpers.team_buff_tiers import compute_team_buff_tier_leaderboards

    calls: list[int] = []

    def _fake_apply(calc_song, *, cfg_dict):
        cfg = cfg_dict.get("HumanHitSim") if isinstance(cfg_dict, dict) else None
        seed = int((cfg or {}).get("Seed", 0) or 0)
        calls.append(int(seed))
        # Minimal "applied" markers; score correctness is tested elsewhere.
        meta = calc_song.get("metadata", {}) or {}
        meta["HumanHitSimApplied"] = True
        meta["HumanHitSimSeed"] = int(seed)
        meta["HumanHitSimApplyTo"] = str((cfg or {}).get("ApplyTo", "FG") or "FG").strip().upper()
        calc_song["metadata"] = meta
        song_data = calc_song.get("song_data", {}) or {}
        if song_data.get("fg_timestamps") is None:
            song_data["fg_timestamps"] = song_data.get("timestamps")
        calc_song["song_data"] = song_data
        return {"seed": int(seed)}

    monkeypatch.setattr(hs, "apply_human_hit_sim", _fake_apply)

    calc_song = _mock_song(name="pytest_hitsim_ctx", n_notes=12)
    ref_arrays = _ref_arrays(TOTAL_ROWS + 1)
    cfg_dict = {"TeamContributionBuffConstant": {"TeamBuff": "T5", "TeamColor": "Rush"}}

    stats = {
        "Perfect Points": 120,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Rush": 200,
        "Flow": 0,
        "Beat": 0,
        "Vibe": 0,
        "Chill": 0,
    }

    entry_a = {
        "score": 0,
        "fg_score": 0,
        "gear": ["A1", "A2", "A3", "A4", "A5", "A6"],
        "minis": ["A7", "A8", "A9"],
        "details": {"Stats": stats, "hs": [111, 0, 0, 0]},
        "force": None,
    }
    entry_b = {
        "score": 0,
        "fg_score": 0,
        "gear": ["B1", "B2", "B3", "B4", "B5", "B6"],
        "minis": ["B7", "B8", "B9"],
        "details": {"Stats": stats, "hs": [222, 0, 0, 0]},
        "force": None,
    }

    compute_team_buff_tier_leaderboards(
        entries=[entry_a, entry_b],
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        cfg_dict=cfg_dict,
        tiers=("T5",),
    )

    assert sorted(calls) == [111, 222]


def test_team_buff_tier_postprocess_base_scoring_matches_gpu_fixed_scoring(monkeypatch):
    """
    Regression test: CPU fixed scoring can diverge from production GPU scoring due to
    the analytical ceiling HitSim timeline path. Tier postprocess must match GPU.
    """
    from gear_optimizer.app_async_db import _get_team_buff_ref_arrays_cached
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.helpers.song_helpers.team_buff_tiers import compute_team_buff_tier_leaderboards
    from gear_optimizer.solver.scoring.stats_scoring import evaluate_stats_score
    from gear_optimizer.solver.scoring_core import lookup_reference_py
    from gear_optimizer.solver.taichi_gem.api.fixed_scoring import score_fixed_stats_gpu

    # Enable the ceiling kernel (tests default it off for most of the suite).
    monkeypatch.setenv("GPU_TIMELINE_CEILING_HITSIM", "1")

    ref_arrays = _get_team_buff_ref_arrays_cached()
    assert isinstance(ref_arrays, dict) and ref_arrays

    # Minimal 12-note prefix extracted from a real chart known to trigger CPU/GPU divergence.
    timestamps = np.asarray(
        [
            0.023000000044703484,
            0.023000000044703484,
            0.023000000044703484,
            0.16899999976158142,
            0.3149999976158142,
            0.3149999976158142,
            0.3149999976158142,
            0.4620000123977661,
            0.6079999804496765,
            0.6079999804496765,
            0.7540000081062317,
            0.9010000228881836,
        ],
        dtype=np.float32,
    )
    calc_song = {
        "metadata": {
            "Song Name": "pytest_gpu_fixed_scoring_regression",
            "Difficulty": "Hard",
            "Primary Color": "Vibe",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": float(timestamps[-1]),
            "Total Notes": int(timestamps.shape[0]),
        },
        "song_data": {"timestamps": timestamps, "note_types": np.ones(int(timestamps.shape[0]), dtype=np.int16)},
    }

    stats = {
        "Perfect Points": 25,
        "Combo Multiplier": 53,
        "Fever Multiplier": 68,
        "Fever Fill Rate": 60,
        "Fever Time": 58,
        "Vibe": 616,
        "Flow": 136,
        "Rush": 60,
        "Beat": 33,
        "Chill": 49,
    }

    cpu = int(evaluate_stats_score(stats, calc_song, ref_arrays))

    primary = calc_song["metadata"]["Primary Color"]
    secondary = calc_song["metadata"]["Secondary Color"]
    pp_factor = lookup_reference_py(int(stats["Perfect Points"]), ref_arrays["Perfect Points"], TOTAL_ROWS)
    base_value = (int(stats.get(primary, 0)) * 2) + int(stats.get(secondary, 0)) + float(pp_factor)
    combo_mul = float(lookup_reference_py(int(stats["Combo Multiplier"]), ref_arrays["Combo Multiplier"], TOTAL_ROWS))
    fever_mul = float(lookup_reference_py(int(stats["Fever Multiplier"]), ref_arrays["Fever Multiplier"], TOTAL_ROWS))
    ft_idx = int(stats["Fever Time"])
    ff_idx = int(stats["Fever Fill Rate"])
    gpu = int(
        score_fixed_stats_gpu(
            [
                {
                    "base_value": float(base_value),
                    "combo_mul": float(combo_mul),
                    "fever_mul": float(fever_mul),
                    "ft_idx": int(ft_idx),
                    "ff_idx": int(ff_idx),
                }
            ],
            calc_song,
            ref_arrays=ref_arrays,
        )[0]
    )

    assert cpu != gpu

    entry = {
        "score": 0,
        "fg_score": 0,
        "gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
        "minis": ["M1", "M2", "M3"],
        "details": {"Stats": stats},
        "force": None,
    }
    cfg_dict = {
        "IterationEngine": {"AutoSelectBuffAndColor": "false"},
        "TeamContributionBuffConstant": {"TeamBuff": "T5", "TeamColor": "Vibe"},
    }

    out = compute_team_buff_tier_leaderboards(
        entries=[entry],
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        cfg_dict=cfg_dict,
        tiers=("T5",),
        limit=1,
    )

    scored = int(out["tiers"]["T5"]["base_top51"][0]["score"])
    assert scored == gpu
    assert scored != cpu
