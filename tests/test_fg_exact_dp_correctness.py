import itertools
from math import ceil

import numpy as np

from gear_optimizer.core.constants import TOTAL_ROWS
from gear_optimizer.solver.fg_exact_dp import (
    _build_fp_actions,
    count_force_greats_baseline_windows_from_prepared,
    prepare_force_greats_exact_dp_inputs,
    score_force_greats_exact_dp_bonus_from_prepared,
    solve_force_greats_exact_dp,
)
from gear_optimizer.solver.scoring.force_greats import evaluate_force_greats
from gear_optimizer.solver.scoring.scoring_core import fast_calculate_score, lookup_reference_py


def _make_constant_ref_arrays(
    *,
    pp: float,
    cm: float,
    fm: float,
    ff: float,
    ft: float,
) -> dict:
    # The solver expects ref arrays shaped like [0..TOTAL_ROWS], so make constant
    # arrays that ignore the stat index (sufficient for deterministic unit tests).
    n = int(TOTAL_ROWS) + 1
    return {
        "Perfect Points": np.full((n,), float(pp), dtype=np.float32),
        "Combo Multiplier": np.full((n,), float(cm), dtype=np.float32),
        "Fever Multiplier": np.full((n,), float(fm), dtype=np.float32),
        "Fever Fill Rate": np.full((n,), float(ff), dtype=np.float32),
        "Fever Time": np.full((n,), float(ft), dtype=np.float32),
    }


def _make_synth_song(
    *,
    n: int,
    spacing_s: float,
    with_great_candidates: bool,
    great_offset_s: float,
) -> dict:
    ts = (np.arange(int(n), dtype=np.float32) * np.float32(spacing_s)).astype(np.float32, copy=False)
    song_data = {
        "timestamps": ts.copy(),
        # FG uses these keys when present.
        "fg_timestamps": ts.copy(),
        "note_types": np.ones((int(n),), dtype=np.int16),
    }

    if with_great_candidates:
        # Make candidates non-monotonic but frequently > activation timestamps,
        # so carry timing can matter.
        wiggle = (np.sin(np.arange(int(n), dtype=np.float32)) * np.float32(0.03)).astype(np.float32, copy=False)
        gc = (ts + np.float32(great_offset_s) + wiggle).astype(np.float32, copy=False)
        song_data["fg_great_candidate_timestamps"] = gc.copy()

    meta = {
        "Long Notes": 0,
        "Last Note Time": float(ts[-1]) if int(n) else 0.0,
        "Primary Color": "Red",
        "Secondary Color": "Blue",
    }
    return {"song_data": song_data, "metadata": meta}


def _normal_all_perfect_score(*, stats: dict, calc_song: dict, ref_arrays: dict) -> int:
    meta = calc_song.get("metadata", {}) or {}
    p_color = str(meta.get("Primary Color", "") or "")
    s_color = str(meta.get("Secondary Color", "") or "")
    primary_val = int(stats.get(p_color, 0))
    secondary_val = int(stats.get(s_color, 0))

    ref_pp = ref_arrays["Perfect Points"]
    ref_cm = ref_arrays["Combo Multiplier"]
    ref_fm = ref_arrays["Fever Multiplier"]

    pp_factor = float(lookup_reference_py(stats.get("Perfect Points", 0), ref_pp, TOTAL_ROWS))
    combo_mul = float(lookup_reference_py(stats.get("Combo Multiplier", 0), ref_cm, TOTAL_ROWS))
    fever_mul = float(lookup_reference_py(stats.get("Fever Multiplier", 0), ref_fm, TOTAL_ROWS))
    base_value = float((primary_val * 2) + secondary_val) + pp_factor

    song_data = calc_song.get("song_data", {}) or {}
    ts = song_data.get("fg_timestamps", song_data.get("timestamps"))
    n = len(ts) if ts is not None else 0

    head_len = min(100, int(n))
    fever_mask_head = np.zeros((head_len,), dtype=np.bool_)
    count_body_fever = 0
    count_body_normal = max(0, int(n) - 100)
    return int(
        fast_calculate_score(
            float(base_value),
            float(combo_mul),
            float(fever_mul),
            fever_mask_head,
            int(count_body_fever),
            int(count_body_normal),
        )
    )


