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
                "ForceGreats": {"config": {"NonFever1": 1}},
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
        "IterationEngine": {},
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


def test_build_team_buff_tier_db_batches_keeps_stable_row_order_for_mixed_base_and_fg_rows(monkeypatch):
    from gear_optimizer.helpers.song_helpers.team_buff_tiers import build_team_buff_tier_db_batches

    calc_song = _mock_song(name="pytest_team_buff_row_order", n_notes=12)
    ref_arrays = _ref_arrays(11)
    cfg_dict = {"TeamContributionBuffConstant": {"TeamBuff": "T5", "TeamColor": "Rush"}}

    stats = {
        "Perfect Points": 100,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Rush": 0,
        "Flow": 0,
        "Beat": 0,
        "Vibe": 0,
        "Chill": 0,
    }

    entries = [
        {"score": 1, "fg_score": 0, "gear": ["B"], "minis": ["M2"], "details": {"Stats": stats}, "force": None},
        {"score": 2, "fg_score": 0, "gear": ["A"], "minis": ["M1"], "details": {"Stats": stats}, "force": None},
        {"score": 3, "fg_score": 0, "gear": ["C"], "minis": ["M3"], "details": {"Stats": stats}, "force": None},
    ]

    def fake_compute_team_buff_tier_leaderboards(**kwargs):
        return {
            "meta": {"base_team_buff": "T5", "team_color": "Rush", "primary_color": "Rush", "secondary_color": "Flow"},
            "tiers": {
                "T5": {
                    "base_top51": [
                        {"gear": ["B"], "minis": ["M2"], "score": 20, "fg_score": 0},
                        {"gear": ["A"], "minis": ["M1"], "score": 10, "fg_score": 0},
                    ],
                    "fg_top51": [
                        {"gear": ["C"], "minis": ["M3"], "score": 30, "fg_score": 40, "fg_base_score": 15},
                    ],
                }
            },
        }

    monkeypatch.setattr(
        "gear_optimizer.helpers.song_helpers.team_buff_tiers.compute_team_buff_tier_leaderboards",
        fake_compute_team_buff_tier_leaderboards,
    )

    batches = build_team_buff_tier_db_batches(
        entries=entries,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        cfg_dict=cfg_dict,
        limit=3,
        tiers=("T5",),
    )

    assert [row["gear"][0] for row in batches["T5"]] == ["B", "A", "C"]


def test_team_buff_tiers_handle_stats_missing_base_team_buff_without_negative_pp():
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.helpers.song_helpers.team_buff_tiers import build_team_buff_tier_db_batches

    calc_song = _mock_song(name="pytest_team_buff_missing_base_effect", n_notes=12)
    ref_arrays = _ref_arrays(TOTAL_ROWS + 1)

    # Auto mode => base TeamBuff is T5 + TeamColor follows Primary (Rush).
    cfg_dict = {"IterationEngine": {}}

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
    from gear_optimizer.solver.scoring.exact_rescore import evaluate_force_greats_exact, score_stats_exact

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

    expected_base = int(score_stats_exact(stats, calc_song, ref_arrays))
    expected_fg = int(evaluate_force_greats_exact(stats, calc_song, ref_arrays, [1])["final_score"])

    out = compute_team_buff_tier_leaderboards(
        entries=[entry],
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        cfg_dict=cfg_dict,
        tiers=("T5",),
        limit=1,
    )

    tier = out["tiers"]["T5"]
    assert tier["base_top51"][0]["score"] == expected_base
    assert tier["base_top51"][0]["fg_score"] == expected_fg
    assert len(tier["fg_top51"]) == 1
    assert tier["fg_top51"][0]["fg_score"] == expected_fg
    assert tier["fg_top51"][0]["fg_base_score"] == 90
    assert tier["fg_top51"][0]["score"] == expected_base


