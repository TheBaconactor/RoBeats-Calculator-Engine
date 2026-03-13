import numpy as np
from copy import deepcopy

from gear_optimizer.solver.hit_simulation import (
    apply_human_hit_sim,
    plan_human_hit_sim,
    refine_human_hit_sim_after_ga,
    simulate_perfect_hit_timestamps_with_great_candidates,
    compute_fever_timeline_signature,
    prepare_perfect_hit_simulation,
    generate_perfect_hit_times_ms,
)
from gear_optimizer.solver.scoring.stats_scoring import evaluate_stats_score
from gear_optimizer.solver.fever_timeline import calculate_fever_timeline_indices
from gear_optimizer.core.constants import TOTAL_ROWS, FEVER_FILL_BASE_RATE, FEVER_TIME_SCALE, FEVER_TIME_OFFSET
from gear_optimizer.core.time_quantize import quantize_to_int_ms


def _build_ref_arrays() -> dict:
    rows = int(TOTAL_ROWS) + 1
    return {
        "Perfect Points": np.linspace(500.0, 200.0, rows, dtype=np.float64),
        "Combo Multiplier": np.linspace(2.6, 1.3, rows, dtype=np.float64),
        "Fever Multiplier": np.linspace(5.3, 2.1, rows, dtype=np.float64),
        "Fever Fill Rate": np.linspace(0.20, 0.55, rows, dtype=np.float64),
        "Fever Time": np.linspace(2.9, 1.8, rows, dtype=np.float64),
    }


def _build_calc_song() -> dict:
    ts = np.array([0.000, 0.080, 0.160, 0.240, 0.320, 0.400], dtype=np.float64)
    note_types = np.array([1, 1, 1, 3, 1, 1], dtype=np.int16)
    return {
        "metadata": {
            "Song Name": "Refine Determinism Song",
            "Difficulty": "Hard",
            "Primary Color": "Vibe",
            "Secondary Color": "Chill",
            "Long Notes": 1,
            "Last Note Time": float(ts[-1]),
            "HumanHitSimApplied": True,
            "HumanHitSimApplyTo": "ALL",
            "HumanHitSimSeed": 123,
            "HumanHitSimDistribution": "uniform",
            "HumanHitSimGreatMode": "full",
        },
        "song_data": {
            "chart_timestamps": ts.copy(),
            "timestamps": ts.copy(),
            "note_types": note_types.copy(),
            "fg_timestamps": ts.copy(),
            "fg_great_candidate_timestamps": ts.copy(),
        },
    }


def _build_dense_calc_song() -> dict:
    ts = np.arange(0.000, 24.000, 0.060, dtype=np.float64)
    note_types = np.ones(ts.shape[0], dtype=np.int16)
    return {
        "metadata": {
            "Song Name": "Refine Dense Song",
            "Difficulty": "Hard",
            "Primary Color": "Vibe",
            "Secondary Color": "Chill",
            "Long Notes": 0,
            "Last Note Time": float(ts[-1]),
            "HumanHitSimApplied": True,
            "HumanHitSimApplyTo": "ALL",
            "HumanHitSimSeed": 111,
            "HumanHitSimDistribution": "uniform",
            "HumanHitSimGreatMode": "full",
        },
        "song_data": {
            "chart_timestamps": ts.copy(),
            "timestamps": ts.copy(),
            "note_types": note_types.copy(),
            "fg_timestamps": ts.copy(),
            "fg_great_candidate_timestamps": ts.copy(),
        },
    }


def _build_best_data(calc_song: dict, ref_arrays: dict) -> dict:
    stats = {
        "Perfect Points": 110,
        "Combo Multiplier": 100,
        "Fever Multiplier": 95,
        "Fever Time": 85,
        "Fever Fill Rate": 90,
        "Beat": 120,
        "Vibe": 180,
        "Rush": 110,
        "Flow": 105,
        "Chill": 140,
    }
    base_score = int(
        evaluate_stats_score(
            stats,
            calc_song,
            ref_arrays,
            song_timestamps=np.asarray(calc_song["song_data"]["timestamps"], dtype=np.float64),
        )
    )
    return {"Stats": stats, "Score": int(base_score), "BaseScore": int(base_score)}


def _make_fake_exact_gpu_out(
    *,
    best_score: int,
    best_candidate_idx: int = 0,
    best_alpha_num: int = 1,
    best_alpha_den: int = 2,
    left_num: int = 0,
    left_den: int = 1,
    right_num: int = 1,
    right_den: int = 1,
    n_notes: int = 6,
    raw_interval_count: int = 5,
    selected_regimes: list[dict] | None = None,
) -> dict:
    event_ms = np.arange(n_notes, dtype=np.int32) + (int(best_alpha_num) * 100)
    great_ms = event_ms + 50
    regimes = selected_regimes
    if regimes is None:
        regimes = [
            {
                "left_num": int(left_num),
                "left_den": int(left_den),
                "right_num": int(right_num),
                "right_den": int(right_den),
                "alpha_num": int(best_alpha_num),
                "alpha_den": int(best_alpha_den),
                "best_score": int(best_score),
                "best_candidate_idx": int(best_candidate_idx),
                "family": "ftff_boundary_rows",
                "scope": "ALL",
            }
        ]
    return {
        "best_score": int(best_score),
        "best_candidate_idx": int(best_candidate_idx),
        "best_alpha_num": int(best_alpha_num),
        "best_alpha_den": int(best_alpha_den),
        "best_left_num": int(left_num),
        "best_left_den": int(left_den),
        "best_right_num": int(right_num),
        "best_right_den": int(right_den),
        "active_param_count": 1,
        "full_regime_count": int(len(regimes)),
        "selected_regime_count": int(len(regimes)),
        "raw_interval_count": int(raw_interval_count),
        "unique_scores": int(len(regimes) + 1),
        "best_event_ms": event_ms,
        "best_great_ms": great_ms,
        "sig_rows": np.asarray([[3, 1, 0, 1, 0, 0, 0]], dtype=np.int32),
        "active_row_mask": np.asarray([1], dtype=np.int32),
        "selected_regimes": list(regimes),
    }


