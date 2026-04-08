import os
import sys
from math import ceil

import numpy as np
import pytest

# Ensure we can import gear_optimizer
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _has_taichi() -> bool:
    try:
        import taichi as _  # noqa: F401
    except Exception:
        return False
    return True


def _make_constant_ref_arrays(
    *,
    pp: float,
    cm: float,
    fm: float,
    ff: float,
    ft: float,
) -> dict:
    from gear_optimizer.core.constants import TOTAL_ROWS

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
) -> tuple[dict, np.ndarray | None]:
    ts = (np.arange(int(n), dtype=np.float32) * np.float32(spacing_s)).astype(np.float32, copy=False)
    song_data = {
        "timestamps": ts.copy(),
        "fg_timestamps": ts.copy(),
        "note_types": np.ones((int(n),), dtype=np.int16),
    }

    gc = None
    if with_great_candidates:
        # Intentionally allow non-monotonic great candidates (timing-aware carry uses a prefix-max rule).
        wiggle = (np.sin(np.arange(int(n), dtype=np.float32)) * np.float32(0.06)).astype(np.float32, copy=False)
        gc = (ts + np.float32(great_offset_s) + wiggle).astype(np.float32, copy=False)
        song_data["fg_great_candidate_timestamps"] = gc.copy()

    meta = {
        "Long Notes": 0,
        "Last Note Time": float(ts[-1]) if int(n) else 0.0,
        "Primary Color": "Red",
        "Secondary Color": "Blue",
    }
    return {"song_data": song_data, "metadata": meta}, gc


def _compute_fill_params(*, stats: dict, calc_song: dict, ref_arrays: dict) -> tuple[np.float32, int]:
    from gear_optimizer.core.constants import FEVER_FILL_BASE_RATE, TOTAL_ROWS
    from gear_optimizer.solver.scoring_core import lookup_reference_py

    meta = calc_song.get("metadata", {}) or {}
    long_notes = int(meta.get("Long Notes", 0) or 0)

    song_data = calc_song.get("song_data", {}) or {}
    ts = song_data.get("fg_timestamps", song_data.get("timestamps"))
    total_notes = int(len(ts)) if ts is not None else 0

    ref_ff = ref_arrays["Fever Fill Rate"]
    fever_fill_rate = float(lookup_reference_py(stats.get("Fever Fill Rate", 0), ref_ff, TOTAL_ROWS))

    non_fever_cas = float(total_notes - long_notes) * float(FEVER_FILL_BASE_RATE)
    if non_fever_cas < 0.0:
        non_fever_cas = 0.0

    raw_fill = np.float32(non_fever_cas * fever_fill_rate)
    non_fever_base = int(ceil(float(raw_fill)))
    return raw_fill, non_fever_base


def _compute_prefix_tables(*, stats: dict, calc_song: dict, ref_arrays: dict) -> tuple[np.ndarray, np.ndarray]:
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.solver.fg_exact_dp import _build_fever_bonus_prefix, _build_forced_great_penalty_prefix
    from gear_optimizer.solver.scoring_core import lookup_reference_py

    meta = calc_song.get("metadata", {}) or {}
    p_color = str(meta.get("Primary Color", "") or "")
    s_color = str(meta.get("Secondary Color", "") or "")
    primary_val = int(stats.get(p_color, 0) or 0)
    secondary_val = int(stats.get(s_color, 0) or 0)

    ref_pp = ref_arrays["Perfect Points"]
    ref_cm = ref_arrays["Combo Multiplier"]
    ref_fm = ref_arrays["Fever Multiplier"]

    pp_factor = float(lookup_reference_py(stats.get("Perfect Points", 0), ref_pp, TOTAL_ROWS))
    combo_mul = float(lookup_reference_py(stats.get("Combo Multiplier", 0), ref_cm, TOTAL_ROWS))
    fever_mul = float(lookup_reference_py(stats.get("Fever Multiplier", 0), ref_fm, TOTAL_ROWS))

    base_value = float((primary_val * 2) + secondary_val) + float(pp_factor)

    song_data = calc_song.get("song_data", {}) or {}
    ts = song_data.get("fg_timestamps", song_data.get("timestamps"))
    total_notes = int(len(ts)) if ts is not None else 0

    w_prefix = _build_fever_bonus_prefix(
        total_notes=total_notes,
        base_value=base_value,
        combo_mul=combo_mul,
        fever_mul=fever_mul,
    )
    c_prefix = _build_forced_great_penalty_prefix(
        total_notes=total_notes,
        base_value=base_value,
        combo_mul=combo_mul,
        primary_val=primary_val,
        secondary_val=secondary_val,
    )
    return w_prefix, c_prefix


