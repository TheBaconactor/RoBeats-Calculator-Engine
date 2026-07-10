"""Deterministic differential test: flat-array FG packet queues vs retired List semantics.

The branch (perf/fg-packet-arrays) replaced the numba List-based packet queue machinery in
``gear_optimizer/solver/taichi_gem/force_greats/response_build_gpu_numba.py`` with
cursor-managed flat CSR arrays + per-family grow-doubling packet-point arenas
(``_numba_packet_arena_ensure`` / ``_numba_packet_union`` / ``_numba_packet_queue_transfer``
/ ``_numba_packet_queue_pop_expired_after`` / ``_numba_packet_queue_push_back``).

This test drives the PRODUCTION njit primitives through the exact caller contract used by
the kernel sweep (arrays allocated as in ``response_build_gpu_numba.py`` lines 3629-3683;
packet rows staged at the arena cursor exactly like ``_numba_packet_queue_push_activation``)
and compares them, AFTER EVERY OPERATION, against a faithful pure-Python port of the retired
List semantics taken verbatim from the pristine implementation:

    git show 2b1a1731:gear_optimizer/solver/taichi_gem/force_greats/response_build_gpu_numba.py
      _numba_append_packet_point   (pristine line 2416)
      _numba_packet_union          (pristine line 2439)
      _numba_packet_queue_transfer (pristine line 2569)
      _numba_packet_queue_pop_expired_after (pristine line 2584)
      _numba_packet_queue_push_back (pristine line 2604)

Compared state after every operation: front/back alpha stacks in order, per-entry aggregate
CONTENT in order (every entry, not just the fed top), and per-entry back PACKET contents.
List-object aliasing in the pristine code maps to flat range shares or materialized copies;
content equality is the invariant.

Region packet families: ``_numba_region2_packet_queue_push_activation``
(response_build_gpu_numba.py:2943) derives its packet POINTS from heavy chart fixtures
(region CSR core tables, floor/candidate timestamps, lanes), but performs all queue
mutation through the very same primitives exercised here, with the identical call shape as
the ordinary-family push (read cursor from ``back_pk_off[seg_base + back_len[f]]`` ->
``_numba_packet_arena_ensure`` -> stage rows at the cursor ->
``_numba_packet_queue_push_back``; compare lines 2903-2939 with 3064-3121), and its pop
side is the same ``_numba_packet_queue_pop_expired_after`` on the region CSR arrays
(line 3759). The region path is therefore covered at the queue-primitive level; the
multi-family segmented-layout test below exercises the exact CSR layout the region families
use (shared 1D arrays, seg_base > 0 segments, per-family arenas). Deriving valid region
packet CONTENT would require full chart fixtures and is out of scope for this differential.
"""
from __future__ import annotations

import random

import numpy as np
import pytest
from numba.typed import List as NumbaList

from gear_optimizer.solver.taichi_gem.force_greats import response_build_gpu_numba as rb

# ---------------------------------------------------------------------------
# Faithful pure-Python reference of the RETIRED List semantics (2b1a1731).
# Plain-Python list model only; intentionally NOT the production code.
# ---------------------------------------------------------------------------


def _ref_append_packet_point(bucket: list[tuple[int, int, int]], point: tuple[int, int, int]) -> bool:
    """Port of pristine _numba_append_packet_point: dominated-candidate check first, then
    in-order survivor compaction, candidate appended last."""
    cf, cn, cq = point
    for kf, kn, kq in bucket:
        if kf >= cf and kn <= cn and kq <= cq:
            return False
    bucket[:] = [kept for kept in bucket if not (cf >= kept[0] and cn <= kept[1] and cq <= kept[2])]
    bucket.append((cf, cn, cq))
    return True


def _ref_packet_union(left: list, right: list) -> list:
    """Port of pristine _numba_packet_union including its alias returns (the same list
    object is returned for the left-alias and right-alias branches)."""
    if len(left) <= 0:
        return right
    if len(right) <= 0:
        return left
    if len(left) == 1:
        cf, cn, cq = left[0]
        for kf, kn, kq in right:
            if kf >= cf and kn <= cn and kq <= cq:
                return right
        out = [(cf, cn, cq)]
        for kf, kn, kq in right:
            if not (cf >= kf and cn <= kn and cq <= kq):
                out.append((kf, kn, kq))
        return out
    if len(right) == 1:
        cf, cn, cq = right[0]
        for kf, kn, kq in left:
            if kf >= cf and kn <= cn and kq <= cq:
                return left
        out = [kept for kept in left if not (cf >= kept[0] and cn <= kept[1] and cq <= kept[2])]
        out.append((cf, cn, cq))
        return out
    out = list(left)
    for point in right:
        _ref_append_packet_point(out, point)
    return out


