"""Cross-machine AMD-GPU vs CPU optimizer-parity harness (zero_ms Lossless-Exact Replay, Task 4d).

WHY THIS EXISTS
---------------
The zero_ms serving host (macOS / MoltenVK) cannot run native f64 on the GPU, so it re-solves the
forced-greats (FG) and base/meta gem allocations on the CPU (native-f64 numba twins of the GPU
kernels). The offline optimizer / GA, by contrast, runs on f64-capable hardware (the AMD RX 7900
XTX, where Vulkan exposes shaderFloat64). Money-critical claim: the EXACT value the Mac serves
equals what the native AMD optimizer would produce for the same (song, loadout, config).

This script CLOSES THE CROSS-VENDOR LOOP on real hardware. For a sample of randomized
(loadout, config) cases it computes the FG result two ways and asserts BIT-EXACT equality:

  (A) FG via the canonical GPU f64 kernel  `_fg_response_inner_group_kernel`
  (B) FG via the serving CPU exact search   `resolve_fg_response_groups_native_f64`

On the AMD box run with `--arch gpu`: (A) executes on the RX 7900 XTX in native f64, (B) on the CPU,
and equality proves served-FG (Mac CPU) == AMD-native-FG. On the Mac run with `--arch cpu`: the GPU
kernel runs on Taichi's CPU backend, so it is a CPU-vs-CPU smoke (trivially equal) that verifies the
harness wiring without an AMD GPU. Both are reported.

THE BASE/META AXIS
------------------
There is intentionally NO GPU base-combo exhaustive kernel. The base zero_ms re-solve
(`scoring/base_inner_cpu_search.resolve_base_combo_exhaustive`) is EXHAUSTIVE => EXACT BY
CONSTRUCTION, and it is the SAME pure-CPU f64/float32 numba code on every machine (it is not a GPU
kernel and has no vendor-specific path). The offline AMD GA optimizes the perfect_window base
leaderboard, which the zero_ms path REPLAYS; there is no AMD zero_ms base reference to diverge from.
So base exactness rests on the exhaustive-by-construction argument, not on matching an AMD run. The
`--base` axis here therefore checks the property that actually carries the exactness claim and that
must hold identically on both machines: the exhaustive search dominates the production greedy
allocation (`scoring_core.optimize_core_jit`) and is self-consistent when re-scored through the
production scoring path (`fast_calculate_score`) -- the same checks as
`tests/test_base_cpu_search_parity.py`, run here as a portable cross-machine soundness gate.

This harness mirrors (and is interchangeable with) the unit gates `tests/test_fg_cpu_search_parity.py`
and `tests/test_base_cpu_search_parity.py`; its added value is being runnable on the AMD GPU to
exercise path (A) on real f64 silicon. It changes NO production compute.

USAGE
-----
  # On the AMD RX 7900 XTX (the real cross-vendor proof):
  PYTHONPATH=. python tools/db/verify_amd_cpu_parity.py --arch gpu --cases 400

  # On the Mac (CPU-vs-CPU smoke; proves the harness, not the cross-vendor claim):
  PYTHONPATH=. python tools/db/verify_amd_cpu_parity.py --arch cpu --cases 400

  # Axis selection (default: both):
  PYTHONPATH=. python tools/db/verify_amd_cpu_parity.py --arch gpu --fg
  PYTHONPATH=. python tools/db/verify_amd_cpu_parity.py --base

Exit code 0 on full parity, 1 on any mismatch (CI/owner-runnable). CPU-only deps for the base axis;
the FG axis needs Taichi (CPU backend always works; `--arch gpu` needs an f64-capable GPU).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# Color-flag configs exercised on the FG axis: (is_p_pp,is_s_pp,is_p_cm,is_s_cm,is_p_fm,is_s_fm,
# is_p_ov,is_s_ov,is_single_color). Cover pp-allowed/blocked and single/dual color lanes.
_FG_FLAG_CONFIGS = (
    np.array([1, 0, 1, 0, 0, 1, 0, 1, 0], np.int32),  # mixed, pp allowed, dual color
    np.array([0, 0, 1, 0, 0, 1, 1, 0, 0], np.int32),  # pp blocked (no chill in p/s)
    np.array([0, 1, 0, 1, 0, 1, 0, 1, 1], np.int32),  # all on secondary, pp allowed, single color
    np.array([1, 1, 0, 0, 0, 0, 0, 0, 0], np.int32),  # only pp lanes
)

# Base-axis color configs: (is_p_pp,is_s_pp,is_p_cm,is_s_cm,is_p_fm,is_s_fm,is_p_ov,is_s_ov).
_BASE_FLAG_CONFIGS = (
    (1, 0, 1, 0, 0, 1, 0, 1),  # mixed, pp allowed
    (0, 0, 1, 0, 0, 1, 1, 0),  # pp blocked
    (0, 1, 0, 1, 0, 1, 0, 1),  # all on secondary, pp allowed
    (1, 1, 0, 0, 0, 0, 0, 0),  # only pp lanes
    (0, 0, 0, 0, 0, 0, 1, 1),  # only overflow lanes (pp blocked)
)


def _build_fg_groups(G, L, head_len, budget, flags, seed):
    """Build a randomized FG group batch identical in shape to tests/test_fg_cpu_search_parity.py.

    Returns the arrays both the GPU kernel and the CPU search consume. budget==0 exercises the
    gems-fixed replay; budget>0 exercises the lossless-exact re-solve.
    """
    from gear_optimizer.app_async_db import _get_team_buff_ref_arrays_cached
    from gear_optimizer.solver.taichi_gem.force_greats.response_inner_host import (
        _precompute_surface_head_coeffs,
    )

    ra = _get_team_buff_ref_arrays_cached()
    pp = np.ascontiguousarray(np.asarray(ra["Perfect Points"], np.float64))
    cm = np.ascontiguousarray(np.asarray(ra["Combo Multiplier"], np.float64))
    fm = np.ascontiguousarray(np.asarray(ra["Fever Multiplier"], np.float64))
    rng = np.random.default_rng(seed)
    rm = np.zeros((G, 8), np.int32)
    for g in range(G):
        rm[g] = [
            budget,
            int(rng.integers(0, 120)),
            int(rng.integers(0, 120)),
            int(rng.integers(0, 120)),
            int(rng.integers(0, 300)),
            int(rng.integers(0, 300)),
            head_len,
            int(rng.integers(head_len + 1, 600)),
        ]
    lengths = np.full(G, L, np.int32)
    offsets = (np.arange(G) * L).astype(np.int32)
    R = G * L
    sw = np.zeros((R, 8), np.uint32)
    sc = np.zeros((R, 3), np.int32)
    wmask = [
        (
            np.uint32((1 << max(0, min(32, head_len - 32 * w))) - 1)
            if max(0, min(32, head_len - 32 * w)) < 32
            else np.uint32(0xFFFFFFFF)
        )
        for w in range(4)
    ]
    for r in range(R):
        bt = int(rm[r // L, 7])
        for w in range(4):
            sw[r, w] = np.uint32(rng.integers(0, 1 << 32, dtype=np.uint64)) & wmask[w]
            sw[r, 4 + w] = np.uint32(rng.integers(0, 1 << 32, dtype=np.uint64)) & wmask[w]
        bf = int(rng.integers(0, bt + 1))
        bg = int(rng.integers(0, bt + 1))
        sc[r] = [bf, bg, int(rng.integers(0, min(bf, bg) + 1))]
    shc = np.ascontiguousarray(_precompute_surface_head_coeffs(sw, head_len=head_len))
    allow_pp = int(flags[0] != 0 or flags[1] != 0)
    return dict(
        G=G,
        rm=rm,
        lengths=lengths,
        offsets=offsets,
        sw=sw,
        sc=sc,
        shc=shc,
        flags=np.ascontiguousarray(flags),
        allow_pp=allow_pp,
        pp=pp,
        cm=cm,
        fm=fm,
    )


def verify_fg(arch: str, cases: int, group_size: int, seed: int) -> tuple[int, int]:
    """FG cross-vendor axis. Returns (n_groups_checked, n_group_mismatches).

    (A) canonical f64 GPU kernel `_fg_response_inner_group_kernel` (on `arch`)
    (B) serving CPU exact search `resolve_fg_response_groups_native_f64`
    Asserts bit-exact across all 11 output columns per group.
    """
    import taichi as ti

    from gear_optimizer.solver.taichi_gem.force_greats.response_inner_kernels import (
        _fg_response_inner_group_kernel,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_inner_cpu_search import (
        resolve_fg_response_groups_native_f64,
    )

    ti_arch = ti.gpu if arch == "gpu" else ti.cpu
    ti.init(arch=ti_arch)
    print(f"  [FG] Taichi initialized: requested arch={arch!r} (ti.gpu runs native f64 on AMD)")

    # Spread `cases` groups across flag configs and a few (head_len, budget, group_len) shapes.
    shapes = [
        (2, 64, 0),   # replay (budget 0), short head
        (2, 64, 3),   # lossless re-solve (budget 3)
        (3, 100, 5),  # max head, larger budget + group
        (1, 32, 8),   # single surface, large budget
    ]
    rng = np.random.default_rng(seed)
    total_groups = 0
    total_bad = 0
    case = 0
    while total_groups < cases:
        flags = _FG_FLAG_CONFIGS[case % len(_FG_FLAG_CONFIGS)]
        L, head_len, budget = shapes[case % len(shapes)]
        G = min(group_size, cases - total_groups)
        if G <= 0:
            G = group_size
        inp = _build_fg_groups(G, L, head_len, budget, flags, seed=int(rng.integers(1, 2**31)))

        out_ref = np.zeros((inp["G"], 11), np.int32)
        _fg_response_inner_group_kernel(
            int(inp["G"]),
            inp["sw"],
            inp["sc"],
            inp["shc"],
            inp["offsets"],
            inp["lengths"],
            inp["rm"],
            inp["flags"],
            inp["pp"],
            inp["cm"],
            inp["fm"],
            out_ref,
            bool(inp["allow_pp"]),
        )
        ti.sync()

        out_new = resolve_fg_response_groups_native_f64(
            inp["offsets"].astype(np.int64),
            inp["lengths"].astype(np.int64),
            inp["rm"],
            inp["sw"],
            inp["sc"],
            inp["flags"],
            inp["pp"],
            inp["cm"],
            inp["fm"],
            int(inp["allow_pp"]),
        ).astype(np.int32)

        bad_mask = np.any(out_ref != out_new, axis=1)
        bad = int(np.sum(bad_mask))
        total_bad += bad
        total_groups += int(inp["G"])
        if bad:
            idx = int(np.flatnonzero(bad_mask)[0])
            print(
                f"  [FG] MISMATCH config={tuple(int(x) for x in flags)} "
                f"budget={budget} head_len={head_len}: {bad}/{inp['G']} groups; "
                f"first GPU={out_ref[idx].tolist()} CPU={out_new[idx].tolist()}"
            )
        case += 1
    status = "EXACT" if total_bad == 0 else "MISMATCH"
    print(f"  [FG] {status}: {total_groups} groups checked, {total_bad} mismatches "
          f"(GPU f64 kernel vs CPU exact search, all 11 columns)")
    return total_groups, total_bad


def _greedy_base(budget, cur_pp, cur_cm, cur_fm, cur_p, cur_s, flags, ref_pp, ref_cm, ref_fm,
                 head, bf, bn):
    from gear_optimizer.core.constants import (
        ELEMENTAL_GEM_SCALE,
        GEM_SCALE_FEVER,
        GEM_SCALE_NORMAL,
        GEM_STAT_TO_ELEMENT_SCALE,
        MAX_STAT_INDEX,
        TOTAL_ROWS,
    )
    from gear_optimizer.solver.scoring_core import (
        fast_calculate_score,
        lookup_reference_py,
        optimize_core_jit,
    )

    (f_pp, f_cm, f_fm, f_p, f_s, _g_pp, _g_cm, _g_fm, _g_ov) = optimize_core_jit(
        budget, cur_pp, cur_cm, cur_fm, cur_p, cur_s,
        flags[0], flags[1], flags[2], flags[3], flags[4], flags[5], flags[6], flags[7],
        ref_pp, ref_cm, ref_fm, head, bf, bn,
        GEM_SCALE_NORMAL, GEM_SCALE_FEVER, GEM_STAT_TO_ELEMENT_SCALE, ELEMENTAL_GEM_SCALE,
        TOTAL_ROWS, MAX_STAT_INDEX,
    )
    base = (f_p * 2) + f_s + lookup_reference_py(f_pp, ref_pp, TOTAL_ROWS)
    c_mul = lookup_reference_py(f_cm, ref_cm, TOTAL_ROWS)
    f_mul = lookup_reference_py(f_fm, ref_fm, TOTAL_ROWS)
    return int(fast_calculate_score(base, c_mul, f_mul, head, bf, bn))


def _rescore_base(out, ref_pp, ref_cm, ref_fm, head, bf, bn):
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.solver.scoring_core import fast_calculate_score, lookup_reference_py

    _score, _g_pp, _g_cm, _g_fm, _g_ov, f_pp, f_cm, f_fm, f_p, f_s = out
    base = (f_p * 2) + f_s + lookup_reference_py(f_pp, ref_pp, TOTAL_ROWS)
    c_mul = lookup_reference_py(f_cm, ref_cm, TOTAL_ROWS)
    f_mul = lookup_reference_py(f_fm, ref_fm, TOTAL_ROWS)
    return int(fast_calculate_score(base, c_mul, f_mul, head, bf, bn))


def verify_base(cases: int, seed: int) -> tuple[int, int]:
    """Base/meta axis: exhaustive >= greedy and self-consistent (vendor-independent CPU code).

    Returns (n_cases, n_violations). This is the property that carries the base exactness claim;
    it runs identically on Mac and AMD (the exhaustive search is pure-CPU numba, no GPU kernel).
    """
    from gear_optimizer.app_async_db import _get_team_buff_ref_arrays_cached
    from gear_optimizer.solver.scoring.base_inner_cpu_search import resolve_base_combo_exhaustive

    ra = _get_team_buff_ref_arrays_cached()
    ref_pp = np.ascontiguousarray(np.asarray(ra["Perfect Points"], np.float32))
    ref_cm = np.ascontiguousarray(np.asarray(ra["Combo Multiplier"], np.float32))
    ref_fm = np.ascontiguousarray(np.asarray(ra["Fever Multiplier"], np.float32))

    rng = np.random.default_rng(seed)
    n_cases = 0
    n_violations = 0
    n_strictly_better = 0
    per_config = max(1, cases // len(_BASE_FLAG_CONFIGS))
    for flags in _BASE_FLAG_CONFIGS:
        for _ in range(per_config):
            budget = int(rng.integers(0, 91))
            cur_pp = int(rng.integers(0, 170))
            cur_cm = int(rng.integers(0, 170))
            cur_fm = int(rng.integers(0, 170))
            cur_p = int(rng.integers(0, 400))
            cur_s = int(rng.integers(0, 400))
            head_len = int(rng.integers(0, 101))
            head = (rng.integers(0, 2, size=head_len) > 0).astype(np.bool_)
            bf = int(rng.integers(0, 400))
            bn = int(rng.integers(0, 400))

            g_score = _greedy_base(budget, cur_pp, cur_cm, cur_fm, cur_p, cur_s, flags,
                                   ref_pp, ref_cm, ref_fm, head, bf, bn)
            out = resolve_base_combo_exhaustive(
                budget, cur_pp, cur_cm, cur_fm, cur_p, cur_s,
                flags[0], flags[1], flags[2], flags[3], flags[4], flags[5], flags[6], flags[7],
                ref_pp, ref_cm, ref_fm, head, bf, bn,
            )
            e_score = int(out[0])
            n_cases += 1
            if e_score < g_score:
                n_violations += 1
                print(f"  [base] DOMINANCE VIOLATION exhaustive {e_score} < greedy {g_score} "
                      f"flags={flags} budget={budget}")
            if e_score != _rescore_base(out, ref_pp, ref_cm, ref_fm, head, bf, bn):
                n_violations += 1
                print(f"  [base] SELF-CONSISTENCY VIOLATION score {e_score} != re-score flags={flags}")
            if int(out[1]) + int(out[2]) + int(out[3]) + int(out[4]) != budget:
                n_violations += 1
                print(f"  [base] BUDGET VIOLATION gem counts != budget flags={flags}")
            if e_score > g_score:
                n_strictly_better += 1
    status = "SOUND" if n_violations == 0 else "VIOLATIONS"
    print(f"  [base] {status}: {n_cases} cases, {n_violations} violations; exhaustive strictly "
          f"beat greedy in {n_strictly_better} (exhaustive => exact by construction, pure-CPU; "
          f"same code on Mac and AMD)")
    return n_cases, n_violations


def main() -> int:
    p = argparse.ArgumentParser(description="AMD-GPU vs CPU optimizer-parity harness (Task 4d).")
    p.add_argument("--arch", choices=("cpu", "gpu"), default="cpu",
                   help="Taichi arch for the FG GPU kernel. 'gpu' on the AMD RX 7900 XTX runs it in "
                        "native f64 (the real cross-vendor proof); 'cpu' is the Mac smoke. Default cpu.")
    p.add_argument("--cases", type=int, default=400, help="Approx number of FG groups / base cases.")
    p.add_argument("--group-size", type=int, default=200, help="FG groups per kernel dispatch.")
    p.add_argument("--seed", type=int, default=20260621, help="RNG seed (deterministic).")
    p.add_argument("--fg", action="store_true", help="Run only the FG cross-vendor axis.")
    p.add_argument("--base", action="store_true", help="Run only the base soundness axis.")
    args = p.parse_args()

    run_fg = args.fg or not args.base
    run_base = args.base or not args.fg

    print(f"AMD/CPU optimizer-parity harness  arch={args.arch}  cases={args.cases}  seed={args.seed}")
    print("  (FG: GPU f64 kernel vs CPU exact search -- bit-exact required.")
    print("   base: exhaustive vs greedy soundness -- exact by construction, vendor-independent.)")

    total_bad = 0
    if run_fg:
        print("\n[axis: FG forced-greats response inner search]")
        _n, bad = verify_fg(args.arch, args.cases, args.group_size, args.seed)
        total_bad += bad
    if run_base:
        print("\n[axis: base/meta exhaustive inner search]")
        _n, viol = verify_base(args.cases, args.seed)
        total_bad += viol

    print()
    if total_bad == 0:
        print("RESULT: PARITY HOLDS. Served EXACT values match the native optimizer path.")
        if args.arch == "cpu" and run_fg:
            print("  NOTE: --arch cpu is a CPU-vs-CPU smoke. Re-run with --arch gpu on the AMD "
                  "RX 7900 XTX to exercise the GPU f64 kernel on real silicon (the cross-vendor proof).")
        return 0
    print(f"RESULT: PARITY FAILED -- {total_bad} mismatch(es)/violation(s). Investigate before serving.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
