"""THROWAWAY: validate FG Vulkan first-frontier kernel against the REAL production
(ft,ff) geometry grid for a real song, + measure real frontier-size distribution.

Read-only on production modules. TDR-safe: tiny chunked launches only.

Run:
  python tools/dev/_fg_real_grid_validate.py            # default: small + medium
  python tools/dev/_fg_real_grid_validate.py --scan     # just print note-count scan
"""
import argparse
import importlib.util
import math
import os
import random
import sys
import time

import numpy as np

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from gear_optimizer.core.constants import TOTAL_ROWS  # noqa: E402
from gear_optimizer.data.csv_parser import read_table  # noqa: E402
from gear_optimizer.data.song_io import get_base_calc_song  # noqa: E402
from gear_optimizer.helpers.song_helpers.ref_array_builder import build_ref_arrays_from_stats  # noqa: E402
from gear_optimizer.solver.scoring.fg_policy import extract_fg_song_inputs  # noqa: E402
from gear_optimizer.solver.taichi_gem.force_greats.response_cache_keys import _response_axes  # noqa: E402
from gear_optimizer.solver.timing_envelope import apply_timing_envelope  # noqa: E402

# --- probe + parity oracle (scripts, imported via importlib) ---
_PROBE = os.path.join(REPO, "tools", "dev", "_fg_layer3_probe.py")
_spec = importlib.util.spec_from_file_location("fgprobe", _PROBE)
probe = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(probe)  # this also inits taichi
fgp = probe.fgp  # parity harness module (build_kernel_args / numba_first_frontier)


def build_ref_arrays():
    stats_table = read_table(os.path.join(REPO, "Data", "Gear", "Stats.txt"))
    return build_ref_arrays_from_stats(stats_table, dtype=np.float64)


def load_song(path):
    calc_song = get_base_calc_song(path, {})
    apply_timing_envelope(calc_song)
    return calc_song


_SCAN_CACHE = os.path.join(os.path.dirname(__file__), "_fg_real_grid_scan_cache.tsv")


