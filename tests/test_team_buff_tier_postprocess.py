import numpy as np
import pytest

pytestmark = pytest.mark.gpu

# Persisted FG payloads carry the response surface (the canonical exact FG
# representation); fixtures mirror that contract. Head-only bits keep the
# surface valid for <100-note mock songs (body counts must stay 0).
_FG_TEST_SURFACE = [1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0]


def _fg_test_surface() -> list[int]:
    return list(_FG_TEST_SURFACE)


def _expected_fg_surface_score(stats: dict, calc_song: dict, ref_arrays: dict) -> int:
    from gear_optimizer.solver.scoring.exact_rescore import score_force_greats_response_surface_exact
    from gear_optimizer.solver.taichi_gem.force_greats.response_types import FgResponseSurface

    return int(
        score_force_greats_response_surface_exact(stats, calc_song, ref_arrays, FgResponseSurface(*_FG_TEST_SURFACE))
    )


def _force_payload_stats(force_obj: dict, fallback_stats: dict) -> dict:
    from gear_optimizer.helpers.song_helpers.force_greats.result_application import read_visible_stats

    if not isinstance(force_obj, dict) or not force_obj:
        return fallback_stats if isinstance(fallback_stats, dict) else {}
    stats = read_visible_stats(force_obj, mutate_payload=False)
    return stats if isinstance(stats, dict) and stats else (fallback_stats if isinstance(fallback_stats, dict) else {})


# GPU exact-replay tests need the timeline frontier prebuilt (same as production startup).
# Isolated GPU unit tests do not run the full app prebuild; call this before real scoring.
def _prebuild_timeline_frontier(calc_song: dict, ref_arrays: dict) -> None:
    from gear_optimizer.solver.taichi_gem.api.timeline import build_or_load_timeline_frontier_payload

    build_or_load_timeline_frontier_payload(calc_song, ref_arrays)


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


# A sentinel key that lets the synthetic re-solve recover the per-tier stat delta from the
# tier-adjusted `fixed_song_stats` row the postprocess hands it (the delta is `fixed_song_stats`
# minus this constant song-level base, which carries only the sentinel).
_SENTINEL_SONG_BASE = "__synthetic_song_base__"

# Mutable cell shared between the loadout-items hook and the cfg/fixed-stats hook within one
# `_install_synthetic_tier_resolve` install (set by the cfg/fixed-stats hook on every install).
_CURRENT_BASE_EFFECT: dict[str, dict] = {"effect": {}}


