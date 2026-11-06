"""A section start's candidate fever sections, written out for the trace search.

The frontier producer prices these sections without keeping them. This is the same enumeration, action by action, with
each section as a row: its activation and forced Greats, the witness an accepted section needs, and its response-surface
edge. Rows come in emission order, and a repeated section keeps its first row.
"""

from __future__ import annotations

from collections import namedtuple

import numpy as np
from numba import njit

from gear_optimizer.frontier.producer_kernels import (
    HitTimes,
    _numba_activation_reachable_contiguous_run,
    _numba_fill_crossing_run,
    _numba_has_shifted_head_region,
    _numba_late_great_activation_hit_for_run,
    _numba_lower_bound_from,
    _numba_mask_hash,
    _numba_minimal_reachable_region_great_end,
    _numba_pack_edge_eg,
    _numba_perfect_activation_hit_for_run,
    _numba_region2_offset_for_count,
    _numba_trace_edge_action_arrays,
)

# Numba's disk cache watches only this file, and the kernels here carry compiled copies of the producer kernels they call.
# This digest of producer_kernels.py makes an edit there change this file too (tests/test_repo_guardrails.py checks it).
_PRODUCER_KERNELS_SHA256 = "5f2043d6ea65d2bfa8174cbde4a55310ced0beb14787b3c3a2cc5afffe3a0b17"

# What the sections of a song read: its hit times, lanes, and one fill denominator and fever time.
SectionContext = namedtuple(
    "SectionContext",
    [
        "timestamps",
        "perfect_floor_timestamps",
        "perfect_candidate_timestamps",
        "great_floor_timestamps",
        "great_candidate_timestamps",
        "late_great_floor_timestamps",
        "exit_ceiling_timestamps",
        "lanes",
        "fever_fill_denom",
        "real_fever_time",
        "use_forced_great_timing",
    ],
)
# The columns of a section row: forced Greats, the next state (the fever end), the activation, whether a late Great
# activates it, the forced run's start and length, its early-Great tail [start, end) (-1: none), the fever end its
# witness reproduces, and whether its hit ends the fever early. The columns from the next state to the tail name the
# section.
_ROW_COLUMNS = 10
_KEY_END = 8


@njit(cache=True, nogil=True)
def fever_end(hit, a, floor_timestamps, real_fever_time, n):
    """The first note past the fever of activation `a` hit at `hit`, by the notes' earliest hits: in (a, n]."""
    return min(max(_numba_lower_bound_from(floor_timestamps, hit + real_fever_time), a + 1), n)


@njit(cache=True, nogil=True)
def _region_section(context, times, section_start, run_start, k):
    """The section of k forced Greats from run_start, as (activation, late Great, run end, end, early-Great end, hit low,
    hit high; activation < 0: none). A crossing on a Great takes its minimal reachable run, kept when it ends later than
    a Perfect of the same run or its early-Great tail reaches further. A crossing on a Perfect needs its latest hit
    reachable by the input engine."""
    none = (-1, 0, 0, 0, 0, 0.0, 0.0)
    ts, lanes = context.timestamps, context.lanes
    n, denom, rft = ts.shape[0], context.fever_fill_denom, context.real_fever_time
    perfect, great = times.perfect_candidate_timestamps, times.great_candidate_timestamps
    floor, great_floor, late_floor = (
        times.perfect_floor_timestamps, times.great_floor_timestamps, times.late_great_floor_timestamps
    )
    a, crossing_is_great = _numba_fill_crossing_run(section_start, run_start, k, denom, n)
    if a < 0:
        return none
    if crossing_is_great:
        run_end, _token = _numba_minimal_reachable_region_great_end(
            a, section_start, run_start, denom, ts, times, lanes, n
        )
        if run_end < 0:
            return none
        count = run_end - run_start
        hit = _numba_late_great_activation_hit_for_run(a, ts, perfect, great, late_floor, run_start, count, n)[0]
        end, tail_end = fever_end(hit, a, floor, rft, n), fever_end(hit, a, great_floor, rft, n)
        perfect_hit, perfect_valid, _token = _numba_perfect_activation_hit_for_run(
            a, ts, perfect, great, run_start, count, n
        )
        if (
            perfect_valid
            and end <= fever_end(perfect_hit, a, floor, rft, n)
            and tail_end <= fever_end(perfect_hit, a, great_floor, rft, n)
        ):
            return none
        return a, 1, run_end, end, tail_end, float(late_floor[a]), hit
    run_end = min(n, run_start + k)
    if run_end <= run_start:
        return none
    count = run_end - run_start
    hit, valid, _token = _numba_perfect_activation_hit_for_run(a, ts, perfect, great, run_start, count, n)
    if not valid or not _numba_activation_reachable_contiguous_run(
        a, hit, ts, times, lanes, denom, section_start, n, run_start, count, 0
    ):
        return none
    end, tail_end = fever_end(hit, a, floor, rft, n), fever_end(hit, a, great_floor, rft, n)
    return a, 0, run_end, end, tail_end, min(float(ts[a]), float(perfect[a])), hit