def scan_note_counts(limit_per_diff=None):
    """Return list of (note_count, path) for all songs, ascending by note_count."""
    if limit_per_diff is None and os.path.isfile(_SCAN_CACHE):
        out = []
        with open(_SCAN_CACHE, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.rstrip("\n")
                if not line:
                    continue
                c, p = line.split("\t", 1)
                if os.path.isfile(p):
                    out.append((int(c), p))
        if out:
            out.sort(key=lambda t: t[0])
            return out
    out = []
    for diff in ("Easy", "Normal", "Hard"):
        folder = os.path.join(REPO, "Data", diff)
        if not os.path.isdir(folder):
            continue
        files = [f for f in os.listdir(folder) if f.lower().endswith(".txt")]
        if limit_per_diff:
            files = files[:limit_per_diff]
        for fn in files:
            path = os.path.join(folder, fn)
            try:
                calc_song = load_song(path)
                si = extract_fg_song_inputs(calc_song)
                out.append((int(si.total_notes), path))
            except Exception as exc:
                print(f"  skip {fn}: {exc}")
    out.sort(key=lambda t: t[0])
    if limit_per_diff is None:
        with open(_SCAN_CACHE, "w", encoding="utf-8") as fh:
            for c, p in out:
                fh.write(f"{c}\t{p}\n")
    return out


def pair_mod_for(n, fill):
    return min(n + 1, n // max(1, int(fill)) + 4)


def axes_report(calc_song, ref_arrays, label):
    si, raw_fill_by_ff, nfb_by_ff, real_time_by_ft = _response_axes(calc_song, ref_arrays)
    n = int(si.total_notes)
    pms = []
    for ff in range(TOTAL_ROWS + 1):
        # production pair_mod uses later_fill[0] = ceil(raw_fever_fill) (k=0 action)
        fill0 = int(math.ceil(float(raw_fill_by_ff[ff])))
        pms.append(pair_mod_for(n, fill0))
    pm_min, pm_max = min(pms), max(pms)
    print(f"\n=== AXES [{label}] n={n} long={si.long_notes} last_t={si.last_note_time:.4f} "
          f"ufgt={si.use_forced_great_timing} ===")
    print(f"  raw_fill_by_ff[0]   = {raw_fill_by_ff[0]:.6f}   raw_fill_by_ff[160] = {raw_fill_by_ff[160]:.6f}")
    print(f"  real_time_by_ft[0]  = {real_time_by_ft[0]:.6f}  real_time_by_ft[160]= {real_time_by_ft[160]:.6f}")
    print(f"  pair_mod (over ff): MIN={pm_min} MAX={pm_max}")
    return si, raw_fill_by_ff, nfb_by_ff, real_time_by_ft, n, pm_min, pm_max


def sample_keys(seed=1234, n_interior=520):
    """4 corners + axis edges + diagonal + random interior. ~400-600 keys."""
    R = TOTAL_ROWS  # 160
    keys = set()
    # corners
    for ft in (0, R):
        for ff in (0, R):
            keys.add((ft, ff))
    # axis edges (every 8 along each border)
    for v in range(0, R + 1, 8):
        keys.add((0, v))
        keys.add((R, v))
        keys.add((v, 0))
        keys.add((v, R))
    # diagonal
    for v in range(0, R + 1, 4):
        keys.add((v, v))
        keys.add((v, R - v))
    # random interior
    rng = random.Random(seed)
    while len([k for k in keys]) < n_interior:
        keys.add((rng.randint(0, R), rng.randint(0, R)))
    return sorted(keys)


def build_args_for_keys(si, raw_fill_by_ff, nfb_by_ff, real_time_by_ft, keys):
    ts = np.ascontiguousarray(np.asarray(si.timestamps, dtype=np.float32).reshape(-1))
    great = np.ascontiguousarray(np.asarray(si.great_candidates, dtype=np.float32).reshape(-1))
    ufgt = bool(si.use_forced_great_timing)
    args = []
    for (ft, ff) in keys:
        a = fgp.build_kernel_args(
            timestamps=ts,
            great_candidate_timestamps=great,
            raw_fever_fill=float(raw_fill_by_ff[ff]),
            non_fever_base=int(nfb_by_ff[ff]),
            real_fever_time=float(real_time_by_ft[ft]),
            use_forced_great_timing=ufgt,
        )
        args.append(a)
    return args, ts, great


def parity_check(label, si, raw_fill_by_ff, nfb_by_ff, real_time_by_ft, n, keys, caps, chunk):
    args, ts, great = build_args_for_keys(si, raw_fill_by_ff, nfb_by_ff, real_time_by_ft, keys)
    t0 = time.perf_counter()
    res = probe.run_kernel(args, n, ts, great, chunk=chunk, caps=caps)
    gpu_ms = (time.perf_counter() - t0) * 1000.0
    fails = []
    branch_a = 0
    def _rowset(arr):
        # order-insensitive: the frontier is consumed as an unordered max-over-set; the
        # bucketed Phase-3 reduction legitimately reorders survivors. Compare as a row multiset.
        if arr.shape[0] == 0:
            return arr.reshape(0, 7)
        return arr[np.lexsort(arr.T[::-1])]

    for i, a in enumerate(args):
        if int(a["first_fill"][0]) >= 100:
            branch_a += 1
        out, se, gs, rt, msf = fgp.numba_first_frontier(a)
        gpu, ctr, ef = res[i]
        # Phase-1 transducer generates a different intermediate count than the old cand-skyline path,
        # so generated_surfaces (ctr[1]) legitimately differs; first-frontier SET + se + rt + msf hold.
        ok = (gpu.shape[0] == out.shape[0] and np.array_equal(_rowset(gpu), _rowset(out))
              and ctr[0] == se and ctr[2] == rt and ctr[3] == msf and ef == 0)
        if not ok:
            fails.append((keys[i], gpu, out, ctr, (se, gs, rt, msf), ef, int(a["first_fill"][0])))
    print(f"\n=== PARITY [{label}] {len(args)-len(fails)}/{len(args)} pass "
          f"(BranchA={branch_a} BranchB={len(args)-branch_a}) gpu={gpu_ms:.0f}ms ===")
    for (ftff, gpu, out, ctr, refctr, ef, ff0) in fails[:8]:
        print(f"  FAIL (ft,ff)={ftff}: gpu_rows={gpu.shape[0]} ref_rows={out.shape[0]} "
              f"ctr_gpu={ctr} ctr_ref={refctr} err={ef} first_fill0={ff0}")
        # show first few rows side by side
        m = min(4, max(gpu.shape[0], out.shape[0]))
        for r in range(m):
            g = gpu[r].tolist() if r < gpu.shape[0] else None
            o = out[r].tolist() if r < out.shape[0] else None
            print(f"      row{r} gpu={g} ref={o}")
    return len(fails), len(args)


def distribution(label, si, raw_fill_by_ff, nfb_by_ff, real_time_by_ft, n, keys, caps, chunk):
    args, ts, great = build_args_for_keys(si, raw_fill_by_ff, nfb_by_ff, real_time_by_ft, keys)
    ff_sizes = []
    skylines = []
    generated = []
    states = []
    errs = 0
    t0 = time.perf_counter()
    res = probe.run_kernel(args, n, ts, great, chunk=chunk, caps=caps)
    gpu_ms = (time.perf_counter() - t0) * 1000.0
    for i in range(len(args)):
        gpu, ctr, ef = res[i]
        if ef != 0:
            errs += 1
        se, gs, rt, msf = ctr
        ff_sizes.append(int(gpu.shape[0]))
        skylines.append(int(msf))
        generated.append(int(gs))
        states.append(int(se))
    ff_sizes = np.asarray(ff_sizes)
    skylines = np.asarray(skylines)
    generated = np.asarray(generated)

    def stat(a):
        return (int(a.min()), int(np.median(a)), int(np.percentile(a, 99)), int(a.max()))

    print(f"\n=== DISTRIBUTION [{label}] {len(args)} keys gpu={gpu_ms:.0f}ms errors={errs} ===")
    print(f"  first_frontier size  min/median/p99/max = {stat(ff_sizes)}")
    print(f"  body_skyline max     min/median/p99/max = {stat(skylines)}")
    print(f"  generated_surfaces   min/median/p99/max = {stat(generated)}")
    return ff_sizes, skylines, generated, errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scan", action="store_true")
    ap.add_argument("--smoke", action="store_true", help="axes + tiny 6-key parity on small song only")
    ap.add_argument("--full", action="store_true", help="full 161x161 grid for distribution")
    args = ap.parse_args()

    ref_arrays = build_ref_arrays()
    print(f"ref_arrays keys: {sorted(ref_arrays.keys())}")
    print(f"  Fever Time len={len(ref_arrays['Fever Time'])} Fever Fill Rate len={len(ref_arrays['Fever Fill Rate'])}")

    print("\nScanning note counts (this parses all charts)...")
    scan = scan_note_counts()
    print(f"  total songs scanned: {len(scan)}")
    print(f"  smallest 5: {[(c, os.path.basename(p)) for c, p in scan[:5]]}")
    mid_idx = len(scan) // 2
    print(f"  median(idx {mid_idx}): {scan[mid_idx][0]} notes -> {os.path.basename(scan[mid_idx][1])}")
    print(f"  largest 5: {[(c, os.path.basename(p)) for c, p in scan[-5:]]}")

    if args.scan:
        return 0

    if args.smoke:
        small = next((p for c, p in scan if c >= 8), scan[0][1])
        calc_song = load_song(small)
        si, raw_fill_by_ff, nfb_by_ff, real_time_by_ft, n, pm_min, pm_max = axes_report(
            calc_song, ref_arrays, "SMOKE/SMALL"
        )
        cap_bt = max(64, pm_max + 16)
        caps = (cap_bt, 512, 8192, 32768, max(8192, (pm_max + 4) * 256))
        keys = [(0, 0), (0, TOTAL_ROWS), (TOTAL_ROWS, 0), (TOTAL_ROWS, TOTAL_ROWS), (80, 80), (40, 120)]
        print(f"  caps={caps} smoke keys={keys}")
        parity_check("SMOKE", si, raw_fill_by_ff, nfb_by_ff, real_time_by_ft, n, keys, caps, chunk=6)
        return 0

    # pick a SMALL real song (smallest note count, but skip degenerate <8 notes) and a MEDIUM one
    small = next((p for c, p in scan if c >= 8), scan[0][1])
    small_n = next((c for c, p in scan if c >= 8), scan[0][0])
    medium = scan[mid_idx][1]
    print(f"\nSMALL  = {os.path.basename(small)} ({small_n} notes)")
    print(f"MEDIUM = {os.path.basename(medium)} ({scan[mid_idx][0]} notes)")

    total_fails = 0
    summary = {}
    for label, path in (("SMALL", small), ("MEDIUM", medium)):
        calc_song = load_song(path)
        si, raw_fill_by_ff, nfb_by_ff, real_time_by_ft, n, pm_min, pm_max = axes_report(
            calc_song, ref_arrays, label
        )
        # caps sized generously off measured pair_mod
        cap_bt = max(64, pm_max + 16)
        cap_head = 512
        cap_ff = 8192
        cap_gen = 32768
        cap_cand = max(8192, (pm_max + 4) * 256)
        caps = (cap_bt, cap_head, cap_ff, cap_gen, cap_cand)
        chunk = 16 if n <= 200 else (8 if n <= 600 else (4 if n <= 1500 else 2))
        print(f"  caps={caps} chunk={chunk}")

        keys = sample_keys(seed=42 if label == "SMALL" else 99)
        f, ntot = parity_check(label, si, raw_fill_by_ff, nfb_by_ff, real_time_by_ft, n, keys, caps, chunk)
        total_fails += f

        # distribution over larger sample (or full grid)
        if args.full:
            dist_keys = [(ft, ff) for ft in range(TOTAL_ROWS + 1) for ff in range(TOTAL_ROWS + 1)]
        else:
            rng = random.Random(7)
            dk = set(keys)
            while len(dk) < 2000:
                dk.add((rng.randint(0, TOTAL_ROWS), rng.randint(0, TOTAL_ROWS)))
            dist_keys = sorted(dk)
        ffs, sky, gen, errs = distribution(
            label, si, raw_fill_by_ff, nfb_by_ff, real_time_by_ft, n, dist_keys, caps, chunk
        )
        summary[label] = dict(
            n=n, pm_min=pm_min, pm_max=pm_max,
            ff_max=int(ffs.max()), sky_max=int(sky.max()), gen_max=int(gen.max()), errs=errs,
        )

    print("\n\n========== SUMMARY ==========")
    for label, s in summary.items():
        print(f"[{label}] n={s['n']} pair_mod={s['pm_min']}..{s['pm_max']} "
              f"ff_max={s['ff_max']} skyline_max={s['sky_max']} gen_max={s['gen_max']} errs={s['errs']}")
    print(f"\nPARITY TOTAL: {'PASS' if total_fails == 0 else f'FAIL ({total_fails} mismatches)'}")
    return 1 if total_fails else 0


if __name__ == "__main__":
    sys.exit(main())
