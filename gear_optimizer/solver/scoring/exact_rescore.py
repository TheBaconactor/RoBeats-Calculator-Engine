"""
CPU exact score replay helpers.

These helpers are intentionally outside the GPU/JIT hot path. They are used for
canonical replay, persistence, and DB repair where the final visible score should
follow Python/Luau-style double precision instead of the optimizer's f32 GPU
search score.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import floor
import threading
from typing import Any, Mapping

import numpy as np

from ...core.constants import FEVER_FILL_BASE_RATE, FEVER_TIME_OFFSET, FEVER_TIME_SCALE, TOTAL_ROWS
from ...helpers.song_helpers.ref_array_builder import resolve_exact_replay_ref_arrays
from ...core.utils import safe_float, safe_int
from ..fever_timeline import calculate_fever_timeline_indices, calculate_force_greats_timeline_indices
from ..score_math import lookup_reference_py
from .fg_policy import (
    accumulate_fg_penalties,
    build_fg_result_dict,
    build_penalty_table_and_body,
    compute_great_penalty_base,
    extract_fg_song_inputs,
    extract_song_meta,
    resolve_stat_factors,
)


_FG_TIMELINE_TLS = threading.local()

# IR schema version -- bump when the ExactScoreIR field set changes. Part of the
# cache_key so reverse-row-predicate compilers and any persisted IR-derived
# artifacts invalidate cleanly on a schema change.
_IR_SCHEMA_VERSION = 1

# Batch slab bounds: the head replay holds ~4 K x 100 f64 intermediates and
# the pool reduction a (pool x K) f64 lane matrix; these caps bound peak RAM
# to a few hundred MB regardless of batch size or pool width.
_CELL_SLAB_HEAD_ROWS = 65_536
_CELL_SLAB_LANE_ELEMS = 16_000_000


@dataclass(frozen=True, slots=True)
class ExactScoreIR:
    """Shared immutable scoring IR for one (chart, ref-table-version, timing-mode).

    Compiled once by ``build_exact_score_ir`` and consumed by BOTH the forward
    scorer (``score_from_ir``) and the reverse row-predicate compiler. The
    field groups (see the K0 audit for full source-line provenance):

    1. Chart state (song-intrinsic scalars)
    2. Ref tables (PP/CM/FM float64, FT/FF float32 axes, shape (161,))
    3. Clamps (stat-index and stat-value bounds, fever fill floor, base_notes offset)
    4. Plateaus (np.unique dedup of PP/CM/FM tables -> values + inverse)
    5. Color projection (base_int formula "2*primary + secondary" and 2-color collapse "v=2*c1+c2")
    6. Frontier grid (per-cell replay pools, head bits, head coeffs, fever activations)
    7. Score formulas (op-order-preserving f64 envelopes; total_score is max over pool lanes)
    8. Residues (per-row stat factors and head residue integers)
    9. Cache key tuple (frontier_cache_key, ref_content_hash, timing_mode, ir_schema_version)
    """

    # Group 1 -- chart state
    total_notes: int
    head_len: int
    body_total: int
    primary_color: str
    secondary_color: str
    color_projection: str
    timing_mode: str
    fever_fill_base_rate: float
    fever_time_scale: float
    fever_time_offset: float
    long_notes: int
    last_note_time: float

    # Group 2 -- ref tables (float64) and FT/FF axes (float32)
    pp_table: np.ndarray
    cm_table: np.ndarray
    fm_table: np.ndarray
    ft_axis: np.ndarray
    ff_axis: np.ndarray

    # Group 3 -- clamps
    stat_index_clamp_lo: int
    stat_index_clamp_hi: int
    stat_value_clamp_lo: int
    stat_value_clamp_hi: int
    fever_fill_floor: int
    base_notes_first_section_offset: int

    # Group 4 -- plateaus (derived-key collapse)
    pp_plateau_values: np.ndarray
    pp_plateau_inverse: np.ndarray
    cm_plateau_values: np.ndarray
    cm_plateau_inverse: np.ndarray
    fm_plateau_values: np.ndarray
    fm_plateau_inverse: np.ndarray

    # Group 5 -- color projection
    base_int_formula: str
    base_int_range: tuple[int, int]
    two_color_collapse_v: str

    # Group 6 -- frontier grid (payload views; the payload stays alive via cache)
    frontier_grid_count: np.ndarray
    frontier_grid_offset: np.ndarray
    frontier_pool_used: int
    frontier_body_fever_pool: np.ndarray
    frontier_body_normal_pool: np.ndarray
    frontier_masks_bits_pool: np.ndarray
    frontier_head_coeffs_pool: np.ndarray
    frontier_head_len: np.ndarray
    frontier_body_fever_min_max: tuple[int, int]
    frontier_body_normal_min_max: tuple[int, int]
    frontier_fever_activations: np.ndarray

    # Group 7 -- score formulas (the f64 op-order envelope guard)
    combo_val_formula: str
    fever_val_formula: str
    body_score_formula: str
    head_combo_slope_formula: str
    head_perfect_value_formula: str
    head_normal_score_formula: str
    head_fever_score_formula: str
    head_fever_delta_formula: str
    head_score_formula: str
    total_score_formula: str
    f64_envelope_guard: int

    # Group 8 -- residues (per-row stat factors are computed in score_from_ir;
    # these are the canonical formula strings + head residue integers for the
    # perfect-window single-bar path the IR is built for)
    residue_pp_factor: str
    residue_combo_val: str
    residue_fever_val: str
    residue_head_normal_i: str
    residue_head_fever_i: str
    residue_great_penalty_base: str
    gear_power_formula: str
    accuracy_formula: str

    # Group 9 -- cache key
    cache_key: tuple


def build_exact_score_ir(
    calc_song: Mapping[str, Any],
    ref_arrays: Mapping[str, Any],
    *,
    timing_mode: str | None = None,
) -> ExactScoreIR:
    """Build the shared immutable scoring IR for one chart.

    Performs the canonical preparation sequence:
      ``build_or_load_timeline_frontier_payload`` -> ``_frontier_replay_refs`` ->
      plateau dedup (``np.unique`` on PP/CM/FM tables) ->
      frontier body range derivation.

    Idempotent over (frontier cache_key, ref content hash, timing_mode).
    """
    from ..taichi_gem.api.timeline import build_or_load_timeline_frontier_payload

    song_dict = calc_song if isinstance(calc_song, dict) else dict(calc_song)
    song_data = song_dict.get("song_data", {}) or {}
    timestamps = song_data.get("chart_timestamps")
    if timestamps is None:
        timestamps = song_data.get("timestamps", ())
    total_notes = int(len(timestamps))

    frontier_refs = _frontier_replay_refs(ref_arrays)
    resolved_timing_mode = _resolve_timing_mode(song_dict, timing_mode)
    frontier_result = build_or_load_timeline_frontier_payload(
        song_dict, frontier_refs, timing_mode=resolved_timing_mode
    )
    payload = frontier_result.payload
    song_meta = extract_song_meta(song_dict)
    metadata = song_dict.get("metadata", {}) or {}
    long_notes = safe_int(metadata.get("Long Notes"), 0)
    default_last_note = float(timestamps[-1]) if total_notes else 0.0
    last_note_time = safe_float(metadata.get("Last Note Time"), default_last_note)

    pp_table = np.asarray(frontier_refs["Perfect Points"], dtype=np.float64).reshape(-1)
    cm_table = np.asarray(frontier_refs["Combo Multiplier"], dtype=np.float64).reshape(-1)
    fm_table = np.asarray(frontier_refs["Fever Multiplier"], dtype=np.float64).reshape(-1)
    ft_axis = np.asarray(frontier_refs["Fever Time"], dtype=np.float32).reshape(-1)
    ff_axis = np.asarray(frontier_refs["Fever Fill Rate"], dtype=np.float32).reshape(-1)

    pp_plateau_values, pp_plateau_inverse = np.unique(pp_table[: TOTAL_ROWS + 1], return_inverse=True)
    cm_plateau_values, cm_plateau_inverse = np.unique(cm_table[: TOTAL_ROWS + 1], return_inverse=True)
    fm_plateau_values, fm_plateau_inverse = np.unique(fm_table[: TOTAL_ROWS + 1], return_inverse=True)

    head_len = min(max(0, int(total_notes)), 100)
    body_total = max(0, int(total_notes) - 100)

    frontier_grid_count = np.asarray(payload.grid_frontier_count[0], dtype=np.int32)
    frontier_grid_offset = np.asarray(payload.grid_frontier_offset[0], dtype=np.int32)
    frontier_pool_used = int(payload.frontier_pool_used)
    frontier_body_fever_pool = np.asarray(payload.grid_frontier_body_fever_pool[0], dtype=np.int64)
    frontier_body_normal_pool = np.asarray(payload.grid_frontier_body_normal_pool[0], dtype=np.int64)
    frontier_masks_bits_pool = np.asarray(payload.grid_frontier_masks_bits_pool[0], dtype=np.uint64)
    frontier_head_coeffs_pool = np.asarray(payload.grid_frontier_head_coeffs_pool[0], dtype=np.int16)
    frontier_head_len = np.asarray(payload.grid_head_len[0], dtype=np.int8)
    frontier_fever_activations = np.asarray(payload.grid_fever_activations[0], dtype=np.int32)

    if frontier_pool_used > 0:
        body_fever_min = int(frontier_body_fever_pool[:frontier_pool_used].min())
        body_fever_max = int(frontier_body_fever_pool[:frontier_pool_used].max())
        body_normal_min = int(frontier_body_normal_pool[:frontier_pool_used].min())
        body_normal_max = int(frontier_body_normal_pool[:frontier_pool_used].max())
    else:
        body_fever_min = body_fever_max = 0
        body_normal_min = body_normal_max = 0

    ref_content_hash = (
        bytes(np.array(pp_table[: TOTAL_ROWS + 1].tobytes())),
        bytes(np.array(cm_table[: TOTAL_ROWS + 1].tobytes())),
        bytes(np.array(fm_table[: TOTAL_ROWS + 1].tobytes())),
        bytes(np.array(ft_axis[: TOTAL_ROWS + 1].tobytes())),
        bytes(np.array(ff_axis[: TOTAL_ROWS + 1].tobytes())),
    )

    cache_key = (
        frontier_result.cache_key,
        ref_content_hash,
        str(resolved_timing_mode),
        int(_IR_SCHEMA_VERSION),
    )

    return ExactScoreIR(
        total_notes=int(total_notes),
        head_len=int(head_len),
        body_total=int(body_total),
        primary_color=str(song_meta.primary_color),
        secondary_color=str(song_meta.secondary_color),
        color_projection="2*primary + secondary",
        timing_mode=str(resolved_timing_mode),
        fever_fill_base_rate=float(FEVER_FILL_BASE_RATE),
        fever_time_scale=float(FEVER_TIME_SCALE),
        fever_time_offset=float(FEVER_TIME_OFFSET),
        long_notes=int(long_notes),
        last_note_time=float(last_note_time),
        pp_table=pp_table,
        cm_table=cm_table,
        fm_table=fm_table,
        ft_axis=ft_axis,
        ff_axis=ff_axis,
        stat_index_clamp_lo=0,
        stat_index_clamp_hi=int(TOTAL_ROWS),
        stat_value_clamp_lo=-80,
        stat_value_clamp_hi=160,
        fever_fill_floor=1,
        base_notes_first_section_offset=-1,
        pp_plateau_values=pp_plateau_values,
        pp_plateau_inverse=pp_plateau_inverse,
        cm_plateau_values=cm_plateau_values,
        cm_plateau_inverse=cm_plateau_inverse,
        fm_plateau_values=fm_plateau_values,
        fm_plateau_inverse=fm_plateau_inverse,
        base_int_formula="2*primary + secondary",
        base_int_range=(0, 2 * 250 + 250),
        two_color_collapse_v="v = 2*c1 + c2",
        frontier_grid_count=frontier_grid_count,
        frontier_grid_offset=frontier_grid_offset,
        frontier_pool_used=int(frontier_pool_used),
        frontier_body_fever_pool=frontier_body_fever_pool,
        frontier_body_normal_pool=frontier_body_normal_pool,
        frontier_masks_bits_pool=frontier_masks_bits_pool,
        frontier_head_coeffs_pool=frontier_head_coeffs_pool,
        frontier_head_len=frontier_head_len,
        frontier_body_fever_min_max=(int(body_fever_min), int(body_fever_max)),
        frontier_body_normal_min_max=(int(body_normal_min), int(body_normal_max)),
        frontier_fever_activations=frontier_fever_activations,
        combo_val_formula="floor(base_value * combo_f)",
        fever_val_formula="floor(base_value * combo_f * fever_f)",
        body_score_formula="body_fever * fever_val + body_normal * combo_val",
        head_combo_slope_formula="(combo_f - 1.0) / 100.0",
        head_perfect_value_formula="base_value * ((combo_slope * (i + 1)) + 1.0)",
        head_normal_score_formula="floor(perfect_value)",
        head_fever_score_formula="floor(perfect_value * fever_f)",
        head_fever_delta_formula="head_fever_score - head_normal_score",
        head_score_formula="sum over i in [0, head_len) of (is_fever ? head_fever_score : head_normal_score)",
        total_score_formula="max over pool lanes of (body_score + head_score)",
        f64_envelope_guard=int(2**52),
        residue_pp_factor="lookup_reference_py(pp_stat, pp_table, TOTAL_ROWS)",
        residue_combo_val="floor(base_value * combo_f)",
        residue_fever_val="floor(base_value * combo_f * fever_f)",
        residue_head_normal_i="floor(base_value * ((combo_slope * (i + 1)) + 1.0))",
        residue_head_fever_i="floor(base_value * ((combo_slope * (i + 1)) + 1.0) * fever_f)",
        residue_great_penalty_base="compute_great_penalty_base(primary_val, secondary_val)",
        gear_power_formula="(2 * primary_val + secondary_val) + pp_factor",
        accuracy_formula="score / max(1, total_score_formula)",
        cache_key=cache_key,
    )


def _resolve_timing_mode(calc_song: Mapping[str, Any], timing_mode: str | None) -> str:
    if timing_mode is not None:
        mode = str(timing_mode).strip().lower()
    else:
        metadata = (calc_song.get("metadata", {}) or {}) if isinstance(calc_song, Mapping) else {}
        mode = str(
            metadata.get("TimingEnvelopeMode") or metadata.get("Timing Mode") or "perfect_window"
        ).strip().lower()
    if mode not in {"perfect_window", "zero_ms"}:
        raise ValueError(f"unknown timeline frontier timing mode {timing_mode!r}")
    return mode


def score_from_ir(
    ir: ExactScoreIR,
    primary_val: np.ndarray,
    secondary_val: np.ndarray,
    pp_stat: np.ndarray,
    cm_stat: np.ndarray,
    fm_stat: np.ndarray,
    ft_stat: np.ndarray,
    ff_stat: np.ndarray,
) -> np.ndarray:
    """Forward array-native scores from a prebuilt IR.

    Canonical forward path: derived-key collapse (group 4) -> per-(FT,FF)-cell
    vectorized pool replay (groups 6-7) -> argmax over pool lanes (group 7,
    ``total_score_formula``). Bit-identical to the per-row replay by
    construction (same f64 op order per lane, exact int64 reductions).

    Both the forward Vulkan scorer and the reverse engine's canonical
    soundness gate call this.
    """
    pv = np.asarray(primary_val, dtype=np.int64).reshape(-1)
    sv = np.asarray(secondary_val, dtype=np.int64).reshape(-1)
    ppi = np.clip(np.asarray(pp_stat, dtype=np.int64).reshape(-1), 0, TOTAL_ROWS)
    cmi = np.clip(np.asarray(cm_stat, dtype=np.int64).reshape(-1), 0, TOTAL_ROWS)
    fmi = np.clip(np.asarray(fm_stat, dtype=np.int64).reshape(-1), 0, TOTAL_ROWS)
    fti = np.clip(np.asarray(ft_stat, dtype=np.int64).reshape(-1), 0, TOTAL_ROWS)
    ffi = np.clip(np.asarray(ff_stat, dtype=np.int64).reshape(-1), 0, TOTAL_ROWS)
    n = int(pv.shape[0])
    if n == 0:
        return np.zeros(0, dtype=np.int64)
    if ir.total_notes <= 0:
        return np.zeros(n, dtype=np.int64)

    base_int = 2 * pv + sv
    base_min = int(base_int.min())
    base_off = base_int - base_min
    n_base = int(base_off.max()) + 1
    dims = (
        n_base,
        int(ir.pp_plateau_values.size),
        int(ir.cm_plateau_values.size),
        int(ir.fm_plateau_values.size),
        TOTAL_ROWS + 1,
        TOTAL_ROWS + 1,
    )
    packed_span = 1
    for d in dims:
        packed_span *= int(d)
    if packed_span >= 2**63:
        raise ValueError(
            f"stat rows outside the packable derived-key range (span {packed_span})"
        )
    key = base_off
    for id_col, d in (
        (ir.pp_plateau_inverse[ppi], dims[1]),
        (ir.cm_plateau_inverse[cmi], dims[2]),
        (ir.fm_plateau_inverse[fmi], dims[3]),
        (fti, dims[4]),
        (ffi, dims[5]),
    ):
        key = key * d + id_col
    uniq_key, first_idx, inverse = np.unique(key, return_index=True, return_inverse=True)

    u_base = base_int[first_idx]
    u_ppf = ir.pp_table[ppi[first_idx]].astype(np.float64)
    u_cmf = ir.cm_table[cmi[first_idx]].astype(np.float64)
    u_fmf = ir.fm_table[fmi[first_idx]].astype(np.float64)
    u_ft = fti[first_idx]
    u_ff = ffi[first_idx]

    out_u = np.zeros(uniq_key.size, dtype=np.int64)
    cell = u_ft * (TOTAL_ROWS + 1) + u_ff
    for cell_key in np.unique(cell):
        sel = np.flatnonzero(cell == cell_key)
        ft_i = int(cell_key) // (TOTAL_ROWS + 1)
        ff_i = int(cell_key) % (TOTAL_ROWS + 1)
        out_u[sel] = _replay_cell(
            ir,
            ft_i=int(ft_i),
            ff_i=int(ff_i),
            base_int=u_base[sel],
            pp_factor=u_ppf[sel],
            combo_mul=u_cmf[sel],
            fever_mul=u_fmf[sel],
        )
    return out_u[inverse]


def score_from_ir_with_pool_idx(
    ir: ExactScoreIR,
    primary_val: int,
    secondary_val: int,
    pp_factor: float,
    combo_mul: float,
    fever_mul: float,
    ft_idx: int,
    ff_idx: int,
) -> tuple[int, int]:
    """Single-row twin of ``score_from_ir`` returning (score, winning pool index).

    The winner's pool index is what the timeline-trace reconstruction needs.
    Bit-identical to ``score_from_ir`` for the same inputs.
    """
    ft_i = max(0, min(int(ft_idx), TOTAL_ROWS))
    ff_i = max(0, min(int(ff_idx), TOTAL_ROWS))
    scores = _replay_cell(
        ir,
        ft_i=int(ft_i),
        ff_i=int(ff_i),
        base_int=np.array([int(primary_val) * 2 + int(secondary_val)], dtype=np.int64),
        pp_factor=np.array([float(pp_factor)], dtype=np.float64),
        combo_mul=np.array([float(combo_mul)], dtype=np.float64),
        fever_mul=np.array([float(fever_mul)], dtype=np.float64),
        return_pool_idx=True,
    )
    if isinstance(scores, tuple):
        return int(scores[0][0]), int(scores[1][0])
    return int(scores[0]), int(scores[2])


def _replay_cell(
    ir: ExactScoreIR,
    *,
    ft_i: int,
    ff_i: int,
    base_int: np.ndarray,
    pp_factor: np.ndarray,
    combo_mul: np.ndarray,
    fever_mul: np.ndarray,
    return_pool_idx: bool = False,
) -> np.ndarray | tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Exact scores for one (FT, FF) frontier cell, vectorized over rows.

    Per-element f64 op order matches ``_score_timeline_frontier_payload_
    vectorized_result`` exactly; only exact-integer reductions are regrouped
    (int64 sums; the pool bit-matrix product runs in f64, which is exact for
    the guarded < 2^52 magnitudes). When ``return_pool_idx`` is True, also
    returns the per-row winning pool index (same argmax as the score).
    """
    frontier_count = int(ir.frontier_grid_count[ft_i, ff_i])
    if frontier_count <= 0:
        raise ValueError("Timing frontier payload has no replayable surface for the requested FT/FF cell")
    frontier_offset = int(ir.frontier_grid_offset[ft_i, ff_i])
    frontier_limit = int(frontier_offset + frontier_count)
    if frontier_offset < 0 or frontier_limit > int(ir.frontier_pool_used):
        raise ValueError("Timing frontier payload contains an invalid surface range")

    body_total = int(ir.body_total)
    body_fever = np.asarray(
        ir.frontier_body_fever_pool[frontier_offset:frontier_limit],
        dtype=np.int64,
    )
    body_normal = np.asarray(
        ir.frontier_body_normal_pool[frontier_offset:frontier_limit],
        dtype=np.int64,
    )
    if bool(np.any(body_fever < 0)) or bool(np.any(body_normal < 0)) or bool(
        np.any((body_fever + body_normal) != int(body_total))
    ):
        raise ValueError("Timing surface body counts do not match song body note count")

    head_len = int(ir.head_len)
    pool_n = int(body_fever.shape[0])
    k_total = int(base_int.shape[0])
    slab = max(1, min(_CELL_SLAB_HEAD_ROWS, _CELL_SLAB_LANE_ELEMS // max(1, pool_n)))
    out = np.zeros(k_total, dtype=np.int64)
    pool_idx_out = np.zeros(k_total, dtype=np.int64) if return_pool_idx else None
    head_bits_f64: np.ndarray | None = None

    for start in range(0, k_total, slab):
        stop = min(k_total, start + slab)
        base = base_int[start:stop].astype(np.float64) + pp_factor[start:stop]
        combo = combo_mul[start:stop]
        fever = fever_mul[start:stop]
        bc = base * combo
        combo_val = np.floor(bc).astype(np.int64)
        fever_val = np.floor(bc * fever).astype(np.int64)
        delta_body = fever_val - combo_val
        scores0 = np.int64(body_total) * combo_val

        head_delta: np.ndarray | None = None
        if head_len > 0:
            positions = np.arange(1, head_len + 1, dtype=np.float64)
            combo_slope = (combo - np.float64(1.0)) / np.float64(100.0)
            perfect_values = base[:, None] * ((combo_slope[:, None] * positions[None, :]) + np.float64(1.0))
            normal_scores = np.floor(perfect_values).astype(np.int64)
            fever_scores = np.floor(perfect_values * fever[:, None]).astype(np.int64)
            scores0 = scores0 + normal_scores.sum(axis=1)
            head_delta = fever_scores - normal_scores
            if not bool(np.any(head_delta)):
                head_delta = None

        if head_delta is None and not bool(np.any(delta_body)):
            out[start:stop] = scores0
            if return_pool_idx:
                # Argmax over a constant lane vector returns 0 for all rows.
                pool_idx_out[start:stop] = int(frontier_offset)
            continue

        bound = int(np.abs(delta_body).max()) * max(1, body_total)
        if head_delta is not None:
            bound += int(np.abs(head_delta).max()) * head_len
        if bound >= int(ir.f64_envelope_guard):
            raise ValueError("frontier replay magnitudes exceed the exact f64 envelope")

        lane = body_fever.astype(np.float64)[:, None] * delta_body.astype(np.float64)[None, :]
        if head_delta is not None:
            if head_bits_f64 is None:
                words = np.asarray(
                    ir.frontier_masks_bits_pool[frontier_offset:frontier_limit, :4],
                    dtype=np.uint64,
                )
                note_idx = np.arange(head_len)
                head_bits_f64 = (
                    (words[:, note_idx // 32] >> (note_idx % 32).astype(np.uint64)) & np.uint64(1)
                ).astype(np.float64)
            lane = lane + head_bits_f64 @ head_delta.T.astype(np.float64)
        lane_i64 = lane.astype(np.int64)
        out[start:stop] = scores0 + lane_i64.max(axis=0)
        if return_pool_idx:
            winner_local = np.argmax(lane_i64, axis=0)
            pool_idx_out[start:stop] = frontier_offset + winner_local
    if return_pool_idx:
        return out, pool_idx_out, np.full(k_total, int(frontier_offset), dtype=np.int64)
    return out

# Base timeline-trace memo: the reconstructed trace is a pure function of
# (frontier payload cache_key, FT cell, FF cell, winning pool row) -- stats enter only
# through those. The cache_key is content-addressed (song + ref axes + cache version),
# so entries can never alias across songs or ref tables. Memoized values are kept
# pristine; every hand-out is a fresh copy because callers graft the per-note dicts
# into mutable details payloads.
_TIMELINE_TRACE_MEMO: dict[tuple, dict[str, Any]] = {}
_TIMELINE_TRACE_MEMO_MAX = 4096


def _copy_timeline_trace_meta(meta: dict[str, Any]) -> dict[str, Any]:
    out = dict(meta)
    out["frontier_trace"] = [dict(source) for source in meta["frontier_trace"]]
    out["response_surface"] = list(meta["response_surface"])
    return out


def _get_fg_timeline_buffers(total_notes: int):
    n = max(0, int(total_notes))
    section_cap = n + 1

    buf = getattr(_FG_TIMELINE_TLS, "buf", None)
    if buf is None:
        buf = {}
        _FG_TIMELINE_TLS.buf = buf

    fever_mask = buf.get("fever_mask")
    if fever_mask is None or int(getattr(fever_mask, "shape", (0,))[0]) != n:
        fever_mask = np.zeros(n, dtype=np.bool_)
        buf["fever_mask"] = fever_mask
    else:
        fever_mask[:] = False

    section_start = buf.get("section_start")
    if section_start is None or int(getattr(section_start, "shape", (0,))[0]) != section_cap:
        section_start = np.zeros(section_cap, dtype=np.int32)
        buf["section_start"] = section_start
    else:
        section_start[:] = 0

    section_forced = buf.get("section_forced")
    if section_forced is None or int(getattr(section_forced, "shape", (0,))[0]) != section_cap:
        section_forced = np.zeros(section_cap, dtype=np.int32)
        buf["section_forced"] = section_forced
    else:
        section_forced[:] = 0

    section_fill_penalty = buf.get("section_fill_penalty")
    if section_fill_penalty is None or int(getattr(section_fill_penalty, "shape", (0,))[0]) != section_cap:
        section_fill_penalty = np.zeros(section_cap, dtype=np.int32)
        buf["section_fill_penalty"] = section_fill_penalty
    else:
        section_fill_penalty[:] = 0

    section_skip_wasted = buf.get("section_skip_wasted")
    if section_skip_wasted is None or int(getattr(section_skip_wasted, "shape", (0,))[0]) != section_cap:
        section_skip_wasted = np.zeros(section_cap, dtype=np.bool_)
        buf["section_skip_wasted"] = section_skip_wasted
    else:
        section_skip_wasted[:] = False

    return fever_mask, section_start, section_forced, section_fill_penalty, section_skip_wasted


def _compute_force_greats_timeline(
    timestamps,
    perfect_candidate_timestamps,
    great_candidate_timestamps,
    perfect_floor_timestamps,
    total_notes,
    fever_fill_rate,
    fever_time_stat,
    long_notes,
    last_note_time,
    force_counts,
    *,
    clamp_base_notes_nonnegative,
    clamp_forced_to_section_notes,
    use_forced_great_timing,
):
    forced_arr = np.asarray(force_counts, dtype=np.int32) if force_counts else np.zeros(0, dtype=np.int32)
    fever_mask_buffer, section_start, section_forced, section_fill_penalty, section_skip_wasted = (
        _get_fg_timeline_buffers(int(total_notes))
    )

    (
        fever_mask_head_view,
        count_body_fever,
        count_body_normal,
        non_fever_base,
        section_count,
    ) = calculate_force_greats_timeline_indices(
        timestamps,
        perfect_candidate_timestamps,
        great_candidate_timestamps,
        perfect_floor_timestamps,
        total_notes,
        fever_fill_rate,
        fever_time_stat,
        long_notes,
        last_note_time,
        forced_arr,
        int(forced_arr.shape[0]),
        bool(clamp_base_notes_nonnegative),
        bool(clamp_forced_to_section_notes),
        bool(use_forced_great_timing),
        fever_mask_buffer,
        section_start,
        section_forced,
        section_fill_penalty,
        section_skip_wasted,
    )

    section_details = []
    for i in range(int(section_count)):
        base_notes = int(non_fever_base) - 1 if i == 0 else int(non_fever_base)
        if clamp_base_notes_nonnegative:
            base_notes = max(0, int(base_notes))
        notes_to_fill = int(base_notes) + int(section_fill_penalty[i])

        section_details.append(
            {
                "start_idx": int(section_start[i]),
                "forced": int(section_forced[i]),
                "fill_penalty_notes": int(section_fill_penalty[i]),
                "skip_wasted": bool(section_skip_wasted[i]),
                "notes": int(notes_to_fill),
            }
        )

    return (
        fever_mask_head_view.copy(),
        int(count_body_fever),
        int(count_body_normal),
        int(non_fever_base),
        section_details,
    )


def calculate_score_exact(
    base_value: float,
    combo_mul: float,
    fever_mul: float,
    fever_mask_head,
    count_body_fever: int,
    count_body_normal: int,
) -> int:
    """
    Score a fixed timeline using float64 arithmetic and per-note floors.

    This mirrors the existing scoring order, but deliberately avoids f32 casts
    so retained/replayed rows do not inherit GPU boundary drift.
    """
    base_f = float(base_value)
    combo_f = float(combo_mul)
    fever_f = float(fever_mul)

    combo_val_per_note = floor(base_f * combo_f)
    fever_val_per_note = floor(base_f * combo_f * fever_f)
    body_score = (int(count_body_fever) * fever_val_per_note) + (int(count_body_normal) * combo_val_per_note)

    total_head = 0
    combo_slope = (combo_f - 1.0) / 100.0
    for i, is_fever in enumerate(fever_mask_head):
        scaling = (combo_slope * float(i + 1)) + 1.0
        perfect_value = base_f * scaling
        total_head += floor(perfect_value * fever_f) if bool(is_fever) else floor(perfect_value)

    return int(body_score + total_head)


def score_stats_exact(
    stats: Mapping[str, Any],
    calc_song: Mapping[str, Any],
    ref_arrays: Mapping[str, Any],
) -> int:
    return int(score_stats_exact_batch([stats], calc_song, ref_arrays)[0])


def score_stats_exact_with_timeline_trace(
    stats: Mapping[str, Any],
    calc_song: Mapping[str, Any],
    ref_arrays: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(stats, Mapping) or not stats:
        return {"score": 0, "TimelineFrontier": {"frontier_trace": []}}

    song_dict = calc_song if isinstance(calc_song, dict) else dict(calc_song)
    song_data = song_dict.get("song_data", {}) or {}
    timestamps = song_data.get("chart_timestamps")
    if timestamps is None:
        timestamps = song_data.get("timestamps", ())
    total_notes = int(len(timestamps))
    if total_notes <= 0:
        return {"score": 0, "TimelineFrontier": {"frontier_trace": []}}

    frontier_refs = _frontier_replay_refs(ref_arrays)
    ir = build_exact_score_ir(song_dict, frontier_refs)
    song_meta = extract_song_meta(song_dict)
    (
        primary_val,
        secondary_val,
        pp_factor,
        combo_mul,
        fever_mul,
        ft_idx,
        ff_idx,
    ) = _score_stat_inputs(stats, frontier_refs, song_meta.primary_color, song_meta.secondary_color)
    ft_i = max(0, min(int(ft_idx), TOTAL_ROWS))
    ff_i = max(0, min(int(ff_idx), TOTAL_ROWS))

    best_score, pool_idx = score_from_ir_with_pool_idx(
        ir,
        primary_val=int(primary_val),
        secondary_val=int(secondary_val),
        pp_factor=float(pp_factor),
        combo_mul=float(combo_mul),
        fever_mul=float(fever_mul),
        ft_idx=int(ft_idx),
        ff_idx=int(ff_idx),
    )
    memo_key = (ir.cache_key[0], ft_i, ff_i, int(pool_idx))
    frontier_meta = _TIMELINE_TRACE_MEMO.get(memo_key)
    if frontier_meta is None:
        frontier_meta = _timeline_trace_for_payload_surface(
            payload=_ir_payload_view(ir),
            pool_idx=int(pool_idx),
            total_notes=int(total_notes),
            ft_idx=int(ft_idx),
            ff_idx=int(ff_idx),
            calc_song=song_dict,
            ref_arrays=frontier_refs,
        )
        while len(_TIMELINE_TRACE_MEMO) >= _TIMELINE_TRACE_MEMO_MAX:
            _TIMELINE_TRACE_MEMO.pop(next(iter(_TIMELINE_TRACE_MEMO)))
        _TIMELINE_TRACE_MEMO[memo_key] = frontier_meta
    return {"score": int(best_score), "TimelineFrontier": _copy_timeline_trace_meta(frontier_meta)}


def score_stats_exact_batch(
    stats_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
    calc_song: Mapping[str, Any],
    ref_arrays: Mapping[str, Any],
) -> list[int]:
    if not stats_rows:
        return []

    song_dict = calc_song if isinstance(calc_song, dict) else dict(calc_song)
    song_data = song_dict.get("song_data", {}) or {}
    timestamps = song_data.get("chart_timestamps")
    if timestamps is None:
        timestamps = song_data.get("timestamps", ())
    total_notes = int(len(timestamps))
    if total_notes <= 0:
        return [0 for _stats in stats_rows]

    frontier_refs = _frontier_replay_refs(ref_arrays)
    ir = build_exact_score_ir(song_dict, frontier_refs)
    song_meta = extract_song_meta(song_dict)
    n = len(stats_rows)
    primary_val = np.zeros(n, dtype=np.int64)
    secondary_val = np.zeros(n, dtype=np.int64)
    pp_stat = np.zeros(n, dtype=np.int64)
    cm_stat = np.zeros(n, dtype=np.int64)
    fm_stat = np.zeros(n, dtype=np.int64)
    ft_stat = np.zeros(n, dtype=np.int64)
    ff_stat = np.zeros(n, dtype=np.int64)
    for i, stats in enumerate(stats_rows):
        primary_val[i] = safe_int(stats.get(song_meta.primary_color, 0), 0)
        secondary_val[i] = safe_int(stats.get(song_meta.secondary_color, 0), 0)
        pp_stat[i] = safe_int(stats.get("Perfect Points", 0), 0)
        cm_stat[i] = safe_int(stats.get("Combo Multiplier", 0), 0)
        fm_stat[i] = safe_int(stats.get("Fever Multiplier", 0), 0)
        ft_stat[i] = safe_int(stats.get("Fever Time", 0), 0)
        ff_stat[i] = safe_int(stats.get("Fever Fill Rate", 0), 0)

    return score_from_ir(
        ir,
        primary_val,
        secondary_val,
        pp_stat,
        cm_stat,
        fm_stat,
        ft_stat,
        ff_stat,
    ).tolist()


def score_stat_arrays_exact_batch(
    primary_val: np.ndarray,
    secondary_val: np.ndarray,
    pp_stat: np.ndarray,
    cm_stat: np.ndarray,
    fm_stat: np.ndarray,
    ft_stat: np.ndarray,
    ff_stat: np.ndarray,
    calc_song: Mapping[str, Any],
    ref_arrays: Mapping[str, Any],
) -> np.ndarray:
    """Array-native exact base scores (int64), bit-identical to the per-row
    frontier replay. Thin adapter over the shared IR: ``build_exact_score_ir``
    once, then ``score_from_ir``. This is the canonical GPU entry the handoff
    names -- the reverse engine's soundness gate also calls this."""
    ir = build_exact_score_ir(calc_song, ref_arrays)
    return score_from_ir(ir, primary_val, secondary_val, pp_stat, cm_stat, fm_stat, ft_stat, ff_stat)


def _ir_payload_view(ir: ExactScoreIR) -> Any:
    """Reconstruct a TimelineFrontierGridPayload view from the IR's stored arrays.

    The IR owns the per-slot slices the scorer needs; the trace reconstruction
    helper still expects a payload object, so we hand it a frozen-shaped view
    that exposes the same attributes it indexes into.
    """
    from ..timeline_exact_frontier import TimelineFrontierGridPayload

    return TimelineFrontierGridPayload(
        grid_count_body_fever=np.zeros((1, 0), dtype=np.int32),
        grid_count_body_normal=np.zeros((1, 0), dtype=np.int32),
        grid_head_len=ir.frontier_head_len[None, :, :],
        grid_fever_masks_bits=np.zeros((1, 0, 4), dtype=np.uint32),
        grid_frontier_count=ir.frontier_grid_count[None, :, :],
        grid_frontier_offset=ir.frontier_grid_offset[None, :, :],
        grid_frontier_body_fever_pool=ir.frontier_body_fever_pool[None, :],
        grid_frontier_body_normal_pool=ir.frontier_body_normal_pool[None, :],
        grid_frontier_masks_bits_pool=ir.frontier_masks_bits_pool[None, :, :],
        grid_frontier_head_coeffs_pool=ir.frontier_head_coeffs_pool[None, :, :],
        grid_gap=np.zeros((1, 0), dtype=np.int32),
        grid_fever_activations=ir.frontier_fever_activations[None, :, :],
        frontier_pool_used=int(ir.frontier_pool_used),
    )


def score_stats_fixed_timing_exact(
    stats: Mapping[str, Any],
    calc_song: Mapping[str, Any],
    ref_arrays: Mapping[str, Any],
) -> int:
    """Exact f64 base replay under fixed 0ms timing (see ``*_batch``)."""
    return int(score_stats_fixed_timing_exact_batch([stats], calc_song, ref_arrays)[0])


def score_stats_fixed_timing_exact_batch(
    stats_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
    calc_song: Mapping[str, Any],
    ref_arrays: Mapping[str, Any],
) -> list[int]:
    """
    Exact f64 base replay for the PREPARED fixed/explicit-timing calc_song.

    Scores the played hit timeline materialized as ``song_data["fg_timestamps"]`` by
    ``apply_timing_envelope(mode="zero_ms", baseline_offset=T)`` (= ``chart + T``). The ``zero_ms``
    / ``T == 0`` preset leaves it == chart, so this is the deterministic chart-time fever timeline
    -- NOT the Perfect-window frontier used by ``score_stats_exact_batch``, and independent of any
    frontier payload. A raw (un-prepared) calc_song falls back to the chart.

    Thin adapter over ``score_stats_timing_exact_batch`` (the canonical explicit-timeline scorer).
    """
    if not stats_rows:
        return []
    song_dict = calc_song if isinstance(calc_song, dict) else dict(calc_song)
    song_data = song_dict.get("song_data", {}) or {}
    hit_timestamps = song_data.get("fg_timestamps")
    if hit_timestamps is None:
        hit_timestamps = song_data.get("chart_timestamps", song_data.get("timestamps", ()))
    return score_stats_timing_exact_batch(stats_rows, song_dict, ref_arrays, hit_timestamps)


def score_stats_timing_exact_batch(
    stats_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
    calc_song: Mapping[str, Any],
    ref_arrays: Mapping[str, Any],
    hit_timestamps: Any,
) -> list[int]:
    """
    Exact f64 base replay under an EXPLICIT per-note hit-time timeline.

    Generalizes the fixed-0ms (``zero_ms``) base replay: the deterministic fever timeline is
    computed from the supplied ``hit_timestamps`` (chart time + a per-note offset ``T``), not
    from chart. ``hit_timestamps == chart_timestamps`` reproduces
    ``score_stats_fixed_timing_exact_batch`` bit-for-bit -- ``zero_ms`` is the ``T == 0`` preset.

    Only the fever-window BOUNDARIES depend on the per-note offset; the fill count is
    offset-independent (see ``fg_response_scoring/fixed_timing.py``) and base scoring carries no
    greats. Song-intrinsic quantities (``total_notes``, ``Long Notes``, ``Last Note Time``) come
    from the chart, not from ``hit_timestamps`` -- ``T`` shifts the played timeline, not the song.

    ``hit_timestamps`` MUST be non-decreasing: ``calculate_fever_timeline_indices`` searches it,
    so a timing vector that reorders notes is an invalid external input and fails loud.
    """
    if not stats_rows:
        return []

    ref_arrays = resolve_exact_replay_ref_arrays(ref_arrays)
    song_dict = calc_song if isinstance(calc_song, dict) else dict(calc_song)
    song_data = song_dict.get("song_data", {}) or {}
    chart = song_data.get("chart_timestamps")
    if chart is None:
        chart = song_data.get("timestamps", song_data.get("fg_timestamps", ()))
    chart = np.asarray(chart, dtype=np.float32)
    total_notes = int(chart.shape[0])
    if total_notes <= 0:
        return [0 for _stats in stats_rows]

    hits = np.asarray(hit_timestamps, dtype=np.float32)
    if int(hits.shape[0]) != total_notes:
        raise ValueError(
            "score_stats_timing_exact_batch: hit_timestamps length "
            f"{int(hits.shape[0])} != song note count {total_notes}"
        )
    if total_notes > 1 and bool(np.any(np.diff(hits) < np.float32(0.0))):
        raise ValueError(
            "score_stats_timing_exact_batch: hit_timestamps must be non-decreasing "
            "(a per-note timing offset may not reorder notes)"
        )

    metadata = song_dict.get("metadata", {}) or {}
    long_notes = safe_int(metadata.get("Long Notes"), 0)
    default_last_note = float(chart[-1]) if total_notes else 0.0
    last_note_time = safe_float(metadata.get("Last Note Time"), default_last_note)

    ft_axis = ref_arrays["Fever Time"]
    ff_axis = ref_arrays["Fever Fill Rate"]
    mask_buffer = np.zeros(total_notes, dtype=np.bool_)
    song_meta = extract_song_meta(song_dict)
    # (FT, FF) -> deterministic fever timeline: a pure function of the cell within one
    # batch (hits/notes/long/last are batch-constant). The njit walk returns a VIEW of
    # the shared mask buffer, so the memo stores a copy.
    timeline_by_cell: dict[tuple[int, int], tuple[np.ndarray, int, int]] = {}

    scores: list[int] = []
    for stats in stats_rows:
        (
            primary_val,
            secondary_val,
            pp_factor,
            combo_mul,
            fever_mul,
            ft_idx,
            ff_idx,
        ) = _score_stat_inputs(stats, ref_arrays, song_meta.primary_color, song_meta.secondary_color)
        base_value = float((int(primary_val) * 2) + int(secondary_val)) + float(pp_factor)
        cell = (int(ft_idx), int(ff_idx))
        cached_timeline = timeline_by_cell.get(cell)
        if cached_timeline is None:
            ft_factor = lookup_reference_py(int(ft_idx), ft_axis, TOTAL_ROWS)
            ff_factor = lookup_reference_py(int(ff_idx), ff_axis, TOTAL_ROWS)
            fever_mask_head, count_body_fever, count_body_normal, _activations, _last_end = (
                calculate_fever_timeline_indices(
                    hits,
                    total_notes,
                    ff_factor,
                    ft_factor,
                    long_notes,
                    last_note_time,
                    mask_buffer,
                )
            )
            cached_timeline = (fever_mask_head.copy(), int(count_body_fever), int(count_body_normal))
            timeline_by_cell[cell] = cached_timeline
        fever_mask_head, count_body_fever, count_body_normal = cached_timeline
        scores.append(
            calculate_score_exact(
                base_value,
                float(combo_mul),
                float(fever_mul),
                fever_mask_head,
                int(count_body_fever),
                int(count_body_normal),
            )
        )
    return scores


def _frontier_replay_refs(ref_arrays: Mapping[str, Any]) -> dict[str, Any]:
    frontier_refs = dict(resolve_exact_replay_ref_arrays(ref_arrays))
    for axis in ("Fever Time", "Fever Fill Rate"):
        axis_values = np.asarray(frontier_refs.get(axis, ())).reshape(-1)
        if int(axis_values.shape[0]) < TOTAL_ROWS + 1:
            raise ValueError(f"{axis} axis must include stat rows 0..{TOTAL_ROWS}")
        frontier_refs[axis] = axis_values[: TOTAL_ROWS + 1]
    return frontier_refs


def _score_stat_inputs(
    stats: Mapping[str, Any],
    ref_arrays: Mapping[str, Any],
    primary: str,
    secondary: str,
) -> tuple[int, int, float, float, float, int, int]:
    """Per-row scoring inputs.

    ``ref_arrays`` must already be resolved and ``primary``/``secondary`` extracted once
    per song -- both are row-invariant, so callers hoist them out of their row loops.
    """
    pp_factor = lookup_reference_py(safe_int(stats.get("Perfect Points", 0), 0), ref_arrays["Perfect Points"], TOTAL_ROWS)
    combo_mul = lookup_reference_py(
        safe_int(stats.get("Combo Multiplier", 0), 0),
        ref_arrays["Combo Multiplier"],
        TOTAL_ROWS,
    )
    fever_mul = lookup_reference_py(
        safe_int(stats.get("Fever Multiplier", 0), 0),
        ref_arrays["Fever Multiplier"],
        TOTAL_ROWS,
    )
    primary_val = safe_int(stats.get(primary, 0), 0)
    secondary_val = safe_int(stats.get(secondary, 0), 0)

    return (
        int(primary_val),
        int(secondary_val),
        float(pp_factor),
        float(combo_mul),
        float(fever_mul),
        safe_int(stats.get("Fever Time", 0), 0),
        safe_int(stats.get("Fever Fill Rate", 0), 0),
    )


def _score_surface_counts_exact(
    *,
    total_notes: int,
    primary_val: int,
    secondary_val: int,
    pp_factor: float,
    combo_mul: float,
    fever_mul: float,
    body_fever: int,
    body_normal: int,
    fever_words,
) -> int:
    head_len = min(max(0, int(total_notes)), 100)
    body_total = max(0, int(total_notes) - 100)
    body_fever = safe_int(body_fever, 0)
    body_normal = safe_int(body_normal, 0)
    if body_fever < 0 or body_normal < 0 or int(body_fever + body_normal) != int(body_total):
        raise ValueError("Timing surface body counts do not match song body note count")

    words = tuple(safe_int(value, 0) for value in tuple(fever_words)[:4])
    if len(words) < 4:
        words = words + (0,) * (4 - len(words))

    base_value = float((int(primary_val) * 2) + int(secondary_val)) + float(pp_factor)
    combo_f = float(combo_mul)
    fever_f = float(fever_mul)
    combo_val = floor(base_value * combo_f)
    fever_val = floor(base_value * combo_f * fever_f)
    score = (int(body_fever) * int(fever_val)) + (int(body_normal) * int(combo_val))

    combo_slope = (combo_f - 1.0) / 100.0
    for i in range(head_len):
        word_idx = i // 32
        bit_idx = i % 32
        scaling = (combo_slope * float(i + 1)) + 1.0
        perfect_value = base_value * scaling
        is_fever = ((int(words[word_idx]) >> int(bit_idx)) & 1) != 0
        score += floor(perfect_value * fever_f) if is_fever else floor(perfect_value)
    return int(score)


def _score_timeline_frontier_payload_vectorized(
    *,
    payload: Any,
    total_notes: int,
    primary_val: int,
    secondary_val: int,
    pp_factor: float,
    combo_mul: float,
    fever_mul: float,
    ft_idx: int,
    ff_idx: int,
) -> int:
    score, _pool_idx = _score_timeline_frontier_payload_vectorized_result(
        payload=payload,
        total_notes=int(total_notes),
        primary_val=int(primary_val),
        secondary_val=int(secondary_val),
        pp_factor=float(pp_factor),
        combo_mul=float(combo_mul),
        fever_mul=float(fever_mul),
        ft_idx=int(ft_idx),
        ff_idx=int(ff_idx),
    )
    return int(score)


def _score_timeline_frontier_payload_vectorized_result(
    *,
    payload: Any,
    total_notes: int,
    primary_val: int,
    secondary_val: int,
    pp_factor: float,
    combo_mul: float,
    fever_mul: float,
    ft_idx: int,
    ff_idx: int,
) -> tuple[int, int]:
    """Scalar-per-row twin of ``score_from_ir_with_pool_idx`` that takes a raw payload.

    Delegates the per-cell replay to ``_replay_cell`` via a minimal IR view, so
    the scalar trace path and the array-native forward path share one exact
    replay implementation. Preserves the body_fever + body_normal == body_total
    invariant check (now lives inside ``_replay_cell``).
    """
    ir = _ir_from_payload(payload, int(total_notes))
    return score_from_ir_with_pool_idx(
        ir,
        primary_val=int(primary_val),
        secondary_val=int(secondary_val),
        pp_factor=float(pp_factor),
        combo_mul=float(combo_mul),
        fever_mul=float(fever_mul),
        ft_idx=int(ft_idx),
        ff_idx=int(ff_idx),
    )


def _ir_from_payload(payload: Any, total_notes: int) -> ExactScoreIR:
    """Build a minimal IR view from a raw TimelineFrontierGridPayload.

    Only the fields ``_replay_cell`` indexes are populated; ref-table and
    plateau fields are empty because the scalar twin already supplies the
    resolved per-row factors. The body-count invariant check is preserved
    inside ``_replay_cell`` via the body_fever/body_normal pool slices.
    """
    head_len = min(max(0, int(total_notes)), 100)
    body_total = max(0, int(total_notes) - 100)
    grid_count = np.asarray(payload.grid_frontier_count[0], dtype=np.int32)
    grid_offset = np.asarray(payload.grid_frontier_offset[0], dtype=np.int32)
    body_fever_pool = np.asarray(payload.grid_frontier_body_fever_pool[0], dtype=np.int64)
    body_normal_pool = np.asarray(payload.grid_frontier_body_normal_pool[0], dtype=np.int64)
    masks_bits_pool = np.asarray(payload.grid_frontier_masks_bits_pool[0], dtype=np.uint64)
    head_coeffs_pool = np.asarray(payload.grid_frontier_head_coeffs_pool[0], dtype=np.int16)
    head_len_grid = np.asarray(payload.grid_head_len[0], dtype=np.int8)
    fever_activations = np.asarray(payload.grid_fever_activations[0], dtype=np.int32)
    pool_used = int(payload.frontier_pool_used)
    if pool_used > 0:
        body_fever_min = int(body_fever_pool[:pool_used].min())
        body_fever_max = int(body_fever_pool[:pool_used].max())
        body_normal_min = int(body_normal_pool[:pool_used].min())
        body_normal_max = int(body_normal_pool[:pool_used].max())
    else:
        body_fever_min = body_fever_max = 0
        body_normal_min = body_normal_max = 0
    return ExactScoreIR(
        total_notes=int(total_notes),
        head_len=int(head_len),
        body_total=int(body_total),
        primary_color="",
        secondary_color="",
        color_projection="2*primary + secondary",
        timing_mode="perfect_window",
        fever_fill_base_rate=float(FEVER_FILL_BASE_RATE),
        fever_time_scale=float(FEVER_TIME_SCALE),
        fever_time_offset=float(FEVER_TIME_OFFSET),
        long_notes=0,
        last_note_time=0.0,
        pp_table=np.zeros(0, dtype=np.float64),
        cm_table=np.zeros(0, dtype=np.float64),
        fm_table=np.zeros(0, dtype=np.float64),
        ft_axis=np.zeros(0, dtype=np.float32),
        ff_axis=np.zeros(0, dtype=np.float32),
        stat_index_clamp_lo=0,
        stat_index_clamp_hi=int(TOTAL_ROWS),
        stat_value_clamp_lo=-80,
        stat_value_clamp_hi=160,
        fever_fill_floor=1,
        base_notes_first_section_offset=-1,
        pp_plateau_values=np.zeros(0, dtype=np.float64),
        pp_plateau_inverse=np.zeros(0, dtype=np.int64),
        cm_plateau_values=np.zeros(0, dtype=np.float64),
        cm_plateau_inverse=np.zeros(0, dtype=np.int64),
        fm_plateau_values=np.zeros(0, dtype=np.float64),
        fm_plateau_inverse=np.zeros(0, dtype=np.int64),
        base_int_formula="2*primary + secondary",
        base_int_range=(0, 2 * 250 + 250),
        two_color_collapse_v="v = 2*c1 + c2",
        frontier_grid_count=grid_count,
        frontier_grid_offset=grid_offset,
        frontier_pool_used=int(pool_used),
        frontier_body_fever_pool=body_fever_pool,
        frontier_body_normal_pool=body_normal_pool,
        frontier_masks_bits_pool=masks_bits_pool,
        frontier_head_coeffs_pool=head_coeffs_pool,
        frontier_head_len=head_len_grid,
        frontier_body_fever_min_max=(int(body_fever_min), int(body_fever_max)),
        frontier_body_normal_min_max=(int(body_normal_min), int(body_normal_max)),
        frontier_fever_activations=fever_activations,
        combo_val_formula="floor(base_value * combo_f)",
        fever_val_formula="floor(base_value * combo_f * fever_f)",
        body_score_formula="body_fever * fever_val + body_normal * combo_val",
        head_combo_slope_formula="(combo_f - 1.0) / 100.0",
        head_perfect_value_formula="base_value * ((combo_slope * (i + 1)) + 1.0)",
        head_normal_score_formula="floor(perfect_value)",
        head_fever_score_formula="floor(perfect_value * fever_f)",
        head_fever_delta_formula="head_fever_score - head_normal_score",
        head_score_formula="sum over i in [0, head_len) of (is_fever ? head_fever_score : head_normal_score)",
        total_score_formula="max over pool lanes of (body_score + head_score)",
        f64_envelope_guard=int(2**52),
        residue_pp_factor="lookup_reference_py(pp_stat, pp_table, TOTAL_ROWS)",
        residue_combo_val="floor(base_value * combo_f)",
        residue_fever_val="floor(base_value * combo_f * fever_f)",
        residue_head_normal_i="floor(base_value * ((combo_slope * (i + 1)) + 1.0))",
        residue_head_fever_i="floor(base_value * ((combo_slope * (i + 1)) + 1.0) * fever_f)",
        residue_great_penalty_base="compute_great_penalty_base(primary_val, secondary_val)",
        gear_power_formula="(2 * primary_val + secondary_val) + pp_factor",
        accuracy_formula="score / max(1, total_score_formula)",
        cache_key=((), (), "perfect_window", int(_IR_SCHEMA_VERSION)),
    )


def _timeline_trace_for_payload_surface(
    *,
    payload: Any,
    pool_idx: int,
    total_notes: int,
    ft_idx: int,
    ff_idx: int,
    calc_song: dict[str, Any],
    ref_arrays: Mapping[str, Any],
) -> dict[str, Any]:
    from ..fg_response_scoring.physical_replay import validate_base_physical_replay
    from ..timeline_exact_frontier import reconstruct_timeline_physical_trace

    pool_idx_i = int(pool_idx)
    if pool_idx_i < 0 or pool_idx_i >= int(payload.frontier_pool_used):
        raise ValueError("Timeline frontier winner points outside the cached surface pool")

    body_fever = int(payload.grid_frontier_body_fever_pool[0, pool_idx_i])
    body_normal = int(payload.grid_frontier_body_normal_pool[0, pool_idx_i])
    words = tuple(int(payload.grid_frontier_masks_bits_pool[0, pool_idx_i, word]) for word in range(4))
    song_inputs = extract_fg_song_inputs(calc_song)
    ref_ft = np.asarray(ref_arrays["Fever Time"], dtype=np.float32).reshape(-1)
    ref_ff = np.asarray(ref_arrays["Fever Fill Rate"], dtype=np.float32).reshape(-1)
    ft_i = max(0, min(int(ft_idx), TOTAL_ROWS))
    ff_i = max(0, min(int(ff_idx), TOTAL_ROWS))

    total_notes_i = int(song_inputs.total_notes)
    long_notes_i = int(song_inputs.long_notes)
    non_fever_cas = float(max(0, total_notes_i - long_notes_i)) * float(FEVER_FILL_BASE_RATE)
    fever_time_cas = float(song_inputs.last_note_time) * FEVER_TIME_SCALE + FEVER_TIME_OFFSET
    raw_fever_fill = float(non_fever_cas) * float(ref_ff[ff_i])
    fill_count = int(np.ceil(raw_fever_fill))
    fill_count = max(1, int(fill_count))
    real_fever_time = max(0.0, float(fever_time_cas) * float(ref_ft[ft_i]))

    trace = reconstruct_timeline_physical_trace(
        head_bits=(int(words[0]), int(words[1]), int(words[2]), int(words[3])),
        body_fever=int(body_fever),
        timestamps=song_inputs.timestamps,
        perfect_candidate_timestamps=song_inputs.perfect_candidates,
        great_candidate_timestamps=song_inputs.great_candidates,
        perfect_floor_timestamps=song_inputs.perfect_floor,
        great_floor_timestamps=song_inputs.great_floor,
        lanes=song_inputs.lanes,
        raw_fever_fill=float(raw_fever_fill),
        real_fever_time=float(real_fever_time),
    )
    song_data = calc_song.get("song_data")
    if not isinstance(song_data, Mapping):
        raise ValueError("Timeline frontier trace requires complete chart geometry")
    response_surface = [
        int(words[0]),
        int(words[1]),
        int(words[2]),
        int(words[3]),
        int(body_fever),
        int(body_normal),
    ]
    validate_base_physical_replay(
        frontier_trace=trace,
        response_surface=response_surface,
        timestamps=song_data.get("timestamps", ()),
        note_types=song_data.get("note_types", ()),
        lanes=song_data.get("lanes", ()),
        fill_count=int(fill_count),
        fever_duration_ms=float(real_fever_time) * 1000.0,
    )
    return {
        "frontier_trace": [dict(section) for section in trace],
        "response_surface": response_surface,
        "frontier_pool_index": int(pool_idx_i),
        "frontier_first_surfaces": int(payload.grid_frontier_count[0, ft_i, ff_i]),
        "activation_judgment": "perfect",
        "fill_count": int(fill_count),
        "fever_duration_ms": float(real_fever_time) * 1000.0,
    }


def score_response_surface_base_exact(
    surface: Any,
    *,
    total_notes: int,
    primary_val: int,
    secondary_val: int,
    pp_factor: float,
    combo_mul: float,
    fever_mul: float,
) -> int:
    body_total = max(0, int(total_notes) - 100)
    body_fever = safe_int(getattr(surface, "body_fever", 0), 0)
    if body_fever < 0 or body_fever > body_total:
        raise ValueError("FG response surface body fever count exceeds song body note count")

    return _score_surface_counts_exact(
        total_notes=int(total_notes),
        primary_val=int(primary_val),
        secondary_val=int(secondary_val),
        pp_factor=float(pp_factor),
        combo_mul=float(combo_mul),
        fever_mul=float(fever_mul),
        body_fever=int(body_fever),
        body_normal=int(body_total - body_fever),
        fever_words=(
            safe_int(getattr(surface, "fever0", 0), 0),
            safe_int(getattr(surface, "fever1", 0), 0),
            safe_int(getattr(surface, "fever2", 0), 0),
            safe_int(getattr(surface, "fever3", 0), 0),
        ),
    )


def score_force_greats_surface_base_exact(
    stats: Mapping[str, Any],
    calc_song: Mapping[str, Any],
    ref_arrays: Mapping[str, Any],
    surface: Any,
) -> int | None:
    """
    Exact base-score replay for a solved FG response surface.

    The response surface already owns the exact fever timeline, so this path scores
    that canonical surface directly instead of rebuilding the same timeline from
    forced counts.
    """
    if not stats or not calc_song:
        return None
    ref_arrays = resolve_exact_replay_ref_arrays(ref_arrays)
    song_inputs = extract_fg_song_inputs(calc_song)
    if song_inputs.total_notes <= 0:
        return None

    primary_val = safe_int(stats.get(song_inputs.primary_color, 0), 0)
    secondary_val = safe_int(stats.get(song_inputs.secondary_color, 0), 0)
    factors = resolve_stat_factors(stats, ref_arrays)
    return int(
        score_response_surface_base_exact(
            surface,
            total_notes=int(song_inputs.total_notes),
            primary_val=int(primary_val),
            secondary_val=int(secondary_val),
            pp_factor=float(factors.pp_factor),
            combo_mul=float(factors.combo_mul),
            fever_mul=float(factors.fever_mul),
        )
    )


def score_force_greats_response_surface_exact(
    stats: Mapping[str, Any],
    calc_song: Mapping[str, Any],
    ref_arrays: Mapping[str, Any],
    surface: Any,
) -> int | None:
    """
    Exact f64 replay for a solved FG response surface.

    The response surface is the canonical representation for timeline-frontier
    FG because it can encode Fever+Great overlap; forced-count configs cannot.
    """
    if not stats or not calc_song:
        return None
    ref_arrays = resolve_exact_replay_ref_arrays(ref_arrays)
    song_inputs = extract_fg_song_inputs(calc_song)
    total_notes = int(song_inputs.total_notes)
    if total_notes <= 0:
        return None

    head_len = min(total_notes, 100)
    body_total = max(0, total_notes - 100)
    body_fever = safe_int(getattr(surface, "body_fever", 0), 0)
    body_great = safe_int(getattr(surface, "body_great", 0), 0)
    body_fever_great = safe_int(getattr(surface, "body_fever_great", 0), 0)
    if (
        body_fever < 0
        or body_great < 0
        or body_fever_great < 0
        or body_fever > body_total
        or body_great > body_total
        or body_fever_great > body_fever
        or body_fever_great > body_great
        or body_fever + body_great - body_fever_great > body_total
    ):
        raise ValueError("FG response surface body categories do not match song body note count")

    primary_val = safe_int(stats.get(song_inputs.primary_color, 0), 0)
    secondary_val = safe_int(stats.get(song_inputs.secondary_color, 0), 0)
    factors = resolve_stat_factors(stats, ref_arrays)
    base_value = float((primary_val * 2) + secondary_val) + float(factors.pp_factor)
    combo_f = float(factors.combo_mul)
    fever_f = float(factors.fever_mul)
    combo_val = floor(base_value * combo_f)
    fever_val = floor(base_value * combo_f * fever_f)

    great_head_base = compute_great_penalty_base(primary_val, secondary_val)

    body_normal_great = int(body_great - body_fever_great)
    body_normal = int(body_total - body_fever)
    if body_normal - body_normal_great < 0:
        raise ValueError("FG response surface body normal category is negative")

    score = 0
    score += int(body_fever) * int(fever_val)
    score += int(body_normal) * int(combo_val)
    great_base = float(great_head_base)
    body_normal_penalty = max(0, int(combo_val) - int(floor(great_base * combo_f)))
    body_fever_penalty = max(0, int(fever_val) - int(floor(great_base * combo_f * fever_f)))
    score -= int(body_normal_great) * int(body_normal_penalty)
    score -= int(body_fever_great) * int(body_fever_penalty)

    fever_words = (
        safe_int(getattr(surface, "fever0", 0), 0),
        safe_int(getattr(surface, "fever1", 0), 0),
        safe_int(getattr(surface, "fever2", 0), 0),
        safe_int(getattr(surface, "fever3", 0), 0),
    )
    great_words = (
        safe_int(getattr(surface, "great0", 0), 0),
        safe_int(getattr(surface, "great1", 0), 0),
        safe_int(getattr(surface, "great2", 0), 0),
        safe_int(getattr(surface, "great3", 0), 0),
    )
    combo_slope = (combo_f - 1.0) / 100.0
    for i in range(head_len):
        word_idx = i // 32
        bit_idx = i % 32
        is_fever = ((int(fever_words[word_idx]) >> int(bit_idx)) & 1) != 0
        is_great = ((int(great_words[word_idx]) >> int(bit_idx)) & 1) != 0
        scaling = (combo_slope * float(i + 1)) + 1.0
        perfect_value = base_value * scaling
        perfect_score = floor(perfect_value * fever_f) if is_fever else floor(perfect_value)
        if is_great:
            great_score = float(great_head_base) * scaling
            great_score = floor(great_score * fever_f) if is_fever else floor(great_score)
            perfect_score -= max(0, int(perfect_score) - int(great_score))
        score += int(perfect_score)
    return int(score)


def evaluate_force_greats_exact(
    stats: Mapping[str, Any],
    calc_song: Mapping[str, Any],
    ref_arrays: Mapping[str, Any],
    forced_counts=None,
) -> dict[str, Any] | None:
    """
    CPU exact replay for a persisted ForceGreats config.

    This preserves the existing ForceGreats timeline and penalty placement rules,
    but computes the visible score with double precision.
    """
    if not stats or not calc_song:
        return None
    ref_arrays = resolve_exact_replay_ref_arrays(ref_arrays)

    song_inputs = extract_fg_song_inputs(calc_song)
    if song_inputs.total_notes <= 0:
        return None

    primary_val = safe_int(stats.get(song_inputs.primary_color, 0), 0)
    secondary_val = safe_int(stats.get(song_inputs.secondary_color, 0), 0)
    factors = resolve_stat_factors(stats, ref_arrays)
    base_value = float((primary_val * 2) + secondary_val) + float(factors.pp_factor)
    penalty_table, body_penalty, combo_value = build_penalty_table_and_body(
        base_value=float(base_value),
        combo_mul=float(factors.combo_mul),
        primary_val=int(primary_val),
        secondary_val=int(secondary_val),
    )

    force_counts = list(forced_counts or [])
    (
        fever_mask_head,
        count_body_fever,
        count_body_normal,
        non_fever_base,
        section_details,
    ) = _compute_force_greats_timeline(
        song_inputs.timestamps,
        song_inputs.perfect_candidates,
        song_inputs.great_candidates,
        song_inputs.perfect_floor,
        song_inputs.total_notes,
        factors.fever_fill_rate,
        factors.fever_time_stat,
        song_inputs.long_notes,
        song_inputs.last_note_time,
        force_counts,
        clamp_base_notes_nonnegative=True,
        clamp_forced_to_section_notes=True,
        use_forced_great_timing=song_inputs.use_forced_great_timing,
    )

    base_score = calculate_score_exact(
        base_value,
        float(factors.combo_mul),
        float(factors.fever_mul),
        fever_mask_head,
        int(count_body_fever),
        int(count_body_normal),
    )

    total_score_penalty, total_fill_penalty, penalty_analysis = accumulate_fg_penalties(
        section_details=section_details,
        penalty_table=penalty_table,
        body_penalty=body_penalty,
        combo_value=combo_value,
    )
    return build_fg_result_dict(
        base_score=int(base_score),
        total_score_penalty=int(total_score_penalty),
        total_fill_penalty=int(total_fill_penalty),
        section_details=section_details,
        config_counts=force_counts,
        penalty_analysis=penalty_analysis,
        non_fever_base=int(non_fever_base),
    )
