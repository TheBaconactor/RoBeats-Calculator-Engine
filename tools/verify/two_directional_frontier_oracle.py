"""Two-directional FG frontier oracle on tiny charts (input-engine ground truth).

Enumerates PHYSICAL press schedules (per-note band-extreme press times) on synthetic tiny charts,
replays every schedule through the faithful engine simulator (``tools/verify/game_sim.py`` --
earliest-hittable-first matching, +200ms despawn, frame-integrated fever, exact-time judging), and
compares the achieved full-combo P/G surfaces against the production FG response frontier built
for the SAME chart and the SIM-DERIVED fever geometry.

Directions:

* UNDER-report: a reachable surface no production surface structurally dominates -- the frontier
  is missing a legal play (the branch's core defect class).
* OVER-report: a production surface that no schedule achieves exactly. If some reachable surface
  structurally dominates it the claim is score-harmless (it can never uniquely win a cell) and is
  reported as ``dominated_only``; otherwise it is a HARD over-report (a phantom strictly better
  than everything achievable somewhere in stat space).

Independence: press candidates come from the simulator's own judgment edges
(``game_sim._JUDGE_EDGES_TAP``), fever membership from ``RegisteredHit.fever``, and the dominance
relation is the semantic structural one -- no production placement/enumeration primitive is
reused, so this oracle cannot inherit a producer bug (the circularity the 2026-07-07 audit flagged
in the contiguous-run oracle).

Scope (v1): tap-only charts, full-combo P/G universe (runs with any okay/miss/whiff are filtered
out -- those judgments leave the FG product's placement space). Holds/tails are a documented
follow-up. Band extremes per note (6 candidates) cover every judgment-band choice and, through
the cross-product, every hit-order inversion those bands allow; interior offsets only interpolate
fever ends between the extremes, so maximal surfaces are captured.

Usage:
    python tools/verify/two_directional_frontier_oracle.py --charts 20 --max-notes 6 --seed 42
    python tools/verify/two_directional_frontier_oracle.py --directed   # curated witness shapes
"""

from __future__ import annotations

import argparse
import itertools
import random
import sys
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))
_TOOLS = Path(__file__).resolve().parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from game_sim import NoteChart, Press, simulate  # noqa: E402

# Per-note press-time candidates (ms relative to chart time), tap bands from _JUDGE_EDGES_TAP
# (430, 190, 40, -20, -95, -235), strict-> comparators (late edge inclusive, early exclusive):
#   Perfect (-20, +40], Great early (-95, -20], Great late (+40, +190].
_TAP_CANDIDATE_DELTAS_MS = (-94.0, -21.0, -19.0, 40.0, 41.0, 190.0)

# Frontier input arrays (seconds), matching the same judgment edges the production tests use.
_PERFECT_CANDIDATE_S = 0.040
_GREAT_CANDIDATE_S = 0.190
_PERFECT_FLOOR_S = -0.019
_GREAT_FLOOR_S = -0.094


def _surface_key_from_sim(result, n: int) -> tuple[int, int] | None:
    """(fever_mask, great_mask) for a legal full-combo P/G run, else None."""
    tally = result.tally
    if int(tally.get("miss", 0)) or int(tally.get("okay", 0)):
        return None
    if int(result.max_combo) != int(n):
        return None
    notes = [h for h in result.registered if h.kind == "note" and not h.is_tail]
    if len(notes) != int(n):
        return None
    if any(h.kind != "note" for h in result.registered):
        return None
    fever = 0
    great = 0
    for h in notes:
        if bool(h.fever):
            fever |= 1 << int(h.note_index)
        if h.result == "great":
            great |= 1 << int(h.note_index)
        elif h.result != "perfect":
            return None
    return fever, great


