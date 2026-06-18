from __future__ import annotations

import logging
import time
from dataclasses import dataclass, replace
from typing import Any

import numpy as np

from gear_optimizer.core.constants import (
    ELEMENTAL_GEM_SCALE,
    GEM_SCALE_FEVER,
    GEM_STAT_TO_ELEMENT_SCALE,
    MAX_STAT_INDEX,
    TOTAL_GEM_BUDGET,
)
from gear_optimizer.core.jit_setup import HAS_NUMBA, jit
from gear_optimizer.solver.fever_timeline import get_song_timeline_grid

logger = logging.getLogger(__name__)

_GRID = int(MAX_STAT_INDEX) + 1
_STAT_GRID_SIZE = _GRID * _GRID * _GRID
_NO_OWNER = np.int32(-1)
_KEY_LANE_STRIDE = 65536
_MAX_COVER_MATRIX_BYTES = 256 * 1024 * 1024
_TIMELINE_PACK_GRID_CACHE_MAX = 8
_TIMELINE_PACK_GRID_CACHE: dict[
    tuple[Any, int],
    tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray],
] = {}


@dataclass(frozen=True)
class ResponseEnvelopePruneStats:
    enabled: bool
    reason: str
    candidates_in: int
    candidates_out: int
    pruned: int
    seconds_total: float
    seconds_states: float = 0.0
    seconds_timing: float = 0.0
    seconds_index: float = 0.0
    seconds_query: float = 0.0
    present_timing_cells: int = 0
    timing_packs: int = 0
    non_timing_owner_hits: int = 0
    timing_cover_hits: int = 0


def response_envelope_phase_counts(stats: ResponseEnvelopePruneStats) -> dict[str, int]:
    return {
        "response_envelope_enabled": 1 if stats.enabled else 0,
        "response_envelope_candidates_in": int(stats.candidates_in),
        "response_envelope_candidates_out": int(stats.candidates_out),
        "response_envelope_pruned": int(stats.pruned),
        "response_envelope_present_timing_cells": int(stats.present_timing_cells),
        "response_envelope_timing_packs": int(stats.timing_packs),
        "response_envelope_non_timing_owner_hits": int(stats.non_timing_owner_hits),
        "response_envelope_timing_cover_hits": int(stats.timing_cover_hits),
    }


def response_envelope_phase_seconds(stats: ResponseEnvelopePruneStats) -> dict[str, float]:
    return {
        "response_envelope_prune_cpu": float(stats.seconds_total),
        "response_envelope.states": float(stats.seconds_states),
        "response_envelope.timing": float(stats.seconds_timing),
        "response_envelope.index": float(stats.seconds_index),
        "response_envelope.query": float(stats.seconds_query),
    }


