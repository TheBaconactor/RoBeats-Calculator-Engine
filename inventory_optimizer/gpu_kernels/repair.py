import time
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
import taichi as ti

from gear_optimizer.solver.taichi_gem import runtime as ti_runtime
from gear_optimizer.solver.taichi_gem.kernels import kernels_helpers

from ..taichi_profile import maybe_print_kernel_profile


_LAST_SIG: Optional[Tuple[int, int, int]] = None


@dataclass(frozen=True)
class GpuRepairResult:
    repaired_mask: "object"  # np.ndarray[int32] shape (S,)
    repaired_offsets: "object"  # np.ndarray[int32] shape (S,6)
    stats: dict


@ti.func
def _pack6_i32(a0: ti.i32, a1: ti.i32, a2: ti.i32, a3: ti.i32, a4: ti.i32, a5: ti.i32) -> ti.types.vector(2, ti.i32):
    # Pack 6x 7-bit values (0..127) into two i32s (42 bits total).
    # bits: [a0:7][a1:7][a2:7][a3:7][a4:7][a5:7]
    lo = (a0 & 127) | ((a1 & 127) << 7) | ((a2 & 127) << 14) | ((a3 & 127) << 21) | ((a4 & 15) << 28)
    hi = ((a4 >> 4) & 7) | ((a5 & 127) << 3)
    return ti.Vector([ti.i32(lo), ti.i32(hi)])


@ti.func
def _hash_key(lo: ti.i32, hi: ti.i32, mask: ti.i32) -> ti.i32:
    # 32-bit hash from (lo,hi); `mask` is (H-1) where H is a power of two.
    x = ti.u32(lo) * ti.u32(0x9E3779B1) ^ (ti.u32(hi) * ti.u32(0x85EBCA77))
    x = kernels_helpers._xorshift32(x)
    return ti.i32(x & ti.u32(mask))


