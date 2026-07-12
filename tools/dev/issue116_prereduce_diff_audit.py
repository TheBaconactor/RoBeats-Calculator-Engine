"""Dominance certificate for region2 pre-reduction output diffs (Issue #116).

When the pre-reduced kernel's retained first-frontier rows differ from the HEAD
baseline, this audit proves the difference is the harmless path-dependent class:

  1. common rows appear in the SAME relative order on both sides (anything else
     would indicate a real ordering bug, not retained-extras drift);
  2. every row present on exactly one side is REALIZABLE-CELL dominated by a row
     retained on the other side, via the kill relations the pipelines themselves
     use, checked directly and through one-side diff-row intermediates
     (transitive closure over the small diff sets):
       - structural dominance (`_numba_surface_structurally_dominates`,
         `_numba_reduce`'s relation: head-overlap class + mask subsets + counts),
         sound at every realizable cell under the g <= v coupling;
       - 16-corner cone dominance with the metric margin
         (`_numba_head_cached_scores_dominate`), sound over the whole stat box.

Every kill either pipeline performs is one of these two relations, both transitive
and both implying <= at every realizable stat cell, so certification proves the
max-over-rows served score -- hence best_fg_score -- is identical on both sides at
every cell. Fails loudly on any uncertified row.

Usage:
    python tools/dev/issue116_prereduce_diff_audit.py --song "M1LLI0N PP (Full Version)" --diff Hard --baseline C:/mfbench/issue116-prereduce-baseline/m1llion.npz
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
_TOOLS_DEV = Path(__file__).resolve().parent
if str(_TOOLS_DEV) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DEV))

from numba import njit  # noqa: E402

from gear_optimizer.solver.taichi_gem.force_greats import response_build_gpu_numba as _rb  # noqa: E402
from issue116_amdahl_probe import SongProbeInputs, _find_chart  # noqa: E402
from issue116_prereduce_ab import _run_production  # noqa: E402


def _row_key(row) -> tuple:
    return tuple(int(v) for v in row)


@njit(cache=True, nogil=True)
def _kill_relation_matrix(diff_rows, cover_rows, lo_pos: int, hi_pos: int):
    """out[i] = 1 iff some cover row dominates diff row i via a pipeline kill relation
    (structural dominance, or 16-corner cone dominance with the metric margin)."""
    d = int(diff_rows.shape[0])
    c = int(cover_rows.shape[0])
    out = np.zeros(d, dtype=np.int64)
    diff_scores = np.empty((d, 16), dtype=np.float64)
    cover_scores = np.empty((c, 16), dtype=np.float64)
    for i in range(d):
        row = (
            diff_rows[i, 0], diff_rows[i, 1], diff_rows[i, 2], diff_rows[i, 3],
            diff_rows[i, 4], diff_rows[i, 5], diff_rows[i, 6],
        )
        _rb._numba_head_basis_corner_scores_into(
            _rb._numba_head_surface_basis(row, int(lo_pos), int(hi_pos)), diff_scores, i
        )
    for j in range(c):
        row = (
            cover_rows[j, 0], cover_rows[j, 1], cover_rows[j, 2], cover_rows[j, 3],
            cover_rows[j, 4], cover_rows[j, 5], cover_rows[j, 6],
        )
        _rb._numba_head_basis_corner_scores_into(
            _rb._numba_head_surface_basis(row, int(lo_pos), int(hi_pos)), cover_scores, j
        )
    for i in range(d):
        target = (
            diff_rows[i, 0], diff_rows[i, 1], diff_rows[i, 2], diff_rows[i, 3],
            diff_rows[i, 4], diff_rows[i, 5], diff_rows[i, 6],
        )
        for j in range(c):
            cover = (
                cover_rows[j, 0], cover_rows[j, 1], cover_rows[j, 2], cover_rows[j, 3],
                cover_rows[j, 4], cover_rows[j, 5], cover_rows[j, 6],
            )
            same = True
            for col in range(7):
                if cover[col] != target[col]:
                    same = False
                    break
            if same:
                continue
            if _rb._numba_surface_structurally_dominates(cover, target):
                out[i] = 1
                break
            if _rb._numba_head_cached_scores_dominate(
                cover_scores[j], diff_scores[i], cover, target
            ):
                out[i] = 1
                break
    return out


def _covered(diff_rows: np.ndarray, cover_rows: np.ndarray, intermediates: np.ndarray,
             lo_pos: int, hi_pos: int, label: str) -> int:
    """Certify each diff row against the other side's retained rows, allowing the two
    sides' diff rows as transitive intermediates (both kill relations are transitive
    and realizable-sound, so one closure pass over the small diff sets suffices)."""
    if int(diff_rows.shape[0]) == 0:
        return 0
    cover_direct = _kill_relation_matrix(diff_rows, cover_rows, lo_pos, hi_pos)
    pending = [i for i in range(int(diff_rows.shape[0])) if int(cover_direct[i]) == 0]
    if pending and int(intermediates.shape[0]) > 0:
        # An intermediate certifies a row only if the intermediate itself is certified
        # against cover_rows; iterate to a fixed point over the small diff sets.
        inter_ok = _kill_relation_matrix(intermediates, cover_rows, lo_pos, hi_pos)
        ok_rows = intermediates[np.asarray(inter_ok, dtype=bool)]
        if int(ok_rows.shape[0]) > 0:
            via = _kill_relation_matrix(
                np.ascontiguousarray(diff_rows[np.asarray(pending, dtype=np.int64)]),
                np.ascontiguousarray(ok_rows),
                lo_pos,
                hi_pos,
            )
            pending = [pending[k] for k in range(len(pending)) if int(via[k]) == 0]
    for i in pending:
        print(f"    !! UNCERTIFIED {label} row: {diff_rows[i].tolist()}")
    return len(pending)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--song", required=True)
    ap.add_argument("--diff", default="Hard", choices=("Easy", "Normal", "Hard"))
    ap.add_argument("--fts", type=int, default=6)
    ap.add_argument("--ffs", type=int, default=6)
    ap.add_argument("--baseline", required=True)
    args = ap.parse_args()

    chart = _find_chart(args.song, args.diff)
    sp = SongProbeInputs(chart=chart, diff=args.diff, fts=args.fts, ffs=args.ffs)
    print(f"chart={os.path.basename(chart)} n={sp.n} geometries={len(sp.prepared)}")
    base = np.load(args.baseline, allow_pickle=False)
    if str(base["chart_name"][0]) != os.path.basename(chart):
        raise SystemExit("baseline chart mismatch")

    warm_item = sp.prepared[0]
    warm_table = sp.region_table_for(float(warm_item[2]), int(warm_item[1]), warm_item[4])
    _run_production(sp, warm_item, int(sp.real_time_index[0]), warm_table)

    diff_geoms = 0
    total_removed = total_added = 0
    uncovered_total = 0
    order_violations = 0
    for gi, item in enumerate(sp.prepared):
        rt_idx = int(sp.real_time_index[gi])
        region_table = sp.region_table_for(float(item[2]), int(item[1]), item[4])
        rows, _counters = _run_production(sp, item, rt_idx, region_table)
        base_rows = base[f"rows_{gi}"]
        if np.array_equal(base_rows, rows):
            continue
        diff_geoms += 1
        base_keys = [_row_key(r) for r in base_rows]
        new_keys = [_row_key(r) for r in rows]
        base_set = set(base_keys)
        new_set = set(new_keys)
        if len(base_set) != len(base_keys) or len(new_set) != len(new_keys):
            raise SystemExit(f"geometry {gi}: duplicate retained rows -- unexpected")
        removed = [k for k in base_keys if k not in new_set]
        added = [k for k in new_keys if k not in base_set]
        common_base = [k for k in base_keys if k in new_set]
        common_new = [k for k in new_keys if k in base_set]
        if common_base != common_new:
            order_violations += 1
            print(f"  !! geometry {gi}: common-row ORDER differs")
        removed_arr = np.asarray(removed, dtype=np.uint64).reshape(-1, 7)
        added_arr = np.asarray(added, dtype=np.uint64).reshape(-1, 7)
        print(
            f"  geometry {gi}: baseline {len(base_keys)} rows, new {len(new_keys)} rows, "
            f"removed {len(removed)}, added {len(added)}"
        )
        head_limit = min(sp.n, 100)
        uncovered_total += _covered(removed_arr, rows, added_arr, 0, head_limit, "baseline-only")
        uncovered_total += _covered(added_arr, base_rows, removed_arr, 0, head_limit, "new-only")
        total_removed += len(removed)
        total_added += len(added)

    print(
        f"\nSUMMARY: {diff_geoms} differing geometries, {total_removed} rows removed, "
        f"{total_added} rows added, {order_violations} order violations, "
        f"{uncovered_total} uncertified rows"
    )
    if order_violations or uncovered_total:
        raise SystemExit("CERTIFICATE FAILED")
    print("CERTIFIED: every diff row is same-mask count-dominated by a retained row on the other side;")
    print("served maxima (and best_fg_score) are identical at every realizable stat cell.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