def test_simulate_perfect_hit_timestamps_is_deterministic_and_monotonic():
    # Includes a chord (duplicate timestamp) and a held-tail note (type=3).
    timestamps = np.array([0.000, 0.050, 0.100, 0.100, 0.120], dtype=np.float64)
    note_types = np.array([1, 1, 1, 1, 3], dtype=np.int16)

    out1, _, dbg1 = simulate_perfect_hit_timestamps_with_great_candidates(timestamps, note_types, seed=123)
    out2, _, dbg2 = simulate_perfect_hit_timestamps_with_great_candidates(timestamps, note_types, seed=123)

    assert np.array_equal(out1, out2)
    assert dbg1 == dbg2

    # Monotonic non-decreasing in integer ms (server-aligned).
    out_ms = quantize_to_int_ms(out1).astype(np.int64)
    assert np.all(np.diff(out_ms) >= 0)

    # Chord notes share the same sampled hit-time.
    assert out_ms[2] == out_ms[3]


def test_simulate_perfect_hit_timestamps_respects_head_and_tail_windows():
    timestamps = np.array([1.000, 1.050, 1.100], dtype=np.float64)
    note_types = np.array([1, 3, 1], dtype=np.int16)  # middle note is held tail

    out, _, dbg = simulate_perfect_hit_timestamps_with_great_candidates(timestamps, note_types, seed=999)
    assert dbg["forced_monotonic"] == 0

    base_ms = quantize_to_int_ms(timestamps).astype(np.int64)
    out_ms = quantize_to_int_ms(out).astype(np.int64)
    delta = out_ms - base_ms

    # Head perfect window at stat=0: [-20, +40]ms
    assert -20 <= int(delta[0]) <= 40
    assert -20 <= int(delta[2]) <= 40

    # Tail window is wider by x2: [-40, +80]ms
    assert -40 <= int(delta[1]) <= 80


def test_simulate_perfect_hit_timestamps_with_great_candidates_respects_late_only_great_band():
    timestamps = np.array([1.000, 1.050, 1.100], dtype=np.float64)
    note_types = np.array([1, 3, 1], dtype=np.int16)  # middle note is held tail

    perfect, great_candidates, dbg = simulate_perfect_hit_timestamps_with_great_candidates(
        timestamps, note_types, seed=42
    )
    assert dbg["notes"] == 3

    base_ms = quantize_to_int_ms(timestamps).astype(np.int64)
    perfect_ms = quantize_to_int_ms(perfect).astype(np.int64)
    great_ms = quantize_to_int_ms(great_candidates).astype(np.int64)

    perfect_delta = perfect_ms - base_ms
    great_delta = great_ms - base_ms

    # Perfect window (stat=0): [-20, +40]ms (tails x2 => [-40, +80]ms).
    assert -20 <= int(perfect_delta[0]) <= 40
    assert -40 <= int(perfect_delta[1]) <= 80
    assert -20 <= int(perfect_delta[2]) <= 40

    # GreatTime in source is an extension beyond Perfect; at stat=0:
    # Great extra upper = 150ms, so Great upper = 40 + 150 = 190ms (tails x2 => 380ms).
    assert 41 <= int(great_delta[0]) <= 190
    assert 81 <= int(great_delta[1]) <= 380
    assert 41 <= int(great_delta[2]) <= 190


def test_simulate_perfect_hit_timestamps_with_great_candidates_full_mode_includes_early_extension_beyond_perfect():
    """
    In source `GearStats.get_note_times`, the Great window is an extension beyond Perfect
    on BOTH sides:
      great_lower_abs = perfect_lower + great_lower_extra
      great_upper_abs = perfect_upper + great_upper_extra

    At stat=0:
      perfect: [-20, +40]
      great extra lower: -75  => great lower abs: -95
      great extra upper: +150 => great upper abs: +190
      (held tails x2)
    """
    timestamps = np.array([1.000, 1.050, 1.100], dtype=np.float64)
    note_types = np.array([1, 3, 1], dtype=np.int16)  # middle note is held tail

    _, great_candidates, _ = simulate_perfect_hit_timestamps_with_great_candidates(
        timestamps, note_types, seed=1234, great_mode="full"
    )

    base_ms = quantize_to_int_ms(timestamps).astype(np.int64)
    great_ms = quantize_to_int_ms(great_candidates).astype(np.int64)
    great_delta = great_ms - base_ms

    # Head notes: Great full window [-95, +190]
    assert -95 <= int(great_delta[0]) <= 190
    assert -95 <= int(great_delta[2]) <= 190

    # Tail note: Great full window [-190, +380]
    assert -190 <= int(great_delta[1]) <= 380


def test_refine_human_hit_sim_after_ga_legacy_aliases_use_exact_gpu(monkeypatch):
    import gear_optimizer.solver.taichi_gem.api.hitsim_refine as hitsim_refine_gpu

    ref_arrays = _build_ref_arrays()
    cfg = {
        "HumanHitSim": {
            "Enabled": "true",
            "ApplyTo": "ALL",
            "Distribution": "uniform",
            "GreatMode": "full",
            "RefineAfterGA": "true",
            "RefineMode": "seed",
            "RefineDevice": "cpu",
            "RefineTrials": "12",
        }
    }
    calc_song = _build_dense_calc_song()
    best_data = _build_best_data(calc_song, ref_arrays)

    monkeypatch.setattr(
        hitsim_refine_gpu,
        "refine_human_hitsim_exact_after_ga_gpu",
        lambda **_kwargs: _make_fake_exact_gpu_out(best_score=777, n_notes=calc_song["song_data"]["timestamps"].shape[0]),
    )

    out = refine_human_hit_sim_after_ga(
        calc_song,
        cfg_dict=cfg,
        best_data=best_data,
        ref_arrays=ref_arrays,
        ga_seed=987654321,
    )

    assert isinstance(out, dict)
    assert out["refine_mode"] == "exact"
    assert out["requested_refine_mode"] == "seed"
    assert out["requested_refine_device"] == "cpu"
    assert out["variant_budget_mode"] == "exact_boundary_table"
    assert int(out["seed_attempts"]) == 5

    meta = calc_song["metadata"]
    assert meta["HumanHitSimRefineMode"] == "exact"
    assert meta["HumanHitSimRefineRequestedMode"] == "seed"
    assert meta["HumanHitSimRefineRequestedDevice"] == "cpu"
    assert int(meta["HumanHitSimRefineExactRawIntervalCount"]) == 5


