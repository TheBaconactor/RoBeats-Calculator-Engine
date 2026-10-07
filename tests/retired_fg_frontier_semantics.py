"""Test-only references for retired Issue #116 B/C frontier semantics.

These deliberately use plain Python scans and Lists instead of the production Fenwick tree and
fused hull stack.  They are differential oracles, not alternate runtime routes.

Provenance is committed main ``f00747a5``.  Body mirrors the retired
``_numba_touch_body_candidate`` -> ``_numba_reduce_touched_body_pairs`` ->
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
    """Retired O(reachable states * actions) activation scan from main ``c3d13ac3``."""
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_numba import (
        _numba_great_floor_extended_end_at_hit,
        _numba_late_edge_extends,
        _numba_mark_early_great_reachable_from_hit,
    )

    def mark_perfect(activation: int) -> int:
        if int(prefix_perfect_valid[int(activation)]) == 0:
            return 0
        edge_e = int(capped_perfect_edge_e[int(real_time_idx), int(activation)])
        if int(edge_e) < 0:
            return 0
        for end_e in range(min(int(capped_perfect_exit_e[int(real_time_idx), int(activation)]), edge_e), edge_e + 1):
            reachable[int(end_e)] = True
        return int(
            _numba_mark_early_great_reachable_from_hit(
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
        if not _numba_late_edge_extends(
            int(edge_e), int(activation_e), int(activation_eg_e), int(edge_eg_e)
        ):
            return 0
        late_exit_e = int(capped_late_exit_e[int(real_time_idx), int(activation)])
        for end_e in range(min(late_exit_e, activation_e), activation_e + 1):
            reachable[int(end_e)] = True
        return int(
            _numba_mark_early_great_reachable_from_hit(
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
                        _numba_great_floor_extended_end_at_hit(
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
                    _numba_great_floor_extended_end_at_hit(
                        int(n),
                        int(activation),
                        float(activation_hit),
                        float(real_fever_time),
                        great_floor_timestamps,
                    )
                )
                if int(perfect_e) >= 0 and not _numba_late_edge_extends(
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
                _numba_mark_early_great_reachable_from_hit(
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