def prune_response_envelope_pairs(
    *,
    pair_gear_idx: np.ndarray,
    pair_mini_idx: np.ndarray,
    gear_ids: np.ndarray,
    mini_ids: np.ndarray,
    gpu_arrays: dict[str, np.ndarray],
    base_fixed_stats_arr: np.ndarray,
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    flags: dict[str, int],
    gear_points: np.ndarray | None = None,
    mini_points: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, ResponseEnvelopePruneStats]:
    started = time.perf_counter()
    n = int(np.asarray(pair_gear_idx).shape[0])
    if n <= 1:
        return pair_gear_idx, pair_mini_idx, _stats(False, "too_few_candidates", n, n, started)

    reason = _fast_path_blocker(flags=flags, ref_arrays=ref_arrays)
    if reason:
        return pair_gear_idx, pair_mini_idx, _stats(False, reason, n, n, started)

    state_started = time.perf_counter()
    item_stats = np.asarray(gpu_arrays["item_stats"], dtype=np.int32)
    if (
        gear_points is not None
        and mini_points is not None
        and _mini_points_have_no_pp(mini_ids=mini_ids, item_stats=item_stats)
    ):
        states = _candidate_state_arrays_from_points(
            pair_gear_idx=pair_gear_idx,
            pair_mini_idx=pair_mini_idx,
            gear_points=gear_points,
            mini_points=mini_points,
            base_fixed_stats_arr=base_fixed_stats_arr,
            flags=flags,
        )
    else:
        states = _candidate_state_arrays(
            pair_gear_idx=pair_gear_idx,
            pair_mini_idx=pair_mini_idx,
            gear_ids=gear_ids,
            mini_ids=mini_ids,
            item_stats=item_stats,
            base_fixed_stats_arr=base_fixed_stats_arr,
            flags=flags,
        )
    seconds_states = time.perf_counter() - state_started
    if states.has_negative_timing_or_stat:
        return pair_gear_idx, pair_mini_idx, ResponseEnvelopePruneStats(
            enabled=False,
            reason="negative_pre_gem_stat",
            candidates_in=n,
            candidates_out=n,
            pruned=0,
            seconds_total=float(time.perf_counter() - started),
            seconds_states=float(seconds_states),
        )

    timing_started = time.perf_counter()
    timing = _build_timing_response_index(
        present_cells=np.unique(states.cell.astype(np.int32, copy=False)),
        calc_song=calc_song,
        ref_arrays=ref_arrays,
    )
    seconds_timing = time.perf_counter() - timing_started

    prune_mask = np.zeros(n, dtype=np.bool_)
    seconds_index = 0.0
    seconds_query = 0.0
    owner_hit_count = 0
    cover_hits = 0

    pp_idx = states.pp.astype(np.intp, copy=False)
    cm_idx = states.cm.astype(np.intp, copy=False)
    fm_idx = states.fm.astype(np.intp, copy=False)
    strategy_queries: list[tuple[np.ndarray, np.ndarray, np.ndarray]] = []
    source_rows_needed: list[np.ndarray] = []
    target_rows_needed: list[np.ndarray] = []
    for _strategy_name, key in _owner_strategy_keys(states):
        index_started = time.perf_counter()
        owner_grid = _build_suffix_owner_index_for_key(states, key)
        seconds_index += time.perf_counter() - index_started

        query_started = time.perf_counter()
        owner = owner_grid[pp_idx, cm_idx, fm_idx]
        owner_hits = np.flatnonzero((owner >= 0) & (states.lane[owner] > states.lane))
        owner_hit_count += int(owner_hits.shape[0])
        if owner_hits.size > 0:
            source_rows = timing.cell_to_row[states.cell[owner[owner_hits]].astype(np.int32, copy=False)]
            target_rows = timing.cell_to_row[states.cell[owner_hits].astype(np.int32, copy=False)]
            strategy_queries.append((owner_hits, source_rows.astype(np.int32, copy=False), target_rows.astype(np.int32, copy=False)))
            source_rows_needed.append(source_rows.astype(np.int32, copy=False))
            target_rows_needed.append(target_rows.astype(np.int32, copy=False))
        seconds_query += time.perf_counter() - query_started

    if source_rows_needed:
        timing_started = time.perf_counter()
        timing = _with_best_source_rows(timing, np.unique(np.concatenate(source_rows_needed)))
        cover_matrix, cover_target_col = _build_source_target_cover_matrix(
            timing,
            target_rows=np.unique(np.concatenate(target_rows_needed)),
        )
        seconds_timing += time.perf_counter() - timing_started
        for owner_hits, source_rows, target_rows in strategy_queries:
            active = ~prune_mask[owner_hits]
            if not np.any(active):
                continue
            active_hits = owner_hits[active]
            query_started = time.perf_counter()
            if cover_matrix is not None:
                best_rows = timing.best_row_for_source_row[source_rows[active]]
                target_cols = cover_target_col[target_rows[active]]
                covered = cover_matrix[best_rows, target_cols]
            else:
                covered = _timing_covers_row_pairs(
                    source_rows=source_rows[active],
                    target_rows=target_rows[active],
                    timing=timing,
                )
            seconds_query += time.perf_counter() - query_started
            if covered.size > 0:
                prune_mask[active_hits] = covered
                cover_hits += int(np.count_nonzero(covered))

    if not np.any(prune_mask):
        elapsed = time.perf_counter() - started
        return (
            pair_gear_idx,
            pair_mini_idx,
            ResponseEnvelopePruneStats(
                enabled=True,
                reason="no_certified_dominance",
                candidates_in=n,
                candidates_out=n,
                pruned=0,
                seconds_total=float(elapsed),
                seconds_states=float(seconds_states),
                seconds_timing=float(seconds_timing),
                seconds_index=float(seconds_index),
                seconds_query=float(seconds_query),
                present_timing_cells=int(timing.cells.shape[0]),
                timing_packs=int(timing.pack_count),
                non_timing_owner_hits=int(owner_hit_count),
                timing_cover_hits=int(cover_hits),
            ),
        )

    keep = ~prune_mask
    out_g = np.asarray(pair_gear_idx)[keep]
    out_m = np.asarray(pair_mini_idx)[keep]
    elapsed = time.perf_counter() - started
    return (
        out_g,
        out_m,
        ResponseEnvelopePruneStats(
            enabled=True,
            reason="certified",
            candidates_in=n,
            candidates_out=int(out_g.shape[0]),
            pruned=int(np.count_nonzero(prune_mask)),
            seconds_total=float(elapsed),
            seconds_states=float(seconds_states),
            seconds_timing=float(seconds_timing),
            seconds_index=float(seconds_index),
            seconds_query=float(seconds_query),
            present_timing_cells=int(timing.cells.shape[0]),
            timing_packs=int(timing.pack_count),
            non_timing_owner_hits=int(owner_hit_count),
            timing_cover_hits=int(cover_hits),
        ),
    )


def _stats(
    enabled: bool,
    reason: str,
    candidates_in: int,
    candidates_out: int,
    started: float,
) -> ResponseEnvelopePruneStats:
    return ResponseEnvelopePruneStats(
        enabled=bool(enabled),
        reason=str(reason),
        candidates_in=int(candidates_in),
        candidates_out=int(candidates_out),
        pruned=int(candidates_in) - int(candidates_out),
        seconds_total=float(time.perf_counter() - float(started)),
    )