def _strip_counts(arr: np.ndarray) -> list[int]:
    out: list[int] = []
    for v in arr.tolist():
        iv = int(v)
        if iv < 0:
            break
        out.append(iv)
    return out


@pytest.mark.gpu
@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_fg_exact_dp_gpu_matches_cpu_count_only():
    import taichi as ti

    from gear_optimizer.solver.fg_exact_dp import solve_force_greats_exact_dp
    from gear_optimizer.solver.taichi_gem import api as gem_api
    from gear_optimizer.solver.taichi_gem.force_greats import fields as fg_fields
    from gear_optimizer.solver.taichi_gem.force_greats import kernels as fg_kernels

    ref_arrays = _make_constant_ref_arrays(pp=0.0, cm=1.25, fm=2.0, ff=0.30, ft=0.60)
    calc_song, _gc = _make_synth_song(n=30, spacing_s=0.10, with_great_candidates=False, great_offset_s=0.20)

    stats = {
        "Perfect Points": 0,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Red": 1000,
        "Blue": 500,
    }

    cpu_sol = solve_force_greats_exact_dp(stats=stats, calc_song=calc_song, ref_arrays=ref_arrays, mode="count_only")

    # GPU setup
    gem_api.ensure_ready(ref_arrays)
    fg_fields.ensure_fields_allocated()

    assert fg_fields.fg_exact_dp_w_prefix is not None
    assert fg_fields.fg_exact_dp_c_prefix is not None
    assert fg_fields.fg_exact_dp_best_delta is not None
    assert fg_fields.fg_exact_dp_counts is not None

    song_data = calc_song["song_data"]
    ts_f32 = np.asarray(song_data["fg_timestamps"], dtype=np.float32)
    n = int(ts_f32.shape[0])
    last_note_time = float(calc_song["metadata"]["Last Note Time"])

    # Use identical great-candidate timestamps (timing disabled anyway).
    fg_kernels.fg_upload_song_timestamps_prefix_kernel(int(n), ts_f32)
    fg_kernels.fg_upload_great_candidate_timestamps_prefix_kernel(int(n), ts_f32)
    fg_kernels.fg_precompute_fever_end_idx_tables_kernel(int(n), float(last_note_time))

    # Upload DP prefix ingredients.
    raw_fill, non_fever_base = _compute_fill_params(stats=stats, calc_song=calc_song, ref_arrays=ref_arrays)
    w_prefix, c_prefix = _compute_prefix_tables(stats=stats, calc_song=calc_song, ref_arrays=ref_arrays)

    w_pad = np.zeros((fg_fields.FG_EXACT_DP_MAX_NOTES + 1,), dtype=np.int64)
    c_pad = np.zeros((fg_fields.FG_EXACT_DP_MAX_NOTES + 1,), dtype=np.int64)
    w_pad[: n + 1] = w_prefix
    c_pad[: n + 1] = c_prefix
    fg_fields.fg_exact_dp_w_prefix.from_numpy(w_pad)
    fg_fields.fg_exact_dp_c_prefix.from_numpy(c_pad)

    fg_kernels.fg_exact_dp_reference_kernel(int(n), float(raw_fill), int(non_fever_base), 0, 0)
    ti.sync()

    best_delta_gpu = int(fg_fields.fg_exact_dp_best_delta.to_numpy())
    counts_gpu = _strip_counts(fg_fields.fg_exact_dp_counts.to_numpy())

    assert best_delta_gpu == int(cpu_sol.best_delta)
    assert len(cpu_sol.section_counts) <= fg_fields.FG_MAX_SECTIONS
    assert counts_gpu[: len(cpu_sol.section_counts)] == [int(x) for x in cpu_sol.section_counts]


