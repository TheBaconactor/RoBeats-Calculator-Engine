"""
API HitSim Refine - GPU HumanHitSim post-GA refinement (ApplyTo=ALL).

This module provides a GPU implementation of the exact boundary-regime scan:
- Upload grouped hit windows (perfect + great)
- Upload alpha regimes, unique timeline param rows, and candidate score inputs
- Evaluate per-alpha signatures + best candidate score on GPU
- Plan regimes by signature change, optionally cap selection, and select best
- Materialize the best timestamps (perfect + great-candidate) on GPU
"""

from __future__ import annotations

import numpy as np

from .. import fields
from ..kernel_loader import get_kernels
from .initialization import ensure_ready

kernels = get_kernels()


def _selection_mode_code(selection_mode: str) -> int:
    mode = str(selection_mode or "all").strip().lower()
    if mode == "head":
        return 1
    if mode == "even":
        return 2
    return 0


def _great_mode_code(great_mode: str) -> int:
    gm = str(great_mode or "late").strip().lower()
    if gm == "early":
        return 1
    if gm == "full":
        return 2
    return 0


def _prepare_hitsim_groups_gpu(
    *,
    ts_ms: np.ndarray,
    note_types: np.ndarray,
    perfect_lower_ms: int,
    perfect_upper_ms: int,
    held_tail_type: int,
    held_tail_time_multiplier: int,
    great_lower_ms: int,
    great_extra_upper_ms: int,
    great_mode: str,
    ref_arrays: dict | None = None,
) -> tuple[np.ndarray, np.ndarray, int, int]:
    ensure_ready(ref_arrays)

    ts_ms = np.asarray(ts_ms, dtype=np.int32)
    note_types = np.asarray(note_types, dtype=np.int16)
    n_notes = int(ts_ms.shape[0])
    if n_notes <= 0:
        raise ValueError("ts_ms has no notes")
    if note_types.shape[0] != n_notes:
        raise ValueError("note_types shape mismatch")
    if n_notes > int(fields.MAX_HITSIM_NOTES):
        raise ValueError(f"Song has {n_notes} notes, max is {fields.MAX_HITSIM_NOTES}")

    kernels.hitsim_build_groups_from_notes_kernel(
        int(n_notes),
        ts_ms,
        note_types,
        int(perfect_lower_ms),
        int(perfect_upper_ms),
        int(held_tail_type),
        int(held_tail_time_multiplier),
        int(great_lower_ms),
        int(great_extra_upper_ms),
        int(_great_mode_code(great_mode)),
    )

    n_groups = int(fields.hitsim_group_count.to_numpy()[0])
    if n_groups <= 0:
        raise ValueError("GPU group builder produced no groups")
    if n_groups > int(fields.MAX_HITSIM_GROUPS):
        raise ValueError(f"Song has {n_groups} groups, max is {fields.MAX_HITSIM_GROUPS}")
    return ts_ms, note_types, int(n_notes), int(n_groups)


def materialize_human_hitsim_regime_gpu(
    *,
    ts_ms: np.ndarray,
    note_types: np.ndarray,
    alpha_num: int,
    alpha_den: int,
    perfect_lower_ms: int,
    perfect_upper_ms: int,
    held_tail_type: int,
    held_tail_time_multiplier: int,
    great_lower_ms: int,
    great_extra_upper_ms: int,
    great_mode: str,
    ref_arrays: dict | None = None,
) -> dict:
    """
    Materialize one deterministic HitSim regime on GPU.

    This is the regime-apply path used by selective continuation so we do not
    rebuild timestamps on CPU once exact boundary regimes are canonical.
    """
    if int(alpha_den) <= 0:
        raise ValueError("alpha_den must be positive")

    _ts_ms, _note_types, n_notes, n_groups = _prepare_hitsim_groups_gpu(
        ts_ms=ts_ms,
        note_types=note_types,
        perfect_lower_ms=perfect_lower_ms,
        perfect_upper_ms=perfect_upper_ms,
        held_tail_type=held_tail_type,
        held_tail_time_multiplier=held_tail_time_multiplier,
        great_lower_ms=great_lower_ms,
        great_extra_upper_ms=great_extra_upper_ms,
        great_mode=great_mode,
        ref_arrays=ref_arrays,
    )

    kernels.hitsim_compute_group_events_tmp_kernel(int(n_groups), int(alpha_num), int(alpha_den), 0)
    kernels.hitsim_prefix_max_tmp_kernel(int(n_groups))
    kernels.hitsim_broadcast_tmp_to_best_event_ms_kernel(int(n_groups), int(n_notes))
    kernels.hitsim_compute_group_events_tmp_kernel(int(n_groups), int(alpha_num), int(alpha_den), 1)
    kernels.hitsim_broadcast_tmp_to_best_great_ms_kernel(int(n_groups), int(n_notes))

    return {
        "event_ms": np.asarray(fields.hitsim_best_event_ms.to_numpy()[:n_notes], dtype=np.int32, order="C"),
        "great_ms": np.asarray(fields.hitsim_best_great_ms.to_numpy()[:n_notes], dtype=np.int32, order="C"),
    }


