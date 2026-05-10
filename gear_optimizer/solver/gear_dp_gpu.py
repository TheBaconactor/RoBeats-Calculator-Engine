import time
from dataclasses import dataclass

import numpy as np

from gear_optimizer.core.constants import MAX_STAT_INDEX
from gear_optimizer.solver.solver_common import GEAR_SLOTS
from gear_optimizer.solver.taichi_gem.runtime import init_taichi


def _item_vec_5(item: dict) -> tuple[int, int, int, int, int]:
    return (
        int(item.get("Perfect Points", 0) or 0),
        int(item.get("Combo Multiplier", 0) or 0),
        int(item.get("Fever Multiplier", 0) or 0),
        int(item.get("Fever Time", 0) or 0),
        int(item.get("Fever Fill Rate", 0) or 0),
    )


def _lane_base_init(item: dict, p_color: str, s_color: str) -> int:
    p = int(item.get(p_color, 0) or 0) if p_color else 0
    s = int(item.get(s_color, 0) or 0) if s_color and s_color != p_color else 0
    return (2 * p) + s


def _compact_max_base(
    pp: np.ndarray,
    cm: np.ndarray,
    fm: np.ndarray,
    ft: np.ndarray,
    ff: np.ndarray,
    base: np.ndarray,
    code: np.ndarray,
) -> tuple:
    N = int(pp.shape[0])
    if N == 0:
        return (
            np.zeros(0, dtype=np.int32),
            np.zeros(0, dtype=np.int32),
            np.zeros(0, dtype=np.int32),
            np.zeros(0, dtype=np.int32),
            np.zeros(0, dtype=np.int32),
            np.zeros(0, dtype=np.int32),
            np.zeros(0, dtype=np.uint64),
        )

    packed = (
        (pp.astype(np.int64) << 40)
        | (cm.astype(np.int64) << 32)
        | (fm.astype(np.int64) << 24)
        | (ft.astype(np.int64) << 16)
        | (ff.astype(np.int64) << 8)
    )
    order = np.lexsort((-base.astype(np.int64), packed))
    p_s = packed[order]
    unique = np.concatenate([[True], p_s[1:] != p_s[:-1]])

    return (
        pp[order][unique],
        cm[order][unique],
        fm[order][unique],
        ft[order][unique],
        ff[order][unique],
        base[order][unique],
        code[order][unique],
    )


def _compact_to_dict(
    pp: np.ndarray,
    cm: np.ndarray,
    fm: np.ndarray,
    ft: np.ndarray,
    ff: np.ndarray,
    base: np.ndarray,
    code: np.ndarray,
) -> dict:
    states: dict = {}
    for i in range(int(pp.shape[0])):
        key = (int(pp[i]), int(cm[i]), int(fm[i]), int(ft[i]))
        val = (int(ff[i]), int(base[i]), int(code[i]))
        fr = states.get(key)
        if fr is None:
            states[key] = [val]
        else:
            fr.append(val)
    for frontier in states.values():
        frontier.sort(key=lambda x: x[0])
    return states


@dataclass(frozen=True)
class LaneAwareGearDPStatsGPU:
    keys_4d: int
    pairs_6d: int
    frontier_mean: float
    frontier_p95: float
    frontier_max: int
    seconds: float


def _prepare_item_arrays(pool: dict, pack, p_color: str, s_color: str) -> list:
    slot_arrays: list = []
    for slot_idx, slot in enumerate(GEAR_SLOTS):
        items = pool.get(slot, [])
        if not items:
            return []
        M = len(items)
        dpp = np.empty(M, dtype=np.int32)
        dcm = np.empty(M, dtype=np.int32)
        dfm = np.empty(M, dtype=np.int32)
        dft = np.empty(M, dtype=np.int32)
        dff = np.empty(M, dtype=np.int32)
        dbase = np.empty(M, dtype=np.int32)
        dcode = np.empty(M, dtype=np.uint64)
        shift = pack.shifts[slot_idx]
        for i, it in enumerate(items):
            dpp[i], dcm[i], dfm[i], dft[i], dff[i] = _item_vec_5(it)
            dbase[i] = _lane_base_init(it, p_color, s_color)
            dcode[i] = np.uint64(i << shift)
        slot_arrays.append(
            {
                "dpp": dpp,
                "dcm": dcm,
                "dfm": dfm,
                "dft": dft,
                "dff": dff,
                "dbase": dbase,
                "dcode": dcode,
            }
        )
    return slot_arrays


