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


def test_simulate_perfect_hit_timestamps_is_deterministic_and_monotonic():
    # Includes a chord (duplicate timestamp) and a held-tail note (type=3).
    timestamps = np.array([0.000, 0.050, 0.100, 0.100, 0.120], dtype=np.float64)
    note_types = np.array([1, 1, 1, 1, 3], dtype=np.int16)

    out1, _, dbg1 = simulate_perfect_hit_timestamps_with_great_candidates(timestamps, note_types, seed=123)
    out2, _, dbg2 = simulate_perfect_hit_timestamps_with_great_candidates(timestamps, note_types, seed=123)

    assert np.array_equal(out1, out2)
    assert dbg1 == dbg2

    # Monotonic non-decreasing in integer ms (server-aligned).
    out_ms = np.floor(out1 * 1000.0 + 1e-6).astype(np.int64)
    assert np.all(np.diff(out_ms) >= 0)

    # Chord notes share the same sampled hit-time.
    assert out_ms[2] == out_ms[3]


def test_simulate_perfect_hit_timestamps_respects_head_and_tail_windows():
    timestamps = np.array([1.000, 1.050, 1.100], dtype=np.float64)
    note_types = np.array([1, 3, 1], dtype=np.int16)  # middle note is held tail

    out, _, dbg = simulate_perfect_hit_timestamps_with_great_candidates(timestamps, note_types, seed=999)
    assert dbg["forced_monotonic"] == 0

    base_ms = np.floor(timestamps * 1000.0 + 1e-6).astype(np.int64)
    out_ms = np.floor(out * 1000.0 + 1e-6).astype(np.int64)
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

    base_ms = np.floor(timestamps * 1000.0 + 1e-6).astype(np.int64)
    perfect_ms = np.floor(perfect * 1000.0 + 1e-6).astype(np.int64)
    great_ms = np.floor(great_candidates * 1000.0 + 1e-6).astype(np.int64)

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

    base_ms = np.floor(timestamps * 1000.0 + 1e-6).astype(np.int64)
    great_ms = np.floor(great_candidates * 1000.0 + 1e-6).astype(np.int64)
    great_delta = great_ms - base_ms

    # Head notes: Great full window [-95, +190]
    assert -95 <= int(great_delta[0]) <= 190
    assert -95 <= int(great_delta[2]) <= 190

    # Tail note: Great full window [-190, +380]
    assert -190 <= int(great_delta[1]) <= 380


def test_refine_human_hit_sim_after_ga_is_deterministic_for_same_song_seed_and_trials():
    ref_arrays = _build_ref_arrays()
    cfg = {
        "HumanHitSim": {
            "Enabled": "true",
            "ApplyTo": "ALL",
            "Distribution": "uniform",
            "GreatMode": "full",
            "RefineAfterGA": "true",
            "RefineTrials": "12",
            "RefineSeedBase": "0",
        }
    }
    calc_song_a = _build_calc_song()
    calc_song_b = deepcopy(calc_song_a)
    best_data_a = _build_best_data(calc_song_a, ref_arrays)
    best_data_b = deepcopy(best_data_a)

    out_a = refine_human_hit_sim_after_ga(
        calc_song_a,
        cfg_dict=cfg,
        best_data=best_data_a,
        ref_arrays=ref_arrays,
        ga_seed=987654321,
    )
    out_b = refine_human_hit_sim_after_ga(
        calc_song_b,
        cfg_dict=cfg,
        best_data=best_data_b,
        ref_arrays=ref_arrays,
        ga_seed=987654321,
    )

    assert isinstance(out_a, dict)
    assert isinstance(out_b, dict)
    assert int(out_a["best_seed"]) == int(out_b["best_seed"])
    assert int(out_a["best_score"]) == int(out_b["best_score"])
    assert int(best_data_a["Score"]) == int(best_data_b["Score"])
    assert int(calc_song_a["metadata"]["HumanHitSimSeed"]) == int(calc_song_b["metadata"]["HumanHitSimSeed"])