def _structurally_dominates(left: tuple[int, int], right: tuple[int, int]) -> bool:
    """left >= right at EVERY stat cell, for any NONDECREASING combo ramp and any real stats
    (fever multiplier >= 1, Perfect >= Great).

    Requires fever superset, then greedily matches each left Great to a distinct right Great at a
    position >= its own whose fever status is no better (a left non-fever Great may match a right
    fever Great -- smaller loss -- but not vice versa). Every unmatched right Great is a pure
    extra loss on the right. Each matched pair is a pointwise per-note score gain for the left:
    same-or-earlier ramp weight, same-or-smaller fever amplification of the Perfect-Great gap."""
    lf, lg = left
    rf, rg = right
    if (rf & ~lf) != 0:
        return False
    if lg == rg:
        return True
    left_greats = [(pos, bool((lf >> pos) & 1)) for pos in range(lg.bit_length()) if (lg >> pos) & 1]
    right_greats = [(pos, bool((rf >> pos) & 1)) for pos in range(rg.bit_length()) if (rg >> pos) & 1]
    if len(left_greats) > len(right_greats):
        return False
    used = [False] * len(right_greats)
    for lpos, lfever in left_greats:
        matched = False
        for j, (rpos, rfever) in enumerate(right_greats):
            if used[j] or rpos < lpos:
                continue
            if lfever and not rfever:
                continue
            used[j] = True
            matched = True
            break
        if not matched:
            return False
    return True


# The engine polls inputs per render frame and removes despawned notes BEFORE processing that
# frame's presses, so at 60fps the last ~1/60s of the +190 late window can be unmatchable
# depending on the note's frame phase. The production frontier follows the leaderboard
# convention (server event-time replay / high-fps client) where the full +190 edge is usable,
# so the oracle simulates a 240fps client (4ms frames) -- fever decay stays continuous either
# way (sub-frame ticks), only the poll granularity changes.
_ORACLE_FRAME_DT_MS = 1000.0 / 240.0


def enumerate_reachable_surfaces(
    timestamps_ms: list[float],
    lanes: list[int],
    statsdict: dict,
    config: dict,
) -> tuple[set[tuple[int, int]], float, float]:
    """All (fever_mask, great_mask) surfaces achievable by band-extreme press schedules."""
    n = len(timestamps_ms)
    chart = NoteChart(timestamps_ms=list(timestamps_ms), lanes=list(lanes), note_types=[1] * n)
    baseline = simulate(
        chart, statsdict, [], [Press(lanes[i], timestamps_ms[i]) for i in range(n)], config,
        frame_dt_ms=_ORACLE_FRAME_DT_MS,
    )
    denom = float(baseline.fever_fill_denom)
    rt = float(baseline.fever_time_sec)
    reachable: set[tuple[int, int]] = set()
    for deltas in itertools.product(_TAP_CANDIDATE_DELTAS_MS, repeat=n):
        presses = sorted(
            (Press(lanes[i], timestamps_ms[i] + deltas[i]) for i in range(n)),
            key=lambda p: p.time_ms,
        )
        result = simulate(chart, statsdict, [], presses, config, frame_dt_ms=_ORACLE_FRAME_DT_MS)
        key = _surface_key_from_sim(result, n)
        if key is not None:
            reachable.add(key)
    return reachable, denom, rt


def production_surfaces(
    timestamps_ms: list[float],
    lanes: list[int],
    denom: float,
    rt: float,
) -> set[tuple[int, int]]:
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_batch import (
        build_force_greats_response_first_frontiers_gpu_batch,
    )

    ts = np.asarray([t / 1000.0 for t in timestamps_ms], dtype=np.float32)
    n = int(ts.shape[0])
    frontier = build_force_greats_response_first_frontiers_gpu_batch(
        timestamps=ts,
        perfect_candidate_timestamps=ts + np.float32(_PERFECT_CANDIDATE_S),
        great_candidate_timestamps=ts + np.float32(_GREAT_CANDIDATE_S),
        perfect_floor_timestamps=ts + np.float32(_PERFECT_FLOOR_S),
        great_floor_timestamps=ts + np.float32(_GREAT_FLOOR_S),
        lanes=np.asarray(lanes, dtype=np.int32),
        geometries=((float(denom), int(n), float(rt)),),
        use_forced_great_timing=True,
    )[0]
    out: set[tuple[int, int]] = set()
    for s in frontier.first_frontier:
        fever = int(s.fever0) | (int(s.fever1) << 32)
        great = int(s.great0) | (int(s.great1) << 32)
        out.add((fever, great))
    return out