class ListPacketQueueReference:
    """Faithful port of the pristine two-stack sliding-window packet queue."""

    def __init__(self) -> None:
        self.front_alpha: list[int] = []
        self.front_aggregate: list[list[tuple[int, int, int]]] = []
        self.back_alpha: list[int] = []
        self.back_packet: list[list[tuple[int, int, int]]] = []
        self.back_aggregate: list[list[tuple[int, int, int]]] = []

    def _transfer(self) -> None:
        aggregate: list[tuple[int, int, int]] = []
        while self.back_alpha:
            alpha = self.back_alpha.pop()
            packet = self.back_packet.pop()
            self.back_aggregate.pop()
            if len(aggregate) <= 0:
                aggregate = packet
            else:
                aggregate = _ref_packet_union(packet, aggregate)
            self.front_alpha.append(alpha)
            self.front_aggregate.append(aggregate)

    def pop_expired_after(self, high_alpha: int) -> None:
        while True:
            if len(self.front_alpha) <= 0:
                self._transfer()
            if len(self.front_alpha) <= 0:
                return
            if self.front_alpha[-1] <= high_alpha:
                return
            self.front_alpha.pop()
            self.front_aggregate.pop()

    def push_back(self, alpha: int, points: list[tuple[int, int, int]]) -> None:
        packet = [(int(cf), int(cn), int(cq)) for cf, cn, cq in points]
        if len(packet) <= 0:
            return
        if len(self.back_aggregate) > 0:
            aggregate = _ref_packet_union(self.back_aggregate[-1], packet)
        else:
            aggregate = packet
        self.back_alpha.append(int(alpha))
        self.back_packet.append(packet)
        self.back_aggregate.append(aggregate)

    def full_state(self):
        front = tuple(
            (int(alpha), tuple(aggregate))
            for alpha, aggregate in zip(self.front_alpha, self.front_aggregate, strict=True)
        )
        back = tuple(
            (int(alpha), tuple(packet), tuple(aggregate))
            for alpha, packet, aggregate in zip(
                self.back_alpha, self.back_packet, self.back_aggregate, strict=True
            )
        )
        return front, back


# ---------------------------------------------------------------------------
# Flat-arena driver over the production njit primitives.
# ---------------------------------------------------------------------------


def _rows(buf, start: int, end: int) -> tuple[tuple[int, int, int], ...]:
    return tuple((int(buf[i, 0]), int(buf[i, 1]), int(buf[i, 2])) for i in range(int(start), int(end)))