def test_refine_human_hit_sim_after_ga_never_decreases_score():
    ref_arrays = _build_ref_arrays()
    cfg = {
        "HumanHitSim": {
            "Enabled": "true",
            "ApplyTo": "ALL",
            "Distribution": "uniform",
            "GreatMode": "late",
            "RefineAfterGA": "true",
            "RefineTrials": "8",
            "RefineSeedBase": "0",
        }
    }
    calc_song = _build_calc_song()
    best_data = _build_best_data(calc_song, ref_arrays)
    baseline = int(best_data["Score"])

    out = refine_human_hit_sim_after_ga(
        calc_song,
        cfg_dict=cfg,
        best_data=best_data,
        ref_arrays=ref_arrays,
        ga_seed=24680,
    )

    assert isinstance(out, dict)
    assert int(best_data["Score"]) >= baseline
    assert int(best_data["BaseScore"]) >= baseline
    assert bool(calc_song["metadata"].get("HumanHitSimRefined")) is True


def test_refine_human_hit_sim_after_ga_prunes_duplicate_timeline_trials(monkeypatch):
    import gear_optimizer.solver.hit_simulation as hit_sim

    ref_arrays = _build_ref_arrays()
    cfg = {
        "HumanHitSim": {
            "Enabled": "true",
            "ApplyTo": "ALL",
            "Distribution": "uniform",
            "GreatMode": "full",
            "RefineAfterGA": "true",
            "RefineTrials": "10",
            "RefineSeedBase": "4242",
        }
    }

    calc_song = _build_dense_calc_song()
    best_data = _build_best_data(calc_song, ref_arrays)

    real_fast_score = hit_sim.fast_calculate_score
    score_calls = {"count": 0}

    def _counting_fast_score(*args, **kwargs):
        score_calls["count"] += 1
        return real_fast_score(*args, **kwargs)

    def _fake_simulate(timestamps_sec, note_types, *, seed, distribution="uniform", great_mode="late", **kwargs):
        ts = np.asarray(timestamps_sec, dtype=np.float64).copy()
        if int(seed) & 1:
            # Different monotonic shape to force a distinct fever timeline.
            ts = ts + np.linspace(0.0, 0.250, num=ts.shape[0], dtype=np.float64)
        return ts, ts.copy(), {"notes": int(ts.shape[0]), "groups": int(ts.shape[0]), "forced_monotonic": 0}

    monkeypatch.setattr(hit_sim, "fast_calculate_score", _counting_fast_score)
    monkeypatch.setattr(hit_sim, "simulate_perfect_hit_timestamps_with_great_candidates", _fake_simulate)

    out = refine_human_hit_sim_after_ga(
        calc_song,
        cfg_dict=cfg,
        best_data=best_data,
        ref_arrays=ref_arrays,
        ga_seed=999,
    )

    assert isinstance(out, dict)
    assert int(out["trials"]) == 10
    assert int(out["evaluated_trials"]) < int(out["trials"])
    assert int(out["timeline_variants"]) == int(out["evaluated_trials"])
    assert int(out["skipped_timeline_duplicates"]) == int(out["trials"]) - int(out["evaluated_trials"])
    assert int(score_calls["count"]) == int(out["evaluated_trials"])

    meta = calc_song["metadata"]
    assert int(meta["HumanHitSimRefineEvaluatedTrials"]) == int(out["evaluated_trials"])
    assert int(meta["HumanHitSimRefineTimelineVariants"]) == int(out["timeline_variants"])
    assert int(meta["HumanHitSimRefineSkippedTimelineDuplicates"]) == int(out["skipped_timeline_duplicates"])


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
    event_ms_full = np.floor(np.asarray(out_sec, dtype=np.float64) * 1000.0 + 1e-6).astype(np.int32)
    assert np.array_equal(event_ms_fast, event_ms_full)