def _install_synthetic_tier_resolve(monkeypatch, *, calc_song: dict, ref_arrays: dict) -> None:
    """Replace the GPU per-(tier, color) re-solve helpers with deterministic CPU-exact synthetics.

    The perfect_window (default) postprocess now RE-SOLVES gems per (tier, color) via the GPU
    helpers ``resolve_tier_base_batch`` / ``resolve_tier_fg_force_batch`` and requires each loadout
    to carry 6 gear + 3 mini stat-dicts. These tests exercise the postprocess LOGIC (tier
    reordering, color modes, FG inclusion/score, identity/mini-repair, witness graft) on entries
    that carry bare loadout NAMES, so we feed the re-solve controlled witnesses instead of running
    the GPU gem search.

    The synthetic re-solve is faithful to the model the tests assert under: for a loadout whose
    persisted base stats are ``S`` (already carrying the baseline TeamBuff effect) and a tier whose
    stat delta is ``D``, the re-solved base witness Stats are ``S + D`` and its retained-row score is
    the CPU-f64 exact rescore ``score_stats_exact_batch([S + D])`` — i.e. the same quantity the
    pre-re-solve postprocess keyed on, so reordering/score assertions stay meaningful. CPU exact
    (``score_stats_exact_batch``) remains the scoring authority: it is the synthetic's final step,
    exactly as the real re-solve's final step is ``score_stats_exact_batch``. FG witnesses score the
    frozen response surface exactly at the tier-shifted FG stats, matching the persisted-surface
    replay the FG-visibility tests assert.
    """
    import gear_optimizer.helpers.song_helpers.team_buff_tiers as tbt
    from gear_optimizer.core.team_buff import team_buff_effect
    from gear_optimizer.solver.scoring.exact_rescore import score_stats_exact_batch

    meta0 = calc_song.get("metadata", {}) or {}
    primary_color = str(meta0.get("Primary Color", "") or "").strip()
    secondary_color = str(meta0.get("Secondary Color", "") or "").strip()

    real_force_payload_stats = _force_payload_stats
    real_ensure_base = tbt._ensure_stats_include_base_effect

    # Captured by the loadout-items hook so the synthetic re-solve can recover the per-loadout
    # base/FG stat rows (the real helper would demand 6 gear + 3 mini stat-dicts).
    def _fake_entry_loadout_items(entry: dict) -> list[dict]:
        e = entry or {}
        details = e.get("details") if isinstance(e.get("details"), dict) else {}
        stats_base = real_ensure_base(details.get("Stats") or {}, _CURRENT_BASE_EFFECT["effect"])
        fg_obj = e.get("force")
        if isinstance(fg_obj, dict):
            fg_stats0 = real_force_payload_stats(fg_obj, stats_base)
            fg_stats = real_ensure_base(fg_stats0, _CURRENT_BASE_EFFECT["effect"]) if isinstance(fg_stats0, dict) else stats_base
        else:
            fg_stats = stats_base
        return [{"__base_stats__": dict(stats_base), "__fg_stats__": dict(fg_stats)}]

    def _fake_tier_cfg_and_song_fixed_stats(cfg_dict, calc_song_arg):
        # Capture the baseline TeamBuff effect (base buff + base color) so the loadout-items hook can
        # mirror the postprocess's `_ensure_stats_include_base_effect` exactly.
        base_team_buff = tbt._resolve_base_team_buff(cfg_dict)
        base_team_color, _target = tbt._resolve_team_colors_for_tiering(cfg_dict, calc_song_arg)
        _CURRENT_BASE_EFFECT["effect"] = team_buff_effect(base_team_buff, base_team_color)
        # Non-empty song base carrying only the sentinel, so `_apply_stat_delta` keeps the per-tier
        # delta keys intact and the synthetic re-solve can subtract the sentinel back out.
        return None, {_SENTINEL_SONG_BASE: 0}

    def _delta_from_fixed(fixed_song_stats: dict) -> dict:
        return {k: int(v) for k, v in dict(fixed_song_stats or {}).items() if k != _SENTINEL_SONG_BASE}

    def _fake_resolve_tier_base_batch(*, fixed_song_stats, loadouts, calc_song, ref_arrays, **_kw):
        delta = _delta_from_fixed(fixed_song_stats)
        resolved_stats_rows = [
            tbt._apply_stat_delta(items[0]["__base_stats__"], delta) for items in loadouts
        ]
        scores = [int(s) for s in score_stats_exact_batch(resolved_stats_rows, calc_song, ref_arrays)]
        return [
            ({"Stats": dict(stats_row), "GemCounts": {"Perfect Points": 0}}, int(score))
            for stats_row, score in zip(resolved_stats_rows, scores, strict=True)
        ]

    def _fake_resolve_tier_fg_force_batch(*, fixed_song_stats, loadouts, calc_song, ref_arrays, selected_color="", **_kw):
        delta = _delta_from_fixed(fixed_song_stats)
        forces: list[dict] = []
        for items in loadouts:
            fg_stats = tbt._apply_stat_delta(items[0]["__fg_stats__"], delta)
            base_stats = tbt._apply_stat_delta(items[0]["__base_stats__"], delta)
            fg_score = _expected_fg_surface_score(fg_stats, calc_song, ref_arrays)
            base_score = int(score_stats_exact_batch([base_stats], calc_song, ref_arrays)[0])
            forces.append(
                {
                    "Score": int(fg_score),
                    "BaseScore": int(base_score),
                    "Stats": dict(fg_stats),
                    "BaseStats": dict(base_stats),
                    "GemCounts": {"Perfect Points": 0},
                    "SelectedElement": str(selected_color or primary_color or ""),
                    "ForceGreats": {"config": {"NonFever1": 1}, "final_score": int(fg_score)},
                    "response_surface": _fg_test_surface(),
                    "forced_counts": {"NonFever1": 1},
                }
            )
        return forces

    monkeypatch.setattr(tbt, "_entry_loadout_items", _fake_entry_loadout_items)
    monkeypatch.setattr(tbt, "_tier_cfg_and_song_fixed_stats", _fake_tier_cfg_and_song_fixed_stats)
    monkeypatch.setattr(tbt, "resolve_tier_base_batch", _fake_resolve_tier_base_batch)
    monkeypatch.setattr(tbt, "resolve_tier_fg_force_batch", _fake_resolve_tier_fg_force_batch)


def test_team_buff_tier_postprocess_reorders_top_entries_across_tiers(monkeypatch):
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
            "Stats": stats_a,
            "ForceGreats": {"config": {"NonFever1": 1}},
            "response_surface": _fg_test_surface(),
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

    _prebuild_timeline_frontier(calc_song, ref_arrays)
    _install_synthetic_tier_resolve(monkeypatch, calc_song=calc_song, ref_arrays=ref_arrays)

    out = compute_team_buff_tier_leaderboards(
        entries=[entry_a, entry_b], calc_song=calc_song, ref_arrays=ref_arrays, cfg_dict=cfg_dict
    )
    tiers = out["tiers"]

    assert "NONE" in tiers
    assert tiers["T5"]["base_top51"][0]["gear"] == entry_a["gear"]
    assert tiers["T20"]["base_top51"][0]["gear"] == entry_b["gear"]


def test_team_buff_tiers_auto_mode_uses_primary_color_and_t5_base(monkeypatch):
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

    _prebuild_timeline_frontier(calc_song, ref_arrays)
    _install_synthetic_tier_resolve(monkeypatch, calc_song=calc_song, ref_arrays=ref_arrays)

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


def test_build_team_buff_tier_db_batches_preserves_identity_and_repairs_corrupt_minis(monkeypatch):
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
        "loadout_hash": "hash-identity",
        "score": 1,
        "fg_score": 0,
        "gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
        # Corrupted minis sometimes show up as strings like "['Name']" inside persisted mini variant groups.
        "minis": [["['M1']"], ["M2"], ["M3"]],
        "details": {"Stats": stats},
        "force": None,
    }

    _prebuild_timeline_frontier(calc_song, ref_arrays)
    _install_synthetic_tier_resolve(monkeypatch, calc_song=calc_song, ref_arrays=ref_arrays)

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
    # Issue #38 (base surface): each emitted base row carries a per-tier timeline trace so the
    # note graph can be drawn for this tier (recomputed from the tier-shifted stats, additive).
    timeline_frontier = (out.get("details") or {}).get("TimelineFrontier")
    assert isinstance(timeline_frontier, dict), "base row must attach a recomputed TimelineFrontier"
    assert timeline_frontier.get("frontier_trace"), "TimelineFrontier must carry a non-empty frontier_trace"