class FlatPacketQueues:
    """Owns the flat CSR arrays + per-family arenas exactly like the production sweep
    (response_build_gpu_numba.py:3629-3683) and calls the production njit primitives.

    ``initial_arena_rows`` defaults to 4 (production seeds 64) so directed tests force
    grow-doubling quickly; ``_numba_packet_arena_ensure`` semantics are capacity-independent.
    """

    def __init__(self, widths: list[int], initial_arena_rows: int = 4) -> None:
        family_count = len(widths)
        seg_off = np.zeros(family_count + 1, dtype=np.int64)
        for family_idx, width in enumerate(widths):
            seg_off[family_idx + 1] = int(seg_off[family_idx]) + int(width) + 3
        total_slots = max(1, int(seg_off[family_count]))
        self.family_count = family_count
        self.seg_off = seg_off
        self.front_alpha = np.zeros(total_slots, dtype=np.int64)
        self.front_ag_start = np.zeros(total_slots, dtype=np.int64)
        self.front_ag_end = np.zeros(total_slots, dtype=np.int64)
        self.front_len = np.zeros(max(1, family_count), dtype=np.int64)
        self.back_alpha = np.zeros(total_slots, dtype=np.int64)
        self.back_pk_off = np.zeros(total_slots, dtype=np.int64)
        self.back_ag_start = np.zeros(total_slots, dtype=np.int64)
        self.back_ag_end = np.zeros(total_slots, dtype=np.int64)
        self.back_len = np.zeros(max(1, family_count), dtype=np.int64)
        self.back_pk_arenas = NumbaList.empty_list(rb._NUMBA_PACKET_ARENA_TYPE)
        self.back_ag_arenas = NumbaList.empty_list(rb._NUMBA_PACKET_ARENA_TYPE)
        self.front_ag_arenas = NumbaList.empty_list(rb._NUMBA_PACKET_ARENA_TYPE)
        for _ in range(family_count):
            self.back_pk_arenas.append(np.empty((int(initial_arena_rows), 3), dtype=np.int64))
            self.back_ag_arenas.append(np.empty((int(initial_arena_rows), 3), dtype=np.int64))
            self.front_ag_arenas.append(np.empty((int(initial_arena_rows), 3), dtype=np.int64))

    def pop_expired_after(self, family: int, high_alpha: int) -> None:
        rb._numba_packet_queue_pop_expired_after(
            int(high_alpha),
            int(family),
            int(self.seg_off[family]),
            self.front_alpha,
            self.front_ag_start,
            self.front_ag_end,
            self.front_len,
            self.back_alpha,
            self.back_pk_off,
            self.back_len,
            self.back_pk_arenas,
            self.front_ag_arenas,
        )

    def push_back(self, family: int, alpha: int, points: list[tuple[int, int, int]]) -> None:
        """Mirrors the push_activation caller contract (response_build_gpu_numba.py:2903-2939
        and the region twin at :3064-3121): early-return on empty packets, stage the packet
        rows at the packet-arena cursor, then hand the range to the production push_back."""
        if len(points) <= 0:
            return
        base = int(self.seg_off[family])
        limit = int(self.seg_off[family + 1])
        pk_cursor = int(self.back_pk_off[base + int(self.back_len[family])])
        pk_buf = rb._numba_packet_arena_ensure(self.back_pk_arenas, int(family), pk_cursor, len(points))
        write = pk_cursor
        for cf, cn, cq in points:
            pk_buf[write, 0] = int(cf)
            pk_buf[write, 1] = int(cn)
            pk_buf[write, 2] = int(cq)
            write += 1
        rb._numba_packet_queue_push_back(
            int(alpha),
            pk_cursor,
            write,
            int(family),
            base,
            limit,
            self.back_alpha,
            self.back_pk_off,
            self.back_ag_start,
            self.back_ag_end,
            self.back_len,
            self.back_pk_arenas,
            self.back_ag_arenas,
        )

    def full_state(self, family: int):
        base = int(self.seg_off[family])
        front_buf = self.front_ag_arenas[family]
        front = tuple(
            (
                int(self.front_alpha[base + i]),
                _rows(front_buf, int(self.front_ag_start[base + i]), int(self.front_ag_end[base + i])),
            )
            for i in range(int(self.front_len[family]))
        )
        pk_buf = self.back_pk_arenas[family]
        ag_buf = self.back_ag_arenas[family]
        back = tuple(
            (
                int(self.back_alpha[base + i]),
                _rows(pk_buf, int(self.back_pk_off[base + i]), int(self.back_pk_off[base + i + 1])),
                _rows(ag_buf, int(self.back_ag_start[base + i]), int(self.back_ag_end[base + i])),
            )
            for i in range(int(self.back_len[family]))
        )
        return front, back


class FlatVsListDifferential:
    """Applies every operation to both models and compares FULL state (all families) after
    each one: alpha stacks, per-entry aggregate content in order, and back packet contents."""

    def __init__(self, widths: list[int], initial_arena_rows: int = 4) -> None:
        self.flat = FlatPacketQueues(widths, initial_arena_rows=initial_arena_rows)
        self.refs = [ListPacketQueueReference() for _ in widths]

    def pop_expired_after(self, family: int, high_alpha: int) -> None:
        self.refs[family].pop_expired_after(int(high_alpha))
        self.flat.pop_expired_after(family, int(high_alpha))
        self.check(f"pop_expired_after(family={family}, high_alpha={high_alpha})")

    def push_back(self, family: int, alpha: int, points: list[tuple[int, int, int]]) -> None:
        self.refs[family].push_back(int(alpha), points)
        self.flat.push_back(family, int(alpha), points)
        self.check(f"push_back(family={family}, alpha={alpha}, points={points})")

    def check(self, context: str) -> None:
        for family, ref in enumerate(self.refs):
            ref_state = ref.full_state()
            flat_state = self.flat.full_state(family)
            assert flat_state == ref_state, (
                f"DIVERGENCE after {context} in family {family}\n"
                f"  reference (front, back): {ref_state}\n"
                f"  flat      (front, back): {flat_state}"
            )


