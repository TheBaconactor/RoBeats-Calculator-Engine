import time
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
import taichi as ti

from gear_optimizer.solver.taichi_gem import runtime as ti_runtime

from .taichi_profile import maybe_print_kernel_profile


_LAST_SIG: Optional[Tuple[int, int, int]] = None


@dataclass(frozen=True)
class GpuRepairResult:
    repaired_mask: "object"  # np.ndarray[int32] shape (S,)
    repaired_offsets: "object"  # np.ndarray[int32] shape (S,6)
    stats: dict


@ti.func
def _xorshift32(x: ti.u32) -> ti.u32:
    x ^= x << 13
    x ^= x >> 17
    x ^= x << 5
    return x


@ti.kernel
def _repair_kernel(
    covered: ti.template(),  # (S,) i32
    totals: ti.template(),  # (S,6) i32
    cand_idx: ti.template(),  # (S,6,C) i32 indices into inv arrays, -1 padded
    cand_count: ti.template(),  # (S,6) i32
    inv_offsets: ti.template(),  # (M,) i32
    inv_gems: ti.template(),  # (M,6) i32
    out_mask: ti.template(),  # (S,) i32
    out_offsets: ti.template(),  # (S,6) i32
    attempts: ti.i32,
    seed_u: ti.u32,
):
    S = totals.shape[0]
    C = cand_idx.shape[2]
    for s in range(S):
        if covered[s] != 0:
            out_mask[s] = 0
            continue

        # Quick reject: any slot has zero candidates -> impossible.
        ok = ti.i32(1)
        for j in ti.static(range(6)):
            if cand_count[s, j] <= 0:
                ok = 0
        if ok == 0:
            out_mask[s] = 0
            continue

        target = ti.Vector.zero(ti.i32, 6)
        for st in ti.static(range(6)):
            target[st] = totals[s, st]

        solved = ti.i32(0)
        chosen = ti.Vector([ti.i32(-1) for _ in range(6)])
        st = seed_u ^ (ti.u32(s) * ti.u32(0x9E3779B9))

        for _t in range(attempts):
            if solved != 0:
                break
            st = _xorshift32(st)
            # Build a random slot order.
            order = ti.Vector([ti.i32(i) for i in range(6)])
            for k in ti.static(range(5, 0, -1)):
                st = _xorshift32(st)
                j = ti.i32(st % ti.u32(k + 1))
                tmp = order[k]
                order[k] = order[j]
                order[j] = tmp

            rem = target
            tmp_choice = ti.Vector([ti.i32(-1) for _ in range(6)])
            fail = ti.i32(0)

            # Choose first 5 slots greedily; solve last by exact match.
            for step in ti.static(range(5)):
                slot = order[step]
                best_idx = ti.i32(-1)
                best_score = ti.i32(-1)
                cnt = cand_count[s, slot]
                st = _xorshift32(st)
                salt = ti.i32(st & ti.u32(0x7FFFFFFF))
                for c in range(C):
                    if c >= cnt:
                        break
                    idx = cand_idx[s, slot, c]
                    if idx < 0:
                        continue
                    g = ti.Vector.zero(ti.i32, 6)
                    for st_i in ti.static(range(6)):
                        g[st_i] = inv_gems[idx, st_i]
                    fits = ti.i32(1)
                    for st_i in ti.static(range(6)):
                        if g[st_i] > rem[st_i]:
                            fits = 0
                    if fits == 0:
                        continue
                    sc = ti.i32(0)
                    for st_i in ti.static(range(6)):
                        sc += g[st_i] * (rem[st_i] + 1)
                    sc += (salt ^ (idx * 1103515245)) & 1023
                    if sc > best_score:
                        best_score = sc
                        best_idx = idx
                if best_idx < 0:
                    fail = 1
                else:
                    tmp_choice[slot] = best_idx
                    for st_i in ti.static(range(6)):
                        rem[st_i] -= inv_gems[best_idx, st_i]

            if fail != 0:
                continue

            last_slot = order[5]
            cnt = cand_count[s, last_slot]
            for c in range(C):
                if c >= cnt:
                    break
                idx = cand_idx[s, last_slot, c]
                if idx < 0:
                    continue
                match = ti.i32(1)
                for st_i in ti.static(range(6)):
                    if inv_gems[idx, st_i] != rem[st_i]:
                        match = 0
                if match != 0:
                    tmp_choice[last_slot] = idx
                    solved = 1
                    break

            if solved != 0:
                chosen = tmp_choice

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

    covered.from_numpy(covered_np)
    totals.from_numpy(totals_np)
    cand_idx.from_numpy(cand_idx_np)
    cand_count.from_numpy(cand_count_np)
    inv_offsets.from_numpy(inv_offsets_np)
    inv_gems.from_numpy(inv_gems_np)

    t0 = time.perf_counter()
    _repair_kernel(
        covered,
        totals,
        cand_idx,
        cand_count,
        inv_offsets,
        inv_gems,
        out_mask,
        out_offsets,
        int(attempts),
        int(seed) if int(seed) != 0 else 1,
    )
    ti.sync()
    dt = time.perf_counter() - t0

    repaired_mask = out_mask.to_numpy()
    repaired_offsets = out_offsets.to_numpy()
    repaired = int((repaired_mask > 0).sum())
    if profile:
        print(f"[InventoryRepair] repaired={repaired} time={dt:.3f}s", flush=True)
    maybe_print_kernel_profile(label="inventory_repair", enabled=bool(profile))

    return GpuRepairResult(
        repaired_mask=repaired_mask,
        repaired_offsets=repaired_offsets,
        stats={"enabled": True, "attempts": int(attempts), "repaired": int(repaired), "time_sec": float(round(dt, 6))},
    )


__all__ = ["GpuRepairResult", "repair_uncovered_with_inventory_gpu"]