def test_refine_human_hit_sim_after_ga_never_decreases_score(monkeypatch):
    import gear_optimizer.solver.taichi_gem.api.hitsim_refine as hitsim_refine_gpu

    ref_arrays = _build_ref_arrays()
    cfg = {
        "HumanHitSim": {
            "Enabled": "true",
            "ApplyTo": "ALL",
            "Distribution": "uniform",
            "GreatMode": "late",
            "RefineAfterGA": "true",
            "RefineMode": "exact",
            "RefineTrials": "8",
        }
    }
    calc_song = _build_calc_song()
    best_data = _build_best_data(calc_song, ref_arrays)
    baseline = int(best_data["Score"])

    monkeypatch.setattr(
        hitsim_refine_gpu,
        "refine_human_hitsim_exact_after_ga_gpu",
        lambda **_kwargs: _make_fake_exact_gpu_out(
            best_score=baseline - 10,
            n_notes=calc_song["song_data"]["timestamps"].shape[0],
        ),
    )

    out = refine_human_hit_sim_after_ga(
        calc_song,
        cfg_dict=cfg,
        best_data=best_data,
        ref_arrays=ref_arrays,
        ga_seed=24680,
    )

    assert isinstance(out, dict)
    assert int(best_data["Score"]) == baseline
    assert int(best_data["BaseScore"]) == baseline
    assert int(out["best_score"]) == baseline
    assert bool(calc_song["metadata"].get("HumanHitSimRefined")) is True


def test_build_exact_alpha_regimes_enumerates_all_interval_midpoints():
    import gear_optimizer.solver.hit_simulation as hit_sim

    regimes = hit_sim._build_exact_alpha_regimes(
        {
            "group_low": np.array([0, 0], dtype=np.int32),
            "group_high": np.array([1, 2], dtype=np.int32),
        }
    )

    got = [(int(row["alpha_num"]), int(row["alpha_den"])) for row in regimes]
    assert got == [(1, 8), (3, 8), (5, 8), (7, 8)]


def test_plan_exact_boundary_regimes_uses_boundary_domain_to_merge_adjacent_intervals(monkeypatch):
    import gear_optimizer.solver.hit_simulation as hit_sim
    hit_sim._EXACT_REGIME_PLAN_CACHE.clear()
    hit_sim._EXACT_REGIME_PLAN_CACHE_ORDER.clear()

    def _fake_regimes(*prepared_variants):
        _ = prepared_variants
        return [
            {"alpha_num": 1, "alpha_den": 8, "left_num": 0, "left_den": 1, "right_num": 1, "right_den": 4},
            {"alpha_num": 3, "alpha_den": 8, "left_num": 1, "left_den": 4, "right_num": 1, "right_den": 2},
            {"alpha_num": 3, "alpha_den": 4, "left_num": 1, "left_den": 2, "right_num": 1, "right_den": 1},
        ]

    def _fake_generate(_prepared, *, alpha_num: int, alpha_den: int, monotonic: bool):
        _ = monotonic
        return np.full((8,), int(alpha_num * 100 + alpha_den), dtype=np.int32), 0

    def _fake_signature(event_ms, *, non_fever_base: int, real_fever_time_ms: int):
        _ = real_fever_time_ms
        marker = int(np.asarray(event_ms, dtype=np.int32)[0])
        code = 1
        if int(non_fever_base) == 9 and marker == 304:
            code = 2
        head = np.zeros((8,), dtype=np.bool_)
        head[:code] = True
        sig = (8, code, 0, bytes([code]))
        return sig, head, code, 0

    monkeypatch.setattr(hit_sim, "_build_exact_alpha_regimes", _fake_regimes)
    monkeypatch.setattr(hit_sim, "generate_deterministic_hit_times_ms", _fake_generate)
    monkeypatch.setattr(hit_sim, "compute_fever_timeline_signature", _fake_signature)
    monkeypatch.setattr(
        hit_sim,
        "compute_fever_timeline_signature_compact",
        lambda event_ms, *, non_fever_base, real_fever_time_ms: hit_sim.compute_fever_timeline_signature(
            event_ms,
            non_fever_base=non_fever_base,
            real_fever_time_ms=real_fever_time_ms,
        )[0],
    )

    single_row = hit_sim._plan_exact_boundary_regimes(
        prepared={},
        great_prepared={},
        signature_param_rows=((1, 1),),
        song_name="Refine Dense Song",
        dist="uniform",
        great_mode="full",
    )
    full_domain = hit_sim._plan_exact_boundary_regimes(
        prepared={},
        great_prepared={},
        signature_param_rows=((1, 1), (9, 9)),
        song_name="Refine Dense Song",
        dist="uniform",
        great_mode="full",
    )

    assert int(single_row["raw_interval_count"]) == 3
    assert len(single_row["regimes"]) == 1

    assert int(full_domain["raw_interval_count"]) == 3
    assert int(full_domain["active_param_count"]) == 1
    assert int(full_domain["active_family_row_count"]) == 1
    assert full_domain["family_mode"] == "ftff_boundary_rows"
    assert int(full_domain["full_regime_count"]) == 2
    assert int(full_domain["selected_regime_count"]) == 2
    assert len(full_domain["regimes"]) == 2
    first_regime = full_domain["regimes"][0]
    second_regime = full_domain["regimes"][1]
    assert first_regime["family"] == "ftff_boundary_rows"
    assert first_regime["scope"] == "ALL"
    assert int(first_regime["active_param_count"]) == 1
    assert int(first_regime["raw_interval_count"]) == 2
    assert (int(first_regime["left_num"]), int(first_regime["left_den"])) == (0, 1)
    assert (int(first_regime["right_num"]), int(first_regime["right_den"])) == (1, 2)
    assert (int(first_regime["alpha_num"]), int(first_regime["alpha_den"])) == (1, 4)
    assert second_regime["regime_id"]
    assert first_regime["regime_id"] != second_regime["regime_id"]