# ---------------------------------------------------------------------------
# Directed cases (reviewer list).
# ---------------------------------------------------------------------------


def test_union_left_alias_branch_back_share_and_transfer_materialization() -> None:
    """Union left-alias branch (code 1) at both call sites.

    push_back: union(old_top_aggregate, packet) keeps the old aggregate -> the flat twin
    range-shares the previous back entry's aggregate range (the List version aliased the
    object). transfer: union(packet, running_aggregate) keeps the packet -> the flat twin
    materializes the packet's points into the front arena with identical content."""
    diff = FlatVsListDifferential([5])
    diff.pop_expired_after(0, 12)
    diff.push_back(0, 12, [(5, 1, 1), (6, 2, 2)])
    diff.push_back(0, 11, [(4, 3, 3)])  # single point dominated by (5,1,1) -> left alias
    base = int(diff.flat.seg_off[0])
    assert int(diff.flat.back_len[0]) == 2
    assert int(diff.flat.back_ag_start[base + 1]) == int(diff.flat.back_ag_start[base + 0])
    assert int(diff.flat.back_ag_end[base + 1]) == int(diff.flat.back_ag_end[base + 0])

    diff2 = FlatVsListDifferential([5])
    diff2.push_back(0, 12, [(5, 1, 9), (6, 2, 9)])  # packet that dominates the seed below
    diff2.push_back(0, 11, [(1, 9, 9)])
    # transfer pops alpha 11 first (seed), then union(packet(12), seed) keeps the packet
    # alone (left alias) -> materialized into the front arena.
    diff2.pop_expired_after(0, 12)
    assert int(diff2.flat.front_len[0]) == 2
    front, _back = diff2.flat.full_state(0)
    assert front == ((11, ((1, 9, 9),)), (12, ((5, 1, 9), (6, 2, 9))))


def test_union_right_alias_branch_back_materialization_and_front_share() -> None:
    """Union right-alias branch (code 2) at both call sites.

    push_back: union(old_top_aggregate, packet) keeps the packet alone -> the flat twin
    materializes the packet into the aggregate arena (the List version aliased the packet
    object). transfer: union(packet, running_aggregate) keeps the running aggregate -> the
    flat twin shares the previous front entry's range."""
    diff = FlatVsListDifferential([5])
    diff.push_back(0, 12, [(3, 5, 5)])
    diff.push_back(0, 11, [(9, 1, 1), (10, 2, 2)])  # dominates the old single-point aggregate
    base = int(diff.flat.seg_off[0])
    assert int(diff.flat.back_len[0]) == 2
    # materialized at the aggregate-arena cursor, directly after the old top's range
    assert int(diff.flat.back_ag_start[base + 1]) == int(diff.flat.back_ag_end[base + 0])
    _front, back = diff.flat.full_state(0)
    assert back[1][2] == ((9, 1, 1), (10, 2, 2))

    diff2 = FlatVsListDifferential([5])
    diff2.push_back(0, 12, [(2, 9, 9)])
    diff2.push_back(0, 11, [(9, 0, 0), (1, 8, 0)])  # seed aggregate; dominates packet(12)
    diff2.pop_expired_after(0, 12)  # transfer: packet(12) single point dominated -> share
    fbase = int(diff2.flat.seg_off[0])
    assert int(diff2.flat.front_len[0]) == 2
    assert int(diff2.flat.front_ag_start[fbase + 1]) == int(diff2.flat.front_ag_start[fbase + 0])
    assert int(diff2.flat.front_ag_end[fbase + 1]) == int(diff2.flat.front_ag_end[fbase + 0])