@njit(cache=True, nogil=True)
def _section_families(context, times, actions, fills, forced, first, state):
    """Per action its Perfect activation, its late-Great activation and its region runs, each a family of sections:
    (forced Greats, activation, late Great, run start, run end, end, early-Great end, hit low, hit high)."""
    ts = context.timestamps
    n, denom = ts.shape[0], context.fever_fill_denom
    forced_timing = context.use_forced_great_timing
    section_start = 0 if first else state + 1
    (
        err, act_a, _act_chart, act_hit_lo, act_perfect_hit, _act_perfect_hit_ok, act_perfect_reachable, act_e,
        act_start_time, act_eg_e, act_late_lo, act_late_hit, act_lg_prefix, act_late_e, _act_late_start, act_late_eg_e,
    ) = _numba_trace_edge_action_arrays(
        actions, fills, forced, int(first), state, n, ts, times.perfect_candidate_timestamps,
        times.great_candidate_timestamps, times.perfect_floor_timestamps, times.great_floor_timestamps,
        times.late_great_floor_timestamps, context.lanes, denom, context.real_fever_time,
    )
    if np.any(err):
        raise ValueError("FG activation reachability received invalid section bounds")
    shifted = bool(_numba_has_shifted_head_region(section_start, denom)) and section_start + 1 < n
    families = []
    prev_fill, prev_start_time, prev_e = -1, -1.0, -1
    for idx in range(act_a.shape[0]):
        k, fill, a, e, eg_e = int(actions[idx]), int(fills[idx]), int(act_a[idx]), int(act_e[idx]), int(act_eg_e[idx])
        if act_perfect_reachable[idx] and (fill != prev_fill or (act_start_time[idx] != prev_start_time and e != prev_e)):
            run_end = min(n, section_start + int(forced[idx]))
            families.append((k, a, 0, section_start, run_end, e, eg_e, act_hit_lo[idx], act_perfect_hit[idx]))
        # lg_prefix < 0 encodes both "no late-Great placement" and "placement not schedulable". A late Great has to
        # reach past the Perfect activation's end or early-Great tail.
        late_e, late_eg_e = int(act_late_e[idx]), int(act_late_eg_e[idx])
        if (
            forced_timing and prev_fill == fill and act_lg_prefix[idx] >= 0
            and (late_e > e or late_eg_e > eg_e)
        ):
            run_end = min(n, section_start + int(act_lg_prefix[idx]))
            families.append((k, a, 1, section_start, run_end, late_e, late_eg_e, act_late_lo[idx], act_late_hit[idx]))
        if forced_timing and k > 0:
            region2 = _numba_region2_offset_for_count(section_start, k, denom, n)
            for offset in (1 if shifted else -1, -1 if shifted and region2 == 1 else region2):
                if offset > 0:
                    run_start = section_start + offset
                    run_a, late, run_end, end, tail_end, hit_lo, hit_hi = _region_section(
                        context, times, section_start, run_start, k
                    )
                    if run_a >= 0:
                        families.append(
                            (run_end - run_start, run_a, late, run_start, run_end, end, tail_end, hit_lo, hit_hi)
                        )
        prev_fill, prev_start_time, prev_e = fill, act_start_time[idx], e
    return families