def _lane_weight(flags: dict[str, int], stat: str, scale: int) -> int:
    return int(scale) * ((2 * int(flags.get(f"is_p_{stat}", 0))) + int(flags.get(f"is_s_{stat}", 0)))


def _fast_path_blocker(*, flags: dict[str, int], ref_arrays: dict[str, Any]) -> str:
    if _lane_weight(flags, "ft", GEM_STAT_TO_ELEMENT_SCALE) != 0:
        return "timing_ft_affects_lane_base"
    if _lane_weight(flags, "ff", GEM_STAT_TO_ELEMENT_SCALE) != 0:
        return "timing_ff_affects_lane_base"

    overflow_weight = _lane_weight(flags, "ov", ELEMENTAL_GEM_SCALE)
    stat_weights = (
        _lane_weight(flags, "pp", GEM_STAT_TO_ELEMENT_SCALE),
        _lane_weight(flags, "cm", GEM_STAT_TO_ELEMENT_SCALE),
        _lane_weight(flags, "fm", GEM_STAT_TO_ELEMENT_SCALE),
    )
    if overflow_weight < max(stat_weights):
        return "overflow_lane_not_dominant"

    for key in ("Perfect Points", "Combo Multiplier", "Fever Multiplier"):
        arr = np.asarray(ref_arrays.get(key), dtype=np.float64).reshape(-1)
        if arr.shape[0] <= int(MAX_STAT_INDEX):
            return f"missing_ref_array_{key}"
        visible = arr[: int(MAX_STAT_INDEX) + 1]
        if np.any(np.diff(visible) < 0):
            logger.warning(
                "_fast_path_blocker: %s reference array is non-monotone over [0..MAX_STAT_INDEX] "
                "- response envelope fast-prune disabled. Data integrity issue.",
                key,
            )
            return f"nonmonotone_ref_array_{key}"
    fever = np.asarray(ref_arrays.get("Fever Multiplier"), dtype=np.float64).reshape(-1)
    if np.min(fever[: int(MAX_STAT_INDEX) + 1]) < 1.0:
        return "fever_multiplier_below_one"
    return ""


@dataclass(frozen=True)
class _CandidateStates:
    pp: np.ndarray
    cm: np.ndarray
    fm: np.ndarray
    cell: np.ndarray
    lane: np.ndarray
    has_negative_timing_or_stat: bool


def _candidate_state_arrays(
    *,
    pair_gear_idx: np.ndarray,
    pair_mini_idx: np.ndarray,
    gear_ids: np.ndarray,
    mini_ids: np.ndarray,
    item_stats: np.ndarray,
    base_fixed_stats_arr: np.ndarray,
    flags: dict[str, int],
) -> _CandidateStates:
    n = int(np.asarray(pair_gear_idx).shape[0])
    pp = np.empty(n, dtype=np.int16)
    cm = np.empty(n, dtype=np.int16)
    fm = np.empty(n, dtype=np.int16)
    cell = np.empty(n, dtype=np.int16)
    lane = np.empty(n, dtype=np.int16)

    base = np.asarray(base_fixed_stats_arr, dtype=np.int32).reshape(-1)
    base_pp = int(base[0]) if base.shape[0] > 0 else 0
    base_cm = int(base[1]) if base.shape[0] > 1 else 0
    base_fm = int(base[2]) if base.shape[0] > 2 else 0
    base_ft = int(base[3]) if base.shape[0] > 3 else 0
    base_ff = int(base[4]) if base.shape[0] > 4 else 0
    base_beat = int(base[5]) if base.shape[0] > 5 else 0
    base_vibe = int(base[6]) if base.shape[0] > 6 else 0
    base_rush = int(base[7]) if base.shape[0] > 7 else 0
    base_flow = int(base[8]) if base.shape[0] > 8 else 0
    base_chill = int(base[9]) if base.shape[0] > 9 else 0

    is_p_ft = int(flags.get("is_p_ft", 0))
    is_s_ft = int(flags.get("is_s_ft", 0))
    is_p_ff = int(flags.get("is_p_ff", 0))
    is_s_ff = int(flags.get("is_s_ff", 0))
    is_p_pp = int(flags.get("is_p_pp", 0))
    is_s_pp = int(flags.get("is_s_pp", 0))
    is_p_cm = int(flags.get("is_p_cm", 0))
    is_s_cm = int(flags.get("is_s_cm", 0))
    is_p_fm = int(flags.get("is_p_fm", 0))
    is_s_fm = int(flags.get("is_s_fm", 0))

    has_negative = False
    g_idx = np.asarray(pair_gear_idx, dtype=np.int32)
    m_idx = np.asarray(pair_mini_idx, dtype=np.int32)
    chunk = 250_000
    for start in range(0, n, chunk):
        end = min(n, start + chunk)
        ids = np.empty((end - start, 9), dtype=np.int32)
        ids[:, :6] = gear_ids[g_idx[start:end]]
        ids[:, 6:] = mini_ids[m_idx[start:end]]
        summed = item_stats[ids].sum(axis=1, dtype=np.int32)

        pp_raw = summed[:, 0] + base_pp
        cm_raw = summed[:, 1] + base_cm
        fm_raw = summed[:, 2] + base_fm
        ft_raw = summed[:, 3] + base_ft
        ff_raw = summed[:, 4] + base_ff
        pp_v = np.minimum(int(MAX_STAT_INDEX), pp_raw)
        cm_v = np.minimum(int(MAX_STAT_INDEX), cm_raw)
        fm_v = np.minimum(int(MAX_STAT_INDEX), fm_raw)
        ft_v = np.minimum(int(MAX_STAT_INDEX), ft_raw)
        ff_v = np.minimum(int(MAX_STAT_INDEX), ff_raw)
        if (
            np.any(pp_raw < 0)
            or np.any(cm_raw < 0)
            or np.any(fm_raw < 0)
            or np.any(ft_raw < 0)
            or np.any(ff_raw < 0)
        ):
            has_negative = True

        beat = summed[:, 5] + base_beat
        vibe = summed[:, 6] + base_vibe
        rush = summed[:, 7] + base_rush
        flow = summed[:, 8] + base_flow
        chill = summed[:, 9] + base_chill

        p_val = (
            (beat * is_p_ft)
            + (vibe * is_p_ff)
            + (rush * is_p_fm)
            + (flow * is_p_cm)
            + (chill * is_p_pp)
        )
        s_val = (
            (beat * is_s_ft)
            + (vibe * is_s_ff)
            + (rush * is_s_fm)
            + (flow * is_s_cm)
            + (chill * is_s_pp)
        )

        pp[start:end] = pp_v.astype(np.int16, copy=False)
        cm[start:end] = cm_v.astype(np.int16, copy=False)
        fm[start:end] = fm_v.astype(np.int16, copy=False)
        cell[start:end] = (ft_v * _GRID + ff_v).astype(np.int16, copy=False)
        lane[start:end] = ((2 * p_val) + s_val).astype(np.int16, copy=False)

    return _CandidateStates(
        pp=pp,
        cm=cm,
        fm=fm,
        cell=cell,
        lane=lane,
        has_negative_timing_or_stat=bool(has_negative),
    )


