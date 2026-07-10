"""Bounded FG frontier replay sweep on tiny charts.

Enumerates a finite set of PHYSICAL press schedules (per-note band-extreme press times) on
synthetic tiny charts, replays every candidate through the faithful engine simulator
(``tools/verify/game_sim.py`` -- earliest-hittable-first matching, +200ms despawn,
frame-integrated fever, exact-time judging), and compares the observed full-combo P/G surfaces
against the production FG response frontier for the SAME chart and SIM-DERIVED fever geometry.

This sweep is sound-positive, not complete: every surface it reports as reachable came from exact
replay, so an observed winning under-report is authoritative. Band extremes do not enumerate every
interior cross-note breakpoint, so the absence of an under-report is regression evidence, not a
completeness proof. The explicit replay witnesses in ``tests/test_fg_tail_activation_dbis.py`` are
authoritative for their directed claims; random/directed ``check_chart`` sweeps are bug-discovery
and regression tools.

Classifications:

* OBSERVED UNDER-report: an exactly replayed surface that no production surface structurally
  dominates and that beats the whole produced set at a checked stat cell. Index-inverted witnesses
  are the DESIGNED known-gap family from ``FG_TAIL_ACTIVATION_DBIS.md`` section 5; they fail only
  under ``--strict``. Any other observed winning witness always fails.
* PRODUCED BUT NOT OBSERVED: a targeted heuristic realizer probes enriched interior candidates. A
  successful construction is exact replay (``over_realized``), and an observed reachable surface
  may prove a claim score-dominated (``over_dominated``). If neither succeeds, the claim is
  ``over_unresolved``: this is conservative evidence requiring adjudication, not proof of a
  phantom. Unresolved claims still fail the sweep.

Independence: press candidates come from the simulator's own judgment edges
(``game_sim._JUDGE_EDGES_TAP``), fever membership from ``RegisteredHit.fever``, and the dominance
relation is the semantic structural one -- no production placement/enumeration primitive is
reused, so this oracle cannot inherit a producer bug (the circularity the 2026-07-07 audit flagged
in the contiguous-run oracle).

Scope (v2, D-bis): bounded full-combo P/G schedules (runs with any okay/miss/whiff are filtered
out) over TAP AND HOLD charts. A hold is a (head=2, tail=3) same-lane pair; the tail is its own
scored note with doubled judge edges and the +200ms despawn cap, played as a RELEASE edge. The six
band-extreme candidates per note sample every judgment band but not every interior ordering/fever
breakpoint. Schedules that are not physically playable are excluded BEFORE replay: a hold's
release must follow its press, and a lane's key is DOWN through its release edge, so no same-lane
press may land inside that closed span.

Production envelopes come from the canonical per-note builders (`timing_envelope.py`), exactly
as `apply_timing_envelope` feeds the real FG build -- held tails keep their widened per-note
windows (+80 Perfect, +200 despawn-capped late Great, -39/-189 floors).

Usage:
    python tools/verify/two_directional_frontier_oracle.py --charts 20 --max-notes 6 --seed 42
    python tools/verify/two_directional_frontier_oracle.py --directed   # curated witness shapes
    python tools/verify/two_directional_frontier_oracle.py --hold-charts 12   # extra hold sweeps
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
# Tail (release) bands are the tap edges doubled (judge.ts / game_sim _JUDGE_EDGES_TAIL), with
# the late side despawn-capped at +200 (a release after tail+200 is a no-op: the hold left the
# active list and the tail already scored a miss). Perfect (-40,+80], Great early (-190,-40],
# Great late (+80,+200-capped].
_TAIL_CANDIDATE_DELTAS_MS = (-189.0, -41.0, -39.0, 80.0, 81.0, 200.0)


def _surface_key_from_sim(result, n: int) -> tuple[int, int] | None:
    """(fever_mask, great_mask) for a legal full-combo P/G run, else None.

    Tails are their own scored notes (their bit is their chart note_index), exactly as the
    production surface indexes them.
    """
    tally = result.tally
    if int(tally.get("miss", 0)) or int(tally.get("okay", 0)):
        return None
    if int(result.max_combo) != int(n):
        return None
    notes = [h for h in result.registered if h.kind == "note"]
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


def _tail_head_pairs(note_types: list[int], lanes: list[int]) -> dict[int, int]:
    """tail_index -> head_index, FIFO per lane (same fold as game_sim.NoteSim)."""
    pending: dict[int, list[int]] = {}
    pairs: dict[int, int] = {}
    for i, nt in enumerate(note_types):
        if int(nt) == 2:
            pending.setdefault(int(lanes[i]), []).append(i)
        elif int(nt) == 3:
            stack = pending.get(int(lanes[i]))
            if not stack:
                raise ValueError(f"tail at index {i} (lane {lanes[i]}) has no pending head")
            pairs[i] = stack.pop(0)
    if any(stack for stack in pending.values()):
        raise ValueError("hold head without a tail in chart")
    return pairs


def _schedule_is_physical(
    times: list[float],
    note_types: list[int],
    lanes: list[int],
    pairs: dict[int, int],
) -> bool:
    """A player can actually input this schedule: each hold's release strictly follows its
    press, and no same-lane press lands inside a hold's key-down span [press, release]."""
    spans: dict[int, list[tuple[float, float]]] = {}
    for tail_i, head_i in pairs.items():
        if not times[head_i] < times[tail_i]:
            return False
        spans.setdefault(int(lanes[tail_i]), []).append((times[head_i], times[tail_i]))
    if not spans:
        return True
    for i, nt in enumerate(note_types):
        if int(nt) == 3:
            continue  # the release edge itself ends its span
        for lo, hi in spans.get(int(lanes[i]), ()):
            if lo < times[i] <= hi:
                return False
            if times[i] == lo and int(nt) != 2:
                return False  # a second press at the head instant on a held lane
    # overlapping holds on one lane would need two keys
    for lane_spans in spans.values():
        lane_spans.sort()
        for (lo1, hi1), (lo2, _hi2) in zip(lane_spans, lane_spans[1:]):
            if lo2 < hi1:
                return False
    return True


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