def test_union_fresh_materialization_general_and_single_point() -> None:
    """Fresh-union materialization (code 0): the general >=2 x >=2 case plus both
    single-point fresh paths (left len 1 not dominated; right len 1 not dominated but
    dominating, forcing survivor compaction)."""
    # general case in push_back: two 2-point antichain packets -> fresh 4-point aggregate
    diff = FlatVsListDifferential([5])
    diff.push_back(0, 12, [(5, 1, 3), (6, 2, 4)])
    diff.push_back(0, 11, [(7, 3, 1), (8, 4, 2)])
    base = int(diff.flat.seg_off[0])
    assert int(diff.flat.back_ag_start[base + 1]) == int(diff.flat.back_ag_end[base + 0])
    _front, back = diff.flat.full_state(0)
    assert back[1][2] == ((5, 1, 3), (6, 2, 4), (7, 3, 1), (8, 4, 2))

    # right len 1 fresh with compaction: candidate dominates every survivor
    diff2 = FlatVsListDifferential([5])
    diff2.push_back(0, 12, [(5, 5, 5), (6, 6, 6)])
    diff2.push_back(0, 11, [(7, 5, 5)])
    _front, back = diff2.flat.full_state(0)
    assert back[1][2] == ((7, 5, 5),)

    # left len 1 fresh during transfer: union(packet(12) len 1 not dominated, aggregate)
    diff3 = FlatVsListDifferential([5])
    diff3.push_back(0, 12, [(2, 0, 9)])
    diff3.push_back(0, 11, [(5, 5, 5), (6, 6, 6)])
    diff3.pop_expired_after(0, 12)
    front, _back = diff3.flat.full_state(0)
    assert front == (
        (11, ((5, 5, 5), (6, 6, 6))),
        (12, ((2, 0, 9), (5, 5, 5), (6, 6, 6))),
    )


def test_repeated_shared_aggregate_ranges_across_consecutive_front_entries() -> None:
    """Three consecutive front entries share ONE aggregate range: the transfer seed (from
    the smallest alpha) dominates every later packet, so both follow-up unions return the
    running aggregate (right alias -> range share). The shared entries then survive a
    partial pop with content intact."""
    diff = FlatVsListDifferential([5])
    diff.pop_expired_after(0, 12)
    diff.push_back(0, 12, [(2, 9, 9)])
    diff.push_back(0, 11, [(3, 8, 8)])
    diff.push_back(0, 10, [(9, 0, 0), (1, 8, 0)])  # transfer seed; dominates both singles
    diff.pop_expired_after(0, 12)  # transfer, no pops (12 <= 12)
    base = int(diff.flat.seg_off[0])
    assert int(diff.flat.front_len[0]) == 3
    ranges = {
        (int(diff.flat.front_ag_start[base + i]), int(diff.flat.front_ag_end[base + i]))
        for i in range(3)
    }
    assert len(ranges) == 1, f"expected one shared aggregate range, got {ranges}"
    front, _back = diff.flat.full_state(0)
    shared = ((9, 0, 0), (1, 8, 0))
    assert front == ((10, shared), (11, shared), (12, shared))
    # window slides: partial pops over the shared entries stay exact
    diff.pop_expired_after(0, 11)
    diff.pop_expired_after(0, 10)
    assert int(diff.flat.front_len[0]) == 1


def test_transfer_then_partial_front_pop_keeps_survivors_exact() -> None:
    """Transfer followed by PARTIAL front popping (survivors remain), then continued live
    use: new back pushes with survivors present (no transfer), and a mid-pop transfer once
    the front drains."""
    diff = FlatVsListDifferential([5])
    diff.pop_expired_after(0, 13)
    diff.push_back(0, 13, [(1, 1, 1)])
    diff.push_back(0, 12, [(2, 2, 2)])
    diff.push_back(0, 11, [(3, 3, 3)])
    diff.push_back(0, 10, [(4, 4, 4)])
    diff.pop_expired_after(0, 13)  # transfer all four, no pops
    assert int(diff.flat.front_len[0]) == 4
    assert int(diff.flat.back_len[0]) == 0
    diff.pop_expired_after(0, 11)  # pops 13, 12 -> survivors (10, 11)
    assert int(diff.flat.front_len[0]) == 2
    diff.push_back(0, 9, [(0, 0, 9)])
    assert int(diff.flat.back_len[0]) == 1
    diff.pop_expired_after(0, 10)  # front non-empty: pops 11, NO transfer
    assert int(diff.flat.front_len[0]) == 1
    assert int(diff.flat.back_len[0]) == 1
    diff.pop_expired_after(0, 9)  # pops 10, front empties, MID-POP transfer of alpha 9
    assert int(diff.flat.front_len[0]) == 1
    assert int(diff.flat.back_len[0]) == 0
    front, _back = diff.flat.full_state(0)
    assert front == ((9, ((0, 0, 9),)),)