def _mini_points_have_no_pp(*, mini_ids: np.ndarray, item_stats: np.ndarray) -> bool:
    ids = np.unique(np.asarray(mini_ids, dtype=np.int32).reshape(-1))
    ids = ids[ids > 0]
    if ids.size == 0:
        return True
    return not bool(np.any(item_stats[ids, 0] != 0))


def _candidate_state_arrays_from_points(
    *,
    pair_gear_idx: np.ndarray,
    pair_mini_idx: np.ndarray,
    gear_points: np.ndarray,
    mini_points: np.ndarray,
    base_fixed_stats_arr: np.ndarray,
    flags: dict[str, int],
) -> _CandidateStates:
    n = int(np.asarray(pair_gear_idx).shape[0])
    pp = np.empty(n, dtype=np.int16)
    cm = np.empty(n, dtype=np.int16)
    fm = np.empty(n, dtype=np.int16)
    cell = np.empty(n, dtype=np.int16)
    lane = np.empty(n, dtype=np.int16)

    base = np.asarray(base_fixed_stats_arr, dtype=np.int32).reshape(-1)
    base_pp = int(base[0]) if base.shape[0] > 0 else 0
    base_cm = int(base[1]) if base.shape[0] > 1 else 0
    base_fm = int(base[2]) if base.shape[0] > 2 else 0
    base_ft = int(base[3]) if base.shape[0] > 3 else 0
    base_ff = int(base[4]) if base.shape[0] > 4 else 0
    base_lane = _base_lane_from_flags(base=base, flags=flags)

    gp = np.asarray(gear_points, dtype=np.int32)
    mp = np.asarray(mini_points, dtype=np.int32)
    gi = np.asarray(pair_gear_idx, dtype=np.int32)
    mi = np.asarray(pair_mini_idx, dtype=np.int32)

    has_negative = False
    chunk = 1_000_000
    for start in range(0, n, chunk):
        end = min(n, start + chunk)
        g = gp[gi[start:end]]
        m = mp[mi[start:end]]

        pp_raw = g[:, 0] + base_pp
        cm_raw = g[:, 1] + m[:, 0] + base_cm
        fm_raw = g[:, 2] + m[:, 1] + base_fm
        ft_raw = g[:, 3] + m[:, 2] + base_ft
        ff_raw = g[:, 4] + m[:, 3] + base_ff
        lane_raw = g[:, 5] + m[:, 4] + base_lane
        if (
            np.any(pp_raw < 0)
            or np.any(cm_raw < 0)
            or np.any(fm_raw < 0)
            or np.any(ft_raw < 0)
            or np.any(ff_raw < 0)
        ):
            has_negative = True

        pp_v = np.minimum(int(MAX_STAT_INDEX), pp_raw)
        cm_v = np.minimum(int(MAX_STAT_INDEX), cm_raw)
        fm_v = np.minimum(int(MAX_STAT_INDEX), fm_raw)
        ft_v = np.minimum(int(MAX_STAT_INDEX), ft_raw)
        ff_v = np.minimum(int(MAX_STAT_INDEX), ff_raw)

        pp[start:end] = pp_v.astype(np.int16, copy=False)
        cm[start:end] = cm_v.astype(np.int16, copy=False)
        fm[start:end] = fm_v.astype(np.int16, copy=False)
        cell[start:end] = (ft_v * _GRID + ff_v).astype(np.int16, copy=False)
        lane[start:end] = lane_raw.astype(np.int16, copy=False)

    return _CandidateStates(
        pp=pp,
        cm=cm,
        fm=fm,
        cell=cell,
        lane=lane,
        has_negative_timing_or_stat=bool(has_negative),
    )