_TAP_BANDS_MS = ((-94.0, -21.0), (-19.0, 40.0), (41.0, 190.0))
_TAIL_BANDS_MS = ((-189.0, -41.0), (-39.0, 80.0), (81.0, 200.0))
_LABEL_HIGH_EDGES_TAP = (40.0, 190.0)
_LABEL_HIGH_EDGES_TAIL = (80.0, 200.0)


def _enriched_candidates_for(i: int, timestamps_ms: list[float], nts: list[int]) -> tuple[float, ...]:
    """Band extremes PLUS cross-note breakpoint offsets for note ``i``.

    The optimum press is generally an INTERIOR point of a band, pinned by another note: either a
    follower's label-high edge (the activation must stop just inside it) or another note's own
    press time (same-lane earliest-hittable-first means "press just AFTER the earlier note's
    press"). So the breakpoints are the other notes' label-high edges AND their own band
    extremes, each +-1ms, clipped to ``i``'s own bands. Band extremes alone under-enumerate
    exactly those surfaces (the 16.33 'interior candidates' completeness caveat).
    """
    own_bands = _TAIL_BANDS_MS if int(nts[i]) == 3 else _TAP_BANDS_MS
    base = _TAIL_CANDIDATE_DELTAS_MS if int(nts[i]) == 3 else _TAP_CANDIDATE_DELTAS_MS
    out = set(float(d) for d in base)
    for j, tj in enumerate(timestamps_ms):
        if j == i:
            continue
        j_tail = int(nts[j]) == 3
        edges = set(_LABEL_HIGH_EDGES_TAIL if j_tail else _LABEL_HIGH_EDGES_TAP)
        edges.update(_TAIL_CANDIDATE_DELTAS_MS if j_tail else _TAP_CANDIDATE_DELTAS_MS)
        for e in edges:
            for shift in (0.0, -1.0, 1.0):
                d = float(tj) + float(e) + float(shift) - float(timestamps_ms[i])
                if any(lo <= d <= hi for lo, hi in own_bands):
                    out.add(round(d, 3))
    return tuple(sorted(out))