def _bruteforce_best_final_score(
    *, stats: dict, calc_song: dict, ref_arrays: dict, max_sections: int
) -> tuple[int, list]:
    # Enumerate full section-count vectors (trailing values are ignored by
    # evaluate_force_greats once the song ends).
    eval0 = evaluate_force_greats(stats, calc_song, ref_arrays, forced_counts=[0] * int(max_sections))
    assert eval0 is not None
    m = int(eval0.get("non_fever_base") or 0)
    assert m >= 0

    best_score = -1
    best_cfg: list[int] = []
    for cfg in itertools.product(range(m + 1), repeat=int(max_sections)):
        out = evaluate_force_greats(stats, calc_song, ref_arrays, forced_counts=list(cfg))
        assert out is not None
        score = int(out["final_score"])
        if score > best_score:
            best_score = score
            best_cfg = list(cfg)
    return best_score, best_cfg


def _greedy_force_greats_counts(
    *,
    stats: dict,
    calc_song: dict,
    ref_arrays: dict,
    mode: str = "timing_aware",
) -> list[int]:
    prepared = prepare_force_greats_exact_dp_inputs(stats=stats, calc_song=calc_song, ref_arrays=ref_arrays)
    assert prepared is not None

    timestamps = prepared.timestamps
    great_candidates = prepared.great_candidates
    total_notes = int(prepared.total_notes)
    raw_fill = float(prepared.raw_fill)
    non_fever_base = int(prepared.non_fever_base)
    fever_duration = float(prepared.fever_duration)
    use_timing_carry = bool(mode == "timing_aware" and great_candidates is not None)
    w_prefix = prepared.w_prefix
    c_prefix = prepared.c_prefix

    end_times_song = timestamps.astype(np.float64) + float(fever_duration)
    fever_end_song = np.searchsorted(timestamps, end_times_song, side="left").astype(np.int32, copy=False)
    if use_timing_carry:
        assert great_candidates is not None
        end_times_gc = great_candidates.astype(np.float64) + float(fever_duration)
        fever_end_gc = np.searchsorted(timestamps, end_times_gc, side="left").astype(np.int32, copy=False)
    else:
        fever_end_gc = None

    p_to_ks = _build_fp_actions(raw_fill, non_fever_base)
    counts: list[int] = []
    i = 0
    first = True
    carry_idx = -1

    while i < total_notes:
        min_notes_to_fill = int(non_fever_base - 1 if first else non_fever_base)
        if min_notes_to_fill < 0:
            min_notes_to_fill = 0
        if i + min_notes_to_fill >= total_notes:
            break

        forced_start_base = i if first else (i + 1)
        best_choice: tuple[int, int, int, int, int] | None = None

        for p, ks in enumerate(p_to_ks):
            notes_to_fill = int(non_fever_base + p)
            if first:
                notes_to_fill -= 1
            if notes_to_fill < 0:
                notes_to_fill = 0

            end_normal = i + notes_to_fill
            if end_normal >= total_notes:
                break

            for k in ks:
                forced_val = max(0, min(int(k), non_fever_base))
                actual_notes = max(0, int(end_normal - i))
                forced_applied = min(forced_val, actual_notes)

                penalty = 0
                if forced_applied > 0 and forced_start_base < total_notes:
                    end_excl = min(total_notes, forced_start_base + forced_applied)
                    penalty = int(c_prefix[end_excl] - c_prefix[forced_start_base])

                next_carry = carry_idx
                if use_timing_carry and forced_applied > 0:
                    assert great_candidates is not None
                    forced_end = forced_start_base + forced_applied - 1
                    if forced_start_base <= forced_end < end_normal < total_notes + 1:
                        cand_t = float(great_candidates[forced_end])
                        if next_carry < 0 or cand_t > float(great_candidates[next_carry]):
                            next_carry = int(forced_end)

                fever_end_idx = int(fever_end_song[end_normal])
                if use_timing_carry and next_carry >= 0:
                    assert great_candidates is not None and fever_end_gc is not None
                    if float(great_candidates[next_carry]) > float(timestamps[end_normal]):
                        fever_end_idx = int(fever_end_gc[next_carry])
                if fever_end_idx <= end_normal:
                    fever_end_idx = min(total_notes, end_normal + 1)

                immediate = int(w_prefix[fever_end_idx] - w_prefix[end_normal]) - int(penalty)
                candidate = (
                    int(immediate),
                    -int(p),
                    -int(forced_val),
                    int(fever_end_idx),
                    int(next_carry),
                )
                if best_choice is None or candidate > best_choice:
                    best_choice = candidate

        assert best_choice is not None
        _immediate, _neg_p, forced_val_neg, next_idx, next_carry = best_choice
        counts.append(int(-forced_val_neg))
        i = int(next_idx)
        first = False

        if use_timing_carry and next_carry >= 0:
            assert great_candidates is not None
            if i >= total_notes or float(great_candidates[next_carry]) <= float(timestamps[i]):
                carry_idx = -1
            else:
                carry_idx = int(next_carry)
        else:
            carry_idx = -1

    return counts