@pytest.mark.gpu
@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_fg_exact_dp_gpu_matches_cpu_timing_aware():
    import taichi as ti

    from gear_optimizer.solver.fg_exact_dp import solve_force_greats_exact_dp
    from gear_optimizer.solver.taichi_gem import api as gem_api
    from gear_optimizer.solver.taichi_gem.force_greats import fields as fg_fields
    from gear_optimizer.solver.taichi_gem.force_greats import kernels as fg_kernels

    ref_arrays = _make_constant_ref_arrays(pp=0.0, cm=1.20, fm=2.0, ff=0.30, ft=0.55)
    calc_song, gc = _make_synth_song(n=32, spacing_s=0.04, with_great_candidates=True, great_offset_s=0.20)
    assert gc is not None

    stats = {
        "Perfect Points": 0,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Red": 900,
        "Blue": 450,
    }

    cpu_sol = solve_force_greats_exact_dp(stats=stats, calc_song=calc_song, ref_arrays=ref_arrays, mode="timing_aware")

    # GPU setup
    gem_api.ensure_ready(ref_arrays)
    fg_fields.ensure_fields_allocated()

    assert fg_fields.fg_exact_dp_w_prefix is not None
    assert fg_fields.fg_exact_dp_c_prefix is not None
    assert fg_fields.fg_exact_dp_best_delta is not None
    assert fg_fields.fg_exact_dp_counts is not None

    song_data = calc_song["song_data"]
    ts_f32 = np.asarray(song_data["fg_timestamps"], dtype=np.float32)
    gc_f32 = np.asarray(song_data["fg_great_candidate_timestamps"], dtype=np.float32)
    n = int(ts_f32.shape[0])
    last_note_time = float(calc_song["metadata"]["Last Note Time"])

    fg_kernels.fg_upload_song_timestamps_prefix_kernel(int(n), ts_f32)
    fg_kernels.fg_upload_great_candidate_timestamps_prefix_kernel(int(n), gc_f32)
    fg_kernels.fg_precompute_fever_end_idx_tables_kernel(int(n), float(last_note_time))

    raw_fill, non_fever_base = _compute_fill_params(stats=stats, calc_song=calc_song, ref_arrays=ref_arrays)
    w_prefix, c_prefix = _compute_prefix_tables(stats=stats, calc_song=calc_song, ref_arrays=ref_arrays)

    w_pad = np.zeros((fg_fields.FG_EXACT_DP_MAX_NOTES + 1,), dtype=np.int64)
    c_pad = np.zeros((fg_fields.FG_EXACT_DP_MAX_NOTES + 1,), dtype=np.int64)
    w_pad[: n + 1] = w_prefix
    c_pad[: n + 1] = c_prefix
    fg_fields.fg_exact_dp_w_prefix.from_numpy(w_pad)
    fg_fields.fg_exact_dp_c_prefix.from_numpy(c_pad)

    fg_kernels.fg_exact_dp_reference_kernel(int(n), float(raw_fill), int(non_fever_base), 0, 1)
    ti.sync()

    best_delta_gpu = int(fg_fields.fg_exact_dp_best_delta.to_numpy())
    counts_gpu = _strip_counts(fg_fields.fg_exact_dp_counts.to_numpy())

    assert best_delta_gpu == int(cpu_sol.best_delta)
    assert len(cpu_sol.section_counts) <= fg_fields.FG_MAX_SECTIONS
    assert counts_gpu[: len(cpu_sol.section_counts)] == [int(x) for x in cpu_sol.section_counts]