def test_refine_human_hit_sim_after_ga_can_miss_best_when_trials_limited(monkeypatch):
    import gear_optimizer.solver.hit_simulation as hit_sim

    ref_arrays = _build_ref_arrays()
    base_cfg = {
        "HumanHitSim": {
            "Enabled": "true",
            "ApplyTo": "ALL",
            "Distribution": "uniform",
            "GreatMode": "full",
            "RefineAfterGA": "true",
            "RefineSeedBase": "9000",
        }
    }

    def _fake_generate(_prepared, *, seed: int):
        # Encode seed in event_ms[0] so the signature hook can branch deterministically.
        out = np.zeros((120,), dtype=np.int32)
        out[0] = int(seed) & 0x7FFFFFFF
        return out

    def _fake_signature(event_ms, *, non_fever_base: int, real_fever_time_ms: int):
        _ = (non_fever_base, real_fever_time_ms)
        seed_tag = int(np.asarray(event_ms, dtype=np.int32)[0])
        # Deterministic: higher seed_tag -> more fever in head -> higher score.
        head = np.zeros((100,), dtype=np.bool_)
        k = 0
        if seed_tag % 3 == 0:
            k = 0
        elif seed_tag % 3 == 1:
            k = 10
        else:
            k = 20
        if k:
            head[:k] = True
        sig = (100, 0, 20, bytes([k]))
        return sig, head, 0, 20

    monkeypatch.setattr(hit_sim, "generate_perfect_hit_times_ms", _fake_generate)
    monkeypatch.setattr(hit_sim, "compute_fever_timeline_signature", _fake_signature)

    cfg2 = deepcopy(base_cfg)
    cfg2["HumanHitSim"]["RefineTrials"] = "2"
    calc_song2 = _build_dense_calc_song()
    best_data2 = _build_best_data(calc_song2, ref_arrays)
    best_data2["Score"] = 0
    best_data2["BaseScore"] = 0
    out2 = refine_human_hit_sim_after_ga(calc_song2, cfg_dict=cfg2, best_data=best_data2, ref_arrays=ref_arrays, ga_seed=1)
    assert isinstance(out2, dict)

    cfg3 = deepcopy(base_cfg)
    cfg3["HumanHitSim"]["RefineTrials"] = "3"
    calc_song3 = _build_dense_calc_song()
    best_data3 = _build_best_data(calc_song3, ref_arrays)
    best_data3["Score"] = 0
    best_data3["BaseScore"] = 0
    out3 = refine_human_hit_sim_after_ga(calc_song3, cfg_dict=cfg3, best_data=best_data3, ref_arrays=ref_arrays, ga_seed=1)
    assert isinstance(out3, dict)

    assert int(out3["best_score"]) >= int(out2["best_score"])
    # With bounded trials, the search may miss a better variant that appears later.
    assert int(out3["best_score"]) > int(out2["best_score"])


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


def test_refine_human_hit_sim_after_ga_matches_bruteforce_baseline_for_same_trials():
    """
    Refinement's fast evaluation path must pick the same best seed/score as a
    brute-force loop that simulates full timestamps and calls evaluate_stats_score.
    """
    ref_arrays = _build_ref_arrays()
    cfg = {
        "HumanHitSim": {
            "Enabled": "true",
            "ApplyTo": "ALL",
            "Distribution": "uniform",
            "GreatMode": "full",
            "RefineAfterGA": "true",
            "RefineTrials": "16",
            # Avoid dependence on song CRC/ga_seed in the test.
            "RefineSeedBase": "424242",
        }
    }
    calc_song = _build_dense_calc_song()
    best_data = _build_best_data(calc_song, ref_arrays)
    # Prevent score clamping from hiding mismatches in tie cases.
    best_data["Score"] = 0
    best_data["BaseScore"] = 0

    out = refine_human_hit_sim_after_ga(
        calc_song,
        cfg_dict=cfg,
        best_data=best_data,
        ref_arrays=ref_arrays,
        ga_seed=123,
    )
    assert isinstance(out, dict)
    got_seed = int(out["best_seed"])
    got_score = int(out["best_score"])

    # Brute-force reference over the same seed range.
    chart_ts = np.asarray(calc_song["song_data"]["chart_timestamps"], dtype=np.float64)
    note_types = np.asarray(calc_song["song_data"]["note_types"], dtype=np.int16)

    seed_base = int(cfg["HumanHitSim"]["RefineSeedBase"])
    trials = int(cfg["HumanHitSim"]["RefineTrials"])
    best_seed = int(seed_base)
    best_score = -1
    for i in range(trials):
        seed = (seed_base + i) & 0xFFFFFFFF
        if seed == 0:
            seed = 1
        sim_ts, _sim_gc, _dbg = simulate_perfect_hit_timestamps_with_great_candidates(
            chart_ts, note_types, seed=int(seed), distribution="uniform", great_mode="full"
        )
        sc = int(
            evaluate_stats_score(
                best_data["Stats"],
                calc_song,
                ref_arrays,
                song_timestamps=np.asarray(sim_ts, dtype=np.float64),
            )
        )
        if sc > best_score:
            best_score = sc
            best_seed = int(seed)

    assert got_score == int(best_score)
    assert got_seed == int(best_seed)


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
        event_ms_full = np.floor(np.asarray(out_sec, dtype=np.float64) * 1000.0 + 1e-6).astype(np.int32)
        assert np.array_equal(event_ms_fast, event_ms_full)
