from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import taichi as ti

from gear_optimizer.solver.taichi_gem import runtime as ti_runtime


@dataclass(frozen=True)
class GpuFullSolution:
    covered: "object"  # np.ndarray[int32] shape (S,)
    chosen_part: "object"  # np.ndarray[int32] shape (S,)
    counts: "object"  # np.ndarray[int32] shape (V, stripes)
    inventory_size: int
    covered_count: int
    stats: dict


@dataclass
class _GpuFullState:
    part_vids: ti.Field
    synergy: ti.Field
    freq: ti.Field
    vid_gid: ti.Field
    vid_is_wild: ti.Field
    seeded: ti.Field
    counts: ti.Field
    counts_total: ti.Field
    gear_var_count: ti.Field
    covered: ti.Field
    chosen: ti.Field
    propose: ti.Field
    inv_size: ti.Field
    cov_count: ti.Field
    best_key: ti.Field
    best_cost: ti.Field
    best_cand: ti.Field
    removed_cnt: ti.Field
    benefit_sum: ti.Field
    tmp_cost: ti.Field
    greedy_did_add: ti.Field
    counts_best: ti.Field
    counts_total_best: ti.Field
    gear_var_count_best: ti.Field
    covered_best: ti.Field
    chosen_best: ti.Field
    inv_best: ti.Field
    cov_best: ti.Field
    repack_best_p: ti.Field


@dataclass
class _GpuFullIslandsState:
    part_vids: ti.Field
    synergy: ti.Field
    freq: ti.Field
    counts: ti.Field
    counts_total: ti.Field
    covered: ti.Field
    chosen: ti.Field
    cap: ti.Field
    inv_size: ti.Field
    cov_count: ti.Field
    best_cost: ti.Field
    best_cand: ti.Field
    did_add_any: ti.Field
    removed_cnt: ti.Field
    destroy_kind: ti.Field
    destroy_target: ti.Field
    repack_best_p: ti.Field


_LAST_STATE_SIG: Optional[Tuple[int, int, int, int, int]] = None
_LAST_STATE: Optional[_GpuFullState] = None
_LAST_ISLANDS_SIG: Optional[Tuple[int, int, int, int, int]] = None
_LAST_ISLANDS_STATE: Optional[_GpuFullIslandsState] = None


def _get_or_build_state(
    *,
    s_count: int,
    k_count: int,
    v_count: int,
    counter_stripes: int,
    gear_count: int,
) -> _GpuFullState:
    """
    Reuse Taichi fields across solves for the same shapes.

    Without this, repeated solves with identical shapes in the same process can return all-zeros
    (likely a Taichi/Vulkan field binding + kernel cache interaction).
    """
    global _LAST_STATE, _LAST_STATE_SIG

    sig = (int(s_count), int(k_count), int(v_count), int(counter_stripes), int(gear_count))
    if _LAST_STATE is not None and _LAST_STATE_SIG == sig:
        # Defensive: other modules in-process may `ti.reset()` / `reset_taichi()` and invalidate fields.
        # If we detect a shape mismatch, drop the cached state and rebuild.
        try:
            if (
                tuple(_LAST_STATE.part_vids.shape) == (int(s_count), int(k_count), 6)
                and tuple(_LAST_STATE.freq.shape) == (int(v_count),)
                and tuple(_LAST_STATE.gear_var_count.shape) == (max(1, int(gear_count) + 1),)
            ):
                return _LAST_STATE
        except Exception:
            pass
        _LAST_STATE = None
        _LAST_STATE_SIG = None

    if _LAST_STATE is None:
        # Start from a clean Taichi runtime before allocating the persistent GPU_FULL fields.
        # This avoids interactions with other Taichi field graphs in the same process.
        try:
            ti_runtime.reset_taichi(reason="gpu_full_solver fresh state")
        except Exception:
            pass
    elif _LAST_STATE_SIG != sig:
        try:
            ti_runtime.reset_taichi(reason="gpu_full_solver shape change")
        except Exception:
            try:
                ti.reset()
            except Exception:
                pass

    ti_runtime.init_taichi()

    part_vids = ti.field(dtype=ti.i32, shape=(s_count, k_count, 6))
    synergy = ti.field(dtype=ti.i32, shape=(s_count, k_count))
    freq = ti.field(dtype=ti.i32, shape=(v_count,))
    vid_gid = ti.field(dtype=ti.i32, shape=(v_count,))
    vid_is_wild = ti.field(dtype=ti.i32, shape=(v_count,))
    seeded = ti.field(dtype=ti.i32, shape=(v_count,))
    counts = ti.field(dtype=ti.i32, shape=(v_count, counter_stripes))
    counts_total = ti.field(dtype=ti.i32, shape=(v_count,))
    gear_var_count = ti.field(dtype=ti.i32, shape=(max(1, int(gear_count) + 1),))
    covered = ti.field(dtype=ti.i32, shape=(s_count,))
    chosen = ti.field(dtype=ti.i32, shape=(s_count,))
    propose = ti.field(dtype=ti.i32, shape=(s_count,))
    inv_size = ti.field(dtype=ti.i32, shape=())
    cov_count = ti.field(dtype=ti.i32, shape=())
    best_key = ti.field(dtype=ti.u64, shape=())
    best_cost = ti.field(dtype=ti.u32, shape=())
    best_cand = ti.field(dtype=ti.u32, shape=())
    removed_cnt = ti.field(dtype=ti.i32, shape=())
    benefit_sum = ti.field(dtype=ti.i32, shape=())
    tmp_cost = ti.field(dtype=ti.i32, shape=())
    greedy_did_add = ti.field(dtype=ti.i32, shape=())

    counts_best = ti.field(dtype=ti.i32, shape=(v_count, counter_stripes))
    counts_total_best = ti.field(dtype=ti.i32, shape=(v_count,))
    gear_var_count_best = ti.field(dtype=ti.i32, shape=(max(1, int(gear_count) + 1),))
    covered_best = ti.field(dtype=ti.i32, shape=(s_count,))
    chosen_best = ti.field(dtype=ti.i32, shape=(s_count,))
    inv_best = ti.field(dtype=ti.i32, shape=())
    cov_best = ti.field(dtype=ti.i32, shape=())
    repack_best_p = ti.field(dtype=ti.i32, shape=(s_count,))

    _LAST_STATE = _GpuFullState(
        part_vids=part_vids,
        synergy=synergy,
        freq=freq,
        vid_gid=vid_gid,
        vid_is_wild=vid_is_wild,
        seeded=seeded,
        counts=counts,
        counts_total=counts_total,
        gear_var_count=gear_var_count,
        covered=covered,
        chosen=chosen,
        propose=propose,
        inv_size=inv_size,
        cov_count=cov_count,
        best_key=best_key,
        best_cost=best_cost,
        best_cand=best_cand,
        removed_cnt=removed_cnt,
        benefit_sum=benefit_sum,
        tmp_cost=tmp_cost,
        greedy_did_add=greedy_did_add,
        counts_best=counts_best,
        counts_total_best=counts_total_best,
        gear_var_count_best=gear_var_count_best,
        covered_best=covered_best,
        chosen_best=chosen_best,
        inv_best=inv_best,
        cov_best=cov_best,
        repack_best_p=repack_best_p,
    )
    _LAST_STATE_SIG = sig
    return _LAST_STATE