@pytest.mark.gpu
@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_fg_exact_dp_sparse_gpu_matches_cpu_count_only():
    import taichi as ti

    from gear_optimizer.solver.fg_exact_dp import solve_force_greats_exact_dp
    from gear_optimizer.solver.taichi_gem import api as gem_api
    from gear_optimizer.solver.taichi_gem.force_greats import fields as fg_fields
    from gear_optimizer.solver.taichi_gem.force_greats import kernels as fg_kernels

    ref_arrays = _make_constant_ref_arrays(pp=0.0, cm=1.25, fm=2.0, ff=0.30, ft=0.60)
    calc_song, _gc = _make_synth_song(n=40, spacing_s=0.10, with_great_candidates=False, great_offset_s=0.20)

    stats = {
        "Perfect Points": 0,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Red": 1000,
        "Blue": 500,
    }

    cpu_sol = solve_force_greats_exact_dp(stats=stats, calc_song=calc_song, ref_arrays=ref_arrays, mode="count_only")

    gem_api.ensure_ready(ref_arrays)
    fg_fields.ensure_fields_allocated()

    assert fg_fields.fg_exact_dp_full_w_prefix is not None
    assert fg_fields.fg_exact_dp_full_c_prefix is not None
    assert fg_fields.fg_exact_dp_sparse_best_delta is not None
    assert fg_fields.fg_exact_dp_sparse_counts is not None
    assert fg_fields.fg_exact_dp_sparse_overflow is not None

    song_data = calc_song["song_data"]
    ts_f32 = np.asarray(song_data["fg_timestamps"], dtype=np.float32)
    n = int(ts_f32.shape[0])
    last_note_time = float(calc_song["metadata"]["Last Note Time"])

    fg_kernels.fg_upload_song_timestamps_prefix_kernel(int(n), ts_f32)
    fg_kernels.fg_upload_great_candidate_timestamps_prefix_kernel(int(n), ts_f32)
    fg_kernels.fg_precompute_fever_end_idx_tables_kernel(int(n), float(last_note_time))

    raw_fill, non_fever_base = _compute_fill_params(stats=stats, calc_song=calc_song, ref_arrays=ref_arrays)
    w_prefix, c_prefix = _compute_prefix_tables(stats=stats, calc_song=calc_song, ref_arrays=ref_arrays)

    fg_kernels.fg_upload_exact_dp_full_w_prefix_kernel(int(n), np.ascontiguousarray(w_prefix, dtype=np.int64))
    fg_kernels.fg_upload_exact_dp_full_c_prefix_kernel(int(n), np.ascontiguousarray(c_prefix, dtype=np.int64))

    # timing_aware=0, prune=0: ablation (count_only, no pruning) to isolate carry semantics
    fg_kernels.fg_exact_dp_sparse_full_kernel(int(n), float(raw_fill), int(non_fever_base), 0, 0, 0)
    ti.sync()

    overflow = int(fg_fields.fg_exact_dp_sparse_overflow.to_numpy())
    best_delta_gpu = int(fg_fields.fg_exact_dp_sparse_best_delta.to_numpy())
    counts_gpu = _strip_counts(fg_fields.fg_exact_dp_sparse_counts.to_numpy())

    assert overflow == 0
    assert best_delta_gpu == int(cpu_sol.best_delta)
    assert len(cpu_sol.section_counts) <= fg_fields.FG_MAX_SECTIONS
    assert counts_gpu[: len(cpu_sol.section_counts)] == [int(x) for x in cpu_sol.section_counts]