def _greedy_target_schedule(
    target: tuple[int, int],
    h_a: float,
    rt_ms: float,
    timestamps_ms: list[float],
    lanes: list[int],
    nts: list[int],
    late_great_first: bool,
) -> list[float] | None:
    """Construct press times realizing ``target`` for a given activation hit ``h_a``.

    Chart-index order with per-lane monotone press times (+1ms separation) reproduces
    earliest-hittable-first binding; each note takes the EARLIEST legal time inside a band
    consistent with its required label (G bit) and fever bit (inside ``(h_a, end)`` vs outside).
    Returns None when some note has no legal slot.
    """
    n = len(timestamps_ms)
    fever_mask, great_mask = target
    act = (fever_mask & -fever_mask).bit_length() - 1
    end = h_a + rt_ms
    times: list[float] = [0.0] * n
    last_on_lane: dict[int, float] = {}
    for i in range(n):
        t_i = timestamps_ms[i]
        is_tail = int(nts[i]) == 3
        bands = _TAIL_BANDS_MS if is_tail else _TAP_BANDS_MS
        if (great_mask >> i) & 1:
            label_bands = [bands[0], bands[2]]  # early-Great, late-Great
            if late_great_first:
                label_bands.reverse()
        else:
            label_bands = [bands[1]]  # Perfect
        floor = last_on_lane.get(int(lanes[i]), float("-inf")) + 1.0
        if i == act:
            candidates = [h_a] if h_a >= floor else []
        else:
            primary: list[tuple[float, float]] = []
            secondary: list[tuple[float, float]] = []
            for lo, hi in label_bands:
                lo_t, hi_t = t_i + lo, t_i + hi
                if (fever_mask >> i) & 1:
                    primary.append((max(lo_t, h_a + 1.0), min(hi_t, end - 1.0)))
                else:
                    # outside fever: strictly before the activation, or at/after the end --
                    # prefer the interval on the note's index side of the activation.
                    pre = (lo_t, min(hi_t, h_a - 1.0))
                    post = (max(lo_t, end + 1.0), hi_t)
                    if i < act:
                        primary.append(pre)
                        secondary.append(post)
                    else:
                        primary.append(post)
                        secondary.append(pre)
            candidates = [max(lo_t, floor) for lo_t, hi_t in primary if max(lo_t, floor) <= hi_t]
            if not candidates:
                candidates = [max(lo_t, floor) for lo_t, hi_t in secondary if max(lo_t, floor) <= hi_t]
        if not candidates:
            return None
        times[i] = min(candidates)
        last_on_lane[int(lanes[i])] = times[i]
    return times


def _realize_surface(
    target: tuple[int, int],
    timestamps_ms: list[float],
    lanes: list[int],
    nts: list[int],
    statsdict: dict,
    config: dict,
) -> bool:
    """OVER-direction refinement: try to physically realize ONE claimed surface.

    Phase A: target-driven greedy schedules over the activation's enriched candidate hits
    (a cheap probe for activation-interior, end-boundary and same-lane-order interior needs).
    Phase B: blind band-extreme product with ONE note's candidate set enriched, for the
    activation and the last two fevered notes (backstop for shapes the greedy misses).
    Returns True the moment a physical schedule replays to exactly ``target``.
    """
    n = len(timestamps_ms)
    fever_mask, _great_mask = target
    if fever_mask == 0:
        return False
    act = (fever_mask & -fever_mask).bit_length() - 1
    pairs = _tail_head_pairs(nts, lanes)
    chart = NoteChart(timestamps_ms=list(timestamps_ms), lanes=list(lanes), note_types=list(nts))

    def _try(times: list[float]) -> bool:
        if pairs and not _schedule_is_physical(times, nts, lanes, pairs):
            return False
        presses = sorted(
            (Press(lanes[i], times[i], is_release=(nts[i] == 3)) for i in range(n)),
            key=lambda p: (p.time_ms, p.is_release),
        )
        result = simulate(chart, statsdict, [], presses, config, frame_dt_ms=_ORACLE_FRAME_DT_MS)
        return _surface_key_from_sim(result, n) == target

    # rt from a baseline on-time run (same source as check_chart's geometry)
    baseline = simulate(
        chart, statsdict, [],
        [Press(lanes[i], timestamps_ms[i], is_release=(nts[i] == 3)) for i in range(n)],
        config, frame_dt_ms=_ORACLE_FRAME_DT_MS,
    )
    rt_ms = float(baseline.fever_time_sec) * 1000.0

    # Phase A -- greedy construction per candidate activation hit.
    act_is_great = bool((target[1] >> act) & 1)
    for delta in _enriched_candidates_for(act, timestamps_ms, nts):
        # the activation's own label must hold at h_a
        bands = _TAIL_BANDS_MS if int(nts[act]) == 3 else _TAP_BANDS_MS
        ok_bands = (bands[0], bands[2]) if act_is_great else (bands[1],)
        if not any(lo <= delta <= hi for lo, hi in ok_bands):
            continue
        h_a = timestamps_ms[act] + delta
        for late_first in (False, True):
            times = _greedy_target_schedule(
                target, h_a, rt_ms, timestamps_ms, lanes, nts, late_great_first=late_first
            )
            if times is not None and _try(times):
                return True

    # Phase B -- blind product, one enriched note at a time.
    fevered = [i for i in range(n) if (fever_mask >> i) & 1]
    enrich_set = {act, *fevered[-2:]}
    for k in sorted(enrich_set):
        candidate_bands = [
            _enriched_candidates_for(i, timestamps_ms, nts)
            if i == k
            else (_TAIL_CANDIDATE_DELTAS_MS if nts[i] == 3 else _TAP_CANDIDATE_DELTAS_MS)
            for i in range(n)
        ]
        for deltas in itertools.product(*candidate_bands):
            if _try([timestamps_ms[i] + deltas[i] for i in range(n)]):
                return True
    return False


