"""Exact packet-monoid reference for FG body frontiers.

This is the replacement reference for the abandoned backward ``(Lambda, q)``
deque idea. It does not optimize the sliding windows yet; it expresses the
packet recurrence directly and measures the interval skyline width ``chi`` that
the optimized implementation must keep small.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

BodyPoint = tuple[int, int, int]  # body_fever, body_great, body_fever_great
PacketPoint = tuple[int, int, int]  # body_fever, shifted normal-great N, body_fever_great
FamilyMode = Literal["P", "L"]


@dataclass(frozen=True, slots=True)
class PacketFamily:
    mode: FamilyMode
    defect: int
    start_offset: int
    end_offset: int


@dataclass(frozen=True, slots=True)
class PacketBodyStats:
    families: tuple[PacketFamily, ...]
    max_body_width: int
    max_interval_width: int
    packets_built: int = 0
    max_active_packets: int = 0


@dataclass(frozen=True, slots=True)
class _QueueEntry:
    alpha: int
    packet: tuple[PacketPoint, ...]
    aggregate: tuple[PacketPoint, ...]


class _SlidingPacketQueue:
    def __init__(self) -> None:
        self._front: list[_QueueEntry] = []
        self._back: list[_QueueEntry] = []

    def __len__(self) -> int:
        return len(self._front) + len(self._back)

    def _transfer(self) -> None:
        aggregate: tuple[PacketPoint, ...] = ()
        while self._back:
            entry = self._back.pop()
            aggregate = _packet_skyline([*entry.packet, *aggregate])
            self._front.append(_QueueEntry(entry.alpha, entry.packet, aggregate))

    def _peek_front_alpha(self) -> int | None:
        if not self._front:
            self._transfer()
        if not self._front:
            return None
        return int(self._front[-1].alpha)

    def pop_expired_after(self, high_alpha: int) -> None:
        while True:
            alpha = self._peek_front_alpha()
            if alpha is None or int(alpha) <= int(high_alpha):
                return
            self._front.pop()

    def push_back(self, alpha: int, packet: tuple[PacketPoint, ...]) -> None:
        if not packet:
            return
        previous = self._back[-1].aggregate if self._back else ()
        aggregate = _packet_skyline([*previous, *packet])
        self._back.append(_QueueEntry(int(alpha), packet, aggregate))

    def aggregate(self) -> tuple[PacketPoint, ...]:
        front = self._front[-1].aggregate if self._front else ()
        back = self._back[-1].aggregate if self._back else ()
        if not front:
            return back
        if not back:
            return front
        return _packet_skyline([*front, *back])


def _edge_end(args: dict, activation_idx: int, *, late_great: bool) -> int:
    n = int(args["n"])
    if int(activation_idx) >= n:
        return -1
    real_time_idx = int(args["real_time_idx"])
    edge_e = int(args["timestamp_end_idx"][real_time_idx, int(activation_idx)])
    if bool(args["use_forced_great_timing_i"]) and bool(late_great):
        late_e = int(args["great_end_idx"][real_time_idx, int(activation_idx)])
        if late_e > edge_e:
            edge_e = int(late_e)
    if edge_e <= int(activation_idx):
        edge_e = int(activation_idx) + 1
    return min(int(edge_e), n)


def _body_skyline(points: list[BodyPoint]) -> frozenset[BodyPoint]:
    normalized: list[tuple[int, int, int]] = []
    for body_fever, body_great, body_fever_great in points:
        if int(body_fever_great) > int(body_great):
            continue
        normalized.append((int(body_fever), int(body_great) - int(body_fever_great), int(body_fever_great)))
    kept: list[BodyPoint] = []
    for idx, point in enumerate(normalized):
        body_fever, normal_great, fever_great = point
        dominated = False
        for other_idx, other in enumerate(normalized):
            if other_idx == idx:
                continue
            other_fever, other_normal, other_fever_great = other
            if (
                other_fever >= body_fever
                and other_normal <= normal_great
                and other_fever_great <= fever_great
                and other != point
            ):
                dominated = True
                break
            if other == point and other_idx < idx:
                dominated = True
                break
        if not dominated:
            kept.append((body_fever, normal_great + fever_great, fever_great))
    return frozenset(kept)


def _packet_skyline(points: list[PacketPoint]) -> tuple[PacketPoint, ...]:
    kept: list[PacketPoint] = []
    for idx, point in enumerate(points):
        body_fever, shifted_normal, fever_great = point
        dominated = False
        for other_idx, other in enumerate(points):
            if other_idx == idx:
                continue
            other_fever, other_shifted_normal, other_fever_great = other
            if (
                other_fever >= body_fever
                and other_shifted_normal <= shifted_normal
                and other_fever_great <= fever_great
                and other != point
            ):
                dominated = True
                break
            if other == point and other_idx < idx:
                dominated = True
                break
        if not dominated:
            kept.append((int(body_fever), int(shifted_normal), int(fever_great)))
    return tuple(kept)


def _families_from_actions(args: dict) -> tuple[PacketFamily, ...]:
    offsets_by_key: dict[tuple[FamilyMode, int], set[int]] = {}
    for action_idx in range(int(args["action_count"])):
        offset = int(args["later_fill"][action_idx])
        normal_forced = int(args["later_forced"][action_idx])
        offsets_by_key.setdefault(("P", normal_forced - (2 * offset)), set()).add(offset)
        late_prefix = int(args["later_activation_forced"][action_idx])
        if late_prefix >= 0:
            offsets_by_key.setdefault(("L", late_prefix - (2 * offset)), set()).add(offset)

    families: list[PacketFamily] = []
    for (mode, defect), offsets in sorted(offsets_by_key.items(), key=lambda item: (item[0][0], item[0][1])):
        sorted_offsets = sorted(int(v) for v in offsets)
        if not sorted_offsets:
            continue
        run_start = sorted_offsets[0]
        prev = sorted_offsets[0]
        for value in sorted_offsets[1:]:
            if int(value) == int(prev) + 1:
                prev = int(value)
                continue
            families.append(PacketFamily(mode, int(defect), int(run_start), int(prev)))
            run_start = int(value)
            prev = int(value)
        families.append(PacketFamily(mode, int(defect), int(run_start), int(prev)))
    return tuple(families)


def _packet_for_activation(
    args: dict,
    family: PacketFamily,
    activation: int,
    tails: dict[int, frozenset[BodyPoint]],
) -> tuple[PacketPoint, ...]:
    if int(activation) < 100 or int(activation) >= int(args["n"]):
        return ()
    perfect_e = _edge_end(args, int(activation), late_great=False)
    if perfect_e < 0:
        return ()
    if family.mode == "P":
        edge_e = perfect_e
        fever_great_delta = 0
    else:
        edge_e = _edge_end(args, int(activation), late_great=True)
        if edge_e <= perfect_e:
            return ()
        fever_great_delta = 1

    fever_len = int(edge_e) - int(activation)
    packet_points: list[PacketPoint] = []
    for tail_fever, tail_great, tail_fever_great in tails.get(edge_e, frozenset({(0, 0, 0)})):
        tail_normal_great = int(tail_great) - int(tail_fever_great)
        packet_points.append(
            (
                int(tail_fever) + fever_len,
                tail_normal_great + (2 * int(activation)) + int(family.defect),
                int(tail_fever_great) + fever_great_delta,
            )
        )
    return _packet_skyline(packet_points)


def reference_body_dp(args: dict) -> dict[int, frozenset[BodyPoint]]:
    """Direct reference body DP matching the production Numba recurrence."""

    n = int(args["n"])
    tails: dict[int, frozenset[BodyPoint]] = {n: frozenset({(0, 0, 0)})}
    for state in range(n - 1, 99, -1):
        candidates: list[BodyPoint] = []
        prev_fill = prev_edge_e = prev_activation_fill = prev_activation_e = -1
        for action_idx in range(int(args["action_count"])):
            fill = int(args["later_fill"][action_idx])
            activation = int(state) + fill
            edge_e = _edge_end(args, activation, late_great=False)
            if edge_e < 0:
                continue
            forced_start = int(state) + 1
            if fill != prev_fill or edge_e != prev_edge_e:
                prev_fill = fill
                prev_edge_e = edge_e
                body_fever = max(0, min(edge_e, n) - max(activation, 100))
                body_great = max(0, min(n, forced_start + int(args["later_forced"][action_idx])) - max(forced_start, 100))
                for tail_fever, tail_great, tail_fever_great in tails.get(edge_e, frozenset({(0, 0, 0)})):
                    candidates.append((body_fever + tail_fever, body_great + tail_great, tail_fever_great))

            late_prefix = int(args["later_activation_forced"][action_idx])
            if bool(args["use_forced_great_timing_i"]) and late_prefix >= 0:
                activation_e = _edge_end(args, activation, late_great=True)
                if activation_e > edge_e:
                    if fill == prev_activation_fill and activation_e == prev_activation_e:
                        continue
                    prev_activation_fill = fill
                    prev_activation_e = activation_e
                    body_fever = max(0, min(activation_e, n) - max(activation, 100))
                    normal_great = max(0, min(n, forced_start + late_prefix) - max(forced_start, 100))
                    body_great = normal_great + 1
                    body_fever_great = 1 if activation < min(activation_e, n) else 0
                    for tail_fever, tail_great, tail_fever_great in tails.get(
                        activation_e, frozenset({(0, 0, 0)})
                    ):
                        candidates.append(
                            (
                                body_fever + tail_fever,
                                body_great + tail_great,
                                body_fever_great + tail_fever_great,
                            )
                        )
        tails[state] = _body_skyline(candidates) if candidates else frozenset({(0, 0, 0)})
    return tails


def packet_body_dp(args: dict) -> tuple[dict[int, frozenset[BodyPoint]], PacketBodyStats]:
    """Packet recurrence with exact two-stack sliding skyline aggregates."""

    n = int(args["n"])
    families = _families_from_actions(args)
    queues = {_family: _SlidingPacketQueue() for _family in families}
    tails: dict[int, frozenset[BodyPoint]] = {n: frozenset({(0, 0, 0)})}
    max_body_width = 1
    max_interval_width = 0
    packets_built = 0
    max_active_packets = 0
    for state in range(n - 1, 99, -1):
        body_candidates: list[BodyPoint] = []
        for family in families:
            queue = queues[family]
            queue.pop_expired_after(int(state) + int(family.end_offset))
            activation = int(state) + int(family.start_offset)
            packet = _packet_for_activation(args, family, activation, tails)
            if packet:
                packets_built += 1
                queue.push_back(activation, packet)
            interval_skyline = queue.aggregate()
            max_interval_width = max(max_interval_width, len(interval_skyline))
            max_active_packets = max(max_active_packets, len(queue))
            for body_fever, shifted_normal, fever_great in interval_skyline:
                true_normal_great = int(shifted_normal) - (2 * int(state))
                body_candidates.append((int(body_fever), true_normal_great + int(fever_great), int(fever_great)))
        tails[state] = _body_skyline(body_candidates) if body_candidates else frozenset({(0, 0, 0)})
        max_body_width = max(max_body_width, len(tails[state]))
    return tails, PacketBodyStats(
        families=families,
        max_body_width=int(max_body_width),
        max_interval_width=int(max_interval_width),
        packets_built=int(packets_built),
        max_active_packets=int(max_active_packets),
    )