def _base_lane_from_flags(*, base: np.ndarray, flags: dict[str, int]) -> int:
    values = {
        "ft": int(base[5]) if base.shape[0] > 5 else 0,
        "ff": int(base[6]) if base.shape[0] > 6 else 0,
        "fm": int(base[7]) if base.shape[0] > 7 else 0,
        "cm": int(base[8]) if base.shape[0] > 8 else 0,
        "pp": int(base[9]) if base.shape[0] > 9 else 0,
    }
    p_val = sum(values[name] * int(flags.get(f"is_p_{name}", 0)) for name in values)
    s_val = sum(values[name] * int(flags.get(f"is_s_{name}", 0)) for name in values)
    same_lane = any(
        int(flags.get(f"is_p_{name}", 0)) != 0 and int(flags.get(f"is_s_{name}", 0)) != 0
        for name in values
    )
    return int(2 * p_val) + (0 if same_lane else int(s_val))


@dataclass(frozen=True)
class _TimingResponseIndex:
    cells: np.ndarray
    cell_to_row: np.ndarray
    env: np.ndarray
    pack_dom: np.ndarray
    pack_dom_offsets: np.ndarray
    pack_dom_targets: np.ndarray
    best: np.ndarray
    best_row_for_source_row: np.ndarray
    needed_offsets: np.ndarray
    needed_packs: np.ndarray
    needed_requirements: np.ndarray
    pack_count: int


def _build_timing_response_index(
    *,
    present_cells: np.ndarray,
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
) -> _TimingResponseIndex:
    cells = np.asarray(present_cells, dtype=np.int32)
    cell_to_row = np.full(_GRID * _GRID, -1, dtype=np.int32)
    cell_to_row[cells] = np.arange(cells.shape[0], dtype=np.int32)

    cell_pack, pack_bits, pack_body_fever, pack_body_normal = _timeline_pack_grid(
        calc_song=calc_song,
        ref_arrays=ref_arrays,
    )
    pack_count = int(pack_body_fever.shape[0])
    env = _timing_envelopes_for_cells(cells=cells, cell_pack=cell_pack, pack_count=pack_count)
    pack_dom = _pack_dominance_matrix(
        pack_bits=pack_bits,
        pack_body_fever=pack_body_fever,
        pack_body_normal=pack_body_normal,
    )
    pack_dom_offsets, pack_dom_targets = _pack_dominance_csr(pack_dom)
    needed_offsets, needed_packs, needed_requirements = _env_active_csr(env)
    return _TimingResponseIndex(
        cells=cells,
        cell_to_row=cell_to_row,
        env=env,
        pack_dom=pack_dom,
        pack_dom_offsets=pack_dom_offsets,
        pack_dom_targets=pack_dom_targets,
        best=np.zeros((0, pack_count), dtype=np.int8),
        best_row_for_source_row=np.full(env.shape[0], -1, dtype=np.int32),
        needed_offsets=needed_offsets,
        needed_packs=needed_packs,
        needed_requirements=needed_requirements,
        pack_count=pack_count,
    )


