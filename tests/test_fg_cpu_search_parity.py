"""Parity gate: the CPU native-f64 FG gem-search must be bit-for-bit identical to the canonical
f64 GPU kernel (`_fg_response_inner_group_kernel`) run on the Taichi CPU backend. Covers the
replay (budget=0) and the lossless-exact re-solve (budget=3). Money-critical: a mismatch here
means a wrong served score, so this is release-blocking. CPU-only (no GPU)."""
import numpy as np


def _build(G, L, head_len, budget, seed):
    from gear_optimizer.app_async_db import _get_team_buff_ref_arrays_cached
    from gear_optimizer.solver.taichi_gem.force_greats.response_inner_host import _precompute_surface_head_coeffs
    ra = _get_team_buff_ref_arrays_cached()
    pp = np.ascontiguousarray(np.asarray(ra["Perfect Points"], np.float64))
    cm = np.ascontiguousarray(np.asarray(ra["Combo Multiplier"], np.float64))
    fm = np.ascontiguousarray(np.asarray(ra["Fever Multiplier"], np.float64))
    rng = np.random.default_rng(seed)
    rm = np.zeros((G, 8), np.int32)
    for g in range(G):
        rm[g] = [budget, int(rng.integers(0, 120)), int(rng.integers(0, 120)), int(rng.integers(0, 120)),
                 int(rng.integers(0, 300)), int(rng.integers(0, 300)), head_len, int(rng.integers(head_len + 1, 600))]
    lengths = np.full(G, L, np.int32)
    offsets = (np.arange(G) * L).astype(np.int32)
    R = G * L
    sw = np.zeros((R, 8), np.uint32)
    sc = np.zeros((R, 3), np.int32)
    wmask = [(np.uint32((1 << max(0, min(32, head_len - 32 * w))) - 1) if max(0, min(32, head_len - 32 * w)) < 32
              else np.uint32(0xFFFFFFFF)) for w in range(4)]
    for r in range(R):
        bt = int(rm[r // L, 7])
        for w in range(4):
            sw[r, w] = np.uint32(rng.integers(0, 1 << 32, dtype=np.uint64)) & wmask[w]
            sw[r, 4 + w] = np.uint32(rng.integers(0, 1 << 32, dtype=np.uint64)) & wmask[w]
        bf = int(rng.integers(0, bt + 1)); bg = int(rng.integers(0, bt + 1))
        sc[r] = [bf, bg, int(rng.integers(0, min(bf, bg) + 1))]
    shc = np.ascontiguousarray(_precompute_surface_head_coeffs(sw, head_len=head_len))
    flags = np.array([1, 0, 1, 0, 0, 1, 0, 1, 0], np.int32)
    allow_pp = int(flags[0] != 0 or flags[1] != 0)
    return dict(G=G, rm=rm, lengths=lengths, offsets=offsets, sw=sw, sc=sc, shc=shc,
                flags=flags, allow_pp=allow_pp, pp=pp, cm=cm, fm=fm)


def test_cpu_search_matches_canonical_f64_kernel():
    import taichi as ti
    from gear_optimizer.solver.taichi_gem.force_greats.response_inner_kernels import _fg_response_inner_group_kernel
    from gear_optimizer.solver.taichi_gem.force_greats.response_inner_cpu_search import (
        resolve_fg_response_groups_native_f64,
    )
    for budget in (0, 3):
        inp = _build(G=300, L=2, head_len=64, budget=budget, seed=budget + 1)
        ti.init(arch=ti.cpu)
        out_ref = np.zeros((inp["G"], 11), np.int32)
        _fg_response_inner_group_kernel(
            int(inp["G"]), inp["sw"], inp["sc"], inp["shc"], inp["offsets"], inp["lengths"],
            inp["rm"], inp["flags"], inp["pp"], inp["cm"], inp["fm"], out_ref, bool(inp["allow_pp"]))
        ti.sync()
        out_new = resolve_fg_response_groups_native_f64(
            inp["offsets"].astype(np.int64), inp["lengths"].astype(np.int64), inp["rm"],
            inp["sw"], inp["sc"], inp["flags"], inp["pp"], inp["cm"], inp["fm"], int(inp["allow_pp"]))
        bad = int(np.sum(np.any(out_ref != out_new.astype(np.int32), axis=1)))
        assert bad == 0, f"budget={budget}: {bad}/{inp['G']} group mismatches"