@pytest.mark.gpu
@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_fg_exact_dp_sparse_gpu_matches_cpu_timing_aware():
    import taichi as ti

    from gear_optimizer.solver.fg_exact_dp import solve_force_greats_exact_dp
    from gear_optimizer.solver.taichi_gem import api as gem_api
    from gear_optimizer.solver.taichi_gem.force_greats import fields as fg_fields
    from gear_optimizer.solver.taichi_gem.force_greats import kernels as fg_kernels

    ref_arrays = _make_constant_ref_arrays(pp=0.0, cm=1.20, fm=2.0, ff=0.30, ft=0.55)
    calc_song, gc = _make_synth_song(n=32, spacing_s=0.04, with_great_candidates=True, great_offset_s=0.20)
    assert gc is not None

    stats = {
        "Perfect Points": 0,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Red": 900,
        "Blue": 450,
    }

    cpu_sol = solve_force_greats_exact_dp(stats=stats, calc_song=calc_song, ref_arrays=ref_arrays, mode="timing_aware")

    gem_api.ensure_ready(ref_arrays)
    fg_fields.ensure_fields_allocated()

    assert fg_fields.fg_exact_dp_full_w_prefix is not None
    assert fg_fields.fg_exact_dp_full_c_prefix is not None
    assert fg_fields.fg_exact_dp_sparse_best_delta is not None
    assert fg_fields.fg_exact_dp_sparse_counts is not None
    assert fg_fields.fg_exact_dp_sparse_overflow is not None

    song_data = calc_song["song_data"]
    ts_f32 = np.asarray(song_data["fg_timestamps"], dtype=np.float32)
    gc_f32 = np.asarray(song_data["fg_great_candidate_timestamps"], dtype=np.float32)
    n = int(ts_f32.shape[0])
    last_note_time = float(calc_song["metadata"]["Last Note Time"])

    fg_kernels.fg_upload_song_timestamps_prefix_kernel(int(n), ts_f32)
    fg_kernels.fg_upload_great_candidate_timestamps_prefix_kernel(int(n), gc_f32)
    fg_kernels.fg_precompute_fever_end_idx_tables_kernel(int(n), float(last_note_time))

    raw_fill, non_fever_base = _compute_fill_params(stats=stats, calc_song=calc_song, ref_arrays=ref_arrays)
    w_prefix, c_prefix = _compute_prefix_tables(stats=stats, calc_song=calc_song, ref_arrays=ref_arrays)

    fg_kernels.fg_upload_exact_dp_full_w_prefix_kernel(int(n), np.ascontiguousarray(w_prefix, dtype=np.int64))
    fg_kernels.fg_upload_exact_dp_full_c_prefix_kernel(int(n), np.ascontiguousarray(c_prefix, dtype=np.int64))

    # timing_aware=1, prune=0: ablation (timing_aware carry, no pruning) — production carry semantics, full transition space
    fg_kernels.fg_exact_dp_sparse_full_kernel(int(n), float(raw_fill), int(non_fever_base), 0, 1, 0)
    ti.sync()

    overflow = int(fg_fields.fg_exact_dp_sparse_overflow.to_numpy())
    best_delta_gpu = int(fg_fields.fg_exact_dp_sparse_best_delta.to_numpy())
    counts_gpu = _strip_counts(fg_fields.fg_exact_dp_sparse_counts.to_numpy())

    assert overflow == 0
    assert best_delta_gpu == int(cpu_sol.best_delta)
    assert len(cpu_sol.section_counts) <= fg_fields.FG_MAX_SECTIONS
    assert counts_gpu[: len(cpu_sol.section_counts)] == [int(x) for x in cpu_sol.section_counts]


@pytest.mark.gpu
@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_fg_exact_dp_public_gpu_api_matches_cpu_timing_aware():
    from gear_optimizer.solver.fg_exact_dp import solve_force_greats_exact_dp
    from gear_optimizer.solver.taichi_gem.force_greats.api import solve_force_greats_exact_dp_gpu_batch

    ref_arrays = _make_constant_ref_arrays(pp=0.0, cm=1.20, fm=2.0, ff=0.30, ft=0.55)
    calc_song, _gc = _make_synth_song(n=40, spacing_s=0.04, with_great_candidates=True, great_offset_s=0.20)

    stats = {
        "Perfect Points": 0,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Red": 900,
        "Blue": 450,
    }

    cpu_sol = solve_force_greats_exact_dp(stats=stats, calc_song=calc_song, ref_arrays=ref_arrays, mode="timing_aware")
    gpu_out = solve_force_greats_exact_dp_gpu_batch(
        stats_list=[stats],
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        timing_aware=True,
        prune=True,
    )

    assert len(gpu_out) == 1
    assert int(gpu_out[0]["best_delta"]) == int(cpu_sol.best_delta)
    assert [int(x) for x in gpu_out[0]["section_counts"]] == [int(x) for x in cpu_sol.section_counts]
    assert int((gpu_out[0]["profile"] or {}).get("states", 0) or 0) > 0