def _witness_is_index_inverted(
    witness: tuple[int, int], denom: float, n: int
) -> bool:
    """Classify an under-report witness as the DESIGNED index-inverted family
    (FG_TAIL_ACTIVATION_DBIS.md section 5: delay-and-catch / same-timestamp closer choice).

    The production surface model walks fill in CHART INDEX order, so its fever range must start
    at a note the index-ordered bar can actually cross on, given the witness's own P/G labels.
    If the index-ordered crossing lands elsewhere, the witness is reachable only by depositing
    an index-earlier note AFTER an index-later one (hit-order inversion) -- exactly the designed
    enumeration family, not a producer cap/emission bug. First-section classifier (tiny charts).
    """
    fever_mask, great_mask = witness
    if fever_mask == 0:
        return False
    act = (fever_mask & -fever_mask).bit_length() - 1
    bar = 0.0
    for i in range(n):
        bar += 0.5 if (great_mask >> i) & 1 else 1.0
        if bar >= float(denom) - 1e-9:
            return i != act
    return False


def enumerate_reachable_surfaces(
    timestamps_ms: list[float],
    lanes: list[int],
    statsdict: dict,
    config: dict,
    note_types: list[int] | None = None,
) -> tuple[set[tuple[int, int]], float, float]:
    """Exactly replayed surfaces found by the bounded, physical band-extreme sweep."""
    n = len(timestamps_ms)
    nts = [1] * n if note_types is None else [int(x) for x in note_types]
    chart = NoteChart(timestamps_ms=list(timestamps_ms), lanes=list(lanes), note_types=nts)
    pairs = _tail_head_pairs(nts, lanes)
    baseline = simulate(
        chart, statsdict, [],
        [Press(lanes[i], timestamps_ms[i], is_release=(nts[i] == 3)) for i in range(n)],
        config, frame_dt_ms=_ORACLE_FRAME_DT_MS,
    )
    denom = float(baseline.fever_fill_denom)
    rt = float(baseline.fever_time_sec)
    reachable: set[tuple[int, int]] = set()
    candidate_bands = [
        _TAIL_CANDIDATE_DELTAS_MS if nts[i] == 3 else _TAP_CANDIDATE_DELTAS_MS for i in range(n)
    ]
    for deltas in itertools.product(*candidate_bands):
        times = [timestamps_ms[i] + deltas[i] for i in range(n)]
        if pairs and not _schedule_is_physical(times, nts, lanes, pairs):
            continue
        presses = sorted(
            (Press(lanes[i], times[i], is_release=(nts[i] == 3)) for i in range(n)),
            key=lambda p: (p.time_ms, p.is_release),
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
    note_types: list[int] | None = None,
) -> set[tuple[int, int]]:
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_batch import (
        build_force_greats_response_first_frontiers_gpu_batch,
    )
    from gear_optimizer.solver.timing_envelope import (
        build_great_candidate_envelope_sec,
        build_great_floor_envelope_sec,
        build_perfect_candidate_envelope_sec,
        build_perfect_floor_envelope_sec,
    )

    ts = np.asarray([t / 1000.0 for t in timestamps_ms], dtype=np.float32)
    n = int(ts.shape[0])
    nt = np.ones(n, dtype=np.int16) if note_types is None else np.asarray(note_types, dtype=np.int16)
    # The exact production envelopes (per-note, held-tail-aware, despawn-capped) -- the same
    # builders apply_timing_envelope attaches for the real FG build.
    frontier = build_force_greats_response_first_frontiers_gpu_batch(
        timestamps=ts,
        perfect_candidate_timestamps=build_perfect_candidate_envelope_sec(ts, nt),
        great_candidate_timestamps=build_great_candidate_envelope_sec(ts, nt, great_mode="late"),
        perfect_floor_timestamps=build_perfect_floor_envelope_sec(ts, nt),
        great_floor_timestamps=build_great_floor_envelope_sec(ts, nt),
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
    note_types: list[int] | None = None,
) -> dict:
    """Run the sound-positive bounded sweep; absence of a witness is not completeness proof."""
    n = len(timestamps_ms)
    nts = [1] * n if note_types is None else [int(x) for x in note_types]
    stats = dict(statsdict or {})
    hit_objects = sum(1 for x in nts if int(x) != 3)  # taps + heads; tails are not hitObjects
    config = {
        "hitCount": n,
        "hitObjectsCount": int(hit_objects),
        "lastNoteTimeSec": (max(timestamps_ms) + 2000.0) / 1000.0,
    }
    reachable, denom, rt = enumerate_reachable_surfaces(
        timestamps_ms, lanes, stats, config, note_types=nts
    )
    produced = production_surfaces(timestamps_ms, lanes, denom, rt, note_types=nts)

    under_structural = [
        r for r in sorted(reachable)
        if not any(_structurally_dominates(p, r) for p in produced)
    ]
    # Score refinement: a structurally-uncovered surface only matters if it BEATS the whole
    # produced set at some stat cell (flat-ramp exact on tiny charts).
    scored_under = [
        (r, margin)
        for r in under_structural
        if (margin := _witness_wins_a_cell(r, produced, n)) > 1e-9
    ]
    # Every member of `reachable` came from exact replay, so an observed winning witness is sound.
    # Index-inverted deposits are the DESIGNED (not implemented) family from
    # FG_TAIL_ACTIVATION_DBIS.md section 5 -- reported loudly, failed only under --strict. Absence
    # of a witness says only that this bounded candidate sweep did not find one.
    under = [(r, m) for (r, m) in scored_under if not _witness_is_index_inverted(r, denom, n)]
    under_design = [(r, m) for (r, m) in scored_under if _witness_is_index_inverted(r, denom, n)]
    over_unresolved: list[tuple[int, int]] = []
    over_dominated: list[tuple[int, int]] = []
    over_realized: list[tuple[int, int]] = []
    for p in sorted(produced):
        if p in reachable:
            continue
        if any(_structurally_dominates(r, p) for r in reachable):
            over_dominated.append(p)
        elif _realize_surface(p, timestamps_ms, lanes, nts, stats, config):
            # Physically replayed after cross-note breakpoint enrichment: exact positive evidence
            # that the bounded base sweep omitted this schedule.
            over_realized.append(p)
        else:
            # A failed heuristic construction does not prove infeasibility. Keep the claim
            # unresolved and fail conservatively until an independent proof adjudicates it.
            over_unresolved.append(p)
    return {
        "label": label,
        "n": n,
        "denom": denom,
        "rt": rt,
        "reachable": len(reachable),
        "produced": len(produced),
        "under": under,
        "under_design": under_design,
        "under_structural": len(under_structural),
        "over_unresolved": over_unresolved,
        "over_dominated": over_dominated,
        "over_realized": over_realized,
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


def _report(res: dict, strict: bool = False) -> bool:
    ok = not res["under"] and not res["over_unresolved"]
    if strict:
        ok = ok and not res["under_design"]
    status = "OK " if ok else "FAIL"
    print(
        f"[{status}] {res['label']}: n={res['n']} denom={res['denom']:.4f} rt={res['rt']:.3f} "
        f"reachable={res['reachable']} produced={res['produced']} "
        f"under={len(res['under'])}+{len(res['under_design'])}known (structural {res['under_structural']}) "
        f"over_unresolved={len(res['over_unresolved'])} over_realized={len(res['over_realized'])} "
        f"over_dominated={len(res['over_dominated'])}"
    )
    for (fever, great), margin in res["under"][:6]:
        print(f"    under: F={_mask_str(fever, res['n'])} G={_mask_str(great, res['n'])} wins_by={margin:.1f}")
    for (fever, great), margin in res["under_design"][:6]:
        print(
            f"    KNOWN-GAP (index-inverted; design FG_TAIL_ACTIVATION_DBIS section 5): "
            f"F={_mask_str(fever, res['n'])} G={_mask_str(great, res['n'])} wins_by={margin:.1f}"
        )
    for fever, great in res["over_realized"][:6]:
        print(f"    over_realized (breakpoint schedule replays it): F={_mask_str(fever, res['n'])} G={_mask_str(great, res['n'])}")
    for fever, great in res["over_unresolved"][:6]:
        print(
            f"    over_unresolved (requires adjudication): "
            f"F={_mask_str(fever, res['n'])} G={_mask_str(great, res['n'])}"
        )
    return ok


def _random_chart(rng: random.Random, max_notes: int) -> tuple[list[float], list[int], list[int] | None, str]:
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
    return list(ts_sorted), list(lanes_sorted), None, f"rand(n={n},lanes={lane_count})"


def _random_hold_chart(rng: random.Random, max_notes: int) -> tuple[list[float], list[int], list[int], str]:
    """Random tap+hold chart. Holds bracket their lane (no same-lane note inside a span, like
    real charts -- the lane's key is down). Tap-at-tail same-time cross-lane chords are seeded
    deliberately: that is the D-bis gap-(c) shape."""
    n = rng.randint(4, max_notes)
    lane_count = rng.choice((2, 4))
    events: list[tuple[float, int, int]] = []  # (time, lane, note_type)
    lane_free_at = {lane: 0.0 for lane in range(lane_count)}
    t = 0.0
    remaining = n
    while remaining > 0:
        free = [lane for lane in range(lane_count) if lane_free_at[lane] <= t]
        if not free:
            t = round(min(lane_free_at.values()), 1)
            continue
        lane = rng.choice(free)
        if remaining >= 2 and rng.random() < 0.45:
            span = rng.choice((240.0, 360.0, 480.0))
            events.append((t, lane, 2))
            events.append((round(t + span, 1), lane, 3))
            lane_free_at[lane] = round(t + span, 1) + 1.0
            remaining -= 2
            # gap-(c) seed: a same-time cross-lane tap at the tail instant
            if remaining > 0 and rng.random() < 0.5:
                others = [ln for ln in range(lane_count) if ln != lane and lane_free_at[ln] <= t + span]
                if others:
                    events.append((round(t + span, 1), rng.choice(others), 1))
                    remaining -= 1
        else:
            events.append((t, lane, 1))
            remaining -= 1
        t = round(t + rng.choice((120.0, 240.0, 300.0)), 1)
    # Stable sort by time ONLY: intra-group (same-timestamp) index order is a real chart degree
    # of freedom the checker must see in both orders (gap-(c)); the generator's emit order
    # already varies it.
    events.sort(key=lambda e: e[0])
    ts = [e[0] for e in events]
    lanes = [e[1] for e in events]
    nts = [e[2] for e in events]
    holds = sum(1 for x in nts if x == 2)
    return ts, lanes, nts, f"rand-hold(n={len(ts)},lanes={lane_count},holds={holds})"


def _directed_charts() -> list[tuple[list[float], list[int], list[int] | None, str]]:
    return [
        # 13.2 shape: one lane, delay-and-catch band inversion around a fill boundary.
        ([0.0, 300.0, 600.0, 900.0, 1200.0, 1320.0], [0, 0, 0, 0, 0, 0], None, "13.2-single-lane"),
        # Aurora shape: same-time cross-lane chord straddling the activation.
        ([0.0, 250.0, 500.0, 500.0, 750.0, 1000.0], [0, 1, 0, 1, 2, 0], None, "chord-straddle"),
        # Dense burst then gap: crossing-identity swaps under early-Great fill.
        ([0.0, 130.0, 260.0, 390.0, 520.0, 1400.0], [0, 1, 2, 3, 0, 1], None, "burst-then-gap"),
        # Region-2 bait: enough notes for k >= 2*denom contiguous runs.
        ([0.0, 200.0, 400.0, 600.0, 800.0, 1000.0, 1200.0], [0, 1, 0, 1, 0, 1, 0], None, "region2-bait"),
    ]


def _directed_tail_charts() -> list[tuple[list[float], list[int], list[int], str]]:
    """D-bis directed shapes: tails as followers, tails as activations, and the same-time
    tap+tail closer-choice pair in BOTH intra-group chart index orders."""
    return [
        # (a)-shape: taps with a cross-lane hold interleaved -- the TAIL is a close follower of
        # the crossing region, so its widened (+80/+200) label edge is exercised as a follower
        # cap in both directions (delaying past it must flip the crossing: fill identity).
        ([0.0, 100.0, 240.0, 460.0, 480.0, 800.0],
         [0, 1, 0, 1, 0, 0],
         [1, 2, 1, 3, 1, 1],
         "tail-follower"),
        # (b)-shape: dense prefix so the crossing lands at/near the TAIL -- its own +80 Perfect /
        # +200 despawn-capped late-Great self-window is the activation lever; production must
        # reach exactly that far and no further.
        ([0.0, 100.0, 120.0, 240.0, 460.0, 700.0],
         [0, 1, 0, 0, 1, 0],
         [1, 2, 1, 1, 3, 1],
         "tail-activation"),
        # (c)-shape, both intra-group index orders: a same-time cross-lane tap+tail chord near
        # the crossing. Order (tap, tail) lets the index-prefix model price the tail closer;
        # order (tail, tap) pins the crossing to the tap and forecloses the tail's wider window
        # (the designed group-closer family's witness).
        ([0.0, 100.0, 200.0, 500.0, 500.0, 740.0],
         [0, 1, 0, 1, 0, 0],
         [1, 2, 1, 3, 1, 1],
         "same-ts-tail-then-tap"),
        ([0.0, 100.0, 200.0, 500.0, 500.0, 740.0],
         [0, 1, 0, 0, 1, 0],
         [1, 2, 1, 1, 3, 1],
         "same-ts-tap-then-tail"),
    ]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--charts", type=int, default=10, help="random tap charts to sweep")
    ap.add_argument("--hold-charts", type=int, default=6, help="random tap+hold charts to sweep")
    ap.add_argument("--max-notes", type=int, default=6, help="max notes per random chart (>=4)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument(
        "--directed",
        action="store_true",
        help="run only the curated bounded regression shapes",
    )
    ap.add_argument("--fever-fill", type=int, default=0, help="FeverFillRate stat (shrinks denom)")
    ap.add_argument("--fever-time", type=int, default=0, help="FeverTime stat (stretches rt)")
    ap.add_argument(
        "--strict",
        action="store_true",
        help="fail on KNOWN-GAP witnesses too (the designed, not-yet-implemented index-inverted family)",
    )
    args = ap.parse_args(argv)

    stats = {}
    if int(args.fever_fill):
        stats["FeverFillRate"] = int(args.fever_fill)
    if int(args.fever_time):
        stats["FeverTime"] = int(args.fever_time)

    failures = 0
    charts: list[tuple[list[float], list[int], list[int] | None, str]] = []
    if args.directed:
        charts = _directed_charts() + _directed_tail_charts()
    else:
        rng = random.Random(int(args.seed))
        charts = [_random_chart(rng, max(4, int(args.max_notes))) for _ in range(int(args.charts))]
        charts.extend(_random_hold_chart(rng, max(4, int(args.max_notes))) for _ in range(int(args.hold_charts)))
        charts.extend(_directed_charts())
        charts.extend(_directed_tail_charts())

    known_gaps = 0
    for ts, lanes, nts, label in charts:
        res = check_chart(ts, lanes, stats, label, note_types=nts)
        known_gaps += len(res["under_design"])
        if not _report(res, strict=bool(args.strict)):
            failures += 1
    verdict = "SWEEP PASS" if failures == 0 else f"SWEEP FAIL ({failures} charts with witnesses)"
    if failures == 0 and known_gaps:
        verdict += f" with {known_gaps} KNOWN-GAP witnesses (designed family, not implemented)"
    print(f"\nBOUNDED VERDICT: {verdict}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