@pytest.mark.parametrize("tier_name", ["NONE", "T1", "T10", "T20", "T50", "T51"])
def test_team_buff_tier_postprocess_derived_tier_fg_visibility_uses_replayed_base_score(monkeypatch, tier_name: str):
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.core.team_buff import team_buff_effect
    from gear_optimizer.helpers.song_helpers.team_buff_tiers import compute_team_buff_tier_leaderboards
    from gear_optimizer.solver.scoring.exact_rescore import evaluate_force_greats_exact, score_stats_exact

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

    base_effect = team_buff_effect("T5", "Rush")
    target_effect = team_buff_effect(tier_name, "Rush")
    tier_stats = dict(stats)
    for key in set(base_effect) | set(target_effect):
        tier_stats[key] = int(tier_stats.get(key, 0)) + int(target_effect.get(key, 0)) - int(base_effect.get(key, 0))
    expected_base = int(score_stats_exact(tier_stats, calc_song, ref_arrays))
    expected_fg = int(evaluate_force_greats_exact(tier_stats, calc_song, ref_arrays, [1])["final_score"])

    out = compute_team_buff_tier_leaderboards(
        entries=[entry],
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        cfg_dict=cfg_dict,
        tiers=(tier_name,),
        limit=1,
    )

    tier = out["tiers"][tier_name]
    assert tier["base_top51"][0]["score"] == expected_base
    assert tier["base_top51"][0]["fg_score"] == expected_fg
    if expected_fg > expected_base:
        assert len(tier["fg_top51"]) == 1
        assert tier["fg_top51"][0]["fg_score"] == expected_fg
        assert tier["fg_top51"][0]["fg_base_score"] == expected_base
        assert tier["fg_top51"][0]["source_fg_base_score"] == 130
        assert tier["fg_top51"][0]["score"] == expected_base
    else:
        assert tier["fg_top51"] == []


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