def _timeline_pack_grid(
    *,
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    timeline = get_song_timeline_grid(calc_song, ref_arrays)
    cache_key = (getattr(timeline, "cache_key", None), id(timeline))
    cached = _TIMELINE_PACK_GRID_CACHE.get(cache_key)
    if cached is not None:
        return cached

    pack_to_id: dict[tuple[bytes, int, int], int] = {}
    pack_bits: list[np.ndarray] = []
    pack_body_fever: list[int] = []
    pack_body_normal: list[int] = []
    cell_pack = np.empty((_GRID, _GRID), dtype=np.int16)

    for ft in range(_GRID):
        for ff in range(_GRID):
            mask, body_fever, body_normal, _activations, _last_end = timeline.get_timeline(ft, ff)
            bits = np.packbits(np.asarray(mask, dtype=np.bool_), bitorder="little")
            key = (bytes(bits), int(body_fever), int(body_normal))
            pack_id = pack_to_id.get(key)
            if pack_id is None:
                pack_id = len(pack_to_id)
                pack_to_id[key] = pack_id
                pack_bits.append(bits.astype(np.uint8, copy=True))
                pack_body_fever.append(int(body_fever))
                pack_body_normal.append(int(body_normal))
            cell_pack[ft, ff] = np.int16(pack_id)

    max_words = max((int(bits.shape[0]) for bits in pack_bits), default=0)
    bits_arr = np.zeros((len(pack_bits), max_words), dtype=np.uint8)
    for idx, bits in enumerate(pack_bits):
        bits_arr[idx, : bits.shape[0]] = bits
    result = (
        cell_pack,
        bits_arr,
        np.asarray(pack_body_fever, dtype=np.int16),
        np.asarray(pack_body_normal, dtype=np.int16),
    )
    _TIMELINE_PACK_GRID_CACHE[cache_key] = result
    while len(_TIMELINE_PACK_GRID_CACHE) > int(_TIMELINE_PACK_GRID_CACHE_MAX):
        _TIMELINE_PACK_GRID_CACHE.pop(next(iter(_TIMELINE_PACK_GRID_CACHE)))
    return result


def _timing_envelopes_for_cells(
    *,
    cells: np.ndarray,
    cell_pack: np.ndarray,
    pack_count: int,
) -> np.ndarray:
    env = np.full((int(cells.shape[0]), int(pack_count)), -1, dtype=np.int8)
    spends_ft: list[int] = []
    spends_ff: list[int] = []
    spends_rem: list[int] = []
    for g_ft in range(int(TOTAL_GEM_BUDGET) + 1):
        max_ff = int(TOTAL_GEM_BUDGET) - int(g_ft)
        for g_ff in range(max_ff + 1):
            spends_ft.append(g_ft)
            spends_ff.append(g_ff)
            spends_rem.append(max_ff - g_ff)
    spend_ft = np.asarray(spends_ft, dtype=np.int16)
    spend_ff = np.asarray(spends_ff, dtype=np.int16)
    spend_rem = np.asarray(spends_rem, dtype=np.int8)

    d_ft = spend_ft.astype(np.int32) * int(GEM_SCALE_FEVER)
    d_ff = spend_ff.astype(np.int32) * int(GEM_SCALE_FEVER)
    for row, cell in enumerate(cells.tolist()):
        raw_ft = int(cell) // _GRID
        raw_ff = int(cell) % _GRID
        cap_ft = max(0, (int(MAX_STAT_INDEX) - raw_ft) // int(GEM_SCALE_FEVER))
        cap_ff = max(0, (int(MAX_STAT_INDEX) - raw_ff) // int(GEM_SCALE_FEVER))
        valid = (spend_ft <= cap_ft) & (spend_ff <= cap_ff)
        final_ft = raw_ft + d_ft[valid]
        final_ff = raw_ff + d_ff[valid]
        packs = cell_pack[final_ft, final_ff].astype(np.intp, copy=False)
        np.maximum.at(env[row], packs, spend_rem[valid])
    return env


def _pack_dominance_matrix(
    *,
    pack_bits: np.ndarray,
    pack_body_fever: np.ndarray,
    pack_body_normal: np.ndarray,
) -> np.ndarray:
    n = int(pack_body_fever.shape[0])
    out = np.zeros((n, n), dtype=np.bool_)
    for i in range(n):
        bit_superset = np.all((pack_bits[i] | pack_bits) == pack_bits[i], axis=1)
        out[i] = (
            bit_superset
            & (pack_body_fever[i] >= pack_body_fever)
            & (pack_body_normal[i] <= pack_body_normal)
        )
    return out


def _with_best_source_rows(timing: _TimingResponseIndex, source_rows: np.ndarray) -> _TimingResponseIndex:
    rows = np.asarray(source_rows, dtype=np.int32)
    rows = rows[(rows >= 0) & (rows < timing.env.shape[0])]
    if rows.size == 0:
        return timing
    rows = np.unique(rows)
    best = _best_remaining_by_dominated_pack(
        env=timing.env[rows],
        pack_dom=timing.pack_dom,
        offsets=timing.pack_dom_offsets,
        targets=timing.pack_dom_targets,
    )
    row_map = np.full(timing.env.shape[0], -1, dtype=np.int32)
    row_map[rows] = np.arange(rows.shape[0], dtype=np.int32)
    return replace(timing, best=best, best_row_for_source_row=row_map)


def _build_source_target_cover_matrix(
    timing: _TimingResponseIndex,
    *,
    target_rows: np.ndarray,
) -> tuple[np.ndarray | None, np.ndarray]:
    source_count = int(timing.best.shape[0])
    targets = np.asarray(target_rows, dtype=np.int32)
    targets = targets[(targets >= 0) & (targets < timing.cells.shape[0])]
    targets = np.unique(targets)
    target_count = int(targets.shape[0])
    target_col = np.full(timing.cells.shape[0], -1, dtype=np.int32)
    if target_count > 0:
        target_col[targets] = np.arange(target_count, dtype=np.int32)
    if source_count <= 0 or target_count <= 0:
        return None, target_col
    if source_count * target_count > int(_MAX_COVER_MATRIX_BYTES):
        return None, target_col

    cover = np.zeros((source_count, target_count), dtype=np.bool_)
    for col, target_row in enumerate(targets.tolist()):
        start = int(timing.needed_offsets[target_row])
        end = int(timing.needed_offsets[target_row + 1])
        packs = timing.needed_packs[start:end]
        if packs.size == 0:
            cover[:, col] = True
            continue
        req = timing.needed_requirements[start:end]
        cover[:, col] = np.all(timing.best[:, packs] >= req, axis=1)
    return cover, target_col


def _best_remaining_by_dominated_pack(
    *,
    env: np.ndarray,
    pack_dom: np.ndarray,
    offsets: np.ndarray | None = None,
    targets: np.ndarray | None = None,
) -> np.ndarray:
    if HAS_NUMBA:
        if offsets is None or targets is None:
            offsets, targets = _pack_dominance_csr(pack_dom)
        best_jit = np.full(env.shape, -1, dtype=np.int8)
        _best_remaining_by_dominated_pack_jit(env, offsets, targets, best_jit)
        return best_jit

    rows, packs = env.shape
    best = np.full((rows, packs), -1, dtype=np.int8)
    for source_pack in range(packs):
        dominated = pack_dom[source_pack]
        if not np.any(dominated):
            continue
        values = env[:, source_pack]
        active = values >= 0
        if not np.any(active):
            continue
        best[np.ix_(active, dominated)] = np.maximum(best[np.ix_(active, dominated)], values[active, None])
    return best


def _pack_dominance_csr(pack_dom: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    dom = np.asarray(pack_dom, dtype=np.bool_)
    counts = np.count_nonzero(dom, axis=1).astype(np.int32, copy=False)
    offsets = np.empty(int(counts.shape[0]) + 1, dtype=np.int32)
    offsets[0] = 0
    np.cumsum(counts, out=offsets[1:])
    targets = np.empty(int(offsets[-1]), dtype=np.int32)
    cursor = 0
    for row in range(int(dom.shape[0])):
        cols = np.flatnonzero(dom[row]).astype(np.int32, copy=False)
        n = int(cols.shape[0])
        targets[cursor : cursor + n] = cols
        cursor += n
    return offsets, targets


def _env_active_csr(env: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    active = np.asarray(env) >= 0
    counts = np.count_nonzero(active, axis=1).astype(np.int32, copy=False)
    offsets = np.empty(int(counts.shape[0]) + 1, dtype=np.int32)
    offsets[0] = 0
    np.cumsum(counts, out=offsets[1:])
    rows, packs = np.nonzero(active)
    del rows
    return offsets, packs.astype(np.int32, copy=False), env[active].astype(np.int8, copy=False)


@jit(nopython=True, cache=True)
def _best_remaining_by_dominated_pack_jit(
    env: np.ndarray,
    offsets: np.ndarray,
    targets: np.ndarray,
    best: np.ndarray,
) -> None:
    rows = env.shape[0]
    packs = env.shape[1]
    for row in range(rows):
        for source_pack in range(packs):
            value = env[row, source_pack]
            if value < 0:
                continue
            start = offsets[source_pack]
            end = offsets[source_pack + 1]
            for pos in range(start, end):
                target_pack = targets[pos]
                if value > best[row, target_pack]:
                    best[row, target_pack] = value


def _owner_strategy_keys(states: _CandidateStates) -> tuple[tuple[str, np.ndarray], ...]:
    cell_i = states.cell.astype(np.int32, copy=False)
    ft = cell_i // _GRID
    ff = cell_i % _GRID
    lane = states.lane.astype(np.int32, copy=False)
    return (
        ("timing_sum_lane", ((ft + ff) * int(_KEY_LANE_STRIDE)) + lane),
        ("timing_min_lane", (np.minimum(ft, ff) * int(_KEY_LANE_STRIDE)) + lane),
    )


def _build_suffix_owner_index_for_key(states: _CandidateStates, key: np.ndarray) -> np.ndarray:
    pp_i = states.pp.astype(np.int32, copy=False)
    cm_i = states.cm.astype(np.int32, copy=False)
    fm_i = states.fm.astype(np.int32, copy=False)
    flat = ((pp_i * _GRID) + cm_i) * _GRID + fm_i

    key_i = np.asarray(key, dtype=np.int32)
    key_grid_1d = np.full(_STAT_GRID_SIZE, np.iinfo(np.int32).min, dtype=np.int32)
    np.maximum.at(key_grid_1d, flat, key_i)

    owner_1d = np.full(_STAT_GRID_SIZE, np.iinfo(np.int32).max, dtype=np.int32)
    idx = np.arange(states.lane.shape[0], dtype=np.int32)
    top_at_coord = key_i == key_grid_1d[flat]
    np.minimum.at(owner_1d, flat[top_at_coord], idx[top_at_coord])
    owner_1d[owner_1d == np.iinfo(np.int32).max] = _NO_OWNER

    key_grid = key_grid_1d.reshape((_GRID, _GRID, _GRID))
    owner_grid = owner_1d.reshape((_GRID, _GRID, _GRID))
    _suffix_max_axis(key_grid, owner_grid, axis=2)
    _suffix_max_axis(key_grid, owner_grid, axis=1)
    _suffix_max_axis(key_grid, owner_grid, axis=0)
    return owner_grid


def _suffix_max_axis(lane: np.ndarray, owner: np.ndarray, *, axis: int) -> None:
    if int(axis) == 0:
        for i in range(_GRID - 2, -1, -1):
            better = lane[i + 1, :, :] > lane[i, :, :]
            lane[i, :, :][better] = lane[i + 1, :, :][better]
            owner[i, :, :][better] = owner[i + 1, :, :][better]
    elif int(axis) == 1:
        for i in range(_GRID - 2, -1, -1):
            better = lane[:, i + 1, :] > lane[:, i, :]
            lane[:, i, :][better] = lane[:, i + 1, :][better]
            owner[:, i, :][better] = owner[:, i + 1, :][better]
    elif int(axis) == 2:
        for i in range(_GRID - 2, -1, -1):
            better = lane[:, :, i + 1] > lane[:, :, i]
            lane[:, :, i][better] = lane[:, :, i + 1][better]
            owner[:, :, i][better] = owner[:, :, i + 1][better]
    else:
        raise ValueError("axis must be 0, 1, or 2")


def _timing_covers_pairs(
    *,
    source_cells: np.ndarray,
    target_cells: np.ndarray,
    timing: _TimingResponseIndex,
) -> np.ndarray:
    count = int(source_cells.shape[0])
    if count == 0:
        return np.zeros(0, dtype=np.bool_)

    source_rows = timing.cell_to_row[source_cells.astype(np.int32, copy=False)]
    target_rows = timing.cell_to_row[target_cells.astype(np.int32, copy=False)]
    return _timing_covers_row_pairs(source_rows=source_rows, target_rows=target_rows, timing=timing)


def _timing_covers_row_pairs(
    *,
    source_rows: np.ndarray,
    target_rows: np.ndarray,
    timing: _TimingResponseIndex,
) -> np.ndarray:
    count = int(source_rows.shape[0])
    if count == 0:
        return np.zeros(0, dtype=np.bool_)
    source_best_rows = timing.best_row_for_source_row[source_rows.astype(np.int32, copy=False)]
    valid = source_best_rows >= 0
    if not np.all(valid):
        out = np.zeros(count, dtype=np.bool_)
        if not np.any(valid):
            return out
        covered = _timing_covers_row_pairs(
            source_rows=source_rows[valid],
            target_rows=target_rows[valid],
            timing=timing,
        )
        out[valid] = covered
        return out

    if HAS_NUMBA:
        n_targets = int(timing.cells.shape[0])
        codes = (source_best_rows.astype(np.int64, copy=False) * np.int64(n_targets)) + target_rows.astype(
            np.int64, copy=False
        )
        order = np.argsort(codes, kind="stable")
        out_jit = np.zeros(count, dtype=np.bool_)
        _timing_covers_sorted_pairs_jit(
            source_best_rows.astype(np.int32, copy=False),
            target_rows.astype(np.int32, copy=False),
            codes,
            order.astype(np.int32, copy=False),
            timing.best,
            timing.needed_offsets,
            timing.needed_packs,
            timing.needed_requirements,
            out_jit,
        )
        return out_jit

    out = np.zeros(count, dtype=np.bool_)
    order = np.argsort(target_rows, kind="stable")

    start = 0
    while start < count:
        target_row = int(target_rows[order[start]])
        end = start + 1
        while end < count and int(target_rows[order[end]]) == target_row:
            end += 1
        loc = order[start:end]
        needed = timing.env[target_row]
        packs = np.flatnonzero(needed >= 0)
        if packs.size == 0:
            out[loc] = True
        else:
            req = needed[packs]
            src = source_best_rows[loc]
            unique_src, inverse = np.unique(src, return_inverse=True)
            unique_cover = np.all(timing.best[unique_src[:, None], packs] >= req, axis=1)
            out[loc] = unique_cover[inverse]
        start = end
    return out


@jit(nopython=True, cache=True)
def _timing_covers_sorted_pairs_jit(
    source_best_rows: np.ndarray,
    target_rows: np.ndarray,
    codes: np.ndarray,
    order: np.ndarray,
    best: np.ndarray,
    needed_offsets: np.ndarray,
    needed_packs: np.ndarray,
    needed_requirements: np.ndarray,
    out: np.ndarray,
) -> None:
    count = order.shape[0]
    i = 0
    while i < count:
        first_idx = order[i]
        code = codes[first_idx]
        source_row = source_best_rows[first_idx]
        target_row = target_rows[first_idx]
        ok = True
        start = needed_offsets[target_row]
        end = needed_offsets[target_row + 1]
        for pos in range(start, end):
            pack = needed_packs[pos]
            req = needed_requirements[pos]
            if best[source_row, pack] < req:
                ok = False
                break
        while i < count:
            idx = order[i]
            if codes[idx] != code:
                break
            out[idx] = ok
            i += 1