def gear_dp_gpu(
    gear_pool: dict,
    *,
    p_color: str,
    s_color: str,
    pack,
) -> tuple:
    from gear_optimizer.solver.taichi_gem.runtime import ti

    t0 = time.perf_counter()

    slot_arrays = _prepare_item_arrays(gear_pool, pack, p_color, s_color)
    if not slot_arrays:
        return {}, LaneAwareGearDPStatsGPU(0, 0, 0.0, 0.0, 0, float(time.perf_counter() - t0))

    init_taichi()

    @ti.kernel
    def _dp_expand_empty_slot(
        pp: ti.types.ndarray(dtype=ti.i32, ndim=1),
        cm: ti.types.ndarray(dtype=ti.i32, ndim=1),
        fm: ti.types.ndarray(dtype=ti.i32, ndim=1),
        ft: ti.types.ndarray(dtype=ti.i32, ndim=1),
        ff: ti.types.ndarray(dtype=ti.i32, ndim=1),
        base: ti.types.ndarray(dtype=ti.i32, ndim=1),
        code: ti.types.ndarray(dtype=ti.u64, ndim=1),
        N: ti.i32,
        out_pp: ti.types.ndarray(dtype=ti.i32, ndim=1),
        out_cm: ti.types.ndarray(dtype=ti.i32, ndim=1),
        out_fm: ti.types.ndarray(dtype=ti.i32, ndim=1),
        out_ft: ti.types.ndarray(dtype=ti.i32, ndim=1),
        out_ff: ti.types.ndarray(dtype=ti.i32, ndim=1),
        out_base: ti.types.ndarray(dtype=ti.i32, ndim=1),
        out_code: ti.types.ndarray(dtype=ti.u64, ndim=1),
    ):
        for i in range(N):
            out_pp[i] = pp[i]
            out_cm[i] = cm[i]
            out_fm[i] = fm[i]
            out_ft[i] = ft[i]
            out_ff[i] = ff[i]
            out_base[i] = base[i]
            out_code[i] = code[i]

    @ti.kernel
    def _dp_expand_flat(
        pp: ti.types.ndarray(dtype=ti.i32, ndim=1),
        cm: ti.types.ndarray(dtype=ti.i32, ndim=1),
        fm: ti.types.ndarray(dtype=ti.i32, ndim=1),
        ft: ti.types.ndarray(dtype=ti.i32, ndim=1),
        ff: ti.types.ndarray(dtype=ti.i32, ndim=1),
        base: ti.types.ndarray(dtype=ti.i32, ndim=1),
        code: ti.types.ndarray(dtype=ti.u64, ndim=1),
        N: ti.i32,
        dpp: ti.types.ndarray(dtype=ti.i32, ndim=1),
        dcm: ti.types.ndarray(dtype=ti.i32, ndim=1),
        dfm: ti.types.ndarray(dtype=ti.i32, ndim=1),
        dft: ti.types.ndarray(dtype=ti.i32, ndim=1),
        dff: ti.types.ndarray(dtype=ti.i32, ndim=1),
        dbase: ti.types.ndarray(dtype=ti.i32, ndim=1),
        dcode: ti.types.ndarray(dtype=ti.u64, ndim=1),
        M: ti.i32,
        out_pp: ti.types.ndarray(dtype=ti.i32, ndim=1),
        out_cm: ti.types.ndarray(dtype=ti.i32, ndim=1),
        out_fm: ti.types.ndarray(dtype=ti.i32, ndim=1),
        out_ft: ti.types.ndarray(dtype=ti.i32, ndim=1),
        out_ff: ti.types.ndarray(dtype=ti.i32, ndim=1),
        out_base: ti.types.ndarray(dtype=ti.i32, ndim=1),
        out_code: ti.types.ndarray(dtype=ti.u64, ndim=1),
        max_stat: ti.i32,
    ):
        for i, j in ti.ndrange(N, M):
            idx = i * M + j
            pv = pp[i] + dpp[j]
            cv = cm[i] + dcm[j]
            fv = fm[i] + dfm[j]
            tv = ft[i] + dft[j]
            rv = ff[i] + dff[j]
            out_pp[idx] = max(0, min(pv, max_stat))
            out_cm[idx] = max(0, min(cv, max_stat))
            out_fm[idx] = max(0, min(fv, max_stat))
            out_ft[idx] = max(0, min(tv, max_stat))
            out_ff[idx] = max(0, min(rv, max_stat))
            out_base[idx] = base[i] + dbase[j]
            out_code[idx] = code[i] | dcode[j]

    pp = np.array([0], dtype=np.int32)
    cm = np.array([0], dtype=np.int32)
    fm = np.array([0], dtype=np.int32)
    ft = np.array([0], dtype=np.int32)
    ff = np.array([0], dtype=np.int32)
    base = np.array([0], dtype=np.int32)
    code = np.array([0], dtype=np.uint64)

    for slot_idx, slot_arr in enumerate(slot_arrays):
        N = int(pp.shape[0])
        M = int(slot_arr["dpp"].shape[0])

        pp_dev = ti.ndarray(dtype=ti.i32, shape=(N,))
        cm_dev = ti.ndarray(dtype=ti.i32, shape=(N,))
        fm_dev = ti.ndarray(dtype=ti.i32, shape=(N,))
        ft_dev = ti.ndarray(dtype=ti.i32, shape=(N,))
        ff_dev = ti.ndarray(dtype=ti.i32, shape=(N,))
        base_dev = ti.ndarray(dtype=ti.i32, shape=(N,))
        code_dev = ti.ndarray(dtype=ti.u64, shape=(N,))

        pp_dev.from_numpy(pp)
        cm_dev.from_numpy(cm)
        fm_dev.from_numpy(fm)
        ft_dev.from_numpy(ft)
        ff_dev.from_numpy(ff)
        base_dev.from_numpy(base)
        code_dev.from_numpy(code)

        if M == 0:
            out_pp_dev = ti.ndarray(dtype=ti.i32, shape=(N,))
            out_cm_dev = ti.ndarray(dtype=ti.i32, shape=(N,))
            out_fm_dev = ti.ndarray(dtype=ti.i32, shape=(N,))
            out_ft_dev = ti.ndarray(dtype=ti.i32, shape=(N,))
            out_ff_dev = ti.ndarray(dtype=ti.i32, shape=(N,))
            out_base_dev = ti.ndarray(dtype=ti.i32, shape=(N,))
            out_code_dev = ti.ndarray(dtype=ti.u64, shape=(N,))

            _dp_expand_empty_slot(
                pp_dev, cm_dev, fm_dev, ft_dev, ff_dev, base_dev, code_dev, N,
                out_pp_dev, out_cm_dev, out_fm_dev, out_ft_dev, out_ff_dev, out_base_dev, out_code_dev,
            )
            ti.sync()

            pp = out_pp_dev.to_numpy()
            cm = out_cm_dev.to_numpy()
            fm = out_fm_dev.to_numpy()
            ft = out_ft_dev.to_numpy()
            ff = out_ff_dev.to_numpy()
            base = out_base_dev.to_numpy()
            code = out_code_dev.to_numpy()
        else:
            total = int(N) * int(M)

            dpp_dev = ti.ndarray(dtype=ti.i32, shape=(M,))
            dcm_dev = ti.ndarray(dtype=ti.i32, shape=(M,))
            dfm_dev = ti.ndarray(dtype=ti.i32, shape=(M,))
            dft_dev = ti.ndarray(dtype=ti.i32, shape=(M,))
            dff_dev = ti.ndarray(dtype=ti.i32, shape=(M,))
            dbase_dev = ti.ndarray(dtype=ti.i32, shape=(M,))
            dcode_dev = ti.ndarray(dtype=ti.u64, shape=(M,))

            dpp_dev.from_numpy(slot_arr["dpp"])
            dcm_dev.from_numpy(slot_arr["dcm"])
            dfm_dev.from_numpy(slot_arr["dfm"])
            dft_dev.from_numpy(slot_arr["dft"])
            dff_dev.from_numpy(slot_arr["dff"])
            dbase_dev.from_numpy(slot_arr["dbase"])
            dcode_dev.from_numpy(slot_arr["dcode"])

            out_pp_dev = ti.ndarray(dtype=ti.i32, shape=(total,))
            out_cm_dev = ti.ndarray(dtype=ti.i32, shape=(total,))
            out_fm_dev = ti.ndarray(dtype=ti.i32, shape=(total,))
            out_ft_dev = ti.ndarray(dtype=ti.i32, shape=(total,))
            out_ff_dev = ti.ndarray(dtype=ti.i32, shape=(total,))
            out_base_dev = ti.ndarray(dtype=ti.i32, shape=(total,))
            out_code_dev = ti.ndarray(dtype=ti.u64, shape=(total,))

            _dp_expand_flat(
                pp_dev, cm_dev, fm_dev, ft_dev, ff_dev, base_dev, code_dev, N,
                dpp_dev, dcm_dev, dfm_dev, dft_dev, dff_dev, dbase_dev, dcode_dev, M,
                out_pp_dev, out_cm_dev, out_fm_dev, out_ft_dev, out_ff_dev, out_base_dev, out_code_dev,
                MAX_STAT_INDEX,
            )
            ti.sync()

            pp = out_pp_dev.to_numpy()
            cm = out_cm_dev.to_numpy()
            fm = out_fm_dev.to_numpy()
            ft = out_ft_dev.to_numpy()
            ff = out_ff_dev.to_numpy()
            base = out_base_dev.to_numpy()
            code = out_code_dev.to_numpy()

            pp, cm, fm, ft, ff, base, code = _compact_max_base(pp, cm, fm, ft, ff, base, code)

    states = _compact_to_dict(pp, cm, fm, ft, ff, base, code)

    keys_4d = len(states)
    pairs_6d = sum(len(fr) for fr in states.values())
    seconds = float(time.perf_counter() - t0)

    frontier_sizes = np.array([len(fr) for fr in states.values()], dtype=np.int32)
    frontier_mean = float(frontier_sizes.mean()) if frontier_sizes.size else 0.0
    frontier_p95 = float(np.percentile(frontier_sizes, 95)) if frontier_sizes.size else 0.0
    frontier_max = int(frontier_sizes.max()) if frontier_sizes.size else 0

    stats = LaneAwareGearDPStatsGPU(
        keys_4d=keys_4d,
        pairs_6d=pairs_6d,
        frontier_mean=frontier_mean,
        frontier_p95=frontier_p95,
        frontier_max=frontier_max,
        seconds=seconds,
    )

    return states, stats