def test_fg_exact_dp_matches_bruteforce_count_only():
    ref_arrays = _make_constant_ref_arrays(pp=0.0, cm=1.25, fm=2.0, ff=0.30, ft=0.60)
    calc_song = _make_synth_song(n=30, spacing_s=0.10, with_great_candidates=False, great_offset_s=0.20)

    stats = {
        "Perfect Points": 0,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Red": 1000,
        "Blue": 500,
    }

    # Baseline section cap from the real timeline (all zero config).
    base = evaluate_force_greats(stats, calc_song, ref_arrays, forced_counts=[0] * 32)
    assert base is not None
    max_sections = int(base["num_non_fever_sections"])
    assert max_sections > 0

    brute_best_score, _brute_cfg = _bruteforce_best_final_score(
        stats=stats, calc_song=calc_song, ref_arrays=ref_arrays, max_sections=max_sections
    )

    sol = solve_force_greats_exact_dp(stats=stats, calc_song=calc_song, ref_arrays=ref_arrays, mode="count_only")
    out = evaluate_force_greats(stats, calc_song, ref_arrays, forced_counts=sol.section_counts)
    assert out is not None
    assert int(out["final_score"]) == int(brute_best_score)

    normal_score = _normal_all_perfect_score(stats=stats, calc_song=calc_song, ref_arrays=ref_arrays)
    assert int(sol.best_delta) == int(out["final_score"]) - int(normal_score)


def test_fg_exact_dp_matches_bruteforce_timing_aware():
    ref_arrays = _make_constant_ref_arrays(pp=0.0, cm=1.20, fm=2.0, ff=0.30, ft=0.55)
    calc_song = _make_synth_song(n=32, spacing_s=0.10, with_great_candidates=True, great_offset_s=0.20)

    stats = {
        "Perfect Points": 0,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Red": 900,
        "Blue": 450,
    }

    base = evaluate_force_greats(stats, calc_song, ref_arrays, forced_counts=[0] * 32)
    assert base is not None
    max_sections = int(base["num_non_fever_sections"])
    assert max_sections > 0

    brute_best_score, _brute_cfg = _bruteforce_best_final_score(
        stats=stats, calc_song=calc_song, ref_arrays=ref_arrays, max_sections=max_sections
    )

    sol = solve_force_greats_exact_dp(stats=stats, calc_song=calc_song, ref_arrays=ref_arrays, mode="timing_aware")
    out = evaluate_force_greats(stats, calc_song, ref_arrays, forced_counts=sol.section_counts)
    assert out is not None
    assert int(out["final_score"]) == int(brute_best_score)

    normal_score = _normal_all_perfect_score(stats=stats, calc_song=calc_song, ref_arrays=ref_arrays)
    assert int(sol.best_delta) == int(out["final_score"]) - int(normal_score)


def test_fg_exact_dp_bonus_converts_to_real_baseline_delta():
    ref_arrays = _make_constant_ref_arrays(pp=0.0, cm=1.20, fm=2.0, ff=0.30, ft=0.55)
    calc_song = _make_synth_song(n=32, spacing_s=0.10, with_great_candidates=True, great_offset_s=0.20)

    stats = {
        "Perfect Points": 0,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Red": 900,
        "Blue": 450,
    }

    sol = solve_force_greats_exact_dp(stats=stats, calc_song=calc_song, ref_arrays=ref_arrays, mode="timing_aware")
    out = evaluate_force_greats(stats, calc_song, ref_arrays, forced_counts=sol.section_counts)
    baseline = evaluate_force_greats(stats, calc_song, ref_arrays, forced_counts=[])
    prepared = prepare_force_greats_exact_dp_inputs(stats=stats, calc_song=calc_song, ref_arrays=ref_arrays)

    assert out is not None
    assert baseline is not None
    assert prepared is not None

    normal_score = _normal_all_perfect_score(stats=stats, calc_song=calc_song, ref_arrays=ref_arrays)
    baseline_bonus = score_force_greats_exact_dp_bonus_from_prepared(prepared=prepared, section_counts=[])
    actual_bonus = score_force_greats_exact_dp_bonus_from_prepared(
        prepared=prepared,
        section_counts=sol.section_counts,
    )

    assert int(normal_score) + int(baseline_bonus) == int(baseline["final_score"])
    assert int(normal_score) + int(actual_bonus) == int(out["final_score"])
    assert int(actual_bonus) - int(baseline_bonus) == int(out["final_score"]) - int(baseline["final_score"])