def test_plan_exact_boundary_regimes_can_cap_selected_regimes_evenly(monkeypatch):
    import gear_optimizer.solver.hit_simulation as hit_sim
    hit_sim._EXACT_REGIME_PLAN_CACHE.clear()
    hit_sim._EXACT_REGIME_PLAN_CACHE_ORDER.clear()

    def _fake_regimes(*prepared_variants):
        _ = prepared_variants
        return [
            {"alpha_num": 1, "alpha_den": 10, "left_num": 0, "left_den": 1, "right_num": 1, "right_den": 5},
            {"alpha_num": 3, "alpha_den": 10, "left_num": 1, "left_den": 5, "right_num": 2, "right_den": 5},
            {"alpha_num": 5, "alpha_den": 10, "left_num": 2, "left_den": 5, "right_num": 3, "right_den": 5},
            {"alpha_num": 7, "alpha_den": 10, "left_num": 3, "left_den": 5, "right_num": 4, "right_den": 5},
            {"alpha_num": 9, "alpha_den": 10, "left_num": 4, "left_den": 5, "right_num": 1, "right_den": 1},
        ]

    def _fake_generate(_prepared, *, alpha_num: int, alpha_den: int, monotonic: bool):
        _ = (alpha_den, monotonic)
        return np.full((8,), int(alpha_num), dtype=np.int32), 0

    def _fake_compact_signature(event_ms, *, non_fever_base: int, real_fever_time_ms: int):
        _ = real_fever_time_ms
        marker = int(np.asarray(event_ms, dtype=np.int32)[0])
        return (8, int(marker + non_fever_base), 0, int(marker), 0, 0, 0)

    monkeypatch.setattr(hit_sim, "_build_exact_alpha_regimes", _fake_regimes)
    monkeypatch.setattr(hit_sim, "generate_deterministic_hit_times_ms", _fake_generate)
    monkeypatch.setattr(hit_sim, "compute_fever_timeline_signature_compact", _fake_compact_signature)

    planned = hit_sim._plan_exact_boundary_regimes(
        prepared={},
        great_prepared={},
        signature_param_rows=((1, 1),),
        song_name="Refine Dense Song",
        dist="uniform",
        great_mode="full",
        max_regimes=2,
        selection_mode="even",
    )

    assert int(planned["full_regime_count"]) == 5
    assert int(planned["selected_regime_count"]) == 2
    assert int(planned["regime_cap"]) == 2
    assert planned["selection_mode"] == "even"
    assert len(planned["regimes"]) == 2
    assert planned["regimes"][0]["left_num"] == 0
    assert planned["regimes"][1]["right_num"] == 1
    assert planned["regimes"][1]["right_den"] == 1


def test_plan_exact_boundary_regimes_ignores_great_only_cut_inflation(monkeypatch):
    import gear_optimizer.solver.hit_simulation as hit_sim
    hit_sim._EXACT_REGIME_PLAN_CACHE.clear()
    hit_sim._EXACT_REGIME_PLAN_CACHE_ORDER.clear()

    prepared = {
        "n": 8,
        "group_low": np.array([0], dtype=np.int32),
        "group_high": np.array([1], dtype=np.int32),
    }
    great_prepared = {
        "n": 8,
        "group_low": np.array([0], dtype=np.int32),
        "group_high": np.array([4], dtype=np.int32),
    }

    def _fake_generate(_prepared, *, alpha_num: int, alpha_den: int, monotonic: bool):
        _ = monotonic
        return np.full((8,), int(alpha_num * 100 + alpha_den), dtype=np.int32), 0

    def _fake_compact_signature(event_ms, *, non_fever_base: int, real_fever_time_ms: int):
        _ = (non_fever_base, real_fever_time_ms)
        marker = int(np.asarray(event_ms, dtype=np.int32)[0])
        return (8, marker, 0, marker, 0, 0, 0)

    monkeypatch.setattr(hit_sim, "generate_deterministic_hit_times_ms", _fake_generate)
    monkeypatch.setattr(hit_sim, "compute_fever_timeline_signature_compact", _fake_compact_signature)

    prepared_only_count = len(hit_sim._build_exact_alpha_regimes(prepared))
    assert len(hit_sim._build_exact_alpha_regimes(prepared, great_prepared)) > prepared_only_count

    planned = hit_sim._plan_exact_boundary_regimes(
        prepared=prepared,
        great_prepared=great_prepared,
        signature_param_rows=((1, 1),),
        song_name="Refine Dense Song",
        dist="uniform",
        great_mode="full",
    )

    assert int(planned["raw_interval_count"]) == int(prepared_only_count)


def test_plan_exact_boundary_regimes_caches_detached_results(monkeypatch):
    import gear_optimizer.solver.hit_simulation as hit_sim

    hit_sim._EXACT_REGIME_PLAN_CACHE.clear()
    hit_sim._EXACT_REGIME_PLAN_CACHE_ORDER.clear()

    calls = {"count": 0}

    def _fake_regimes(*prepared_variants):
        _ = prepared_variants
        calls["count"] += 1
        return [
            {"alpha_num": 1, "alpha_den": 4, "left_num": 0, "left_den": 1, "right_num": 1, "right_den": 2},
            {"alpha_num": 3, "alpha_den": 4, "left_num": 1, "left_den": 2, "right_num": 1, "right_den": 1},
        ]

    def _fake_generate(_prepared, *, alpha_num: int, alpha_den: int, monotonic: bool):
        _ = (alpha_den, monotonic)
        return np.full((8,), int(alpha_num), dtype=np.int32), 0

    def _fake_compact_signature(event_ms, *, non_fever_base: int, real_fever_time_ms: int):
        _ = (non_fever_base, real_fever_time_ms)
        marker = int(np.asarray(event_ms, dtype=np.int32)[0])
        return (8, marker, 0, marker, 0, 0, 0)

    monkeypatch.setattr(hit_sim, "_build_exact_alpha_regimes", _fake_regimes)
    monkeypatch.setattr(hit_sim, "generate_deterministic_hit_times_ms", _fake_generate)
    monkeypatch.setattr(hit_sim, "compute_fever_timeline_signature_compact", _fake_compact_signature)

    prepared = {
        "n": 8,
        "group_starts": np.array([0], dtype=np.int32),
        "group_ends": np.array([8], dtype=np.int32),
        "group_base_t": np.array([100], dtype=np.int32),
        "group_low": np.array([0], dtype=np.int32),
        "group_high": np.array([1], dtype=np.int32),
    }

    first = hit_sim._plan_exact_boundary_regimes(
        prepared=prepared,
        great_prepared={},
        signature_param_rows=((1, 1),),
        song_name="Cache Song",
        dist="uniform",
        great_mode="full",
    )
    first["regimes"][0]["family"] = "mutated"

    second = hit_sim._plan_exact_boundary_regimes(
        prepared=prepared,
        great_prepared={},
        signature_param_rows=((1, 1),),
        song_name="Cache Song",
        dist="uniform",
        great_mode="full",
        max_regimes=1,
        selection_mode="head",
    )

    assert int(calls["count"]) == 1
    assert second["regimes"][0]["family"] == "ftff_boundary_rows"
    assert int(second["selected_regime_count"]) == 1