def gear_dp_vectorized(
    gear_pool: dict,
    *,
    p_color: str,
    s_color: str,
    pack,
) -> tuple:
    t0 = time.perf_counter()

    slot_arrays = _prepare_item_arrays(gear_pool, pack, p_color, s_color)
    if not slot_arrays:
        return {}, LaneAwareGearDPStatsGPU(0, 0, 0.0, 0.0, 0, float(time.perf_counter() - t0))

    pp = np.array([0], dtype=np.int32)
    cm = np.array([0], dtype=np.int32)
    fm = np.array([0], dtype=np.int32)
    ft = np.array([0], dtype=np.int32)
    ff = np.array([0], dtype=np.int32)
    base = np.array([0], dtype=np.int32)
    code = np.array([0], dtype=np.uint64)

    for slot_arr in slot_arrays:
        dpp = slot_arr["dpp"]
        dcm = slot_arr["dcm"]
        dfm = slot_arr["dfm"]
        dft = slot_arr["dft"]
        dff = slot_arr["dff"]
        dbase = slot_arr["dbase"]
        dcode = slot_arr["dcode"]

        pp2 = np.clip(pp[:, None] + dpp[None, :], 0, MAX_STAT_INDEX).ravel()
        cm2 = np.clip(cm[:, None] + dcm[None, :], 0, MAX_STAT_INDEX).ravel()
        fm2 = np.clip(fm[:, None] + dfm[None, :], 0, MAX_STAT_INDEX).ravel()
        ft2 = np.clip(ft[:, None] + dft[None, :], 0, MAX_STAT_INDEX).ravel()
        ff2 = np.clip(ff[:, None] + dff[None, :], 0, MAX_STAT_INDEX).ravel()
        base2 = (base[:, None].astype(np.int64) + dbase[None, :].astype(np.int64)).ravel()
        code2 = np.bitwise_or(
            code[:, None].astype(np.uint64),
            dcode[None, :].astype(np.uint64),
        ).ravel()

        packed = (
            (pp2.astype(np.int64) << 40)
            | (cm2.astype(np.int64) << 32)
            | (fm2.astype(np.int64) << 24)
            | (ft2.astype(np.int64) << 16)
            | (ff2.astype(np.int64) << 8)
        )
        order = np.lexsort((-base2.astype(np.int64), packed))
        p_s = packed[order]
        unique = np.concatenate([[True], p_s[1:] != p_s[:-1]])

        pp = pp2[order][unique]
        cm = cm2[order][unique]
        fm = fm2[order][unique]
        ft = ft2[order][unique]
        ff = ff2[order][unique]
        base = base2[order][unique].astype(np.int32, copy=False)
        code = code2[order][unique]

    states = _compact_to_dict(pp, cm, fm, ft, ff, base, code)

    keys_4d = len(states)
    pairs_6d = sum(len(fr) for fr in states.values())
    seconds = float(time.perf_counter() - t0)

    frontier_sizes = np.array([len(fr) for fr in states.values()], dtype=np.int32)
    frontier_mean = float(frontier_sizes.mean()) if frontier_sizes.size else 0.0
    frontier_p95 = float(np.percentile(frontier_sizes, 95)) if frontier_sizes.size else 0.0
    frontier_max = int(frontier_sizes.max()) if frontier_sizes.size else 0

    stats = LaneAwareGearDPStatsGPU(
        keys_4d=keys_4d,
        pairs_6d=pairs_6d,
        frontier_mean=frontier_mean,
        frontier_p95=frontier_p95,
        frontier_max=frontier_max,
        seconds=seconds,
    )

    return states, stats