def test_arena_growth_during_back_aggregation() -> None:
    """Grow-doubling triggered while aggregating at the BACK: the second push's packet
    staging outgrows the packet arena and its union outgrows the aggregate arena. Live
    rows must be preserved verbatim across the growth."""
    diff = FlatVsListDifferential([5], initial_arena_rows=4)
    diff.push_back(0, 12, [(1, 1, 0), (2, 2, 0), (3, 3, 0)])
    pk_cap_before = int(diff.flat.back_pk_arenas[0].shape[0])
    ag_cap_before = int(diff.flat.back_ag_arenas[0].shape[0])
    assert pk_cap_before == 4 and ag_cap_before == 4
    diff.push_back(0, 11, [(4, 4, 0), (5, 5, 0), (6, 6, 0)])  # antichain: 6-point union
    assert int(diff.flat.back_pk_arenas[0].shape[0]) > pk_cap_before
    assert int(diff.flat.back_ag_arenas[0].shape[0]) > ag_cap_before
    _front, back = diff.flat.full_state(0)
    assert back[1][2] == ((1, 1, 0), (2, 2, 0), (3, 3, 0), (4, 4, 0), (5, 5, 0), (6, 6, 0))


def test_arena_growth_during_front_transfer() -> None:
    """Grow-doubling triggered while transferring to the FRONT: the second popped entry's
    union needs more front-arena rows than the seed capacity."""
    diff = FlatVsListDifferential([5], initial_arena_rows=4)
    diff.push_back(0, 12, [(1, 1, 0), (2, 2, 0), (3, 3, 0)])
    diff.push_back(0, 11, [(4, 4, 0), (5, 5, 0), (6, 6, 0)])
    front_cap_before = int(diff.flat.front_ag_arenas[0].shape[0])
    assert front_cap_before == 4
    diff.pop_expired_after(0, 12)  # transfer both entries
    assert int(diff.flat.front_ag_arenas[0].shape[0]) > front_cap_before
    front, _back = diff.flat.full_state(0)
    assert front[0] == (11, ((4, 4, 0), (5, 5, 0), (6, 6, 0)))
    assert front[1] == (12, ((1, 1, 0), (2, 2, 0), (3, 3, 0), (4, 4, 0), (5, 5, 0), (6, 6, 0)))


def test_packet_arena_offset_reuse_after_complete_transfer() -> None:
    """After a COMPLETE transfer (back_len returns to 0) the next push must reuse the
    packet arena from offset 0 (back_pk_off[seg_base] is the permanent CSR origin) and the
    back aggregate arena from offset 0 (empty-back branch), with exact content."""
    diff = FlatVsListDifferential([5])
    diff.push_back(0, 12, [(1, 1, 0), (2, 2, 0)])
    diff.push_back(0, 11, [(3, 3, 0)])
    base = int(diff.flat.seg_off[0])
    assert int(diff.flat.back_pk_off[base + 2]) == 3  # CSR advanced to 3 staged rows
    diff.pop_expired_after(0, 12)  # complete transfer
    assert int(diff.flat.back_len[0]) == 0
    assert int(diff.flat.front_len[0]) == 2
    diff.push_back(0, 10, [(4, 4, 0), (5, 5, 0), (6, 6, 0)])
    assert int(diff.flat.back_pk_off[base + 0]) == 0
    assert int(diff.flat.back_pk_off[base + 1]) == 3  # packet rows reused offsets [0, 3)
    assert int(diff.flat.back_ag_start[base + 0]) == 0  # aggregate arena reused from 0
    _front, back = diff.flat.full_state(0)
    assert back[0][1] == ((4, 4, 0), (5, 5, 0), (6, 6, 0))
    diff.push_back(0, 9, [(7, 7, 0)])
    assert int(diff.flat.back_pk_off[base + 2]) == 4  # CSR continues past the reused rows


