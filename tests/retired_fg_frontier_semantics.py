"""Test-only references for retired Issue #116 B/C frontier semantics.

These deliberately use plain Python scans and Lists instead of the production Fenwick tree and
fused hull stack.  They are differential oracles, not alternate runtime routes.

Provenance is committed main ``f00747a5``.  Body mirrors the retired
``touch_body_candidate`` -> ``reduce_touched_body_pairs`` ->
``_numba_hull_filter_body_pairs`` pipeline.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence

import numpy as np
from numba import njit
from numba.typed import List


BodyRow = tuple[int, int, int]
def clamped_end_idx_at_hit(
    n: int,
    activation_idx: int,
    hit: float,
    real_fever_time: float,
    floor_timestamps,
) -> int:
    """Plain-Python retired endpoint search with the production float32 cutoff semantics."""
    raw_end = int(
        np.searchsorted(
            floor_timestamps,
            np.float32(float(hit) + float(real_fever_time)),
            side="left",
        )
    )
    return min(int(n), max(int(activation_idx) + 1, int(raw_end)))


def retired_nested_action_reachability_prepass(
    *,
    n: int,
    action_count: int,
    later_fill,
    first_fill,
    later_activation_forced,
    first_activation_forced,
    prefix_perfect_hit,
    prefix_perfect_valid,
    prefix_late_hit,
    prefix_late_valid,
    capped_perfect_edge_e,
    capped_late_edge_e,
    capped_eg_perfect_e,
    capped_eg_late_e,
    capped_perfect_exit_e,
    capped_late_exit_e,
    real_fever_time: float,
    real_time_idx: int,
    use_forced_great_timing_i: int,
    region_starts,
    region_offsets,
    region_activations,
    region_great_ends,
    region_is_greats,
    region_act_hits,
    region_perfect_hits,
    region_perfect_valids,
    perfect_floor_timestamps,
    great_floor_timestamps,
):
    """Retired O(reachable states * actions) activation scan from main ``c3d13ac3``. Every fever end is searched
    here (the early-Great reach too), so the scan also checks the fever-end tables the production prepass reads."""
    from gear_optimizer.frontier.producer_kernels import late_edge_extends

    def great_floor_extended_end_at_hit(n, activation, hit, real_fever_time, great_floor_timestamps) -> int:
        return clamped_end_idx_at_hit(n, activation, hit, real_fever_time, great_floor_timestamps)

    def mark_early_great_reachable_from_hit(
        reachable, n, activation, base_e, activation_hit, great_floor_timestamps, real_fever_time
    ) -> int:
        if base_e < 0 or activation < 0 or activation >= n:
            return 0
        eg_e = clamped_end_idx_at_hit(n, activation, activation_hit, real_fever_time, great_floor_timestamps)
        for end in range(base_e + 1, eg_e + 1):
            reachable[end] = True
        return max(0, eg_e - base_e)

    def mark_perfect(activation: int) -> int:
        if int(prefix_perfect_valid[int(activation)]) == 0:
            return 0
        edge_e = int(capped_perfect_edge_e[int(real_time_idx), int(activation)])
        if int(edge_e) < 0:
            return 0
        for end_e in range(min(int(capped_perfect_exit_e[int(real_time_idx), int(activation)]), edge_e), edge_e + 1):
            reachable[int(end_e)] = True
        return int(
            mark_early_great_reachable_from_hit(
                reachable,
                int(n),
                int(activation),
                int(edge_e),
                float(prefix_perfect_hit[int(activation)]),
                great_floor_timestamps,
                float(real_fever_time),
            )
        )

    def mark_late(activation: int) -> int:
        edge_e = -1
        edge_eg_e = 0
        if int(prefix_perfect_valid[int(activation)]) != 0:
            edge_e = int(capped_perfect_edge_e[int(real_time_idx), int(activation)])
            edge_eg_e = int(capped_eg_perfect_e[int(real_time_idx), int(activation)])
        activation_e = -1
        activation_eg_e = 0
        if int(prefix_late_valid[int(activation)]) != 0:
            activation_e = int(capped_late_edge_e[int(real_time_idx), int(activation)])
            activation_eg_e = int(capped_eg_late_e[int(real_time_idx), int(activation)])
        if not late_edge_extends(
            int(edge_e), int(activation_e), int(activation_eg_e), int(edge_eg_e)
        ):
            return 0
        late_exit_e = int(capped_late_exit_e[int(real_time_idx), int(activation)])
        for end_e in range(min(late_exit_e, activation_e), activation_e + 1):
            reachable[int(end_e)] = True
        return int(
            mark_early_great_reachable_from_hit(
                reachable,
                int(n),
                int(activation),
                int(activation_e),
                float(prefix_late_hit[int(activation)]),
                great_floor_timestamps,
                float(real_fever_time),
            )
        )

    def mark_region(section_start: int) -> int:
        max_width = 0
        for idx in range(
            int(region_starts[int(section_start)]),
            int(region_starts[int(section_start) + 1]),
        ):
            activation = int(region_activations[int(idx)])
            if int(region_is_greats[int(idx)]) != 0:
                perfect_e = -1
                perfect_eg_e = -1
                if int(region_perfect_valids[int(idx)]) != 0:
                    perfect_e = int(
                        clamped_end_idx_at_hit(
                            int(n),
                            int(activation),
                            float(region_perfect_hits[int(idx)]),
                            float(real_fever_time),
                            perfect_floor_timestamps,
                        )
                    )
                    perfect_eg_e = int(
                        great_floor_extended_end_at_hit(
                            int(n),
                            int(activation),
                            float(region_perfect_hits[int(idx)]),
                            float(real_fever_time),
                            great_floor_timestamps,
                        )
                    )
                activation_hit = float(region_act_hits[int(idx)])
                edge_e = int(
                    clamped_end_idx_at_hit(
                        int(n),
                        int(activation),
                        float(activation_hit),
                        float(real_fever_time),
                        perfect_floor_timestamps,
                    )
                )
                activation_eg_e = int(
                    great_floor_extended_end_at_hit(
                        int(n),
                        int(activation),
                        float(activation_hit),
                        float(real_fever_time),
                        great_floor_timestamps,
                    )
                )
                if int(perfect_e) >= 0 and not late_edge_extends(
                    int(perfect_e),
                    int(edge_e),
                    int(activation_eg_e),
                    int(perfect_eg_e),
                ):
                    continue
            else:
                activation_hit = float(region_perfect_hits[int(idx)])
                edge_e = int(
                    clamped_end_idx_at_hit(
                        int(n),
                        int(activation),
                        float(activation_hit),
                        float(real_fever_time),
                        perfect_floor_timestamps,
                    )
                )
            reachable[int(edge_e)] = True
            exit_table = capped_perfect_exit_e if int(region_is_greats[int(idx)]) == 0 else capped_late_exit_e
            for end_e in range(min(int(exit_table[int(real_time_idx), int(activation)]), int(edge_e)), int(edge_e)):
                reachable[int(end_e)] = True
            width = int(
                mark_early_great_reachable_from_hit(
                    reachable,
                    int(n),
                    int(activation),
                    int(edge_e),
                    float(activation_hit),
                    great_floor_timestamps,
                    float(real_fever_time),
                )
            )
            if int(width) > int(max_width):
                max_width = int(width)
        return int(max_width)

    reachable = np.zeros(int(n) + 1, dtype=np.bool_)
    reachable[int(n)] = True
    perfect_activation_processed = np.zeros(int(n), dtype=np.bool_)
    late_activation_processed = np.zeros(int(n), dtype=np.bool_)
    max_eg_width = 0

    for action_idx in range(int(action_count)):
        fill = int(first_fill[int(action_idx)])
        if int(fill) >= int(n):
            continue
        if not perfect_activation_processed[int(fill)]:
            perfect_activation_processed[int(fill)] = True
            max_eg_width = max(int(max_eg_width), mark_perfect(int(fill)))
        if (
            int(use_forced_great_timing_i) != 0
            and int(first_activation_forced[int(action_idx)]) >= 0
            and not late_activation_processed[int(fill)]
        ):
            late_activation_processed[int(fill)] = True
            max_eg_width = max(int(max_eg_width), mark_late(int(fill)))

    if int(use_forced_great_timing_i) != 0:
        max_eg_width = max(
            int(max_eg_width),
            int(
                mark_region(0)
            ),
        )

    for state_i in range(int(n)):
        if not reachable[int(state_i)]:
            continue
        for action_idx in range(int(action_count)):
            activation = int(state_i) + int(later_fill[int(action_idx)])
            if int(activation) >= int(n):
                continue
            if not perfect_activation_processed[int(activation)]:
                perfect_activation_processed[int(activation)] = True
                max_eg_width = max(int(max_eg_width), mark_perfect(int(activation)))
            if (
                int(use_forced_great_timing_i) != 0
                and int(later_activation_forced[int(action_idx)]) >= 0
                and not late_activation_processed[int(activation)]
            ):
                late_activation_processed[int(activation)] = True
                max_eg_width = max(int(max_eg_width), mark_late(int(activation)))
        if int(use_forced_great_timing_i) != 0:
            max_eg_width = max(
                int(max_eg_width),
                int(
                    mark_region(int(state_i) + 1)
                ),
            )
    return reachable, int(max_eg_width)


def retired_region_rows(*, action_k, raw_fever_fill: float, timestamps, hit_times, lanes):
    """The region core table as it was laid out before it was organised by activation: per section start 0 .. n its
    valid runs in enumeration order (action ascending, the region-2 offset before the shifted-head one), every run
    built on its own with the general kernels. Returns (starts, offsets, activations, great_ends, is_greats,
    act_hits, perfect_hits, perfect_valids), the hits as times (-1.0: none)."""
    from gear_optimizer.frontier import producer_kernels as kernels

    n = int(timestamps.shape[0])
    perfect_candidates, great_candidates = hit_times.perfect_candidate_timestamps, hit_times.great_candidate_timestamps
    stop = int(kernels.region2_k_scan_stop(len(action_k), raw_fever_fill))
    starts = [0]
    rows: list[tuple[int, int, int, int, float, float, int]] = []
    for section_start in range(n + 1):
        shifted = 1 if kernels.has_shifted_head_region(section_start, raw_fever_fill) else -1
        for action, k in enumerate(int(value) for value in action_k):
            region = int(kernels.region2_offset_for_count(section_start, k, raw_fever_fill, n)) if action < stop else -1
            for offset in (region,) if shifted == region else (region, shifted):
                if offset < 1:
                    continue
                run_start = section_start + offset
                activation, is_great = kernels.fill_crossing_run(section_start, run_start, k, raw_fever_fill, n)
                if activation < 0:
                    continue
                if is_great:
                    great_end, _token = kernels.minimal_reachable_region_great_end(
                        activation, section_start, run_start, raw_fever_fill, timestamps, hit_times, lanes, n
                    )
                    if great_end < 0:
                        continue
                    act_hit = kernels.late_great_activation_hit_for_run(
                        activation, timestamps, perfect_candidates, great_candidates,
                        hit_times.late_great_floor_timestamps, run_start, great_end - run_start, n,
                    )[0]
                    perfect_hit, perfect_valid, _token = kernels.perfect_activation_hit_for_run(
                        activation, timestamps, perfect_candidates, great_candidates, run_start, great_end - run_start, n
                    )
                    rows.append((
                        offset, activation, great_end, 1, float(act_hit), float(perfect_hit) if perfect_valid else -1.0,
                        int(perfect_valid),
                    ))
                    continue
                great_end = min(n, run_start + k)
                if great_end <= run_start:
                    continue
                perfect_hit, perfect_valid, _token = kernels.perfect_activation_hit_for_run(
                    activation, timestamps, perfect_candidates, great_candidates, run_start, great_end - run_start, n
                )
                if not perfect_valid or not kernels.activation_reachable_contiguous_run(
                    activation, float(perfect_hit), timestamps, hit_times, lanes, raw_fever_fill,
                    (section_start, n, run_start, great_end - run_start), 0,
                ):
                    continue
                rows.append((offset, activation, great_end, 0, -1.0, float(perfect_hit), 1))
        starts.append(len(rows))
    columns = list(zip(*rows)) if rows else [()] * 7
    return (
        np.asarray(starts, dtype=np.int64),
        *(np.asarray(columns[index], dtype=np.int32) for index in range(4)),
        np.asarray(columns[4], dtype=np.float64),
        np.asarray(columns[5], dtype=np.float64),
        np.asarray(columns[6], dtype=np.int32),
    )


def region_table_runs(table, hit_of_token, section_start: int):
    """What a region table (producer_kernels.region_core_table) holds at one section start: its head rows there in
    order, as (offset, activation, Great end, late-Great hit, Perfect hit), and the set of (activation, Great end,
    late-Great hit, Perfect hit) its key rows hold there. Hits are times (-1.0: none)."""
    head_starts, head_rows, key_starts, key_rows = table

    def hit(token: int) -> float:
        return float(hit_of_token[token]) if token >= 0 else -1.0

    head = []
    if section_start + 1 < head_starts.shape[0]:
        head = [
            (int(row[0]), int(row[1]), int(row[2]), hit(int(row[3])), hit(int(row[4])))
            for row in head_rows[int(head_starts[section_start]) : int(head_starts[section_start + 1])]
        ]
    keys = set()
    for activation in range(key_starts.shape[0] - 1):
        for row in key_rows[int(key_starts[activation]) : int(key_starts[activation + 1])]:
            if int(row[0]) <= section_start <= int(row[1]):
                keys.add((activation, int(row[2]), hit(int(row[3])), hit(int(row[4]))))
    return head, keys


def retired_touch_body_candidates(
    rows: Sequence[BodyRow], *, pair_mod: int
) -> tuple[list[int], dict[int, int]]:
    """Plain-Python first-stamp registration and packed-pair max from raw candidate rows."""
    touched_pair: list[int] = []
    best_fever_by_pair: dict[int, int] = {}
    for raw_body_fever, raw_body_great, raw_body_fever_great in rows:
        body_fever = int(raw_body_fever)
        body_great = int(raw_body_great)
        body_fever_great = int(raw_body_fever_great)
        if body_fever_great > body_great:
            continue
        normal_great = int(body_great) - int(body_fever_great)
        if body_fever_great < 0 or body_fever_great >= int(pair_mod):
            raise ValueError("retired body candidate exceeded pair radix")
        pair_idx = int(normal_great) * int(pair_mod) + int(body_fever_great)
        if pair_idx not in best_fever_by_pair:
            touched_pair.append(int(pair_idx))
            best_fever_by_pair[int(pair_idx)] = int(body_fever)
        elif int(body_fever) > int(best_fever_by_pair[int(pair_idx)]):
            best_fever_by_pair[int(pair_idx)] = int(body_fever)
    return touched_pair, best_fever_by_pair


def retired_body_reduce_from_raw_candidates(
    rows: Sequence[BodyRow], *, pair_mod: int
) -> list[BodyRow]:
    touched_pair, best_fever_by_pair = retired_touch_body_candidates(
        rows, pair_mod=int(pair_mod)
    )
    return retired_two_stage_body_reduce(
        pair_mod=int(pair_mod),
        touched_pair=touched_pair,
        best_fever_by_pair=best_fever_by_pair,
    )


def retired_two_stage_body_reduce(
    *,
    pair_mod: int,
    touched_pair: Sequence[int],
    best_fever_by_pair: Mapping[int, int] | Sequence[int],
) -> list[BodyRow]:
    """Retired sorted Pareto reduce followed by its per-normal-Great hull filter."""
    reduced: list[BodyRow] = []
    processed: list[tuple[int, int]] = []
    sorted_pairs = sorted(int(value) for value in touched_pair)
    idx = 0
    while idx < len(sorted_pairs):
        pair_idx = int(sorted_pairs[idx])
        idx += 1
        while idx < len(sorted_pairs) and int(sorted_pairs[idx]) == int(pair_idx):
            idx += 1
        normal_great, fever_great = divmod(int(pair_idx), int(pair_mod))
        body_fever = int(best_fever_by_pair[int(pair_idx)])
        prefix_max = max(
            (
                prior_fever
                for prior_fever_great, prior_fever in processed
                if int(prior_fever_great) <= int(fever_great)
            ),
            default=-1,
        )
        if int(body_fever) > int(prefix_max):
            reduced.append(
                (int(body_fever), int(normal_great) + int(fever_great), int(fever_great))
            )
        processed.append((int(fever_great), int(body_fever)))

    if len(reduced) <= 2:
        return reduced

    ordered = sorted(
        reduced,
        key=lambda row: (int(row[1]) - int(row[2]), int(row[0]), -int(row[2])),
    )
    output: list[BodyRow] = []
    group: list[BodyRow] = []
    group_normal_great: int | None = None
    for row in ordered:
        normal_great = int(row[1]) - int(row[2])
        if group_normal_great is None or int(normal_great) == int(group_normal_great):
            group.append(row)
            group_normal_great = int(normal_great)
            continue
        output.extend(_retired_body_hull_group(group))
        group = [row]
        group_normal_great = int(normal_great)
    output.extend(_retired_body_hull_group(group))
    return output


def _retired_body_hull_group(rows: Sequence[BodyRow]) -> list[BodyRow]:
    if len(rows) <= 2:
        return list(rows)
    stack: list[BodyRow] = []
    for row in rows:
        x = int(row[0])
        y = -int(row[2])
        while len(stack) >= 2:
            x1, y1 = int(stack[-2][0]), -int(stack[-2][2])
            x2, y2 = int(stack[-1][0]), -int(stack[-1][2])
            cross = (x2 - x1) * (y - y1) - (y2 - y1) * (x - x1)
            if int(cross) < 0:
                break
            stack.pop()
        stack.append(row)
    return stack