def test_fg_exact_dp_timing_aware_beats_count_only_baseline_on_carry_set():
    """
    Regression for the timing-envelope breakthrough:
    count-only FG cannot see delayed Great-candidate carry, while timing-aware exact DP can.
    """
    stats = {
        "Perfect Points": 0,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Red": 900,
        "Blue": 450,
    }

    # These cells are intentionally tiny but score-separating. They prove the
    # timing-aware DP is not merely matching the old count-only/no-DP baseline.
    cases = [
        (28, 0.04, 0.15, 0.35, 9724),
        (28, 0.04, 0.15, 0.45, 7441),
        (28, 0.04, 0.15, 0.55, 5128),
    ]
    for n_notes, spacing_s, ff_factor, ft_factor, min_gain in cases:
        ref_arrays = _make_constant_ref_arrays(pp=0.0, cm=1.20, fm=2.0, ff=ff_factor, ft=ft_factor)
        calc_song = _make_synth_song(
            n=n_notes,
            spacing_s=spacing_s,
            with_great_candidates=True,
            great_offset_s=0.20,
        )

        count_sol = solve_force_greats_exact_dp(stats=stats, calc_song=calc_song, ref_arrays=ref_arrays, mode="count_only")
        timing_sol = solve_force_greats_exact_dp(
            stats=stats,
            calc_song=calc_song,
            ref_arrays=ref_arrays,
            mode="timing_aware",
        )
        count_out = evaluate_force_greats(stats, calc_song, ref_arrays, forced_counts=count_sol.section_counts)
        timing_out = evaluate_force_greats(stats, calc_song, ref_arrays, forced_counts=timing_sol.section_counts)
        baseline = evaluate_force_greats(stats, calc_song, ref_arrays, forced_counts=[])

        assert count_out is not None
        assert timing_out is not None
        assert baseline is not None
        assert int(count_out["final_score"]) == int(baseline["final_score"])
        assert int(timing_out["final_score"]) - int(count_out["final_score"]) >= int(min_gain)
        assert int(timing_sol.profile.states) <= 16
        assert int(timing_sol.profile.transitions) <= 41


def test_fg_exact_dp_beats_greedy_on_three_window_frontier():
    """
    The bounded exact frontier should still improve on a local greedy section policy.
    """
    ref_arrays = _make_constant_ref_arrays(pp=0.0, cm=1.20, fm=2.0, ff=0.35, ft=0.65)
    calc_song = _make_synth_song(n=20, spacing_s=0.08, with_great_candidates=True, great_offset_s=0.20)

    stats = {
        "Perfect Points": 0,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Red": 900,
        "Blue": 450,
    }

    prepared = prepare_force_greats_exact_dp_inputs(stats=stats, calc_song=calc_song, ref_arrays=ref_arrays)
    assert prepared is not None
    assert count_force_greats_baseline_windows_from_prepared(prepared) == 3

    exact = solve_force_greats_exact_dp(stats=stats, calc_song=calc_song, ref_arrays=ref_arrays, mode="timing_aware")
    greedy_counts = _greedy_force_greats_counts(
        stats=stats,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        mode="timing_aware",
    )

    exact_out = evaluate_force_greats(stats, calc_song, ref_arrays, forced_counts=exact.section_counts)
    greedy_out = evaluate_force_greats(stats, calc_song, ref_arrays, forced_counts=greedy_counts)
    baseline = evaluate_force_greats(stats, calc_song, ref_arrays, forced_counts=[])
    brute_best_score, _ = _bruteforce_best_final_score(stats=stats, calc_song=calc_song, ref_arrays=ref_arrays, max_sections=3)

    assert exact_out is not None
    assert greedy_out is not None
    assert baseline is not None
    assert int(exact_out["final_score"]) == int(brute_best_score)
    assert int(exact_out["final_score"]) - int(greedy_out["final_score"]) >= 8297
    assert int(exact_out["final_score"]) >= int(baseline["final_score"])
    assert int(exact.profile.states) <= 10
    assert int(exact.profile.transitions) <= 30