@ti.kernel
def _repair_mitm_kernel(
    covered: ti.template(),  # (S,) i32
    totals: ti.template(),  # (S,6) i32
    cand_idx: ti.template(),  # (S,6,C) i32 indices into inv arrays, -1 padded
    cand_count: ti.template(),  # (S,6) i32
    inv_offsets: ti.template(),  # (M,) i32
    inv_gems: ti.template(),  # (M,6) i32
    table_key_lo: ti.template(),  # (S,H) i32
    table_key_hi: ti.template(),  # (S,H) i32
    table_vals: ti.template(),  # (S,H) i32 packed inv idx triplets
    out_mask: ti.template(),  # (S,) i32
    out_offsets: ti.template(),  # (S,6) i32
):
    """
    Exact inventory-only repair via meet-in-the-middle.

    For each uncovered song:
    - Select 3 slots with the smallest candidate counts as side A, remaining 3 as side B.
    - Hash all A triplet sums (in 6D) into a per-song table.
    - Scan B triplets and look up the complement.

    This is deterministic and (within the truncated cand_idx lists) complete.
    """
    S = totals.shape[0]
    C = cand_idx.shape[2]
    H = table_key_lo.shape[1]
    mask = ti.i32(H - 1)
    empty = ti.i32(-1)

    for s in range(S):
        if covered[s] != 0:
            out_mask[s] = 0
            continue

        ok = ti.i32(1)
        for j in ti.static(range(6)):
            if cand_count[s, j] <= 0:
                ok = 0
        if ok == 0:
            out_mask[s] = 0
            for j in ti.static(range(6)):
                out_offsets[s, j] = -1
            continue

        # Sort slots by increasing candidate count (selection sort).
        slots = ti.Vector([ti.i32(0), ti.i32(1), ti.i32(2), ti.i32(3), ti.i32(4), ti.i32(5)])
        for i in ti.static(range(5)):
            best = i
            best_cnt = cand_count[s, slots[i]]
            for j in range(i + 1, 6):
                cnt = cand_count[s, slots[j]]
                if cnt < best_cnt:
                    best = j
                    best_cnt = cnt
            if best != i:
                tmp = slots[i]
                slots[i] = slots[best]
                slots[best] = tmp

        a0 = slots[0]
        a1 = slots[1]
        a2 = slots[2]
        b0 = slots[3]
        b1 = slots[4]
        b2 = slots[5]

        # Clear per-song hash table.
        for h in range(H):
            table_key_lo[s, h] = empty
            table_key_hi[s, h] = empty
            table_vals[s, h] = -1

        # Target totals vector.
        t0 = ti.i32(totals[s, 0])
        t1 = ti.i32(totals[s, 1])
        t2 = ti.i32(totals[s, 2])
        t3 = ti.i32(totals[s, 3])
        t4 = ti.i32(totals[s, 4])
        t5 = ti.i32(totals[s, 5])
        # Insert all A-side triplet sums.
        cnt_a0 = ti.i32(cand_count[s, a0])
        cnt_a1 = ti.i32(cand_count[s, a1])
        cnt_a2 = ti.i32(cand_count[s, a2])
        for i0 in range(C):
            if i0 >= cnt_a0:
                break
            idx0 = ti.i32(cand_idx[s, a0, i0])
            if idx0 < 0:
                continue
            for i1 in range(C):
                if i1 >= cnt_a1:
                    break
                idx1 = ti.i32(cand_idx[s, a1, i1])
                if idx1 < 0:
                    continue
                for i2 in range(C):
                    if i2 >= cnt_a2:
                        break
                    idx2 = ti.i32(cand_idx[s, a2, i2])
                    if idx2 < 0:
                        continue
                    s0 = ti.i32(inv_gems[idx0, 0]) + ti.i32(inv_gems[idx1, 0]) + ti.i32(inv_gems[idx2, 0])
                    s1 = ti.i32(inv_gems[idx0, 1]) + ti.i32(inv_gems[idx1, 1]) + ti.i32(inv_gems[idx2, 1])
                    s2 = ti.i32(inv_gems[idx0, 2]) + ti.i32(inv_gems[idx1, 2]) + ti.i32(inv_gems[idx2, 2])
                    s3 = ti.i32(inv_gems[idx0, 3]) + ti.i32(inv_gems[idx1, 3]) + ti.i32(inv_gems[idx2, 3])
                    s4 = ti.i32(inv_gems[idx0, 4]) + ti.i32(inv_gems[idx1, 4]) + ti.i32(inv_gems[idx2, 4])
                    s5 = ti.i32(inv_gems[idx0, 5]) + ti.i32(inv_gems[idx1, 5]) + ti.i32(inv_gems[idx2, 5])
                    # Quick reject: A sum cannot exceed target in any stat.
                    if s0 > t0 or s1 > t1 or s2 > t2 or s3 > t3 or s4 > t4 or s5 > t5:
                        continue
                    key = _pack6_i32(s0, s1, s2, s3, s4, s5)
                    lo = key[0]
                    hi = key[1]
                    pos = _hash_key(lo, hi, mask)
                    for _probe in range(H):
                        cur_lo = table_key_lo[s, pos]
                        cur_hi = table_key_hi[s, pos]
                        if cur_lo == empty:
                            table_key_lo[s, pos] = lo
                            table_key_hi[s, pos] = hi
                            table_vals[s, pos] = (idx0 & 255) | ((idx1 & 255) << 8) | ((idx2 & 255) << 16)
                            break
                        if cur_lo == lo and cur_hi == hi:
                            break
                        pos = (pos + 1) & mask

        solved = ti.i32(0)
        chosen = ti.Vector([ti.i32(-1) for _ in range(6)])

        cnt_b0 = ti.i32(cand_count[s, b0])
        cnt_b1 = ti.i32(cand_count[s, b1])
        cnt_b2 = ti.i32(cand_count[s, b2])
        for j0 in range(C):
            if solved != 0:
                break
            if j0 >= cnt_b0:
                break
            idx0 = ti.i32(cand_idx[s, b0, j0])
            if idx0 < 0:
                continue
            for j1 in range(C):
                if solved != 0:
                    break
                if j1 >= cnt_b1:
                    break
                idx1 = ti.i32(cand_idx[s, b1, j1])
                if idx1 < 0:
                    continue
                for j2 in range(C):
                    if solved != 0:
                        break
                    if j2 >= cnt_b2:
                        break
                    idx2 = ti.i32(cand_idx[s, b2, j2])
                    if idx2 < 0:
                        continue

                    s0 = ti.i32(inv_gems[idx0, 0]) + ti.i32(inv_gems[idx1, 0]) + ti.i32(inv_gems[idx2, 0])
                    s1 = ti.i32(inv_gems[idx0, 1]) + ti.i32(inv_gems[idx1, 1]) + ti.i32(inv_gems[idx2, 1])
                    s2 = ti.i32(inv_gems[idx0, 2]) + ti.i32(inv_gems[idx1, 2]) + ti.i32(inv_gems[idx2, 2])
                    s3 = ti.i32(inv_gems[idx0, 3]) + ti.i32(inv_gems[idx1, 3]) + ti.i32(inv_gems[idx2, 3])
                    s4 = ti.i32(inv_gems[idx0, 4]) + ti.i32(inv_gems[idx1, 4]) + ti.i32(inv_gems[idx2, 4])
                    s5 = ti.i32(inv_gems[idx0, 5]) + ti.i32(inv_gems[idx1, 5]) + ti.i32(inv_gems[idx2, 5])

                    c0 = t0 - s0
                    c1 = t1 - s1
                    c2 = t2 - s2
                    c3 = t3 - s3
                    c4 = t4 - s4
                    c5 = t5 - s5
                    if c0 < 0 or c1 < 0 or c2 < 0 or c3 < 0 or c4 < 0 or c5 < 0:
                        continue
                    need = _pack6_i32(c0, c1, c2, c3, c4, c5)
                    need_lo = need[0]
                    need_hi = need[1]

                    pos = _hash_key(need_lo, need_hi, mask)
                    for _probe in range(H):
                        cur_lo = table_key_lo[s, pos]
                        if cur_lo == empty:
                            break
                        cur_hi = table_key_hi[s, pos]
                        if cur_lo == need_lo and cur_hi == need_hi:
                            packed = table_vals[s, pos]
                            if packed >= 0:
                                ia0 = ti.i32(packed & 255)
                                ia1 = ti.i32((packed >> 8) & 255)
                                ia2 = ti.i32((packed >> 16) & 255)
                                chosen[a0] = ia0
                                chosen[a1] = ia1
                                chosen[a2] = ia2
                                chosen[b0] = idx0
                                chosen[b1] = idx1
                                chosen[b2] = idx2
                                solved = 1
                            break
                        pos = (pos + 1) & mask

        out_mask[s] = solved
        if solved != 0:
            for j in ti.static(range(6)):
                idx = chosen[j]
                out_offsets[s, j] = inv_offsets[idx] if idx >= 0 else -1
        else:
            for j in ti.static(range(6)):
                out_offsets[s, j] = -1