def check_chart(
    timestamps_ms: list[float],
    lanes: list[int],
    statsdict: dict | None = None,
    label: str = "",
) -> dict:
    n = len(timestamps_ms)
    stats = dict(statsdict or {})
    config = {"hitCount": n, "hitObjectsCount": n, "lastNoteTimeSec": (max(timestamps_ms) + 2000.0) / 1000.0}
    reachable, denom, rt = enumerate_reachable_surfaces(timestamps_ms, lanes, stats, config)
    produced = production_surfaces(timestamps_ms, lanes, denom, rt)

    under_structural = [
        r for r in sorted(reachable)
        if not any(_structurally_dominates(p, r) for p in produced)
    ]
    # Score refinement: a structurally-uncovered surface only matters if it BEATS the whole
    # produced set at some stat cell (flat-ramp exact on tiny charts).
    under = [
        (r, margin)
        for r in under_structural
        if (margin := _witness_wins_a_cell(r, produced, n)) > 1e-9
    ]
    over_hard: list[tuple[int, int]] = []
    over_dominated: list[tuple[int, int]] = []
    for p in sorted(produced):
        if p in reachable:
            continue
        if any(_structurally_dominates(r, p) for r in reachable):
            over_dominated.append(p)
        else:
            over_hard.append(p)
    return {
        "label": label,
        "n": n,
        "denom": denom,
        "rt": rt,
        "reachable": len(reachable),
        "produced": len(produced),
        "under": under,
        "under_structural": len(under_structural),
        "over_hard": over_hard,
        "over_dominated": over_dominated,
    }


def _cell_score(surface: tuple[int, int], n: int, perfect: float, great: float, fever: float) -> float:
    """Flat-ramp cell score (exact for tiny charts: full combo stays under the first combo
    threshold, so the ramp is constant and only the four counts matter)."""
    f, g = surface
    total = 0.0
    for i in range(n):
        base = great if (g >> i) & 1 else perfect
        total += base * (fever if (f >> i) & 1 else 1.0)
    return total


_SCORE_GRID = tuple(
    (450.0, great, fever)
    for great in (150.0, 225.0, 300.0)
    for fever in (1.0, 3.0, 4.75, 5.25)
)


def _witness_wins_a_cell(witness: tuple[int, int], produced: set[tuple[int, int]], n: int) -> float:
    """Max score margin (over the stat grid) by which the witness beats EVERY produced surface;
    <= 0 means the produced set covers it score-wise everywhere despite structural incomparability."""
    best = float("-inf")
    for perfect, great, fever in _SCORE_GRID:
        w = _cell_score(witness, n, perfect, great, fever)
        p = max(_cell_score(s, n, perfect, great, fever) for s in produced) if produced else 0.0
        best = max(best, w - p)
    return best


def _mask_str(mask: int, n: int) -> str:
    return "".join("1" if (mask >> i) & 1 else "." for i in range(n))


def _report(res: dict) -> bool:
    ok = not res["under"] and not res["over_hard"]
    status = "OK " if ok else "FAIL"
    print(
        f"[{status}] {res['label']}: n={res['n']} denom={res['denom']:.4f} rt={res['rt']:.3f} "
        f"reachable={res['reachable']} produced={res['produced']} "
        f"under={len(res['under'])} (structural {res['under_structural']}) "
        f"over_hard={len(res['over_hard'])} over_dominated={len(res['over_dominated'])}"
    )
    for (fever, great), margin in res["under"][:6]:
        print(f"    under: F={_mask_str(fever, res['n'])} G={_mask_str(great, res['n'])} wins_by={margin:.1f}")
    for fever, great in res["over_hard"][:6]:
        print(f"    over_hard: F={_mask_str(fever, res['n'])} G={_mask_str(great, res['n'])}")
    return ok