def test_build_team_buff_tier_db_batches_preserves_source_fg_metadata_from_fg_top_rows(monkeypatch):
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.helpers.song_helpers.team_buff_tiers import build_team_buff_tier_db_batches

    calc_song = _mock_song(name="pytest_team_buff_fg_source_meta", n_notes=12)
    ref_arrays = _ref_arrays(TOTAL_ROWS + 1)
    cfg_dict = {"TeamContributionBuffConstant": {"TeamBuff": "T5", "TeamColor": "Rush"}}

    entry = {
        "score": 100,
        "fg_score": 95,
        "fg_base_score": 90,
        "gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
        "minis": ["M1", "M2", "M3"],
        "details": {"Stats": {}},
        "force": {"ForceGreats": {"config": {"NonFever1": 1}}},
    }

    def _fake_compute_team_buff_tier_leaderboards(**kwargs):
        return {
            "meta": {"base_team_buff": "T5", "team_color": "Rush", "primary_color": "Rush", "secondary_color": "Flow"},
            "tiers": {
                "T10": {
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
                            "fg_score": 120,
                            "fg_base_score": 110,
                            "source_score": 100,
                            "source_fg_base_score": 90,
                            "source_fg_score": 95,
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
        tiers=("T10",),
        limit=1,
    )

    row = batches["T10"][0]
    assert row["source_score"] == 100
    assert row["source_fg_base_score"] == 90
    assert row["source_fg_score"] == 95


def test_build_team_buff_tier_db_batches_strict_sanity_preserves_scores_and_target_team_color(monkeypatch):
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.core.team_buff import team_buff_effect
    from gear_optimizer.helpers.song_helpers.team_buff_tiers import build_team_buff_tier_db_batches

    calc_song = _mock_song(name="pytest_team_buff_strict_sanity", n_notes=12)
    ref_arrays = _ref_arrays(TOTAL_ROWS + 1)
    cfg_dict = {"TeamContributionBuffConstant": {"TeamBuff": "T5", "TeamColor": "Rush"}}

    stats = {
        "Perfect Points": 125,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Rush": 210,
        "Flow": 55,
        "Beat": 0,
        "Vibe": 0,
        "Chill": 0,
    }

    def _entry(loadout_hash: str, gear_name: str, mini_name: str, *, score: int, fg_score: int, fg_base_score: int) -> dict:
        return {
            "loadout_hash": loadout_hash,
            "score": score,
            "fg_score": fg_score,
            "fg_base_score": fg_base_score,
            "gear": [gear_name, "G2", "G3", "G4", "G5", "G6"],
            "minis": [mini_name, "M2", "M3"],
            "details": {
                "Stats": dict(stats),
                "SelectedElement": "Rush",
            },
            "force": {
                "Score": fg_score,
                "BaseStats": dict(stats),
                "ForceGreats": {
                    "config": {"NonFever1": 1},
                    "final_score": fg_score,
                },
            },
        }

    entry_a = _entry("hash-a", "GA", "MA", score=100, fg_score=120, fg_base_score=90)
    entry_b = _entry("hash-b", "GB", "MB", score=101, fg_score=0, fg_base_score=0)

    def _fake_compute_team_buff_tier_leaderboards(**kwargs):
        return {
            "meta": {"base_team_buff": "T5", "team_color": "Flow", "primary_color": "Rush", "secondary_color": "Flow"},
            "tiers": {
                "T20": {
                    "base_top51": [
                        {
                            "loadout_hash": entry_b["loadout_hash"],
                            "gear": list(entry_b["gear"]),
                            "minis": list(entry_b["minis"]),
                            "score": 330,
                            "fg_score": 0,
                            "source_score": 101,
                            "source_fg_score": 0,
                        },
                        {
                            "loadout_hash": entry_a["loadout_hash"],
                            "gear": list(entry_a["gear"]),
                            "minis": list(entry_a["minis"]),
                            "score": 320,
                            "fg_score": 120,
                            "source_score": 100,
                            "source_fg_score": 120,
                        },
                    ],
                    "fg_top51": [
                        {
                            "loadout_hash": entry_a["loadout_hash"],
                            "gear": list(entry_a["gear"]),
                            "minis": list(entry_a["minis"]),
                            "score": 320,
                            "fg_score": 350,
                            "fg_base_score": 320,
                            "source_score": 100,
                            "source_fg_base_score": 90,
                            "source_fg_score": 120,
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
        entries=[entry_a, entry_b],
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        cfg_dict=cfg_dict,
        tiers=("T20",),
        limit=2,
        target_team_color_override="Flow",
    )

    rows = batches["T20"]
    assert [str(row.get("loadout_hash") or "") for row in rows] == ["hash-b", "hash-a"]

    base_effect = team_buff_effect("T5", "Rush")
    target_effect = team_buff_effect("T20", "Flow")
    expected_delta_pp = int(target_effect.get("Perfect Points", 0) - base_effect.get("Perfect Points", 0))
    expected_delta_rush = int(target_effect.get("Rush", 0) - base_effect.get("Rush", 0))
    expected_delta_flow = int(target_effect.get("Flow", 0) - base_effect.get("Flow", 0))

    base_row = rows[0]
    fg_row = rows[1]

    assert int(base_row["score"]) == 330
    assert int(base_row["source_score"]) == 101
    assert int(base_row["details"]["Stats"]["Perfect Points"]) == int(stats["Perfect Points"]) + expected_delta_pp
    assert int(base_row["details"]["Stats"]["Rush"]) == int(stats["Rush"]) + expected_delta_rush
    assert int(base_row["details"]["Stats"]["Flow"]) == int(stats["Flow"]) + expected_delta_flow

    assert int(fg_row["score"]) == 320
    assert int(fg_row["fg_score"]) == 350
    assert int(fg_row["fg_base_score"]) == 320
    assert int(fg_row["source_score"]) == 100
    assert int(fg_row["source_fg_base_score"]) == 90
    assert int(fg_row["source_fg_score"]) == 120
    assert int(fg_row["details"]["Stats"]["Perfect Points"]) == int(stats["Perfect Points"]) + expected_delta_pp
    assert int(fg_row["details"]["Stats"]["Rush"]) == int(stats["Rush"]) + expected_delta_rush
    assert int(fg_row["details"]["Stats"]["Flow"]) == int(stats["Flow"]) + expected_delta_flow
    assert int(fg_row["force"]["Score"]) == 350
    assert int(fg_row["force"]["BaseStats"]["Perfect Points"]) == int(stats["Perfect Points"]) + expected_delta_pp
    assert int(fg_row["force"]["BaseStats"]["Rush"]) == int(stats["Rush"]) + expected_delta_rush
    assert int(fg_row["force"]["BaseStats"]["Flow"]) == int(stats["Flow"]) + expected_delta_flow
    assert int(fg_row["force"]["ForceGreats"]["final_score"]) == 350


def test_build_team_buff_tier_db_batches_preserves_replayed_base_order_and_appends_fg_only_rows(monkeypatch):
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.helpers.song_helpers.team_buff_tiers import build_team_buff_tier_db_batches

    calc_song = _mock_song(name="pytest_team_buff_batch_order", n_notes=12)
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

    def _entry(loadout_hash: str, gear_name: str, mini_name: str) -> dict:
        return {
            "loadout_hash": loadout_hash,
            "score": 0,
            "fg_score": 0,
            "gear": [gear_name, "G2", "G3", "G4", "G5", "G6"],
            "minis": [mini_name, "M2", "M3"],
            "details": {"Stats": dict(stats)},
            "force": {"Stats": dict(stats), "ForceGreats": {"config": {"NonFever1": 1}}},
        }

    entry_a = _entry("hash-a", "GA", "MA")
    entry_b = _entry("hash-b", "GB", "MB")
    entry_c = _entry("hash-c", "GC", "MC")

    def _fake_compute_team_buff_tier_leaderboards(**kwargs):
        return {
            "meta": {"base_team_buff": "T5", "team_color": "Rush", "primary_color": "Rush", "secondary_color": "Flow"},
            "tiers": {
                "T10": {
                    "base_top51": [
                        {
                            "loadout_hash": entry_b["loadout_hash"],
                            "gear": list(entry_b["gear"]),
                            "minis": list(entry_b["minis"]),
                            "score": 220,
                            "fg_score": 0,
                        },
                        {
                            "loadout_hash": entry_a["loadout_hash"],
                            "gear": list(entry_a["gear"]),
                            "minis": list(entry_a["minis"]),
                            "score": 210,
                            "fg_score": 0,
                        },
                    ],
                    "fg_top51": [
                        {
                            "loadout_hash": entry_c["loadout_hash"],
                            "gear": list(entry_c["gear"]),
                            "minis": list(entry_c["minis"]),
                            "score": 190,
                            "fg_score": 260,
                            "fg_base_score": 190,
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
        entries=[entry_a, entry_b, entry_c],
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        cfg_dict=cfg_dict,
        tiers=("T10",),
        limit=3,
    )

    rows = batches["T10"]
    assert [str(row.get("loadout_hash") or "") for row in rows] == ["hash-b", "hash-a", "hash-c"]
    assert [int(row.get("score") or 0) for row in rows] == [220, 210, 190]
    assert int(rows[2].get("fg_score") or 0) == 260
    assert int(rows[2].get("fg_base_score") or 0) == 190


def test_team_buff_tier_postprocess_base_scoring_uses_cpu_exact_rescore(monkeypatch):
    """
    Regression test: GPU f32 fixed scoring can diverge at floor boundaries.
    Tier postprocess now uses CPU exact replay as the retained-row authority.
    """
    from gear_optimizer.app_async_db import _get_team_buff_ref_arrays_cached
    from gear_optimizer.helpers.song_helpers.team_buff_tiers import compute_team_buff_tier_leaderboards
    from gear_optimizer.solver.scoring.exact_rescore import score_stats_exact

    # Enable the ceiling kernel (tests default it off for most of the suite).
    monkeypatch.setenv("GPU_TIMELINE_CEILING_ENVELOPE", "1")

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
            "Song Name": "pytest_exact_rescore_regression",
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

    exact = int(score_stats_exact(stats, calc_song, ref_arrays))

    entry = {
        "score": 0,
        "fg_score": 0,
        "gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
        "minis": ["M1", "M2", "M3"],
        "details": {"Stats": stats},
        "force": None,
    }
    cfg_dict = {
        "IterationEngine": {},
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
    assert scored == exact