def repair_uncovered_with_inventory_gpu(
    *,
    covered_np: np.ndarray,
    totals_np: np.ndarray,
    cand_idx_np: np.ndarray,
    cand_count_np: np.ndarray,
    inv_offsets_np: np.ndarray,
    inv_gems_np: np.ndarray,
    attempts: int,
    seed: int,
    profile: bool = False,
) -> GpuRepairResult:
    covered_np = np.asarray(covered_np, dtype=np.int32)
    totals_np = np.asarray(totals_np, dtype=np.int32)
    cand_idx_np = np.asarray(cand_idx_np, dtype=np.int32)
    cand_count_np = np.asarray(cand_count_np, dtype=np.int32)
    inv_offsets_np = np.asarray(inv_offsets_np, dtype=np.int32)
    inv_gems_np = np.asarray(inv_gems_np, dtype=np.int32)

    if covered_np.ndim != 1:
        raise ValueError("covered_np must be (S,).")
    if totals_np.shape != (covered_np.shape[0], 6):
        raise ValueError("totals_np must be (S,6).")
    if cand_count_np.shape != (covered_np.shape[0], 6):
        raise ValueError("cand_count_np must be (S,6).")
    if cand_idx_np.ndim != 3 or cand_idx_np.shape[0] != covered_np.shape[0] or cand_idx_np.shape[1] != 6:
        raise ValueError("cand_idx_np must be (S,6,C).")
    if inv_offsets_np.ndim != 1:
        raise ValueError("inv_offsets_np must be (M,).")
    if inv_gems_np.shape != (inv_offsets_np.shape[0], 6):
        raise ValueError("inv_gems_np must be (M,6).")

    S = int(covered_np.shape[0])
    C = int(cand_idx_np.shape[2])
    M = int(inv_offsets_np.shape[0])
    if S <= 0 or C <= 0:
        raise ValueError("Invalid shapes for repair.")
    if M <= 0:
        return GpuRepairResult(
            repaired_mask=np.zeros((S,), dtype=np.int32),
            repaired_offsets=np.full((S, 6), -1, dtype=np.int32),
            stats={"enabled": True, "attempts": int(attempts), "repaired": 0, "time_sec": 0.0},
        )

    attempts = int(attempts)
    if attempts <= 0:
        raise ValueError("attempts must be positive.")

    sig = (int(S), int(C), int(M))
    global _LAST_SIG
    if _LAST_SIG != sig:
        ti_runtime.reset_taichi(reason="gpu_inventory_repair shape change")
        ti_runtime.init_taichi()
        _LAST_SIG = sig
    else:
        ti_runtime.init_taichi()

    covered = ti.field(dtype=ti.i32, shape=(S,))
    totals = ti.field(dtype=ti.i32, shape=(S, 6))
    cand_idx = ti.field(dtype=ti.i32, shape=(S, 6, C))
    cand_count = ti.field(dtype=ti.i32, shape=(S, 6))
    inv_offsets = ti.field(dtype=ti.i32, shape=(M,))
    inv_gems = ti.field(dtype=ti.i32, shape=(M, 6))
    out_mask = ti.field(dtype=ti.i32, shape=(S,))
    out_offsets = ti.field(dtype=ti.i32, shape=(S, 6))

    # Meet-in-the-middle scratch table.
    # For C<=8, H=2048 is plenty; for C==16, H=16384.
    Cmax = int(C)
    amax = int(Cmax * Cmax * Cmax)
    h = 1
    target = max(256, int(amax) * 4)
    while h < target:
        h <<= 1
    # Bound the table to keep memory predictable; this still works well for C<=16.
    h = int(min(h, 16384))
    if h < 256:
        h = 256
    table_key_lo = ti.field(dtype=ti.i32, shape=(S, h))
    table_key_hi = ti.field(dtype=ti.i32, shape=(S, h))
    table_vals = ti.field(dtype=ti.i32, shape=(S, h))

    covered.from_numpy(covered_np)
    totals.from_numpy(totals_np)
    cand_idx.from_numpy(cand_idx_np)
    cand_count.from_numpy(cand_count_np)
    inv_offsets.from_numpy(inv_offsets_np)
    inv_gems.from_numpy(inv_gems_np)

    t0 = time.perf_counter()
    _repair_mitm_kernel(
        covered,
        totals,
        cand_idx,
        cand_count,
        inv_offsets,
        inv_gems,
        table_key_lo,
        table_key_hi,
        table_vals,
        out_mask,
        out_offsets,
    )
    ti.sync()
    dt = time.perf_counter() - t0

    repaired_mask = out_mask.to_numpy()
    repaired_offsets = out_offsets.to_numpy()
    repaired = int((repaired_mask > 0).sum())
    maybe_print_kernel_profile(label="inventory_repair", enabled=bool(profile))

    return GpuRepairResult(
        repaired_mask=repaired_mask,
        repaired_offsets=repaired_offsets,
        stats={
            "enabled": True,
            "mode": "mitm",
            "attempts": int(attempts),
            "repaired": int(repaired),
            "time_sec": float(round(dt, 6)),
            "cand_limit": int(C),
            "hash_size": int(h),
        },
    )


__all__ = ["GpuRepairResult", "repair_uncovered_with_inventory_gpu"]