def _get_or_build_islands_state(
    *,
    islands: int,
    s_count: int,
    k_count: int,
    v_count: int,
    counter_stripes: int,
) -> _GpuFullIslandsState:
    """
    Allocate persistent Taichi fields for the multi-island ALNS path.

    We store islands by flattening `(I, S)` into `IS = I*S` for covered/chosen and `(I, V)` into `IV = I*V`
    for counts_total. This avoids 2D loop/indexing overhead in Taichi kernels.
    """
    global _LAST_ISLANDS_SIG, _LAST_ISLANDS_STATE

    sig = (int(islands), int(s_count), int(k_count), int(v_count), int(counter_stripes))
    if _LAST_ISLANDS_STATE is not None and _LAST_ISLANDS_SIG == sig:
        try:
            if tuple(_LAST_ISLANDS_STATE.covered.shape) == (int(islands) * int(s_count),) and tuple(
                _LAST_ISLANDS_STATE.counts_total.shape
            ) == (int(islands) * int(v_count),):
                return _LAST_ISLANDS_STATE
        except Exception:
            pass
        _LAST_ISLANDS_STATE = None
        _LAST_ISLANDS_SIG = None

    # Multi-island state is large; prefer a clean runtime to avoid backend graph conflicts.
    try:
        ti_runtime.reset_taichi(reason="gpu_full_solver islands state")
    except Exception:
        pass
    ti_runtime.init_taichi()

    n_islands = int(islands)
    IS = int(islands) * int(s_count)
    IV = int(islands) * int(v_count)

    part_vids = ti.field(dtype=ti.i32, shape=(int(s_count), int(k_count), 6))
    synergy = ti.field(dtype=ti.i32, shape=(int(s_count), int(k_count)))
    freq = ti.field(dtype=ti.i32, shape=(int(v_count),))
    counts = ti.field(dtype=ti.i32, shape=(IV, int(counter_stripes)))
    counts_total = ti.field(dtype=ti.i32, shape=(IV,))
    covered = ti.field(dtype=ti.i32, shape=(IS,))
    chosen = ti.field(dtype=ti.i32, shape=(IS,))
    cap = ti.field(dtype=ti.i32, shape=(n_islands,))
    inv_size = ti.field(dtype=ti.i32, shape=(n_islands,))
    cov_count = ti.field(dtype=ti.i32, shape=(n_islands,))

    best_cost = ti.field(dtype=ti.u32, shape=(n_islands,))
    best_cand = ti.field(dtype=ti.u32, shape=(n_islands,))  # packed (s,p) key
    did_add_any = ti.field(dtype=ti.i32, shape=(n_islands,))
    removed_cnt = ti.field(dtype=ti.i32, shape=(n_islands,))
    destroy_kind = ti.field(dtype=ti.i32, shape=(n_islands,))
    destroy_target = ti.field(dtype=ti.i32, shape=(n_islands,))
    repack_best_p = ti.field(dtype=ti.i32, shape=(IS,))

    _LAST_ISLANDS_STATE = _GpuFullIslandsState(
        part_vids=part_vids,
        synergy=synergy,
        freq=freq,
        counts=counts,
        counts_total=counts_total,
        covered=covered,
        chosen=chosen,
        cap=cap,
        inv_size=inv_size,
        cov_count=cov_count,
        best_cost=best_cost,
        best_cand=best_cand,
        did_add_any=did_add_any,
        removed_cnt=removed_cnt,
        destroy_kind=destroy_kind,
        destroy_target=destroy_target,
        repack_best_p=repack_best_p,
    )
    _LAST_ISLANDS_SIG = sig
    return _LAST_ISLANDS_STATE


__all__ = [
    "GpuFullSolution",
    "_GpuFullIslandsState",
    "_GpuFullState",
    "_get_or_build_islands_state",
    "_get_or_build_state",
]