def test_refine_human_hit_sim_after_ga_exact_mode_uses_planned_regimes(monkeypatch):
    import gear_optimizer.solver.taichi_gem.api.hitsim_refine as hitsim_refine_gpu

    ref_arrays = _build_ref_arrays()
    cfg = {
        "HumanHitSim": {
            "Enabled": "true",
            "ApplyTo": "ALL",
            "Distribution": "uniform",
            "GreatMode": "full",
            "RefineAfterGA": "true",
            "RefineMode": "exact",
            "RefineTrials": "1",
        }
    }

    calc_song = _build_dense_calc_song()
    best_data = {"Stats": {"Fever Time": 0, "Fever Fill Rate": 0}, "Score": 0, "BaseScore": 0}

    def _fake_full_domain(**kwargs):
        _ = kwargs
        return {"param_rows": ((1, 1), (9, 9)), "full_pair_count": 25921, "unique_param_count": 2}
    monkeypatch.setattr(
        "gear_optimizer.solver.hit_simulation._build_full_ftff_boundary_domain",
        _fake_full_domain,
    )
    monkeypatch.setattr(
        hitsim_refine_gpu,
        "refine_human_hitsim_exact_after_ga_gpu",
        lambda **_kwargs: _make_fake_exact_gpu_out(
            best_score=2,
            best_alpha_num=2,
            best_alpha_den=3,
            left_num=1,
            left_den=2,
            right_num=1,
            right_den=1,
            n_notes=calc_song["song_data"]["timestamps"].shape[0],
            selected_regimes=[
                {
                    "left_num": 0,
                    "left_den": 1,
                    "right_num": 1,
                    "right_den": 2,
                    "alpha_num": 1,
                    "alpha_den": 3,
                    "best_score": 1,
                    "best_candidate_idx": 0,
                    "family": "ftff_boundary_rows",
                    "scope": "ALL",
                },
                {
                    "left_num": 1,
                    "left_den": 2,
                    "right_num": 1,
                    "right_den": 1,
                    "alpha_num": 2,
                    "alpha_den": 3,
                    "best_score": 2,
                    "best_candidate_idx": 0,
                    "family": "ftff_boundary_rows",
                    "scope": "ALL",
                },
            ],
        ),
    )

    out = refine_human_hit_sim_after_ga(
        calc_song,
        cfg_dict=cfg,
        best_data=best_data,
        ref_arrays=ref_arrays,
        ga_seed=42,
    )

    assert isinstance(out, dict)
    assert out["refine_mode"] == "exact"
    assert out["variant_budget_mode"] == "exact_boundary_table"
    assert int(out["seed_attempts"]) == 5
    assert int(out["evaluated_trials"]) == 2
    assert int(out["timeline_variants"]) == 2
    assert int(out["exact_regime_count"]) == 2
    assert int(out["exact_full_regime_count"]) == 2
    assert int(out["exact_raw_interval_count"]) == 5
    assert int(out["exact_regime_cap"]) == 0
    assert out["exact_regime_selection"] == "all"
    assert int(out["boundary_domain_unique_params"]) == 2
    assert int(out["boundary_domain_active_params"]) == 1
    assert int(out["boundary_domain_full_pairs"]) == 25921
    assert out["exact_family_mode"] == "candidate_timeline_rows"
    assert str(out["regime_id"]).startswith("exact:")
    assert out["regime_family"] == "candidate_timeline_rows"
    assert out["regime_scope"] == "ALL"
    assert (int(out["regime_left_num"]), int(out["regime_left_den"])) == (1, 2)
    assert (int(out["regime_right_num"]), int(out["regime_right_den"])) == (1, 1)

    meta = calc_song["metadata"]
    assert meta["HumanHitSimRefineMode"] == "exact"
    assert int(meta["HumanHitSimRefineExactRegimeCount"]) == 2
    assert int(meta["HumanHitSimRefineExactFullRegimeCount"]) == 2
    assert int(meta["HumanHitSimRefineExactRawIntervalCount"]) == 5
    assert int(meta["HumanHitSimRefineExactRegimeCap"]) == 0
    assert meta["HumanHitSimRefineExactRegimeSelection"] == "all"
    assert int(meta["HumanHitSimRefineBoundaryDomainUniqueParams"]) == 2
    assert int(meta["HumanHitSimRefineBoundaryDomainActiveParams"]) == 1
    assert int(meta["HumanHitSimRefineBoundaryDomainFullPairs"]) == 25921
    assert meta["HumanHitSimRefineExactFamilyMode"] == "candidate_timeline_rows"
    assert str(meta["HumanHitSimRegimeId"]).startswith("exact:")
    assert meta["HumanHitSimRegimeFamily"] == "candidate_timeline_rows"
    assert meta["HumanHitSimRegimeScope"] == "ALL"
    assert np.isclose(
        float(np.asarray(calc_song["song_data"]["fg_great_candidate_timestamps"], dtype=np.float64)[0]),
        0.250,
    )