def test_build_team_buff_tier_db_batches_keeps_stable_row_order_for_mixed_base_and_fg_rows(monkeypatch):
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.helpers.song_helpers.team_buff_tiers import build_team_buff_tier_db_batches

    calc_song = _mock_song(name="pytest_team_buff_row_order", n_notes=12)
    ref_arrays = _ref_arrays(TOTAL_ROWS + 1)
    _prebuild_timeline_frontier(calc_song, ref_arrays)
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
        {
            "loadout_hash": "hash-b",
            "score": 1,
            "fg_score": 0,
            "gear": ["B"],
            "minis": ["M2"],
            "details": {"Stats": stats},
            "force": None,
        },
        {
            "loadout_hash": "hash-a",
            "score": 2,
            "fg_score": 0,
            "gear": ["A"],
            "minis": ["M1"],
            "details": {"Stats": stats},
            "force": None,
        },
        {
            "loadout_hash": "hash-c",
            "score": 3,
            "fg_score": 0,
            "gear": ["C"],
            "minis": ["M3"],
            "details": {"Stats": stats},
            "force": {"ForceGreats": {"config": {"NonFever1": 1}}, "response_surface": _fg_test_surface()},
        },
    ]

    def fake_compute_team_buff_tier_leaderboards(**kwargs):
        return {
            "meta": {"base_team_buff": "T5", "team_color": "Rush", "primary_color": "Rush", "secondary_color": "Flow"},
            "tiers": {
                "T5": {
                    "base_top51": [
                        {"loadout_hash": "hash-b", "gear": ["B"], "minis": ["M2"], "score": 20, "fg_score": 0},
                        {"loadout_hash": "hash-a", "gear": ["A"], "minis": ["M1"], "score": 10, "fg_score": 0},
                    ],
                    "fg_top51": [
                        {
                            "loadout_hash": "hash-c",
                            "gear": ["C"],
                            "minis": ["M3"],
                            "score": 30,
                            "fg_score": 40,
                            "fg_base_score": 15,
                        },
                    ],
                }
            },
            # The graft fails loud unless every hashed (tier, loadout) carries a re-solved witness;
            # supply one per hash (real stat dict reused) so the row-order assertion can run.
            "resolved_base_by_tier_hash": {
                "T5": {
                    h: {"Stats": dict(stats), "GemCounts": {"Perfect Points": 0}}
                    for h in ("hash-b", "hash-a", "hash-c")
                }
            },
            "resolved_fg_force_by_tier_hash": {
                "T5": {
                    "hash-c": {
                        "Score": 40,
                        "BaseScore": 15,
                        "Stats": dict(stats),
                        "BaseStats": dict(stats),
                        "GemCounts": {"Perfect Points": 0},
                        "ForceGreats": {"config": {"NonFever1": 1}, "final_score": 40},
                        "response_surface": _fg_test_surface(),
                    }
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


def test_build_team_buff_tier_db_batches_attaches_details_by_loadout_hash_not_gear_minis(monkeypatch):
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.helpers.song_helpers.team_buff_tiers import build_team_buff_tier_db_batches

    calc_song = _mock_song(name="pytest_team_buff_hash_collision", n_notes=12)
    ref_arrays = _ref_arrays(TOTAL_ROWS + 1)
    _prebuild_timeline_frontier(calc_song, ref_arrays)
    cfg_dict = {"TeamContributionBuffConstant": {"TeamBuff": "T5", "TeamColor": "Rush"}}

    shared_stats = {
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
    shared_gear = ["G1", "G2", "G3", "G4", "G5", "G6"]
    shared_minis = ["M1", "M2", "M3"]

    entry_a = {
        "loadout_hash": "hash-a",
        "score": 100,
        "fg_score": 0,
        "gear": list(shared_gear),
        "minis": list(shared_minis),
        "details": {"Stats": dict(shared_stats), "Marker": "entry-a"},
        "force": None,
    }
    entry_b = {
        "loadout_hash": "hash-b",
        "score": 101,
        "fg_score": 250,
        "gear": list(shared_gear),
        "minis": list(shared_minis),
        "details": {"Stats": dict(shared_stats), "Marker": "entry-b"},
        "force": {
            "Score": 250,
            "BaseStats": dict(shared_stats),
            "ForceGreats": {"config": {"NonFever1": 1}, "final_score": 250, "Marker": "force-b"},
            "response_surface": _fg_test_surface(),
        },
    }

    def _fake_compute_team_buff_tier_leaderboards(**kwargs):
        return {
            "meta": {"base_team_buff": "T5", "team_color": "Rush", "primary_color": "Rush", "secondary_color": "Flow"},
            "tiers": {
                "T5": {
                    "base_top51": [
                        {
                            "loadout_hash": "hash-a",
                            "gear": list(shared_gear),
                            "minis": list(shared_minis),
                            "score": 320,
                            "fg_score": 0,
                        }
                    ],
                    "fg_top51": [
                        {
                            "loadout_hash": "hash-b",
                            "gear": list(shared_gear),
                            "minis": list(shared_minis),
                            "score": 300,
                            "fg_score": 350,
                            "fg_base_score": 300,
                            "force_config": {"NonFever1": 1},
                        }
                    ],
                }
            },
            # Base witnesses for every hashed row (graft fails loud otherwise); witness Stats/GemCounts
            # override only those keys, so the entry's `details.Marker` is preserved (the property
            # under test: details attach by loadout_hash).
            "resolved_base_by_tier_hash": {
                "T5": {
                    "hash-a": {"Stats": dict(shared_stats), "GemCounts": {"Perfect Points": 0}},
                    "hash-b": {"Stats": dict(shared_stats), "GemCounts": {"Perfect Points": 0}},
                }
            },
            # FG witness only for the fg_top loadout (hash-b); the re-solved force IS the served
            # force, so it carries the marker the assertion checks. hash-a has no FG witness, so its
            # served force stays None (the base-only row).
            "resolved_fg_force_by_tier_hash": {
                "T5": {
                    "hash-b": {
                        "Score": 350,
                        "BaseScore": 300,
                        "Stats": dict(shared_stats),
                        "BaseStats": dict(shared_stats),
                        "GemCounts": {"Perfect Points": 0},
                        "ForceGreats": {"config": {"NonFever1": 1}, "final_score": 350, "Marker": "force-b"},
                        "response_surface": _fg_test_surface(),
                    }
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
        tiers=("T5",),
        limit=2,
    )

    rows = batches["T5"]
    assert len(rows) == 2
    base_row = next(row for row in rows if str(row.get("loadout_hash") or "") == "hash-a")
    fg_row = next(row for row in rows if str(row.get("loadout_hash") or "") == "hash-b")
    assert base_row.get("details", {}).get("Marker") == "entry-a"
    assert base_row.get("force") is None
    assert fg_row.get("details", {}).get("Marker") == "entry-b"
    assert fg_row.get("force", {}).get("ForceGreats", {}).get("Marker") == "force-b"


def test_team_buff_tiers_handle_stats_missing_base_team_buff_without_negative_pp(monkeypatch):
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
        "loadout_hash": "hash-missing-base",
        "score": 1,
        "fg_score": 2,
        "gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
        "minis": ["M1", "M2", "M3"],
        "details": {"Stats": stats},
        # Flat force payload as stored in DB; BaseStats also missing base effect to emulate repaired rows.
        "force": {
            "BaseStats": stats,
            "GemCounts": {"Perfect Points": 0},
            "ForceGreats": {"config": {"NonFever1": 1}},
            "response_surface": _fg_test_surface(),
        },
    }

    _prebuild_timeline_frontier(calc_song, ref_arrays)
    _install_synthetic_tier_resolve(monkeypatch, calc_song=calc_song, ref_arrays=ref_arrays)

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


def test_team_buff_tiers_support_target_team_color_overrides(monkeypatch):
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
        "loadout_hash": "hash-color-modes",
        "score": 0,
        "fg_score": 0,
        "gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
        "minis": ["M1", "M2", "M3"],
        "details": {"Stats": stats},
        "force": None,
    }

    _prebuild_timeline_frontier(calc_song, ref_arrays)
    _install_synthetic_tier_resolve(monkeypatch, calc_song=calc_song, ref_arrays=ref_arrays)

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


def test_team_buff_tiers_apply_tier_deltas_to_fg_score(monkeypatch):
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
    _prebuild_timeline_frontier(calc_song, ref_arrays)

    # Production invariant: a persisted FG entry carries fg_score == the exact surface
    # score. The baseline (T5) tier CARRIES that value verbatim (identical-context
    # carry); only non-baseline tiers re-solve, which is exactly what this test pins.
    carried_fg = _expected_fg_surface_score(stats, calc_song, ref_arrays)
    entry = {
        "score": 0,
        "fg_score": int(carried_fg),
        "gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
        "minis": ["M1", "M2", "M3"],
        "details": {"Stats": stats},
        "force": {
            "BaseStats": stats,
            "GemCounts": {"Perfect Points": 0},
            "ForceGreats": {"config": {"NonFever1": 1}},
            "response_surface": _fg_test_surface(),
        },
    }

    _install_synthetic_tier_resolve(monkeypatch, calc_song=calc_song, ref_arrays=ref_arrays)

    out = compute_team_buff_tier_leaderboards(
        entries=[entry],
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        cfg_dict=cfg_dict,
        tiers=("T5", "T51"),
    )

    t5 = out["tiers"]["T5"]["base_top51"][0]
    t51 = out["tiers"]["T51"]["base_top51"][0]
    t5_fg = out["tiers"]["T5"]["fg_top51"][0]
    t51_fg = out["tiers"]["T51"]["fg_top51"][0]

    assert t5["score"] != t51["score"]
    assert t5_fg["fg_score"] != t51_fg["fg_score"]


def test_team_buff_tier_replay_requires_persisted_response_surface():
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.helpers.song_helpers.team_buff_tiers import compute_team_buff_tier_leaderboards

    calc_song = _mock_song(name="pytest_team_buff_missing_surface", n_notes=12)
    ref_arrays = _ref_arrays(TOTAL_ROWS + 1)
    cfg_dict = {"TeamContributionBuffConstant": {"TeamBuff": "T5", "TeamColor": "Rush"}}

    stats = {"Perfect Points": 100, "Combo Multiplier": 0, "Fever Multiplier": 0,
             "Fever Fill Rate": 0, "Fever Time": 0, "Rush": 150, "Flow": 0,
             "Beat": 0, "Vibe": 0, "Chill": 0}
    entry = {
        "score": 100,
        "fg_score": 95,
        "gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
        "minis": ["M1", "M2", "M3"],
        "details": {"Stats": dict(stats)},
        # Valid FG config but no persisted response_surface: invalid FG state.
        "force": {"Stats": dict(stats), "ForceGreats": {"config": {"NonFever1": 1}}},
    }

    with pytest.raises(ValueError, match="response_surface"):
        compute_team_buff_tier_leaderboards(
            entries=[entry],
            calc_song=calc_song,
            ref_arrays=ref_arrays,
            cfg_dict=cfg_dict,
            tiers=("T5",),
            limit=1,
        )


def test_team_buff_tier_postprocess_uses_source_fg_base_score_for_fg_inclusion(monkeypatch):
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.helpers.song_helpers.team_buff_tiers import compute_team_buff_tier_leaderboards
    from gear_optimizer.solver.scoring.exact_rescore import score_stats_exact

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
    _prebuild_timeline_frontier(calc_song, ref_arrays)

    expected_base = int(score_stats_exact(stats, calc_song, ref_arrays))
    expected_fg = _expected_fg_surface_score(stats, calc_song, ref_arrays)

    # Production invariant: the persisted fg_score IS the exact surface score; the
    # baseline (T5) tier carries it verbatim (identical-context carry).
    entry = {
        "score": 100,
        "fg_score": int(expected_fg),
        "fg_base_score": 90,
        "gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
        "minis": ["M1", "M2", "M3"],
        "details": {"Stats": dict(stats)},
        "force": {
            "Stats": dict(stats),
            "ForceGreats": {"config": {"NonFever1": 1}},
            "response_surface": _fg_test_surface(),
        },
    }

    _install_synthetic_tier_resolve(monkeypatch, calc_song=calc_song, ref_arrays=ref_arrays)

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
    expected_paired_fg_base = int(score_stats_exact(stats, calc_song, ref_arrays))
    assert len(tier["fg_top51"]) == 1
    assert tier["fg_top51"][0]["fg_score"] == expected_fg
    assert tier["fg_top51"][0]["fg_base_score"] == expected_paired_fg_base
    assert "score" not in tier["fg_top51"][0]


def test_baseline_carry_fails_loud_on_valid_force_with_nonpositive_fg_score(monkeypatch):
    """Regression (PR #87 review): the baseline (T5) perfect_window identical-context carry ranks
    FG rows from the entry-level ``fg_score`` WITHOUT re-solving. If an entry reaches the FG loop
    with a VALID force payload (valid config + response surface) but a stale/missing non-positive
    top-level ``fg_score``, the pre-fix carry wrote 0 into the rank list and the ``fg_score > 0``
    filter silently DROPPED the row -- a lost valid FG loadout. The re-solve branch it replaced
    would have RANKED that row from its freshly recomputed force Score. Since the carry does not
    recompute, it must fail loud on the inconsistency rather than silently drop."""
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.helpers.song_helpers.team_buff_tiers import compute_team_buff_tier_leaderboards

    calc_song = _mock_song(name="pytest_carry_stale_fg_score", n_notes=12)
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
    _prebuild_timeline_frontier(calc_song, ref_arrays)

    # Valid FG force (config + response surface) but a stale, non-positive top-level fg_score.
    entry = {
        "score": 100,
        "fg_score": 0,  # stale/missing -- inconsistent with the valid force below
        "fg_base_score": 90,
        "gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
        "minis": ["M1", "M2", "M3"],
        "details": {"Stats": dict(stats)},
        "force": {
            "Stats": dict(stats),
            "ForceGreats": {"config": {"NonFever1": 1}},
            "response_surface": _fg_test_surface(),
        },
    }

    _install_synthetic_tier_resolve(monkeypatch, calc_song=calc_song, ref_arrays=ref_arrays)

    with pytest.raises(ValueError, match="non-positive fg_score"):
        compute_team_buff_tier_leaderboards(
            entries=[entry],
            calc_song=calc_song,
            ref_arrays=ref_arrays,
            cfg_dict=cfg_dict,
            tiers=("T5",),
            limit=1,
        )


def test_fg_paired_base_is_loadout_base_not_gemless_recompute(monkeypatch):
    """Regression (recurring site): the FG row's paired base (fg_base_score) MUST be the same
    loadout's re-solved BASE score, never a second recompute off the force payload's pre-gem
    ``BaseStats``. Production stored BaseStats WITHOUT the loadout gems (FeverFill/element), so a
    paired-base recompute off it collapsed to ~30-45% of the real base (fever barely activated),
    neutering the ``fg_score > base`` gate and showing set-crafters a wrong base on the site. Here
    ``force['BaseStats']`` is deliberately gemless; ``fg_base_score`` must still equal the loadout's
    base leaderboard score."""
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.helpers.song_helpers.team_buff_tiers import compute_team_buff_tier_leaderboards
    from gear_optimizer.solver.scoring.exact_rescore import score_stats_exact

    calc_song = _mock_song(name="pytest_fg_paired_base_gemless_guard", n_notes=12)
    ref_arrays = _ref_arrays(TOTAL_ROWS + 1)
    cfg_dict = {"TeamContributionBuffConstant": {"TeamBuff": "T5", "TeamColor": "Rush"}}

    stats = {
        "Perfect Points": 100,
        "Combo Multiplier": 40,
        "Fever Multiplier": 40,
        "Fever Fill Rate": 40,
        "Fever Time": 40,
        "Rush": 200,
        "Flow": 0,
        "Beat": 0,
        "Vibe": 0,
        "Chill": 0,
    }
    # What production actually persisted in force['BaseStats']: the loadout WITHOUT its gems
    # (FeverFill 0, low element). A paired-base recompute off this collapses well below the truth.
    gemless_base_stats = dict(stats)
    gemless_base_stats["Fever Fill Rate"] = 0
    gemless_base_stats["Rush"] = 60
    entry = {
        "score": 100,
        "fg_score": 95,
        "fg_base_score": 90,
        "gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
        "minis": ["M1", "M2", "M3"],
        "details": {"Stats": dict(stats)},
        "force": {
            "Stats": dict(stats),
            "BaseStats": dict(gemless_base_stats),
            "ForceGreats": {"config": {"NonFever1": 1}},
            "response_surface": _fg_test_surface(),
        },
    }

    _prebuild_timeline_frontier(calc_song, ref_arrays)
    _install_synthetic_tier_resolve(monkeypatch, calc_song=calc_song, ref_arrays=ref_arrays)

    expected_base = int(score_stats_exact(stats, calc_song, ref_arrays))
    gemless_score = int(score_stats_exact(gemless_base_stats, calc_song, ref_arrays))
    assert gemless_score < expected_base  # the discarded recompute would be strictly lower

    out = compute_team_buff_tier_leaderboards(
        entries=[entry],
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        cfg_dict=cfg_dict,
        tiers=("T5",),
        limit=1,
    )
    tier = out["tiers"]["T5"]
    assert len(tier["fg_top51"]) == 1
    fg_base = int(tier["fg_top51"][0]["fg_base_score"])
    assert fg_base == expected_base                        # the loadout's real base
    assert fg_base == int(tier["base_top51"][0]["score"])  # identical to the base leaderboard row
    assert fg_base != gemless_score                        # NOT the gemless force['BaseStats']


@pytest.mark.parametrize("tier_name", ["NONE", "T1", "T10", "T20", "T50", "T51"])
def test_team_buff_tier_postprocess_derived_tier_fg_visibility_uses_replayed_base_score(monkeypatch, tier_name: str):
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.core.team_buff import team_buff_effect
    from gear_optimizer.helpers.song_helpers.team_buff_tiers import compute_team_buff_tier_leaderboards
    from gear_optimizer.solver.scoring.exact_rescore import score_stats_exact

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
            "response_surface": _fg_test_surface(),
        },
    }

    base_effect = team_buff_effect("T5", "Rush")
    target_effect = team_buff_effect(tier_name, "Rush")
    tier_stats = dict(stats)
    for key in set(base_effect) | set(target_effect):
        tier_stats[key] = int(tier_stats.get(key, 0)) + int(target_effect.get(key, 0)) - int(base_effect.get(key, 0))
    _prebuild_timeline_frontier(calc_song, ref_arrays)

    _install_synthetic_tier_resolve(monkeypatch, calc_song=calc_song, ref_arrays=ref_arrays)

    expected_base = int(score_stats_exact(tier_stats, calc_song, ref_arrays))
    expected_fg = _expected_fg_surface_score(tier_stats, calc_song, ref_arrays)

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
    if expected_fg > 0:
        assert len(tier["fg_top51"]) == 1
        assert tier["fg_top51"][0]["fg_score"] == expected_fg
        assert tier["fg_top51"][0]["fg_base_score"] == expected_base
        assert tier["fg_top51"][0]["source_fg_base_score"] == 130
        assert "score" not in tier["fg_top51"][0]
    else:
        assert tier["fg_top51"] == []


def test_build_team_buff_tier_db_batches_preserves_fg_base_score_from_fg_top_rows(monkeypatch):
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.helpers.song_helpers.team_buff_tiers import build_team_buff_tier_db_batches

    calc_song = _mock_song(name="pytest_team_buff_fg_batch_ctx", n_notes=12)
    ref_arrays = _ref_arrays(TOTAL_ROWS + 1)
    _prebuild_timeline_frontier(calc_song, ref_arrays)
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
        "loadout_hash": "hash-fg-base",
        "score": 100,
        "fg_score": 95,
        "fg_base_score": 90,
        "gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
        "minis": ["M1", "M2", "M3"],
        "details": {"Stats": dict(stats)},
        "force": {
            "Stats": dict(stats),
            "ForceGreats": {"config": {"NonFever1": 1}},
            "response_surface": _fg_test_surface(),
        },
    }

    def _fake_compute_team_buff_tier_leaderboards(**kwargs):
        return {
            "meta": {"base_team_buff": "T5", "team_color": "Rush", "primary_color": "Rush", "secondary_color": "Flow"},
            "tiers": {
                "T5": {
                    "base_top51": [
                        {
                            "loadout_hash": entry["loadout_hash"],
                            "gear": list(entry["gear"]),
                            "minis": list(entry["minis"]),
                            "score": 110,
                            "fg_score": 95,
                        }
                    ],
                    "fg_top51": [
                        {
                            "loadout_hash": entry["loadout_hash"],
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
            "resolved_base_by_tier_hash": {
                "T5": {entry["loadout_hash"]: {"Stats": dict(stats), "GemCounts": {"Perfect Points": 0}}}
            },
            # The served FG force IS the re-solved witness; it carries the FG config the assertion
            # checks is preserved through the graft.
            "resolved_fg_force_by_tier_hash": {
                "T5": {
                    entry["loadout_hash"]: {
                        "Score": 95,
                        "BaseScore": 90,
                        "Stats": dict(stats),
                        "BaseStats": dict(stats),
                        "GemCounts": {"Perfect Points": 0},
                        "ForceGreats": {"config": {"NonFever1": 1}, "final_score": 95},
                        "response_surface": _fg_test_surface(),
                    }
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
        "loadout_hash": "hash-source-meta",
        "score": 100,
        "fg_score": 95,
        "fg_base_score": 90,
        "gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
        "minis": ["M1", "M2", "M3"],
        "details": {"Stats": {}},
        "force": {"ForceGreats": {"config": {"NonFever1": 1}}, "response_surface": _fg_test_surface()},
    }

    def _fake_compute_team_buff_tier_leaderboards(**kwargs):
        return {
            "meta": {"base_team_buff": "T5", "team_color": "Rush", "primary_color": "Rush", "secondary_color": "Flow"},
            "tiers": {
                "T10": {
                    "base_top51": [
                        {
                            "loadout_hash": entry["loadout_hash"],
                            "gear": list(entry["gear"]),
                            "minis": list(entry["minis"]),
                            "score": 110,
                            "fg_score": 95,
                        }
                    ],
                    "fg_top51": [
                        {
                            "loadout_hash": entry["loadout_hash"],
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
            # This entry carries empty details Stats; keep the base witness Stats empty too so the
            # (Stats-driven) per-tier TimelineFrontier recompute stays skipped — this test pins
            # source-FG metadata propagation, not the base note-graph, and runs without the timeline
            # frontier prebuilt. An empty-but-present witness still satisfies the fail-loud graft.
            "resolved_base_by_tier_hash": {
                "T10": {entry["loadout_hash"]: {"Stats": {}, "GemCounts": {"Perfect Points": 0}}}
            },
            "resolved_fg_force_by_tier_hash": {
                "T10": {
                    entry["loadout_hash"]: {
                        "Score": 120,
                        "BaseScore": 110,
                        "Stats": {},
                        "BaseStats": {},
                        "GemCounts": {"Perfect Points": 0},
                        "ForceGreats": {"config": {"NonFever1": 1}, "final_score": 120},
                        "response_surface": _fg_test_surface(),
                    }
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


def test_build_team_buff_tier_db_batches_zero_ms_fg_preserves_persisted_loadout_identity(monkeypatch):
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.helpers.song_helpers.team_buff_tiers import build_team_buff_tier_db_batches

    calc_song = _mock_song(name="pytest_team_buff_zero_ms_fg_identity", n_notes=12)
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
    persisted_force = {
        "Score": 95,
        "BaseStats": dict(stats),
        "GemCounts": {
            "Perfect Points": 3,
            "Combo Multiplier": 4,
            "Fever Multiplier": 5,
            "Element": 6,
        },
        "SelectedElement": "Rush",
        "ForceGreats": {
            "config": {"NonFever1": 1},
            "frontier_trace": {"source": "persisted"},
            "non_fever_base": 11,
            "frontier_first_surfaces": [{"source": "persisted"}],
            "final_score": 95,
        },
        "response_surface": _fg_test_surface(),
        "forced_counts": {"NonFever1": 1},
    }
    witness_force = {
        "Score": 123,
        "BaseScore": 110,
        "BaseStats": {"Perfect Points": 111},
        "Stats": {"Perfect Points": 111},
        "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 0,
            "Element": 0,
        },
        "SelectedElement": "Rush",
        "ForceGreats": {
            "config": {"NonFever1": 7},
            "frontier_trace": {"source": "zero-ms"},
            "non_fever_base": 22,
            "frontier_first_surfaces": [{"source": "zero-ms"}],
            "final_score": 123,
        },
        "response_surface": [9, 8, 7, 6, 5, 4, 3, 2, 1, 0, 0],
        "forced_counts": {"NonFever1": 7},
    }
    entry = {
        "loadout_hash": "hash-zero-ms-fg",
        "score": 100,
        "fg_score": 95,
        "fg_base_score": 90,
        "gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
        "minis": ["M1", "M2", "M3"],
        "details": {"Stats": dict(stats)},
        "force": persisted_force,
    }

    def _fake_compute_team_buff_tier_leaderboards(**kwargs):
        return {
            "meta": {
                "base_team_buff": "T5",
                "base_team_color": "Rush",
                "target_team_color": "Rush",
                "team_color": "Rush",
                "primary_color": "Rush",
                "secondary_color": "Flow",
            },
            "tiers": {
                "T5": {
                    "base_top51": [],
                    "fg_top51": [
                        {
                            "loadout_hash": entry["loadout_hash"],
                            "gear": list(entry["gear"]),
                            "minis": list(entry["minis"]),
                            "score": 110,
                            "fg_score": 123,
                            "fg_base_score": 110,
                            "force_config": {"NonFever1": 7},
                        }
                    ],
                }
            },
            "resolved_fg_force_by_tier_hash": {"T5": {entry["loadout_hash"]: witness_force}},
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
        replay_surface="fg",
        timing_mode="zero_ms",
    )

    row = batches["T5"][0]
    force = row["force"]
    assert row["gear"] == entry["gear"]
    assert row["minis"] == entry["minis"]
    assert int(row["fg_score"]) == 123
    assert int(row["fg_base_score"]) == witness_force["BaseScore"]
    assert force["GemCounts"] == witness_force["GemCounts"]
    assert force["GemCounts"] != persisted_force["GemCounts"]
    assert force["BaseStats"] == witness_force["BaseStats"]
    assert force["SelectedElement"] == witness_force["SelectedElement"]
    assert force["ForceGreats"]["config"] == witness_force["ForceGreats"]["config"]
    assert force["ForceGreats"]["frontier_trace"] == witness_force["ForceGreats"]["frontier_trace"]
    assert force["ForceGreats"]["non_fever_base"] == witness_force["ForceGreats"]["non_fever_base"]
    assert force["ForceGreats"]["frontier_first_surfaces"] == witness_force["ForceGreats"]["frontier_first_surfaces"]
    assert force["response_surface"] == witness_force["response_surface"]
    assert force["forced_counts"] == witness_force["forced_counts"]
    assert int(force["Score"]) == 123
    assert int(force["ForceGreats"]["final_score"]) == 123


def test_build_team_buff_tier_db_batches_strict_sanity_preserves_scores_and_target_team_color(monkeypatch):
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.core.team_buff import team_buff_effect
    from gear_optimizer.helpers.song_helpers.team_buff_tiers import build_team_buff_tier_db_batches

    calc_song = _mock_song(name="pytest_team_buff_strict_sanity", n_notes=12)
    ref_arrays = _ref_arrays(TOTAL_ROWS + 1)
    _prebuild_timeline_frontier(calc_song, ref_arrays)
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

    def _entry(
        loadout_hash: str,
        gear_name: str,
        mini_name: str,
        *,
        score: int,
        fg_score: int,
        fg_base_score: int,
    ) -> dict:
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
                "response_surface": _fg_test_surface(),
            },
        }

    entry_a = _entry("hash-a", "GA", "MA", score=100, fg_score=120, fg_base_score=90)
    entry_b = _entry("hash-b", "GB", "MB", score=101, fg_score=0, fg_base_score=0)

    # The re-solved base/FG witnesses are already at-tier (T20, target color Flow); their Stats are
    # the tier-shifted persisted Stats. Build them the same way the postprocess would, so the served
    # base details (witness Stats override) and FG force carry exactly the at-tier stats the
    # assertions check.
    _base_eff = team_buff_effect("T5", "Rush")
    _target_eff = team_buff_effect("T20", "Flow")
    _shift = {
        "Perfect Points": int(_target_eff.get("Perfect Points", 0) - _base_eff.get("Perfect Points", 0)),
        "Rush": int(_target_eff.get("Rush", 0) - _base_eff.get("Rush", 0)),
        "Flow": int(_target_eff.get("Flow", 0) - _base_eff.get("Flow", 0)),
    }
    shifted_stats = dict(stats)
    for _k, _d in _shift.items():
        shifted_stats[_k] = int(shifted_stats.get(_k, 0)) + _d

    def _fake_compute_team_buff_tier_leaderboards(**kwargs):
        return {
            "meta": {"base_team_buff": "T5", "team_color": "Flow", "primary_color": "Rush", "secondary_color": "Flow"},
            "resolved_base_by_tier_hash": {
                "T20": {
                    entry_a["loadout_hash"]: {"Stats": dict(shifted_stats), "GemCounts": {"Perfect Points": 0}},
                    entry_b["loadout_hash"]: {"Stats": dict(shifted_stats), "GemCounts": {"Perfect Points": 0}},
                }
            },
            # FG witness only for the fg_top loadout (hash-a). The served FG force IS this witness:
            # at-tier Score/BaseStats and the FG config, all checked by the assertions.
            "resolved_fg_force_by_tier_hash": {
                "T20": {
                    entry_a["loadout_hash"]: {
                        "Score": 350,
                        "BaseScore": 320,
                        "Stats": dict(shifted_stats),
                        "BaseStats": dict(shifted_stats),
                        "GemCounts": {"Perfect Points": 0},
                        "SelectedElement": "Rush",
                        "ForceGreats": {"config": {"NonFever1": 1}, "final_score": 350},
                        "response_surface": _fg_test_surface(),
                    }
                }
            },
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
    _prebuild_timeline_frontier(calc_song, ref_arrays)
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
            "force": {
                "Stats": dict(stats),
                "ForceGreats": {"config": {"NonFever1": 1}},
                "response_surface": _fg_test_surface(),
            },
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
            "resolved_base_by_tier_hash": {
                "T10": {
                    h: {"Stats": dict(stats), "GemCounts": {"Perfect Points": 0}}
                    for h in ("hash-b", "hash-a", "hash-c")
                }
            },
            "resolved_fg_force_by_tier_hash": {
                "T10": {
                    "hash-c": {
                        "Score": 260,
                        "BaseScore": 190,
                        "Stats": dict(stats),
                        "BaseStats": dict(stats),
                        "GemCounts": {"Perfect Points": 0},
                        "ForceGreats": {"config": {"NonFever1": 1}, "final_score": 260},
                        "response_surface": _fg_test_surface(),
                    }
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
    Tier postprocess uses CPU exact replay as the retained-row authority.

    The per-(tier, color) base re-solve's final, user-visible scoring step is the CPU-f64 exact
    rescore (``score_stats_exact_batch``); the GPU gem search only proposes the allocation. We pin
    that authority here by stubbing the GPU re-solve with a synthetic whose final scoring step is
    the SAME ``score_stats_exact_batch`` over the re-solved Stats, and asserting the score the
    postprocess surfaces equals an independent CPU ``score_stats_exact`` of those Stats. (At T5/Vibe
    the tier delta is zero, so the re-solved Stats equal the persisted Stats and the retained score
    must equal the CPU-exact replay of the persisted Stats — the floor-boundary divergence guard.)
    """
    from gear_optimizer.app_async_db import _get_team_buff_ref_arrays_cached
    from gear_optimizer.helpers.song_helpers.team_buff_tiers import compute_team_buff_tier_leaderboards
    from gear_optimizer.solver.scoring.exact_rescore import score_stats_exact

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

    from gear_optimizer.solver.timing_envelope import apply_timing_envelope

    apply_timing_envelope(calc_song)
    _prebuild_timeline_frontier(calc_song, ref_arrays)
    _install_synthetic_tier_resolve(monkeypatch, calc_song=calc_song, ref_arrays=ref_arrays)
    exact = int(score_stats_exact(stats, calc_song, ref_arrays))

    entry = {
        "loadout_hash": "hash-exact-rescore",
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