@njit(cache=True, nogil=True)
def _same_section(first, second):
    for column in range(1, _KEY_END):
        if first[column] != second[column]:
            return False
    return True


@njit(cache=True, nogil=True)
def _emit(store, count, family, n, section):
    """Row `count` is `family`'s `section` (next state, tail start, tail end, witness end, early exit, hit low), unless a
    row already names the section; returns the next free row."""
    rows, edges, hits, slots = store
    k, a, late, run_start, run_end, _end, _early_great_end, _hit_lo, hit_hi = family
    next_state, tail_start, tail_end, target_end, early_exit, hit_lo = section
    row = rows[count]
    row[0], row[1], row[2], row[3], row[4] = k, next_state, a, late, run_start
    row[5], row[6], row[7], row[8], row[9] = run_end - run_start, tail_start, tail_end, target_end, early_exit
    hashed = _numba_mask_hash(
        np.uint64(next_state), np.uint64(a) | (np.uint64(late) << np.uint64(32)),
        np.uint64(run_start) | (np.uint64(run_end) << np.uint64(32)),
        np.uint64(tail_start + 1) | (np.uint64(tail_end + 1) << np.uint64(32)),
    )
    mask = slots.shape[0] - 1
    slot = np.int64(hashed & np.uint64(mask))
    while slots[slot] >= 0:
        if _same_section(rows[slots[slot]], row):
            return count
        slot = (slot + 1) & mask
    slots[slot] = count
    edge = _numba_pack_edge_eg(n, a, next_state, run_start, run_end, a if late else -1, tail_start, tail_end)
    for column in range(7):
        edges[count, column] = edge[column]
    hits[count, 0], hits[count, 1] = hit_lo, hit_hi
    return count + 1


@njit(cache=True, nogil=True)
def section_rows(context, actions, fills, forced, first, state):
    """The options of the section start after `state` (the first section when `first`), in emission order: per action of
    the frontier's action table (`fills` and `forced` for this kind of section) its families; per family the section to
    its end, then one per later end up to its early-Great end whose tail past the end is fever-great (issue #44: the same
    witness still reproduces the end), then the activation ending its fever early: hit from its earliest legal hit (a
    Perfect's floor, a late Great's late-Great floor), at every end from which the later notes can still be hit past its
    cutoff. Returns rows (_ROW_COLUMNS), their edges (`_numba_pack_edge_eg`) and witness hit windows (low, high)."""
    n = context.timestamps.shape[0]
    times = HitTimes(
        context.perfect_floor_timestamps, context.perfect_candidate_timestamps, context.great_floor_timestamps,
        context.great_candidate_timestamps, context.late_great_floor_timestamps,
    )
    families = _section_families(context, times, actions, fills, forced, first, state)
    exits = np.empty(len(families), dtype=np.int64)
    lows = np.empty(len(families), dtype=np.float64)
    total = 0
    for index in range(len(families)):
        _k, a, late, _run_start, _run_end, end, early_great_end, _hit_lo, _hit_hi = families[index]
        lows[index] = (context.late_great_floor_timestamps if late else context.perfect_floor_timestamps)[a]
        exit_lo = _numba_lower_bound_from(context.exit_ceiling_timestamps, lows[index] + context.real_fever_time)
        exits[index] = min(max(exit_lo, a + 1), end)
        total += 1 + max(0, early_great_end - end) + end - exits[index]
    size = 2
    while size < 2 * total:
        size *= 2
    store = (
        np.empty((total, _ROW_COLUMNS), dtype=np.int64), np.empty((total, 7), dtype=np.uint64),
        np.empty((total, 2), dtype=np.float64), np.full(size, -1, dtype=np.int64),
    )
    count = 0
    for index in range(len(families)):
        family = families[index]
        end, early_great_end, hit_lo = family[5], family[6], family[7]
        count = _emit(store, count, family, n, (end, -1, -1, end, 0, hit_lo))
        for tail_end in range(end + 1, early_great_end + 1):
            count = _emit(store, count, family, n, (tail_end, end, tail_end, end, 0, hit_lo))
        for early_end in range(exits[index], end):
            count = _emit(store, count, family, n, (early_end, -1, -1, early_end, 1, lows[index]))
    return store[0][:count], store[1][:count], store[2][:count]