def test_formula_timeline_signature_matches_reference_timeline():
    # Include chords and varying gaps to exercise searchsorted boundaries.
    event_ms = np.array([0, 80, 160, 160, 230, 410, 580, 580, 800, 1050, 1400], dtype=np.int32)
    ts = event_ms.astype(np.float64) * 0.001
    total_notes = int(event_ms.shape[0])
    long_notes = 2
    last_note = float(ts[-1])
    fever_fill_rate = 0.33
    fever_time_stat = 2.25

    non_fever_cas = (total_notes - long_notes) * FEVER_FILL_BASE_RATE
    non_fever_base = int(np.ceil(non_fever_cas * fever_fill_rate))
    fever_time_cas = (last_note * FEVER_TIME_SCALE) + FEVER_TIME_OFFSET
    real_fever_time = float(fever_time_cas * fever_time_stat)
    real_fever_time_ms = int(np.ceil(real_fever_time * 1000.0 - 1e-9))

    sig, head_formula, body_fever_formula, body_normal_formula = compute_fever_timeline_signature(
        event_ms,
        non_fever_base=int(non_fever_base),
        real_fever_time_ms=int(real_fever_time_ms),
    )

    mask = np.zeros(total_notes, dtype=np.bool_)
    head_ref, body_fever_ref, body_normal_ref, _, _ = calculate_fever_timeline_indices(
        ts,
        total_notes,
        float(fever_fill_rate),
        float(fever_time_stat),
        int(long_notes),
        float(last_note),
        mask,
    )
    head_ref_u8 = np.asarray(head_ref, dtype=np.uint8)
    sig_ref = (
        int(head_ref_u8.shape[0]),
        int(body_fever_ref),
        int(body_normal_ref),
        bytes(np.packbits(head_ref_u8, bitorder="little").tobytes()),
    )

    assert sig == sig_ref
    assert np.array_equal(np.asarray(head_formula, dtype=np.bool_), np.asarray(head_ref, dtype=np.bool_))
    assert int(body_fever_formula) == int(body_fever_ref)
    assert int(body_normal_formula) == int(body_normal_ref)


def test_compact_timeline_signature_matches_reference_timeline():
    import gear_optimizer.solver.hit_simulation as hit_sim

    event_ms = np.array([0, 80, 160, 160, 230, 410, 580, 580, 800, 1050, 1400], dtype=np.int32)
    sig_full, _head_formula, _body_fever_formula, _body_normal_formula = compute_fever_timeline_signature(
        event_ms,
        non_fever_base=3,
        real_fever_time_ms=625,
    )
    sig_compact = hit_sim.compute_fever_timeline_signature_compact(
        event_ms,
        non_fever_base=3,
        real_fever_time_ms=625,
    )

    assert hit_sim._normalize_signature_row(sig_compact) == sig_full


def test_generate_perfect_hit_times_ms_matches_full_simulator():
    timestamps = np.array([0.000, 0.050, 0.100, 0.100, 0.120, 0.240, 0.241], dtype=np.float64)
    note_types = np.array([1, 1, 1, 1, 3, 1, 1], dtype=np.int16)
    seed = 12345

    prepared = prepare_perfect_hit_simulation(
        timestamps,
        note_types,
        perfect_lower_ms=-20,
        perfect_upper_ms=40,
        held_tail_type=3,
        held_tail_time_multiplier=2,
        quantize_ms=True,
    )
    event_ms_fast = np.asarray(generate_perfect_hit_times_ms(prepared, seed=seed), dtype=np.int32)

    out_sec, _, _ = simulate_perfect_hit_timestamps_with_great_candidates(
        timestamps, note_types, seed=seed, distribution="uniform", great_mode="full"
    )
    event_ms_full = quantize_to_int_ms(out_sec)
    assert np.array_equal(event_ms_fast, event_ms_full)


def test_refine_human_hit_sim_after_ga_can_switch_to_candidate_pool_winner(monkeypatch):
    import gear_optimizer.solver.taichi_gem.api.hitsim_refine as hitsim_refine_gpu

    ref_arrays = _build_ref_arrays()
    cfg = {
        "HumanHitSim": {
            "Enabled": "true",
            "ApplyTo": "ALL",
            "Distribution": "uniform",
            "GreatMode": "full",
            "RefineAfterGA": "true",
            "RefineMode": "exact",
            "RefineTrials": "1",
            "RefineCandidateLimit": "4",
        }
    }

    calc_song = _build_calc_song()
    best_data = _build_best_data(calc_song, ref_arrays)
    best_data["Score"] = 10
    best_data["BaseScore"] = 10

    alt_data = deepcopy(best_data)
    alt_stats = dict(alt_data["Stats"])
    alt_stats["Vibe"] = int(alt_stats.get("Vibe", 0)) + 100
    alt_data["Stats"] = alt_stats
    alt_data["Score"] = 5
    alt_data["BaseScore"] = 5

    candidate_pool = [
        {
            "Score": 5,
            "BaseScore": 5,
            "Gear": ["Alt Gear"],
            "Minis": ["Alt Mini"],
            "Data": alt_data,
        }
    ]

    monkeypatch.setattr(
        hitsim_refine_gpu,
        "refine_human_hitsim_exact_after_ga_gpu",
        lambda **_kwargs: _make_fake_exact_gpu_out(
            best_score=130,
            best_candidate_idx=1,
            n_notes=calc_song["song_data"]["timestamps"].shape[0],
            selected_regimes=[
                {
                    "left_num": 0,
                    "left_den": 1,
                    "right_num": 1,
                    "right_den": 1,
                    "alpha_num": 1,
                    "alpha_den": 2,
                    "best_score": 130,
                    "best_candidate_idx": 1,
                    "family": "ftff_boundary_rows",
                    "scope": "ALL",
                }
            ],
        ),
    )

    out = refine_human_hit_sim_after_ga(
        calc_song,
        cfg_dict=cfg,
        best_data=best_data,
        ref_arrays=ref_arrays,
        ga_seed=1,
        candidate_pool=candidate_pool,
    )

    assert isinstance(out, dict)
    assert bool(out["candidate_changed"]) is True
    assert int(out["candidate_count"]) == 2
    assert out["selected_candidate"]["Gear"] == ["Alt Gear"]
    assert out["selected_candidate"]["Minis"] == ["Alt Mini"]
    assert int(best_data["BaseScore"]) == int(out["best_score"])
    assert int(alt_data["BaseScore"]) == int(out["best_score"])
    assert bool(calc_song["metadata"]["HumanHitSimRefineCandidateChanged"]) is True


