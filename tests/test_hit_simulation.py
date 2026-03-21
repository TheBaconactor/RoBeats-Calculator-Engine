import numpy as np
from copy import deepcopy

from gear_optimizer.solver.hit_simulation import (
    apply_human_hit_sim,
    plan_human_hit_sim,
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
    selected_windows: list[dict] | None = None,
) -> dict:
    event_ms = np.arange(n_notes, dtype=np.int32) + (int(best_alpha_num) * 100)
    great_ms = event_ms + 50
    windows = selected_windows
    if windows is None:
        windows = [
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
        "full_window_count": int(len(windows)),
        "selected_window_count": int(len(windows)),
        "raw_interval_count": int(raw_interval_count),
        "unique_scores": int(len(windows) + 1),
        "best_event_ms": event_ms,
        "best_great_ms": great_ms,
        "sig_rows": np.asarray([[3, 1, 0, 1, 0, 0, 0]], dtype=np.int32),
        "active_row_mask": np.asarray([1], dtype=np.int32),
        "selected_windows": list(windows),
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


def test_hitsim_seed_zero_randomizes_for_apply_all_and_preserves_planned_seed():
    cfg = {
        "HumanHitSim": {
            "Enabled": "true",
            "ApplyTo": "ALL",
            "Seed": "0",
            "Distribution": "uniform",
            "GreatMode": "full",
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
    assert bool(calc_song["metadata"]["HumanHitSimSeedIsRandom"]) is True

    info2 = apply_human_hit_sim(calc_song, cfg_dict=cfg)
    assert isinstance(info2, dict)
    assert int(calc_song["metadata"]["HumanHitSimSeed"]) == int(info["seed"])
    assert bool(calc_song["metadata"]["HumanHitSimSeedIsRandom"]) is True


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