def test_baseline_window_count_bounds_forced_paths():
    ref_arrays = _make_constant_ref_arrays(pp=0.0, cm=1.20, fm=2.0, ff=0.30, ft=0.55)
    calc_song = _make_synth_song(n=48, spacing_s=0.07, with_great_candidates=True, great_offset_s=0.20)

    stats = {
        "Perfect Points": 0,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Red": 900,
        "Blue": 450,
    }
    prepared = prepare_force_greats_exact_dp_inputs(stats=stats, calc_song=calc_song, ref_arrays=ref_arrays)
    assert prepared is not None
    baseline_windows = count_force_greats_baseline_windows_from_prepared(prepared)
    assert baseline_windows > 0

    def _count_windows_for_counts(counts: list[int]) -> int:
        timestamps = prepared.timestamps
        great_candidates = prepared.great_candidates
        total_notes = int(prepared.total_notes)
        end_times_song = timestamps.astype(np.float64) + float(prepared.fever_duration)
        fever_end_song = np.searchsorted(timestamps, end_times_song, side="left").astype(np.int32, copy=False)
        if great_candidates is not None:
            end_times_gc = great_candidates.astype(np.float64) + float(prepared.fever_duration)
            fever_end_gc = np.searchsorted(timestamps, end_times_gc, side="left").astype(np.int32, copy=False)
        else:
            fever_end_gc = None

        i = 0
        is_first = True
        carry_idx = -1
        windows = 0
        section_idx = 0
        while i < total_notes:
            if great_candidates is not None and carry_idx >= 0 and float(great_candidates[carry_idx]) <= float(timestamps[i]):
                carry_idx = -1
            forced_val = int(counts[section_idx]) if section_idx < len(counts) else 0
            forced_val = max(0, min(int(forced_val), int(prepared.non_fever_base)))

            notes_to_fill = int(ceil(float(prepared.raw_fill) + 0.5 * float(forced_val)))
            if is_first:
                notes_to_fill -= 1
            notes_to_fill = max(0, int(notes_to_fill))
            end_normal = int(i + notes_to_fill)
            if end_normal >= total_notes:
                break

            forced_start = int(i if is_first else i + 1)
            actual_notes = max(0, int(end_normal - i))
            forced_applied = min(int(forced_val), int(actual_notes))
            if great_candidates is not None and forced_applied > 0:
                forced_end = forced_start + forced_applied - 1
                if forced_end >= forced_start and forced_end < end_normal and forced_end < total_notes:
                    if carry_idx < 0 or float(great_candidates[forced_end]) > float(great_candidates[carry_idx]):
                        carry_idx = int(forced_end)

            fever_end_idx = int(fever_end_song[end_normal])
            if great_candidates is not None and fever_end_gc is not None and carry_idx >= 0:
                if float(great_candidates[carry_idx]) > float(timestamps[end_normal]):
                    fever_end_idx = int(fever_end_gc[carry_idx])
            if fever_end_idx <= end_normal:
                fever_end_idx = min(total_notes, end_normal + 1)

            windows += 1
            if great_candidates is not None and carry_idx >= 0 and fever_end_idx < total_notes:
                if float(great_candidates[carry_idx]) <= float(timestamps[fever_end_idx]):
                    carry_idx = -1
            i = int(fever_end_idx)
            is_first = False
            section_idx += 1
        return int(windows)

    assert _count_windows_for_counts([]) == baseline_windows

    base = evaluate_force_greats(stats, calc_song, ref_arrays, forced_counts=[0] * 32)
    assert base is not None
    max_sections = int(base["num_non_fever_sections"])

    # Forced Greats and timing carry only delay activations/ends, so no forced
    # configuration can realize more fever windows than the all-normal path.
    for cfg in itertools.product(range(0, 4), repeat=min(max_sections, 4)):
        out = evaluate_force_greats(stats, calc_song, ref_arrays, forced_counts=list(cfg))
        assert out is not None
        assert _count_windows_for_counts(list(cfg)) <= int(baseline_windows)