def test_refine_human_hit_sim_after_ga_returns_regime_winners_and_merged_candidates(monkeypatch):
    import gear_optimizer.solver.taichi_gem.api.hitsim_refine as hitsim_refine_gpu

    ref_arrays = _build_ref_arrays()
    calc_song = _build_calc_song()
    best_data = _build_best_data(calc_song, ref_arrays)
    base_entry = {
        "Score": int(best_data["BaseScore"]),
        "BaseScore": int(best_data["BaseScore"]),
        "Gear": ["Base Gear"],
        "Minis": ["Base Mini"],
        "Data": best_data,
    }

    alt_data = deepcopy(best_data)
    alt_data["Stats"] = dict(alt_data["Stats"])
    alt_data["Stats"]["Perfect Points"] = int(alt_data["Stats"]["Perfect Points"]) + 1
    alt_data["Score"] = int(best_data["BaseScore"]) - 5
    alt_data["BaseScore"] = int(best_data["BaseScore"]) - 5
    alt_entry = {
        "Score": int(alt_data["BaseScore"]),
        "BaseScore": int(alt_data["BaseScore"]),
        "Gear": ["Alt Gear"],
        "Minis": ["Alt Mini"],
        "Data": alt_data,
    }

    cfg = {
        "HumanHitSim": {
            "Enabled": "true",
            "ApplyTo": "ALL",
            "Distribution": "uniform",
            "GreatMode": "full",
            "RefineAfterGA": "true",
            "RefineTrials": "2",
            "RefineMode": "exact",
        }
    }
    base_score = int(best_data["BaseScore"])
    monkeypatch.setattr(
        hitsim_refine_gpu,
        "refine_human_hitsim_exact_after_ga_gpu",
        lambda **_kwargs: _make_fake_exact_gpu_out(
            best_score=base_score + 23,
            best_candidate_idx=1,
            best_alpha_num=3,
            best_alpha_den=4,
            left_num=1,
            left_den=2,
            right_num=1,
            right_den=1,
            n_notes=calc_song["song_data"]["timestamps"].shape[0],
            selected_regimes=[
                {
                    "left_num": 0,
                    "left_den": 1,
                    "right_num": 1,
                    "right_den": 2,
                    "alpha_num": 1,
                    "alpha_den": 4,
                    "best_score": base_score + 11,
                    "best_candidate_idx": 0,
                    "family": "ftff_boundary_rows",
                    "scope": "ALL",
                },
                {
                    "left_num": 1,
                    "left_den": 2,
                    "right_num": 1,
                    "right_den": 1,
                    "alpha_num": 3,
                    "alpha_den": 4,
                    "best_score": base_score + 23,
                    "best_candidate_idx": 1,
                    "family": "ftff_boundary_rows",
                    "scope": "ALL",
                },
            ],
        ),
    )

    out = refine_human_hit_sim_after_ga(
        calc_song,
        cfg_dict=cfg,
        best_data=best_data,
        ref_arrays=ref_arrays,
        ga_seed=99,
        candidate_pool=[base_entry, alt_entry],
    )

    assert isinstance(out, dict)
    assert int(out["regime_winner_count"]) == 2
    assert int(out["merged_candidate_count"]) == 2
    assert [winner["Gear"] for winner in out["regime_winners"]] == [["Base Gear"], ["Alt Gear"]]
    assert [candidate["Gear"] for candidate in out["merged_candidates"]] == [["Alt Gear"], ["Base Gear"]]
    assert int(out["merged_candidates"][0]["Data"]["HumanHitSimMergedRegimeCount"]) == 1
    assert str(out["merged_candidates"][0]["Data"]["HumanHitSimRegimeFamily"]) == "ftff_boundary_rows"
    assert int(calc_song["metadata"]["HumanHitSimRefineRegimeWinnerCount"]) == 2
    assert int(calc_song["metadata"]["HumanHitSimRefineMergedCandidateCount"]) == 2
    assert int(best_data["BaseScore"]) == base_score + 23


def test_materialize_human_hit_sim_regime_uses_gpu_exact_materializer(monkeypatch):
    from gear_optimizer.solver.hit_simulation import materialize_human_hit_sim_regime
    import gear_optimizer.solver.taichi_gem.api.hitsim_refine as hitsim_refine_gpu

    calc_song = _build_calc_song()
    original = np.asarray(calc_song["song_data"]["timestamps"], dtype=np.float32).copy()
    monkeypatch.setattr(
        hitsim_refine_gpu,
        "materialize_human_hitsim_regime_gpu",
        lambda **_kwargs: {
            "event_ms": np.asarray([11, 22, 33, 44, 55, 66], dtype=np.int32),
            "great_ms": np.asarray([21, 32, 43, 54, 65, 76], dtype=np.int32),
        },
    )
    out = materialize_human_hit_sim_regime(
        calc_song,
        regime_data={
            "HumanHitSimRefineMode": "analytical",
            "HumanHitSimDistribution": "uniform",
            "HumanHitSimGreatMode": "full",
            "HumanHitSimSeed": 777,
            "HumanHitSimRegimeId": "exact:test",
            "HumanHitSimRegimeFamily": "ftff_boundary_rows",
            "HumanHitSimRegimeScope": "ALL",
            "HumanHitSimRegimeAlphaNumerator": 1,
            "HumanHitSimRegimeAlphaDenominator": 2,
            "HumanHitSimRegimeLeftNumerator": 1,
            "HumanHitSimRegimeLeftDenominator": 2,
            "HumanHitSimRegimeRightNumerator": 1,
            "HumanHitSimRegimeRightDenominator": 2,
        },
    )

    assert isinstance(out, dict)
    assert out["refine_mode"] == "exact"
    assert str(calc_song["metadata"]["HumanHitSimRegimeId"]) == "exact:test"
    assert str(calc_song["metadata"]["HumanHitSimRefineMode"]) == "exact"
    assert str(calc_song["metadata"]["HumanHitSimRefineRequestedMode"]) == "analytical"
    assert np.asarray(calc_song["song_data"]["timestamps"], dtype=np.float32).shape == original.shape
    assert not np.array_equal(np.asarray(calc_song["song_data"]["timestamps"], dtype=np.float32), original)
    assert np.allclose(np.asarray(calc_song["song_data"]["fg_great_candidate_timestamps"], dtype=np.float32), 0.001 * np.asarray([21, 32, 43, 54, 65, 76], dtype=np.float32))