def _random_chart(rng: random.Random, max_notes: int) -> tuple[list[float], list[int], str]:
    n = rng.randint(4, max_notes)
    lane_count = rng.choice((1, 2, 4))
    ts: list[float] = [0.0]
    for _ in range(n - 1):
        # step 0 = a chord slot (only meaningful with >1 lane; capped by free lanes below)
        step = rng.choice((0.0, 120.0, 240.0, 300.0, 450.0) if lane_count > 1 else (120.0, 240.0, 300.0, 450.0))
        ts.append(round(ts[-1] + step, 1))
    lanes: list[int] = []
    used_at_time: dict[float, set[int]] = {}
    for time in ts:
        taken = used_at_time.setdefault(time, set())
        free = [lane for lane in range(lane_count) if lane not in taken]
        if not free:
            # chord exhausted the lanes: nudge the note off the chord instead
            time = round(time + 60.0, 1)
            taken = used_at_time.setdefault(time, set())
            free = [lane for lane in range(lane_count) if lane not in taken] or [0]
        lane = rng.choice(free)
        taken.add(lane)
        lanes.append(lane)
    ts_sorted, lanes_sorted = zip(*sorted(zip(ts, lanes)))
    return list(ts_sorted), list(lanes_sorted), f"rand(n={n},lanes={lane_count})"


def _directed_charts() -> list[tuple[list[float], list[int], str]]:
    return [
        # 13.2 shape: one lane, delay-and-catch band inversion around a fill boundary.
        ([0.0, 300.0, 600.0, 900.0, 1200.0, 1320.0], [0, 0, 0, 0, 0, 0], "13.2-single-lane"),
        # Aurora shape: same-time cross-lane chord straddling the activation.
        ([0.0, 250.0, 500.0, 500.0, 750.0, 1000.0], [0, 1, 0, 1, 2, 0], "chord-straddle"),
        # Dense burst then gap: crossing-identity swaps under early-Great fill.
        ([0.0, 130.0, 260.0, 390.0, 520.0, 1400.0], [0, 1, 2, 3, 0, 1], "burst-then-gap"),
        # Region-2 bait: enough notes for k >= 2*denom contiguous runs.
        ([0.0, 200.0, 400.0, 600.0, 800.0, 1000.0, 1200.0], [0, 1, 0, 1, 0, 1, 0], "region2-bait"),
    ]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--charts", type=int, default=10, help="random charts to sweep")
    ap.add_argument("--max-notes", type=int, default=6, help="max notes per random chart (>=4)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--directed", action="store_true", help="run the curated witness shapes only")
    ap.add_argument("--fever-fill", type=int, default=0, help="FeverFillRate stat (shrinks denom)")
    ap.add_argument("--fever-time", type=int, default=0, help="FeverTime stat (stretches rt)")
    args = ap.parse_args(argv)

    stats = {}
    if int(args.fever_fill):
        stats["FeverFillRate"] = int(args.fever_fill)
    if int(args.fever_time):
        stats["FeverTime"] = int(args.fever_time)

    failures = 0
    charts: list[tuple[list[float], list[int], str]] = []
    if args.directed:
        charts = _directed_charts()
    else:
        rng = random.Random(int(args.seed))
        charts = [_random_chart(rng, max(4, int(args.max_notes))) for _ in range(int(args.charts))]
        charts.extend(_directed_charts())

    for ts, lanes, label in charts:
        res = check_chart(ts, lanes, stats, label)
        if not _report(res):
            failures += 1
    print(f"\nVERDICT: {'PASS' if failures == 0 else f'FAIL ({failures} charts with witnesses)'}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