def refine_human_hitsim_exact_after_ga_gpu(
    *,
    ts_ms: np.ndarray,
    note_types: np.ndarray,
    signature_param_rows: tuple[tuple[int, int], ...] | list[tuple[int, int]],
    refine_candidates: list[dict],
    prev_score: int,
    max_regimes: int,
    selection_mode: str,
    perfect_lower_ms: int,
    perfect_upper_ms: int,
    held_tail_type: int,
    held_tail_time_multiplier: int,
    great_lower_ms: int,
    great_extra_upper_ms: int,
    great_mode: str,
    ref_arrays: dict | None = None,
) -> dict:
    """
    GPU exact-mode refinement. Returns a dict of GPU outputs:
      - best_score, best_candidate_idx
      - best alpha midpoint and regime bounds
      - counts: active_param_count, full_regime_count, selected_regime_count
      - best_event_ms, best_great_ms (int32 ms arrays)
      - sig_rows (row_count, 7) compact signature rows for best representative alpha
      - active_row_mask (row_count,) int32
    """
    _ts_ms, _note_types, n_notes, n_groups = _prepare_hitsim_groups_gpu(
        ts_ms=ts_ms,
        note_types=note_types,
        perfect_lower_ms=perfect_lower_ms,
        perfect_upper_ms=perfect_upper_ms,
        held_tail_type=held_tail_type,
        held_tail_time_multiplier=held_tail_time_multiplier,
        great_lower_ms=great_lower_ms,
        great_extra_upper_ms=great_extra_upper_ms,
        great_mode=great_mode,
        ref_arrays=ref_arrays,
    )

    # Build exact alpha regimes on GPU (Perfect spans only).
    kernels.hitsim_build_exact_alpha_regimes_kernel(int(fields.MAX_HITSIM_ALPHAS), int(fields.MAX_HITSIM_SPAN))
    n_alphas = int(fields.hitsim_alpha_count.to_numpy()[0])
    if n_alphas < 0:
        raise ValueError(
            "GPU alpha regime builder overflowed. "
            f"Try increasing GPU_HITSIM_MAX_ALPHAS (current {fields.MAX_HITSIM_ALPHAS}) "
            f"and/or GPU_HITSIM_MAX_SPAN (current {fields.MAX_HITSIM_SPAN})."
        )
    if n_alphas <= 0:
        raise ValueError("GPU alpha regime builder produced no alphas")

    # Upload unique timeline param rows.
    rows = list(signature_param_rows or ())
    n_rows = int(len(rows))
    if n_rows <= 0:
        raise ValueError("signature_param_rows empty")
    if n_rows > int(fields.MAX_HITSIM_ROWS):
        raise ValueError(f"Too many signature rows: {n_rows} > {fields.MAX_HITSIM_ROWS}")
    row_nf = np.empty((n_rows,), dtype=np.int32)
    row_ft = np.empty((n_rows,), dtype=np.int32)
    row_to_idx: dict[tuple[int, int], int] = {}
    for i, (nf, ft) in enumerate(rows):
        key = (int(nf), int(ft))
        row_nf[i] = int(nf)
        row_ft[i] = int(ft)
        row_to_idx[key] = int(i)

    kernels.hitsim_upload_rows_kernel(int(n_rows), row_nf, row_ft)

    # Upload candidates (mapped onto row indices).
    candidates = list(refine_candidates or [])
    n_candidates = int(len(candidates))
    if n_candidates <= 0:
        raise ValueError("refine_candidates empty")
    if n_candidates > int(fields.MAX_HITSIM_CANDIDATES):
        raise ValueError(f"Too many candidates: {n_candidates} > {fields.MAX_HITSIM_CANDIDATES}")

    cand_row_idx = np.empty((n_candidates,), dtype=np.int32)
    cand_base_value = np.empty((n_candidates,), dtype=np.float32)
    cand_combo_mul = np.empty((n_candidates,), dtype=np.float32)
    cand_fever_mul = np.empty((n_candidates,), dtype=np.float32)
    for i, cand in enumerate(candidates):
        score_inputs = cand.get("score_inputs") or {}
        key = tuple(score_inputs.get("timeline_key") or ())
        if len(key) != 2:
            raise ValueError("candidate missing timeline_key")
        row_idx = row_to_idx.get((int(key[0]), int(key[1])))
        if row_idx is None:
            raise ValueError("candidate timeline_key not present in signature_param_rows")
        cand_row_idx[i] = int(row_idx)
        cand_base_value[i] = np.float32(score_inputs.get("total_base", 0.0))
        cand_combo_mul[i] = np.float32(score_inputs.get("combo_mul", 1.0))
        cand_fever_mul[i] = np.float32(score_inputs.get("fever_mul", 1.0))

    kernels.hitsim_upload_candidates_kernel(
        int(n_candidates),
        cand_row_idx,
        cand_base_value,
        cand_combo_mul,
        cand_fever_mul,
    )

    # Evaluate all alpha midpoints in batches (keeps scratch buffer bounded).
    batch_max = int(fields.MAX_HITSIM_ALPHA_BATCH)
    for start in range(0, n_alphas, batch_max):
        batch = int(min(batch_max, n_alphas - start))
        kernels.hitsim_compute_group_events_batch_kernel(int(start), int(batch), int(n_groups))
        kernels.hitsim_prefix_max_batch_kernel(int(batch), int(n_groups))
        kernels.hitsim_eval_alpha_batch_kernel(
            int(start),
            int(batch),
            int(n_groups),
            int(n_notes),
            int(n_rows),
            int(n_candidates),
        )

    # Plan regimes + selection and select best (no CPU scoring/loops).
    kernels.hitsim_plan_regimes_kernel(
        int(n_alphas),
        int(n_rows),
        int(max_regimes),
        int(_selection_mode_code(selection_mode)),
    )
    kernels.hitsim_select_best_regime_kernel(int(prev_score))
    kernels.hitsim_pack_scalar_outputs_kernel()

    packed = np.asarray(fields.hitsim_scalar_out.to_numpy(), dtype=np.int32, order="C")
    best_score = int(packed[0])
    best_candidate_idx = int(packed[1])
    best_regime_idx = int(packed[2])
    best_alpha_num = int(packed[3])
    best_alpha_den = int(packed[4])
    best_left_num = int(packed[5])
    best_left_den = int(packed[6])
    best_right_num = int(packed[7])
    best_right_den = int(packed[8])
    best_rep_alpha = int(packed[9])
    active_param_count = int(packed[10])
    full_regime_count = int(packed[11])
    selected_regime_count = int(packed[12])

    # Stage compact signature rows for representative alpha (stable inside regime).
    kernels.hitsim_stage_signature_rows_kernel(int(best_rep_alpha), int(n_rows))
    sig_rows = np.asarray(fields.hitsim_sig_rows_staging.to_numpy()[:n_rows, :], dtype=np.int32, order="C")
    active_mask = np.asarray(fields.hitsim_active_row_mask.to_numpy()[:n_rows], dtype=np.int32, order="C")

    # Materialize best timestamps (perfect + great-candidate) on GPU.
    kernels.hitsim_compute_group_events_tmp_kernel(int(n_groups), int(best_alpha_num), int(best_alpha_den), 0)
    kernels.hitsim_prefix_max_tmp_kernel(int(n_groups))
    kernels.hitsim_broadcast_tmp_to_best_event_ms_kernel(int(n_groups), int(n_notes))
    kernels.hitsim_compute_group_events_tmp_kernel(int(n_groups), int(best_alpha_num), int(best_alpha_den), 1)
    kernels.hitsim_broadcast_tmp_to_best_great_ms_kernel(int(n_groups), int(n_notes))

    best_event_ms = np.asarray(fields.hitsim_best_event_ms.to_numpy()[:n_notes], dtype=np.int32, order="C")
    best_great_ms = np.asarray(fields.hitsim_best_great_ms.to_numpy()[:n_notes], dtype=np.int32, order="C")
    # Metadata-only: we avoid downloading extra GPU arrays just to count unique scores.
    unique_score_count = int(max(1, int(selected_regime_count) + 1))
    selected_regimes: list[dict] = []
    if int(selected_regime_count) > 0:
        alpha_best_score = np.asarray(fields.hitsim_alpha_best_score.to_numpy()[:n_alphas], dtype=np.int32, order="C")
        alpha_best_candidate_idx = np.asarray(
            fields.hitsim_alpha_best_candidate_idx.to_numpy()[:n_alphas], dtype=np.int32, order="C"
        )
        selected_regime_indices = np.asarray(
            fields.hitsim_selected_regime_indices.to_numpy()[:selected_regime_count], dtype=np.int32, order="C"
        )
        regime_left_num = np.asarray(fields.hitsim_regime_left_num.to_numpy()[:full_regime_count], dtype=np.int32, order="C")
        regime_left_den = np.asarray(fields.hitsim_regime_left_den.to_numpy()[:full_regime_count], dtype=np.int32, order="C")
        regime_right_num = np.asarray(fields.hitsim_regime_right_num.to_numpy()[:full_regime_count], dtype=np.int32, order="C")
        regime_right_den = np.asarray(fields.hitsim_regime_right_den.to_numpy()[:full_regime_count], dtype=np.int32, order="C")
        regime_alpha_num = np.asarray(fields.hitsim_regime_alpha_num.to_numpy()[:full_regime_count], dtype=np.int32, order="C")
        regime_alpha_den = np.asarray(fields.hitsim_regime_alpha_den.to_numpy()[:full_regime_count], dtype=np.int32, order="C")
        regime_rep_alpha = np.asarray(fields.hitsim_regime_rep_alpha.to_numpy()[:full_regime_count], dtype=np.int32, order="C")
        regime_selected_mask = np.asarray(
            fields.hitsim_regime_selected_mask.to_numpy()[:full_regime_count], dtype=np.int32, order="C"
        )
        for raw_regime_idx in selected_regime_indices:
            regime_idx = int(raw_regime_idx)
            if regime_idx < 0 or regime_idx >= int(full_regime_count):
                continue
            if int(regime_selected_mask[regime_idx]) == 0:
                continue
            rep_alpha = int(regime_rep_alpha[regime_idx])
            if rep_alpha < 0 or rep_alpha >= int(n_alphas):
                continue
            selected_regimes.append(
                {
                    "regime_idx": int(regime_idx),
                    "left_num": int(regime_left_num[regime_idx]),
                    "left_den": int(regime_left_den[regime_idx]),
                    "right_num": int(regime_right_num[regime_idx]),
                    "right_den": int(regime_right_den[regime_idx]),
                    "alpha_num": int(regime_alpha_num[regime_idx]),
                    "alpha_den": int(regime_alpha_den[regime_idx]),
                    "rep_alpha": int(rep_alpha),
                    "best_score": int(alpha_best_score[rep_alpha]),
                    "best_candidate_idx": int(alpha_best_candidate_idx[rep_alpha]),
                    "family": "ftff_boundary_rows",
                    "scope": "ALL",
                }
            )

    return {
        "best_score": int(best_score),
        "best_candidate_idx": int(best_candidate_idx),
        "best_regime_idx": int(best_regime_idx),
        "best_alpha_num": int(best_alpha_num),
        "best_alpha_den": int(best_alpha_den),
        "best_left_num": int(best_left_num),
        "best_left_den": int(best_left_den),
        "best_right_num": int(best_right_num),
        "best_right_den": int(best_right_den),
        "best_rep_alpha": int(best_rep_alpha),
        "active_param_count": int(active_param_count),
        "full_regime_count": int(full_regime_count),
        "selected_regime_count": int(selected_regime_count),
        "raw_interval_count": int(n_alphas),
        "row_count": int(n_rows),
        "unique_scores": int(unique_score_count),
        "best_event_ms": best_event_ms,
        "best_great_ms": best_great_ms,
        "sig_rows": sig_rows,
        "active_row_mask": active_mask,
        "selected_regimes": selected_regimes,
    }