def test_materialize_human_hit_sim_regime_rejects_legacy_seed_payload():
    from gear_optimizer.solver.hit_simulation import materialize_human_hit_sim_regime

    calc_song = _build_calc_song()
    out = materialize_human_hit_sim_regime(
        calc_song,
        regime_data={
            "HumanHitSimRefineMode": "seed",
            "HumanHitSimSeed": 123,
        },
    )
    assert out is None


def test_hitsim_seed_zero_is_deterministic_when_refinement_enabled_for_apply_all():
    cfg = {
        "HumanHitSim": {
            "Enabled": "true",
            "ApplyTo": "ALL",
            "Seed": "0",
            "Distribution": "uniform",
            "GreatMode": "full",
            "RefineAfterGA": "true",
            "RefineTrials": "8",
        }
    }
    ts = np.array([0.000, 0.100, 0.200], dtype=np.float64)
    calc_song = {
        "metadata": {"Song Name": "Seed Determinism Song"},
        "song_data": {"timestamps": ts.copy(), "chart_timestamps": ts.copy(), "note_types": np.ones(ts.shape[0], dtype=np.int16)},
    }

    info = plan_human_hit_sim(calc_song, cfg_dict=cfg)
    assert isinstance(info, dict)
    assert int(calc_song["metadata"]["HumanHitSimSeed"]) > 0
    assert bool(calc_song["metadata"]["HumanHitSimSeedIsRandom"]) is False

    info2 = apply_human_hit_sim(calc_song, cfg_dict=cfg)
    assert isinstance(info2, dict)
    assert int(calc_song["metadata"]["HumanHitSimSeed"]) == int(info["seed"])
    assert bool(calc_song["metadata"]["HumanHitSimSeedIsRandom"]) is False


def test_compute_fever_timeline_signature_matches_reference_randomized():
    rng = np.random.default_rng(12345)
    for _ in range(100):
        n = int(rng.integers(1, 250))
        # Monotonic event_ms with occasional chords (0 delta).
        deltas = rng.integers(0, 60, size=n, endpoint=False, dtype=np.int32)
        event_ms = np.cumsum(deltas, dtype=np.int64).astype(np.int32, copy=False)
        ts = event_ms.astype(np.float64) * 0.001

        total_notes = int(n)
        long_notes = int(rng.integers(0, min(10, total_notes + 1)))
        last_note = float(ts[-1]) if total_notes else 0.0
        fever_fill_rate = float(rng.uniform(0.15, 0.75))
        fever_time_stat = float(rng.uniform(1.2, 3.5))

        non_fever_cas = (total_notes - long_notes) * FEVER_FILL_BASE_RATE
        non_fever_base = int(np.ceil(non_fever_cas * fever_fill_rate))
        fever_time_cas = (last_note * FEVER_TIME_SCALE) + FEVER_TIME_OFFSET
        real_fever_time = float(fever_time_cas * fever_time_stat)
        real_fever_time_ms = int(np.ceil(real_fever_time * 1000.0 - 1e-9))
        if real_fever_time_ms < 0:
            real_fever_time_ms = 0

        sig, head_formula, body_fever_formula, body_normal_formula = compute_fever_timeline_signature(
            event_ms,
            non_fever_base=int(non_fever_base),
            real_fever_time_ms=int(real_fever_time_ms),
        )

        mask = np.zeros(total_notes, dtype=np.bool_)
        head_ref, body_fever_ref, body_normal_ref, _, _ = calculate_fever_timeline_indices(
            ts,
            total_notes,
            float(fever_fill_rate),
            float(fever_time_stat),
            int(long_notes),
            float(last_note),
            mask,
        )
        head_ref_u8 = np.asarray(head_ref, dtype=np.uint8)
        sig_ref = (
            int(head_ref_u8.shape[0]),
            int(body_fever_ref),
            int(body_normal_ref),
            bytes(np.packbits(head_ref_u8, bitorder="little").tobytes()),
        )

        assert sig == sig_ref
        assert np.array_equal(np.asarray(head_formula, dtype=np.bool_), np.asarray(head_ref, dtype=np.bool_))
        assert int(body_fever_formula) == int(body_fever_ref)
        assert int(body_normal_formula) == int(body_normal_ref)


def test_generate_perfect_hit_times_ms_matches_full_simulator_many_seeds():
    rng = np.random.default_rng(999)
    # Build a chart with chords + tails.
    ts = np.array([0.000, 0.050, 0.100, 0.100, 0.120, 0.240, 0.241, 0.300, 0.300, 0.600], dtype=np.float64)
    note_types = np.array([1, 1, 1, 1, 3, 1, 1, 1, 3, 1], dtype=np.int16)
    prepared = prepare_perfect_hit_simulation(
        ts,
        note_types,
        perfect_lower_ms=-20,
        perfect_upper_ms=40,
        held_tail_type=3,
        held_tail_time_multiplier=2,
        quantize_ms=True,
    )

    for _ in range(25):
        seed = int(rng.integers(1, 2**32 - 1, endpoint=True))
        event_ms_fast = np.asarray(generate_perfect_hit_times_ms(prepared, seed=seed), dtype=np.int32)
        out_sec, _, _ = simulate_perfect_hit_timestamps_with_great_candidates(
            ts, note_types, seed=seed, distribution="uniform", great_mode="full"
        )
        event_ms_full = quantize_to_int_ms(out_sec)
        assert np.array_equal(event_ms_fast, event_ms_full)