def test_multi_family_segmented_layout_matches_listwise_queues() -> None:
    """Region-family queue shape: several families in CSR segments of SHARED 1D arrays
    (seg_base > 0 for families 1+), one arena set per family, driven in the production
    order (per state: pop, then pushes) -- the exact layout the region packet families use
    (region_seg_off / region_* arrays, response_build_gpu_numba.py:3660-3683). Every
    operation on any family must leave every family bit-identical to its own independent
    List-reference queue (cross-family isolation of the shared arrays)."""
    params = [(1, 2), (3, 3), (2, 1)]  # (start_off, width) per family
    diff = FlatVsListDifferential([width for _, width in params])
    assert int(diff.flat.seg_off[1]) == 5 and int(diff.flat.seg_off[2]) == 11  # seg_base > 0
    rng = random.Random(20260709)
    n = 15
    next_push = [n - 1] * len(params)
    families_live_together = 0
    for state in range(n - 1, -1, -1):
        for family, (start_off, width) in enumerate(params):
            end_off = start_off + width - 1
            high_alpha = state + end_off
            diff.pop_expired_after(family, high_alpha)
            push_state = min(next_push[family], high_alpha - start_off)
            while push_state >= state:
                diff.push_back(family, push_state + start_off, _random_packet(rng, 3))
                push_state -= 1
            next_push[family] = state - 1
        live = sum(
            1
            for family in range(len(params))
            if int(diff.flat.front_len[family]) + int(diff.flat.back_len[family]) > 0
        )
        families_live_together = max(families_live_together, live)
    assert families_live_together >= 2, "schedule never exercised concurrently live families"


def test_window_bound_guard_raises_and_preserves_state() -> None:
    """The family window bound (seg slots = width + 3) is a hard invariant: overfilling the
    back stack must fail loudly and leave the recorded queue state untouched."""
    diff = FlatVsListDifferential([1])  # 4 slots -> at most 3 back entries
    diff.push_back(0, 12, [(1, 1, 1)])
    diff.push_back(0, 11, [(2, 2, 2)])
    diff.push_back(0, 10, [(3, 3, 3)])
    state_before = diff.flat.full_state(0)
    with pytest.raises(ValueError, match="family window bound"):
        diff.flat.push_back(0, 9, [(4, 4, 4)])
    assert diff.flat.full_state(0) == state_before


# ---------------------------------------------------------------------------
# Seeded randomized sweep over production-shaped schedules.
# ---------------------------------------------------------------------------


def _random_packet(rng: random.Random, coord_hi: int) -> list[tuple[int, int, int]]:
    if rng.random() < 0.15:
        # antichain (f and n both increasing): grows aggregates and forces arena growth
        size = rng.randint(3, 6)
        start = rng.randint(0, 3)
        return [(start + i + 1, start + i + 1, rng.randint(0, coord_hi)) for i in range(size)]
    points = [
        (rng.randint(0, coord_hi), rng.randint(0, coord_hi), rng.randint(0, coord_hi))
        for _ in range(rng.randint(0, 4))
    ]
    if points and rng.random() < 0.3:
        points.append(points[0])  # verbatim duplicate: exercises dominated-candidate path
    return points


def _run_production_shaped_schedule(seed: int, family_count: int) -> int:
    """One randomized schedule shaped exactly like the kernel sweep: states walk n-1 -> 0
    with random unreachable gaps; per reachable state and family, pop-expired to the
    window's high edge, then push the newly-live activations in decreasing alpha order.
    Small coordinates create heavy dominance/alias traffic; tiny arenas force growth."""
    rng = random.Random(seed)
    n = rng.randint(6, 48)
    params = [(rng.randint(1, 5), rng.randint(1, 8)) for _ in range(family_count)]
    diff = FlatVsListDifferential([width for _, width in params], initial_arena_rows=4)
    coord_hi = rng.randint(1, 4)
    next_push = [n - 1] * family_count
    states_processed = 0
    state = n - 1
    while state >= 0:
        if rng.random() < 0.25:
            state -= rng.randint(1, 4)  # unreachable-state gap
            continue
        for family, (start_off, width) in enumerate(params):
            end_off = start_off + width - 1
            high_alpha = state + end_off
            diff.pop_expired_after(family, high_alpha)
            push_state = min(next_push[family], high_alpha - start_off)
            while push_state >= state:
                diff.push_back(family, push_state + start_off, _random_packet(rng, coord_hi))
                push_state -= 1
            next_push[family] = state - 1
        states_processed += 1
        state -= 1
    return states_processed


def test_randomized_schedule_sweep_single_family() -> None:
    states_processed = 0
    for seed in range(160):
        states_processed += _run_production_shaped_schedule(seed, family_count=1)
    assert states_processed > 1000, "sweep degenerated: too few states processed"


def test_randomized_schedule_sweep_two_families_segmented() -> None:
    states_processed = 0
    for seed in range(1000, 1040):
        states_processed += _run_production_shaped_schedule(seed, family_count=2)
    assert states_processed > 300, "sweep degenerated: too few states processed"
