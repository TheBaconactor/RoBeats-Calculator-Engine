"""A/B byte-equality harness for the region2 same-mask pre-reduction (Issue #116).

Two subcommands over strided real-geometry grids (production prep, JIT warmed):

  dump     run the production first-frontier kernel per geometry and persist the
           exact output rows + counters to an .npz baseline
  compare  re-run the (possibly modified) kernel and require byte-identical rows
           and counters against the baseline; fails loudly on any difference

The baseline must be captured BEFORE editing production code, the compare run
after. Grid, chart, and geometry identity are stored in the baseline and
re-derived on compare, so a drifted grid cannot silently pass.

Usage:
    python tools/dev/issue116_prereduce_ab.py dump --song "M1LLI0N PP (Full Version)" --diff Hard --out C:/mfbench/issue116-prereduce-baseline/m1llion.npz
    python tools/dev/issue116_prereduce_ab.py compare --song "M1LLI0N PP (Full Version)" --diff Hard --baseline C:/mfbench/issue116-prereduce-baseline/m1llion.npz
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
_TOOLS_DEV = Path(__file__).resolve().parent
if str(_TOOLS_DEV) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DEV))

from gear_optimizer.solver.taichi_gem.force_greats import response_build_gpu_numba as _rb  # noqa: E402
from issue116_amdahl_probe import SongProbeInputs, _find_chart  # noqa: E402


def _run_production(sp: SongProbeInputs, item, rt_idx: int, region_table):
    ws = sp.ws
    result = _rb._first_frontier_from_precomputed_end_indices_numba(
        sp.n,
        int(item[5].shape[0]),
        int(item[4].shape[0]),
        float(item[2]),
        item[4],
        item[5],
        item[6],
        item[7],
        item[8],
        item[9],
        item[10],
        sp.ts,
        sp.candidate_high_delta_max,
        sp.perfect_ts,
        sp.great_ts,
        sp.floor_ts,
        sp.great_floor_ts,
        sp.lane_arr,
        sp.prefix_perfect_hit,
        sp.prefix_perfect_valid,
        sp.prefix_late_hit,
        sp.prefix_late_valid,
        sp.timestamp_end_idx,
        sp.perfect_end_idx,
        sp.great_end_idx,
        sp.great_floor_end_idx,
        sp.capped_perfect_edge_e,
        sp.capped_late_edge_e,
        sp.capped_eg_perfect_e,
        sp.capped_eg_late_e,
        float(item[3]),
        int(rt_idx),
        1 if sp.uft else 0,
        int(_rb._HEAD_FILTER_MIN_SURFACES),
        region_table[0],
        region_table[1],
        region_table[2],
        region_table[3],
        region_table[4],
        region_table[5],
        region_table[6],
        region_table[7],
        ws.pair_values,
        ws.pair_stamps,
        ws.pair_touched,
        ws.bit_values,
        ws.bit_stamps,
        ws.branch_a_values,
        ws.branch_a_stamps,
        int(ws.pair_epoch),
        int(ws.bit_epoch),
        int(ws.branch_a_epoch),
    )
    ws.store_epochs(int(result[5]), int(result[6]), int(result[7]))
    rows = np.ascontiguousarray(result[0])
    counters = np.asarray(
        [int(result[1]), int(result[2]), int(result[3]), int(result[4])], dtype=np.int64
    )
    return rows, counters


def _run_grid(song: str, diff: str, fts: int, ffs: int):
    chart = _find_chart(song, diff)
    sp = SongProbeInputs(chart=chart, diff=diff, fts=fts, ffs=ffs)
    print(f"chart={os.path.basename(chart)} n={sp.n} geometries={len(sp.prepared)}")
    warm_item = sp.prepared[0]
    warm_table = sp.region_table_for(float(warm_item[2]), int(warm_item[1]), warm_item[4])
    _run_production(sp, warm_item, int(sp.real_time_index[0]), warm_table)

    rows_by_geom = []
    counters_by_geom = []
    keys = []
    t0 = time.perf_counter()
    for gi, item in enumerate(sp.prepared):
        rt_idx = int(sp.real_time_index[gi])
        region_table = sp.region_table_for(float(item[2]), int(item[1]), item[4])
        rows, counters = _run_production(sp, item, rt_idx, region_table)
        rows_by_geom.append(rows)
        counters_by_geom.append(counters)
        keys.append((float(item[2]), int(item[1]), float(item[3])))
    elapsed = time.perf_counter() - t0
    print(f"kernel total {elapsed:.3f} s over {len(sp.prepared)} geometries")
    return os.path.basename(chart), keys, rows_by_geom, counters_by_geom


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("dump", "compare"))
    ap.add_argument("--song", required=True)
    ap.add_argument("--diff", default="Hard", choices=("Easy", "Normal", "Hard"))
    ap.add_argument("--fts", type=int, default=6)
    ap.add_argument("--ffs", type=int, default=6)
    ap.add_argument("--out", default=None)
    ap.add_argument("--baseline", default=None)
    args = ap.parse_args()

    chart_name, keys, rows_by_geom, counters_by_geom = _run_grid(
        args.song, args.diff, args.fts, args.ffs
    )
    key_arr = np.asarray(keys, dtype=np.float64)

    if args.mode == "dump":
        if not args.out:
            raise SystemExit("dump requires --out")
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"chart_name": np.asarray([chart_name]), "keys": key_arr}
        for gi, (rows, counters) in enumerate(zip(rows_by_geom, counters_by_geom, strict=True)):
            payload[f"rows_{gi}"] = rows
            payload[f"counters_{gi}"] = counters
        np.savez_compressed(out_path, **payload)
        print(f"baseline written: {out_path} ({len(rows_by_geom)} geometries)")
        return 0

    if not args.baseline:
        raise SystemExit("compare requires --baseline")
    base = np.load(args.baseline, allow_pickle=False)
    if str(base["chart_name"][0]) != chart_name:
        raise SystemExit(
            f"baseline chart {base['chart_name'][0]!r} != current chart {chart_name!r}"
        )
    if not np.array_equal(base["keys"], key_arr):
        raise SystemExit("baseline geometry keys differ from the re-derived grid")
    mismatches = 0
    for gi, (rows, counters) in enumerate(zip(rows_by_geom, counters_by_geom, strict=True)):
        base_rows = base[f"rows_{gi}"]
        base_counters = base[f"counters_{gi}"]
        if not np.array_equal(base_rows, rows):
            mismatches += 1
            print(
                f"  !! rows mismatch geometry {gi}: baseline {base_rows.shape} vs {rows.shape}"
            )
        if not np.array_equal(base_counters, counters):
            mismatches += 1
            print(
                f"  !! counters mismatch geometry {gi}: baseline {base_counters.tolist()} "
                f"vs {counters.tolist()}"
            )
    if mismatches:
        raise SystemExit(f"{mismatches} mismatches vs baseline -- NOT byte-identical")
    print(f"BYTE-IDENTICAL: all {len(rows_by_geom)} geometries match the baseline (rows + counters)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
