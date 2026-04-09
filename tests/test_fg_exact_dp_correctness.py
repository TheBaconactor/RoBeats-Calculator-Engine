import itertools

import numpy as np

from gear_optimizer.core.constants import TOTAL_ROWS
from gear_optimizer.solver.fg_exact_dp import (
    prepare_force_greats_exact_dp_inputs,
    score_force_greats_exact_dp_bonus_from_prepared,
    solve_force_greats_exact_dp,
)
from gear_optimizer.solver.scoring.force_greats import evaluate_force_greats
from gear_optimizer.solver.scoring_core import fast_calculate_score, lookup_reference_py


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
        # FG uses these keys when present (HitSim ApplyTo=FG populates them).
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
