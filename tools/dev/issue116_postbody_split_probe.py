"""Phase split for the FG first-frontier kernel (Issue #116 K0 audit).

This probe splits the current production driver into its real phases by running a
VERBATIM copy with cumulative skip flags:

  cfg=0  full driver (output byte-checked against the production kernel)
  cfg=1  skip the FINAL reduce+envelope filter(s) of the first frontier
  cfg=2  ... and skip the first-frontier region2 emit
  cfg=3  ... and skip the branch-A bucket loop / else-branch first generation
  cfg=4  ... and skip the whole head-state loop (leaves prepass + body DP)
  cfg=5  ... and skip the body DP (leaves the reachability/radix prepass)

Deltas between consecutive configs price each phase with production-real upstream
inputs. Measurement-only research tooling: production sub-kernels are called
directly (never copied), and cfg=0 equality with the production kernel gates the
validity of every reported number.

Usage:
    python tools/dev/issue116_postbody_split_probe.py --song "M1LLI0N PP (Full Version)" --diff Hard
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

from numba import njit, types  # noqa: E402
from numba.typed import Dict, List  # noqa: E402

from gear_optimizer.solver.taichi_gem.force_greats import response_build_gpu_numba as _rb  # noqa: E402
from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_reducer import (  # noqa: E402
    _exact_action_fill_runs,
)
from issue116_amdahl_probe import SongProbeInputs, _find_chart  # noqa: E402

_SURFACE_TYPE = _rb._NUMBA_SURFACE_TYPE
_SCORES_TYPE = _rb._NUMBA_HEAD_SCORES_TYPE


@njit(cache=True, nogil=True)
def _split_driver(
    cfg: int,
    census: int,
    n: int,
    action_count: int,
    region_action_count: int,
    raw_fever_fill: float,
    action_k,
    later_fill,
    first_fill,
    later_forced,
    first_forced,
    later_activation_forced,
    first_activation_forced,
    perfect_run_starts,
    perfect_run_ends,
    late_run_starts,
    late_run_ends,
    timestamps,
    candidate_high_delta_max,
    perfect_candidate_timestamps,
    great_candidate_timestamps,
    perfect_floor_timestamps,
    great_floor_timestamps,
    lanes,
    prefix_perfect_hit,
    prefix_perfect_valid,
    prefix_late_hit,
    prefix_late_valid,
    timestamp_end_idx,
    perfect_end_idx,
    great_end_idx,
    great_floor_end_idx,
    capped_perfect_edge_e,
    capped_late_edge_e,
    capped_eg_perfect_e,
    capped_eg_late_e,
    real_fever_time: float,
    real_time_idx: int,
    use_forced_great_timing_i: int,
    head_filter_min: int,
    region_starts,
    region_offsets,
    region_activations,
    region_great_ends,
    region_is_greats,
    region_act_hit_ids,
    region_perfect_hit_ids,
    region_perfect_valids,
    region_hit_token_to_id,
    region_perfect_end_by_hit,
    region_great_end_by_hit,
    ws_pair_values,
    ws_pair_stamps,
    ws_pair_touched,
    ws_bit_values,
    ws_bit_stamps,
    ws_branch_a_values,
    ws_branch_a_stamps,
    ws_perfect_successor,
    ws_perfect_successor_stamps,
    ws_late_successor,
    ws_late_successor_stamps,
    successor_epoch_in: int,
    pair_epoch_in: int,
    bit_epoch_in: int,
    branch_a_epoch_in: int,
):
    # cfg semantics (cumulative skips): 1=final filter, 2=first region2 emit,
    # 3=branch-A buckets / else first-generation, 4=head-state loop.
    reachable, max_eg_width = _rb._numba_first_frontier_reachability_prepass(
        int(n),
        int(action_count),
        later_fill,
        first_fill,
        later_activation_forced,
        first_activation_forced,
        perfect_run_starts,
        perfect_run_ends,
        late_run_starts,
        late_run_ends,
        prefix_perfect_hit,
        prefix_perfect_valid,
        prefix_late_hit,
        prefix_late_valid,
        capped_perfect_edge_e,
        capped_late_edge_e,
        capped_eg_perfect_e,
        capped_eg_late_e,
        float(real_fever_time),
        int(real_time_idx),
        int(use_forced_great_timing_i),
        region_starts,
        region_offsets,
        region_activations,
        region_great_ends,
        region_is_greats,
        region_act_hit_ids,
        region_perfect_hit_ids,
        region_perfect_valids,
        region_perfect_end_by_hit,
        region_great_end_by_hit,
        perfect_floor_timestamps,
        great_floor_timestamps,
        ws_perfect_successor,
        ws_perfect_successor_stamps,
        ws_late_successor,
        ws_late_successor_stamps,
        int(successor_epoch_in),
    )
    states_evaluated = 0
    retained_total = 1
    max_state_frontier = 1
    generated_surfaces = 0
    min_later_fill = max(1, int(later_fill[0]) if int(action_count) > 0 else 1)
    section_bound = int(n) // int(min_later_fill) + 4
    pair_mod = min(int(n) + 1, int(section_bound) * (1 + int(max_eg_width)) + 1)
    pair_size = (int(n) + 1) * int(pair_mod)
    branch_a_bound = (int(pair_mod) + 1) * (int(n) + 2)
    if (
        int(ws_pair_values.shape[0]) < int(pair_size)
        or int(ws_pair_stamps.shape[0]) < int(pair_size)
        or int(ws_pair_touched.shape[0]) < int(pair_size)
        or int(ws_bit_values.shape[0]) < int(pair_mod) + 1
        or int(ws_bit_stamps.shape[0]) < int(pair_mod) + 1
        or int(ws_branch_a_values.shape[0]) < int(branch_a_bound)
        or int(ws_branch_a_stamps.shape[0]) < int(branch_a_bound)
    ):
        raise ValueError("split-probe stamp workspace is undersized for this geometry's pair radix")
    if int(cfg) >= 5:
        return (
            np.zeros((0, 7), dtype=np.uint64),
            0,
            0,
            1,
            1,
            int(pair_epoch_in),
            int(bit_epoch_in),
            int(branch_a_epoch_in),
            0,
            0,
            0,
        )
    best_fever_by_pair = ws_pair_values[: int(pair_size)]
    pair_stamp = ws_pair_stamps[: int(pair_size)]
    touched_pair = ws_pair_touched[: int(pair_size)]
    pair_stamp_value = int(pair_epoch_in)
    bit_values = ws_bit_values[: int(pair_mod) + 1]
    bit_stamps = ws_bit_stamps[: int(pair_mod) + 1]
    bit_stamp_value = int(bit_epoch_in)

    (
        body_values,
        body_starts,
        body_counts,
        states_evaluated,
        generated_surfaces,
        retained_total,
        max_state_frontier,
        pair_stamp_value,
        bit_stamp_value,
    ) = _rb._numba_packet_body_tails_from_precomputed_end_indices(
        int(n),
        int(action_count),
        int(region_action_count),
        float(raw_fever_fill),
        action_k,
        later_fill,
        later_forced,
        later_activation_forced,
        reachable,
        int(use_forced_great_timing_i),
        timestamps,
        candidate_high_delta_max,
        perfect_candidate_timestamps,
        great_candidate_timestamps,
        perfect_floor_timestamps,
        great_floor_timestamps,
        lanes,
        region_starts,
        region_offsets,
        region_activations,
        region_great_ends,
        region_is_greats,
        region_act_hit_ids,
        region_perfect_hit_ids,
        region_perfect_valids,
        region_hit_token_to_id,
        region_perfect_end_by_hit,
        region_great_end_by_hit,
        prefix_perfect_hit,
        prefix_perfect_valid,
        prefix_late_hit,
        prefix_late_valid,
        timestamp_end_idx,
        perfect_end_idx,
        great_end_idx,
        great_floor_end_idx,
        capped_perfect_edge_e,
        capped_late_edge_e,
        capped_eg_perfect_e,
        capped_eg_late_e,
        float(real_fever_time),
        int(real_time_idx),
        int(pair_mod),
        best_fever_by_pair,
        pair_stamp,
        touched_pair,
        int(pair_stamp_value),
        bit_values,
        bit_stamps,
        int(bit_stamp_value),
    )

    head_limit = min(int(n), 100)
    head_pool = np.empty((256, 7), dtype=np.uint64)
    head_pool_cursor = 0
    head_state_start = np.zeros(max(1, int(head_limit)), dtype=np.int64)
    head_state_count = np.zeros(max(1, int(head_limit)), dtype=np.int64)
    region_node_surface = np.empty((64, 7), dtype=np.uint64)
    region_node_next = np.empty(64, dtype=np.int64)
    region_bucket_head = np.full(int(n) + 2, -1, dtype=np.int64)
    region_bucket_tail = np.full(int(n) + 2, -1, dtype=np.int64)
    region_pending_ends = np.empty(int(n) + 2, dtype=np.int64)

    headloop_added = 0
    if int(cfg) < 4:
        for state_i in range(head_limit - 1, -1, -1):
            if not reachable[state_i]:
                continue
            states_evaluated += 1
            generated = List.empty_list(_SURFACE_TYPE)
            generated_scores = List.empty_list(_SCORES_TYPE)
            generated_seen = Dict.empty(_SURFACE_TYPE, types.uint8)
            generated_score_matrix_holder = List.empty_list(_rb._NUMBA_HEAD_SCORE_MATRIX_TYPE)
            generated_score_matrix_count = np.zeros(1, dtype=np.int64)
            generated_count = 0
            bounded_mode = 0
            prev_fill = -1
            prev_edge_e = -1
            prev_activation_fill = -1
            prev_activation_e = -1
            prev_activation_prefix = -1
            for action_idx in range(int(action_count)):
                fill = int(later_fill[int(action_idx)])
                forced_start = int(state_i) + 1
                activation = int(state_i) + int(fill)
                if int(activation) >= int(n):
                    break
                if int(activation) < int(forced_start):
                    continue
                forced_count = int(later_forced[int(action_idx)])
                perfect_hit = float(prefix_perfect_hit[int(activation)])
                perfect_valid = int(prefix_perfect_valid[int(activation)])
                if int(perfect_valid) == 0 or int(forced_count) < 0:
                    edge_e = -1
                else:
                    edge_e = int(capped_perfect_edge_e[int(real_time_idx), int(activation)])
                if (
                    int(edge_e) >= 0
                    and (
                        int(fill) != int(prev_fill)
                        or int(edge_e) != int(prev_edge_e)
                    )
                ):
                    prev_fill = int(fill)
                    prev_edge_e = int(edge_e)
                    edge = _rb._numba_pack_edge(
                        int(n),
                        int(activation),
                        int(edge_e),
                        int(forced_start),
                        min(int(n), int(forced_start) + int(forced_count)),
                        -1,
                    )
                    generated, generated_scores, added, bounded_mode = (
                        _rb._numba_append_head_generated_candidate(
                            generated,
                            generated_scores,
                            generated_seen,
                            generated_score_matrix_holder,
                            generated_score_matrix_count,
                            edge,
                            int(edge_e),
                            body_values,
                            body_starts,
                            body_counts,
                            head_pool,
                            head_state_start,
                            head_state_count,
                            int(head_limit),
                            int(state_i),
                            int(head_limit),
                            int(head_filter_min),
                            int(bounded_mode),
                        )
                    )
                    generated_count += int(added)
                    generated, generated_scores, added, bounded_mode = (
                        _rb._numba_emit_early_great_edges(
                            generated,
                            generated_scores,
                            generated_seen,
                            generated_score_matrix_holder,
                            generated_score_matrix_count,
                            int(n),
                            int(activation),
                            int(edge_e),
                            float(perfect_hit),
                            int(forced_start),
                            min(int(n), int(forced_start) + int(forced_count)),
                            -1,
                            great_floor_timestamps,
                            float(real_fever_time),
                            body_values,
                            body_starts,
                            body_counts,
                            head_pool,
                            head_state_start,
                            head_state_count,
                            int(head_limit),
                            int(state_i),
                            int(head_limit),
                            int(head_filter_min),
                            int(bounded_mode),
                        )
                    )
                    generated_count += int(added)
                prefix_forced = int(later_activation_forced[int(action_idx)])
                activation_hit = 0.0
                activation_e = -1
                if int(use_forced_great_timing_i) != 0 and int(prefix_forced) >= 0:
                    activation_hit = float(prefix_late_hit[int(activation)])
                    activation_valid = int(prefix_late_valid[int(activation)])
                    if int(activation_valid) != 0:
                        activation_e = int(capped_late_edge_e[int(real_time_idx), int(activation)])
                if _rb._numba_late_edge_extends(
                    int(edge_e),
                    int(activation_e),
                    int(capped_eg_late_e[int(real_time_idx), int(activation)]),
                    int(capped_eg_perfect_e[int(real_time_idx), int(activation)]),
                ):
                    if (
                        int(fill) == int(prev_activation_fill)
                        and int(activation_e) == int(prev_activation_e)
                        and int(prefix_forced) == int(prev_activation_prefix)
                    ):
                        continue
                    prev_activation_fill = int(fill)
                    prev_activation_e = int(activation_e)
                    prev_activation_prefix = int(prefix_forced)
                    activation_edge = _rb._numba_pack_edge(
                        int(n),
                        int(activation),
                        int(activation_e),
                        int(forced_start),
                        min(int(n), int(forced_start) + int(prefix_forced)),
                        int(activation),
                    )
                    generated, generated_scores, added, bounded_mode = (
                        _rb._numba_append_head_generated_candidate(
                            generated,
                            generated_scores,
                            generated_seen,
                            generated_score_matrix_holder,
                            generated_score_matrix_count,
                            activation_edge,
                            int(activation_e),
                            body_values,
                            body_starts,
                            body_counts,
                            head_pool,
                            head_state_start,
                            head_state_count,
                            int(head_limit),
                            int(state_i),
                            int(head_limit),
                            int(head_filter_min),
                            int(bounded_mode),
                        )
                    )
                    generated_count += int(added)
                    generated, generated_scores, added, bounded_mode = (
                        _rb._numba_emit_early_great_edges(
                            generated,
                            generated_scores,
                            generated_seen,
                            generated_score_matrix_holder,
                            generated_score_matrix_count,
                            int(n),
                            int(activation),
                            int(activation_e),
                            float(activation_hit),
                            int(forced_start),
                            min(int(n), int(forced_start) + int(prefix_forced)),
                            int(activation),
                            great_floor_timestamps,
                            float(real_fever_time),
                            body_values,
                            body_starts,
                            body_counts,
                            head_pool,
                            head_state_start,
                            head_state_count,
                            int(head_limit),
                            int(state_i),
                            int(head_limit),
                            int(head_filter_min),
                            int(bounded_mode),
                        )
                    )
                    generated_count += int(added)
            generated, generated_scores, added, bounded_mode, region_node_surface, region_node_next = (
                _rb._numba_emit_region2_head_edges(
                    generated,
                    generated_scores,
                    generated_seen,
                    generated_score_matrix_holder,
                    generated_score_matrix_count,
                    region_node_surface,
                    region_node_next,
                    region_bucket_head,
                    region_bucket_tail,
                    region_pending_ends,
                    int(n),
                    int(state_i) + 1,
                    region_starts,
                    region_offsets,
                    region_activations,
                    region_great_ends,
                    region_is_greats,
                    region_act_hit_ids,
                    region_perfect_hit_ids,
                    region_perfect_valids,
                    region_perfect_end_by_hit,
                    region_great_end_by_hit,
                    int(use_forced_great_timing_i),
                    body_values,
                    body_starts,
                    body_counts,
                    head_pool,
                    head_state_start,
                    head_state_count,
                    int(head_limit),
                    int(state_i),
                    int(head_limit),
                    int(head_filter_min),
                    int(bounded_mode),
                )
            )
            generated_count += int(added)
            generated_surfaces += generated_count
            headloop_added += generated_count
            frontier = _rb._numba_head_envelope_filter(
                _rb._numba_reduce(generated), int(state_i), int(head_limit), int(head_filter_min)
            )
            head_pool = _rb._numba_u64_rows_ensure(head_pool, int(head_pool_cursor), len(frontier))
            head_state_start[int(state_i)] = int(head_pool_cursor)
            head_state_count[int(state_i)] = len(frontier)
            for frontier_idx in range(len(frontier)):
                surface = frontier[frontier_idx]
                pool_row = int(head_pool_cursor) + int(frontier_idx)
                head_pool[pool_row, 0] = surface[0]
                head_pool[pool_row, 1] = surface[1]
                head_pool[pool_row, 2] = surface[2]
                head_pool[pool_row, 3] = surface[3]
                head_pool[pool_row, 4] = surface[4]
                head_pool[pool_row, 5] = surface[5]
                head_pool[pool_row, 6] = surface[6]
            head_pool_cursor += len(frontier)
            retained_total += len(frontier)
            if len(frontier) > max_state_frontier:
                max_state_frontier = len(frontier)

    first_generated_count = 0
    bucket_added = 0
    region2_added = 0
    first_frontier = List.empty_list(_SURFACE_TYPE)
    first_region_generated = List.empty_list(_SURFACE_TYPE)
    first_region_scores = List.empty_list(_SCORES_TYPE)
    first_region_seen = Dict.empty(_SURFACE_TYPE, types.uint8)
    first_region_score_matrix_holder = List.empty_list(_rb._NUMBA_HEAD_SCORE_MATRIX_TYPE)
    first_region_score_matrix_count = np.zeros(1, dtype=np.int64)
    first_region_bounded = 0
    branch_a_epoch_out = int(branch_a_epoch_in)
    if int(action_count) > 0 and int(first_fill[0]) >= 100:
        if int(cfg) < 3:
            first_edge_e_by_action = np.empty(int(action_count), dtype=np.int32)
            first_normal_head_by_action = np.empty(int(action_count), dtype=np.int32)
            first_activation_e_by_action = np.empty(int(action_count), dtype=np.int32)
            first_activation_prefix_by_action = np.empty(int(action_count), dtype=np.int32)
            first_activation_head_by_action = np.empty(int(action_count), dtype=np.int32)
            for action_idx in range(int(action_count)):
                fill = int(first_fill[int(action_idx)])
                forced_count = int(first_forced[int(action_idx)])
                edge_valid = 0
                if int(fill) < int(n):
                    edge_valid = int(prefix_perfect_valid[int(fill)])
                edge_e = -1
                if int(edge_valid) != 0 and int(forced_count) >= 0:
                    edge_e = int(capped_perfect_edge_e[int(real_time_idx), int(fill)])
                first_edge_e_by_action[int(action_idx)] = int(edge_e)
                first_normal_head_by_action[int(action_idx)] = min(100, max(0, int(forced_count)))
                prefix_forced = int(first_activation_forced[int(action_idx)])
                activation_e = -1
                if int(use_forced_great_timing_i) != 0 and int(prefix_forced) >= 0 and int(fill) < int(n):
                    activation_valid = int(prefix_late_valid[int(fill)])
                    if int(activation_valid) != 0:
                        activation_e = int(capped_late_edge_e[int(real_time_idx), int(fill)])
                first_activation_e_by_action[int(action_idx)] = int(activation_e)
                first_activation_prefix_by_action[int(action_idx)] = int(prefix_forced)
                first_activation_head_by_action[int(action_idx)] = min(100, max(0, int(prefix_forced)))
            branch_a_width = int(n) + 2
            branch_a_size = (int(pair_mod) + 1) * int(branch_a_width)
            branch_a_values = ws_branch_a_values[: int(branch_a_size)]
            branch_a_stamps = ws_branch_a_stamps[: int(branch_a_size)]
            branch_a_epoch_out = int(branch_a_epoch_in) + 1
            branch_a_stamp = int(branch_a_epoch_out)
            first_reduce_values = np.empty((1024, 3), dtype=np.uint64)
            normal_bucket_offsets = np.zeros(102, dtype=np.int32)
            activation_bucket_offsets = np.zeros(102, dtype=np.int32)
            for action_idx in range(int(action_count)):
                edge_e = int(first_edge_e_by_action[int(action_idx)])
                if int(edge_e) >= 100:
                    hgc = int(first_normal_head_by_action[int(action_idx)])
                    normal_bucket_offsets[int(hgc) + 1] += 1
                activation_e = int(first_activation_e_by_action[int(action_idx)])
                if int(activation_e) >= 100 and _rb._numba_late_edge_extends(
                    int(edge_e),
                    int(activation_e),
                    int(capped_eg_late_e[int(real_time_idx), int(first_fill[int(action_idx)])]),
                    int(capped_eg_perfect_e[int(real_time_idx), int(first_fill[int(action_idx)])]),
                ):
                    hgc = int(first_activation_head_by_action[int(action_idx)])
                    activation_bucket_offsets[int(hgc) + 1] += 1
            for head_great_count in range(101):
                normal_bucket_offsets[int(head_great_count) + 1] += normal_bucket_offsets[int(head_great_count)]
                activation_bucket_offsets[int(head_great_count) + 1] += activation_bucket_offsets[int(head_great_count)]
            normal_actions_by_head = np.empty(int(normal_bucket_offsets[101]), dtype=np.int32)
            activation_actions_by_head = np.empty(int(activation_bucket_offsets[101]), dtype=np.int32)
            normal_bucket_write = np.zeros(101, dtype=np.int32)
            activation_bucket_write = np.zeros(101, dtype=np.int32)
            for action_idx in range(int(action_count)):
                edge_e = int(first_edge_e_by_action[int(action_idx)])
                if int(edge_e) >= 100:
                    hgc = int(first_normal_head_by_action[int(action_idx)])
                    pos = int(normal_bucket_offsets[int(hgc)]) + int(normal_bucket_write[int(hgc)])
                    normal_actions_by_head[int(pos)] = int(action_idx)
                    normal_bucket_write[int(hgc)] += 1
                activation_e = int(first_activation_e_by_action[int(action_idx)])
                if int(activation_e) >= 100 and _rb._numba_late_edge_extends(
                    int(edge_e),
                    int(activation_e),
                    int(capped_eg_late_e[int(real_time_idx), int(first_fill[int(action_idx)])]),
                    int(capped_eg_perfect_e[int(real_time_idx), int(first_fill[int(action_idx)])]),
                ):
                    hgc = int(first_activation_head_by_action[int(action_idx)])
                    pos = int(activation_bucket_offsets[int(hgc)]) + int(activation_bucket_write[int(hgc)])
                    activation_actions_by_head[int(pos)] = int(action_idx)
                    activation_bucket_write[int(hgc)] += 1
            for head_great_count in range(101):
                touched_count = 0
                pair_stamp_value += 1
                prev_fill = -1
                prev_edge_e = -1
                prev_activation_fill = -1
                prev_activation_e = -1
                prev_activation_prefix = -1
                for bucket_idx in range(
                    int(normal_bucket_offsets[int(head_great_count)]),
                    int(normal_bucket_offsets[int(head_great_count) + 1]),
                ):
                    action_idx = int(normal_actions_by_head[int(bucket_idx)])
                    edge_e = int(first_edge_e_by_action[int(action_idx)])
                    fill = int(first_fill[int(action_idx)])
                    forced_count = int(first_forced[int(action_idx)])
                    if (
                        int(fill) != int(prev_fill)
                        or int(edge_e) != int(prev_edge_e)
                    ):
                        prev_fill = int(fill)
                        prev_edge_e = int(edge_e)
                        edge = _rb._numba_pack_edge(
                            int(n),
                            int(fill),
                            int(edge_e),
                            0,
                            min(int(n), int(forced_count)),
                            -1,
                        )
                        touched_count, added_count = _rb._numba_touch_body_tail_array_candidates(
                            edge,
                            int(edge_e),
                            body_values,
                            body_starts,
                            body_counts,
                            int(pair_mod),
                            int(pair_stamp_value),
                            pair_stamp,
                            best_fever_by_pair,
                            touched_pair,
                            int(touched_count),
                        )
                        first_generated_count += int(added_count)
                        eg_e = int(capped_eg_perfect_e[int(real_time_idx), int(fill)])
                        for end_e in range(int(edge_e) + 1, int(eg_e) + 1):
                            edge_eg = _rb._numba_pack_edge_eg(
                                int(n), int(fill), int(end_e), 0,
                                min(int(n), int(forced_count)), -1,
                                int(edge_e), int(end_e),
                            )
                            touched_count, added_eg = _rb._numba_touch_body_tail_array_candidates(
                                edge_eg, int(end_e), body_values, body_starts, body_counts,
                                int(pair_mod), int(pair_stamp_value), pair_stamp,
                                best_fever_by_pair, touched_pair, int(touched_count),
                            )
                            first_generated_count += int(added_eg)
                for bucket_idx in range(
                    int(activation_bucket_offsets[int(head_great_count)]),
                    int(activation_bucket_offsets[int(head_great_count) + 1]),
                ):
                    action_idx = int(activation_actions_by_head[int(bucket_idx)])
                    edge_e = int(first_edge_e_by_action[int(action_idx)])
                    activation_e = int(first_activation_e_by_action[int(action_idx)])
                    fill = int(first_fill[int(action_idx)])
                    prefix_forced = int(first_activation_prefix_by_action[int(action_idx)])
                    if (
                        int(fill) == int(prev_activation_fill)
                        and int(activation_e) == int(prev_activation_e)
                        and int(prefix_forced) == int(prev_activation_prefix)
                    ):
                        continue
                    prev_activation_fill = int(fill)
                    prev_activation_e = int(activation_e)
                    prev_activation_prefix = int(prefix_forced)
                    activation_edge = _rb._numba_pack_edge(
                        int(n),
                        int(fill),
                        int(activation_e),
                        0,
                        min(int(n), int(prefix_forced)),
                        int(fill),
                    )
                    touched_count, added_count = _rb._numba_touch_body_tail_array_candidates(
                        activation_edge,
                        int(activation_e),
                        body_values,
                        body_starts,
                        body_counts,
                        int(pair_mod),
                        int(pair_stamp_value),
                        pair_stamp,
                        best_fever_by_pair,
                        touched_pair,
                        int(touched_count),
                    )
                    first_generated_count += int(added_count)
                    eg_e_late = int(capped_eg_late_e[int(real_time_idx), int(fill)])
                    for end_e in range(int(activation_e) + 1, int(eg_e_late) + 1):
                        activation_edge_eg = _rb._numba_pack_edge_eg(
                            int(n), int(fill), int(end_e), 0,
                            min(int(n), int(prefix_forced)), int(fill),
                            int(activation_e), int(end_e),
                        )
                        touched_count, added_eg = _rb._numba_touch_body_tail_array_candidates(
                            activation_edge_eg, int(end_e), body_values, body_starts, body_counts,
                            int(pair_mod), int(pair_stamp_value), pair_stamp,
                            best_fever_by_pair, touched_pair, int(touched_count),
                        )
                        first_generated_count += int(added_eg)

                if int(touched_count) <= 0:
                    continue
                bit_stamp_value += 1
                first_reduce_values, body_frontier_len = _rb._numba_reduce_touched_body_pairs(
                    int(pair_mod),
                    touched_pair,
                    int(touched_count),
                    best_fever_by_pair,
                    bit_values,
                    bit_stamps,
                    int(bit_stamp_value),
                    first_reduce_values,
                )
                for body_idx in range(int(body_frontier_len)):
                    _rb._numba_append_branch_a_body_prefix_surface(
                        first_frontier,
                        int(head_great_count),
                        first_reduce_values[int(body_idx), 0],
                        first_reduce_values[int(body_idx), 1],
                        first_reduce_values[int(body_idx), 2],
                        branch_a_values,
                        branch_a_stamps,
                        int(branch_a_stamp),
                        int(branch_a_width),
                    )
            bucket_added = int(first_generated_count)
        if int(cfg) < 2:
            first_region_generated, first_region_scores, added, first_region_bounded, region_node_surface, region_node_next = (
                _rb._numba_emit_region2_head_edges(
                    first_region_generated,
                    first_region_scores,
                    first_region_seen,
                    first_region_score_matrix_holder,
                    first_region_score_matrix_count,
                    region_node_surface,
                    region_node_next,
                    region_bucket_head,
                    region_bucket_tail,
                    region_pending_ends,
                    int(n),
                    0,
                    region_starts,
                    region_offsets,
                    region_activations,
                    region_great_ends,
                    region_is_greats,
                    region_act_hit_ids,
                    region_perfect_hit_ids,
                    region_perfect_valids,
                    region_perfect_end_by_hit,
                    region_great_end_by_hit,
                    int(use_forced_great_timing_i),
                    body_values,
                    body_starts,
                    body_counts,
                    head_pool,
                    head_state_start,
                    head_state_count,
                    int(head_limit),
                    0,
                    int(head_limit),
                    int(head_filter_min),
                    int(first_region_bounded),
                )
            )
            first_generated_count += int(added)
            region2_added = int(added)
    else:
        first_generated = List.empty_list(_SURFACE_TYPE)
        first_generated_scores = List.empty_list(_SCORES_TYPE)
        first_generated_seen = Dict.empty(_SURFACE_TYPE, types.uint8)
        first_generated_score_matrix_holder = List.empty_list(_rb._NUMBA_HEAD_SCORE_MATRIX_TYPE)
        first_generated_score_matrix_count = np.zeros(1, dtype=np.int64)
        first_bounded_mode = 0
        prev_fill = -1
        prev_edge_e = -1
        prev_activation_fill = -1
        prev_activation_e = -1
        prev_activation_prefix = -1
        if int(cfg) < 3:
            for action_idx in range(int(action_count)):
                fill = int(first_fill[int(action_idx)])
                if int(fill) >= int(n):
                    break
                forced_count = int(first_forced[int(action_idx)])
                perfect_hit = float(prefix_perfect_hit[int(fill)])
                perfect_valid = int(prefix_perfect_valid[int(fill)])
                if int(perfect_valid) == 0 or int(forced_count) < 0:
                    edge_e = -1
                else:
                    edge_e = int(capped_perfect_edge_e[int(real_time_idx), int(fill)])
                if (
                    int(edge_e) >= 0
                    and (
                        int(fill) != int(prev_fill)
                        or int(edge_e) != int(prev_edge_e)
                    )
                ):
                    prev_fill = int(fill)
                    prev_edge_e = int(edge_e)
                    edge = _rb._numba_pack_edge(
                        int(n),
                        int(fill),
                        int(edge_e),
                        0,
                        min(int(n), int(forced_count)),
                        -1,
                    )
                    first_generated, first_generated_scores, added, first_bounded_mode = (
                        _rb._numba_append_head_generated_candidate(
                            first_generated,
                            first_generated_scores,
                            first_generated_seen,
                            first_generated_score_matrix_holder,
                            first_generated_score_matrix_count,
                            edge,
                            int(edge_e),
                            body_values,
                            body_starts,
                            body_counts,
                            head_pool,
                            head_state_start,
                            head_state_count,
                            int(head_limit),
                            0,
                            int(head_limit),
                            int(head_filter_min),
                            int(first_bounded_mode),
                        )
                    )
                    first_generated_count += int(added)
                    first_generated, first_generated_scores, added, first_bounded_mode = (
                        _rb._numba_emit_early_great_edges(
                            first_generated,
                            first_generated_scores,
                            first_generated_seen,
                            first_generated_score_matrix_holder,
                            first_generated_score_matrix_count,
                            int(n),
                            int(fill),
                            int(edge_e),
                            float(perfect_hit),
                            0,
                            min(int(n), int(forced_count)),
                            -1,
                            great_floor_timestamps,
                            float(real_fever_time),
                            body_values,
                            body_starts,
                            body_counts,
                            head_pool,
                            head_state_start,
                            head_state_count,
                            int(head_limit),
                            0,
                            int(head_limit),
                            int(head_filter_min),
                            int(first_bounded_mode),
                        )
                    )
                    first_generated_count += int(added)
                prefix_forced = int(first_activation_forced[int(action_idx)])
                activation_hit = 0.0
                activation_e = -1
                if int(use_forced_great_timing_i) != 0 and int(prefix_forced) >= 0:
                    activation_hit = float(prefix_late_hit[int(fill)])
                    activation_valid = int(prefix_late_valid[int(fill)])
                    if int(activation_valid) != 0:
                        activation_e = int(capped_late_edge_e[int(real_time_idx), int(fill)])
                if _rb._numba_late_edge_extends(
                    int(edge_e),
                    int(activation_e),
                    int(capped_eg_late_e[int(real_time_idx), int(fill)]),
                    int(capped_eg_perfect_e[int(real_time_idx), int(fill)]),
                ):
                    if (
                        int(fill) == int(prev_activation_fill)
                        and int(activation_e) == int(prev_activation_e)
                        and int(prefix_forced) == int(prev_activation_prefix)
                    ):
                        continue
                    prev_activation_fill = int(fill)
                    prev_activation_e = int(activation_e)
                    prev_activation_prefix = int(prefix_forced)
                    activation_edge = _rb._numba_pack_edge(
                        int(n),
                        int(fill),
                        int(activation_e),
                        0,
                        min(int(n), int(prefix_forced)),
                        int(fill),
                    )
                    first_generated, first_generated_scores, added, first_bounded_mode = (
                        _rb._numba_append_head_generated_candidate(
                            first_generated,
                            first_generated_scores,
                            first_generated_seen,
                            first_generated_score_matrix_holder,
                            first_generated_score_matrix_count,
                            activation_edge,
                            int(activation_e),
                            body_values,
                            body_starts,
                            body_counts,
                            head_pool,
                            head_state_start,
                            head_state_count,
                            int(head_limit),
                            0,
                            int(head_limit),
                            int(head_filter_min),
                            int(first_bounded_mode),
                        )
                    )
                    first_generated_count += int(added)
                    first_generated, first_generated_scores, added, first_bounded_mode = (
                        _rb._numba_emit_early_great_edges(
                            first_generated,
                            first_generated_scores,
                            first_generated_seen,
                            first_generated_score_matrix_holder,
                            first_generated_score_matrix_count,
                            int(n),
                            int(fill),
                            int(activation_e),
                            float(activation_hit),
                            0,
                            min(int(n), int(prefix_forced)),
                            int(fill),
                            great_floor_timestamps,
                            float(real_fever_time),
                            body_values,
                            body_starts,
                            body_counts,
                            head_pool,
                            head_state_start,
                            head_state_count,
                            int(head_limit),
                            0,
                            int(head_limit),
                            int(head_filter_min),
                            int(first_bounded_mode),
                        )
                    )
                    first_generated_count += int(added)
            bucket_added = int(first_generated_count)
        if int(cfg) < 2:
            first_generated, first_generated_scores, added, first_bounded_mode, region_node_surface, region_node_next = (
                _rb._numba_emit_region2_head_edges(
                    first_generated,
                    first_generated_scores,
                    first_generated_seen,
                    first_generated_score_matrix_holder,
                    first_generated_score_matrix_count,
                    region_node_surface,
                    region_node_next,
                    region_bucket_head,
                    region_bucket_tail,
                    region_pending_ends,
                    int(n),
                    0,
                    region_starts,
                    region_offsets,
                    region_activations,
                    region_great_ends,
                    region_is_greats,
                    region_act_hit_ids,
                    region_perfect_hit_ids,
                    region_perfect_valids,
                    region_perfect_end_by_hit,
                    region_great_end_by_hit,
                    int(use_forced_great_timing_i),
                    body_values,
                    body_starts,
                    body_counts,
                    head_pool,
                    head_state_start,
                    head_state_count,
                    int(head_limit),
                    0,
                    int(head_limit),
                    int(head_filter_min),
                    int(first_bounded_mode),
                )
            )
            first_generated_count += int(added)
            region2_added = int(added)
        if int(cfg) < 1:
            first_frontier = _rb._numba_head_envelope_filter(
                _rb._numba_reduce(first_generated), 0, int(head_limit), int(head_filter_min)
            )
    if int(cfg) < 1 and len(first_region_generated) > 0:
        for idx in range(len(first_frontier)):
            first_region_generated.append(first_frontier[idx])
        first_frontier = _rb._numba_head_envelope_filter(
            _rb._numba_reduce_pattern_runs(first_region_generated),
            0,
            int(head_limit),
            int(head_filter_min),
        )
    generated_surfaces += first_generated_count
    retained_total += len(first_frontier)
    if len(first_frontier) > max_state_frontier:
        max_state_frontier = len(first_frontier)

    if int(census) != 0:
        # Census mode (cfg==1 with a huge head_filter_min): return the RAW region2
        # candidate stream instead of the (empty) first frontier.
        out = np.zeros((len(first_region_generated), 7), dtype=np.uint64)
        for idx in range(len(first_region_generated)):
            surface = first_region_generated[idx]
            for col in range(7):
                out[idx, col] = surface[col]
        return (
            out,
            states_evaluated,
            generated_surfaces,
            retained_total,
            max_state_frontier,
            int(pair_stamp_value),
            int(bit_stamp_value),
            int(branch_a_epoch_out),
            int(bucket_added),
            int(region2_added),
            int(headloop_added),
        )
    out = np.zeros((len(first_frontier), 7), dtype=np.uint64)
    for idx in range(len(first_frontier)):
        surface = first_frontier[idx]
        for col in range(7):
            out[idx, col] = surface[col]
    return (
        out,
        states_evaluated,
        generated_surfaces,
        retained_total,
        max_state_frontier,
        int(pair_stamp_value),
        int(bit_stamp_value),
        int(branch_a_epoch_out),
        int(bucket_added),
        int(region2_added),
        int(headloop_added),
    )


@njit(cache=True, nogil=True)
def _intra_mask_prereduce(rows, group_ids, group_count: int):
    """Same-mask two-phase weak-dominance reduce, mirroring `_numba_reduce` restricted to
    rows with identical fever/great masks (where its mask-subset conditions are trivially
    true): phase 1 drops a candidate weakly dominated by a kept same-group row (first
    occurrence wins exact ties), phase 2 retires kept rows the candidate weakly dominates.
    Removals are therefore a subset of `_numba_reduce`'s own removals; survivor order is
    original stream order."""
    n_rows = int(rows.shape[0])
    kept_flag = np.zeros(n_rows, dtype=np.bool_)
    head = np.full(int(group_count), -1, dtype=np.int64)
    prev = np.full(n_rows, -1, dtype=np.int64)
    for i in range(n_rows):
        g = int(group_ids[i])
        bf_i = np.int64(rows[i, 4])
        ng_i = np.int64(rows[i, 5]) - np.int64(rows[i, 6])
        q_i = np.int64(rows[i, 6])
        dominated = False
        pos = int(head[g])
        while pos != -1:
            if kept_flag[pos]:
                bf_k = np.int64(rows[pos, 4])
                ng_k = np.int64(rows[pos, 5]) - np.int64(rows[pos, 6])
                q_k = np.int64(rows[pos, 6])
                if bf_k >= bf_i and ng_k <= ng_i and q_k <= q_i:
                    dominated = True
                    break
            pos = int(prev[pos])
        if dominated:
            continue
        pos = int(head[g])
        while pos != -1:
            if kept_flag[pos]:
                bf_k = np.int64(rows[pos, 4])
                ng_k = np.int64(rows[pos, 5]) - np.int64(rows[pos, 6])
                q_k = np.int64(rows[pos, 6])
                if bf_i >= bf_k and ng_i <= ng_k and q_i <= q_k:
                    kept_flag[pos] = False
            pos = int(prev[pos])
        prev[i] = int(head[g])
        head[g] = i
        kept_flag[i] = True
    return kept_flag


@njit(cache=True, nogil=True)
def _filter_rows_through_production(rows, head_limit: int, filter_min: int):
    """reduce+envelope-filter a row block exactly like the driver's final merge step."""
    lst = List.empty_list(_SURFACE_TYPE)
    for i in range(int(rows.shape[0])):
        lst.append(
            (
                rows[i, 0],
                rows[i, 1],
                rows[i, 2],
                rows[i, 3],
                rows[i, 4],
                rows[i, 5],
                rows[i, 6],
            )
        )
    frontier = _rb._numba_head_envelope_filter(
        _rb._numba_reduce(lst), 0, int(head_limit), int(filter_min)
    )
    out = np.zeros((len(frontier), 7), dtype=np.uint64)
    for idx in range(len(frontier)):
        surface = frontier[idx]
        for col in range(7):
            out[idx, col] = surface[col]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--song", required=True)
    ap.add_argument("--diff", default="Hard", choices=("Easy", "Normal", "Hard"))
    ap.add_argument("--fts", type=int, default=6)
    ap.add_argument("--ffs", type=int, default=6)
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument(
        "--dump-census",
        default=None,
        help="write the per-geometry census streams (region2 emit contents under a disabled "
        "promotion threshold) to this .npz and skip the timing phases",
    )
    args = ap.parse_args()

    chart = _find_chart(args.song, args.diff)
    sp = SongProbeInputs(chart=chart, diff=args.diff, fts=args.fts, ffs=args.ffs)
    ws = sp.ws
    print(f"chart={os.path.basename(chart)} n={sp.n} geometries={len(sp.prepared)}")

    fill_run_cache: dict[tuple[int, int], tuple[np.ndarray, ...]] = {}

    def fill_runs_for(item) -> tuple[np.ndarray, ...]:
        key = (id(item[5]), id(item[9]))
        runs = fill_run_cache.get(key)
        if runs is None:
            runs = (
                *_exact_action_fill_runs(item[5]),
                *_exact_action_fill_runs(item[5], item[9]),
            )
            fill_run_cache[key] = runs
        return runs

    def run_cfg(
        cfg: int, item, rt_idx: int, region_table, *, census: int = 0, filter_min: int | None = None
    ) -> tuple[float, tuple]:
        perfect_run_starts, perfect_run_ends, late_run_starts, late_run_ends = fill_runs_for(item)
        region_perfect_end_by_hit = sp.region_perfect_end_by_real_time[int(rt_idx)]
        region_great_end_by_hit = sp.region_great_end_by_real_time[int(rt_idx)]
        successor_epoch = ws.next_successor_epoch()
        t0 = time.perf_counter()
        out = _split_driver(
            int(cfg),
            int(census),
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
            perfect_run_starts,
            perfect_run_ends,
            late_run_starts,
            late_run_ends,
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
            int(_rb._HEAD_FILTER_MIN_SURFACES) if filter_min is None else int(filter_min),
            region_table[0],
            region_table[1],
            region_table[2],
            region_table[3],
            region_table[4],
            region_table[5],
            region_table[6],
            region_table[7],
            sp.region_hit_token_to_id,
            region_perfect_end_by_hit,
            region_great_end_by_hit,
            ws.pair_values,
            ws.pair_stamps,
            ws.pair_touched,
            ws.bit_values,
            ws.bit_stamps,
            ws.branch_a_values,
            ws.branch_a_stamps,
            ws.perfect_successor,
            ws.perfect_successor_stamps,
            ws.late_successor,
            ws.late_successor_stamps,
            int(successor_epoch),
            int(ws.pair_epoch),
            int(ws.bit_epoch),
            int(ws.branch_a_epoch),
        )
        elapsed = time.perf_counter() - t0
        ws.store_epochs(int(out[5]), int(out[6]), int(out[7]))
        return elapsed, out

    def run_production(item, rt_idx: int, region_table):
        perfect_run_starts, perfect_run_ends, late_run_starts, late_run_ends = fill_runs_for(item)
        region_perfect_end_by_hit = sp.region_perfect_end_by_real_time[int(rt_idx)]
        region_great_end_by_hit = sp.region_great_end_by_real_time[int(rt_idx)]
        successor_epoch = ws.next_successor_epoch()
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
            perfect_run_starts,
            perfect_run_ends,
            late_run_starts,
            late_run_ends,
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
            sp.region_hit_token_to_id,
            region_perfect_end_by_hit,
            region_great_end_by_hit,
            ws.pair_values,
            ws.pair_stamps,
            ws.pair_touched,
            ws.bit_values,
            ws.bit_stamps,
            ws.branch_a_values,
            ws.branch_a_stamps,
            ws.perfect_successor,
            ws.perfect_successor_stamps,
            ws.late_successor,
            ws.late_successor_stamps,
            int(successor_epoch),
            int(ws.pair_epoch),
            int(ws.bit_epoch),
            int(ws.branch_a_epoch),
        )
        ws.store_epochs(int(result[5]), int(result[6]), int(result[7]))
        return result

    warm_item = sp.prepared[0]
    warm_table = sp.region_table_for(float(warm_item[2]), int(warm_item[1]), warm_item[4])
    if args.dump_census:
        run_cfg(1, warm_item, int(sp.real_time_index[0]), warm_table, census=1, filter_min=1 << 30)
        payload = {}
        for gi, item in enumerate(sp.prepared):
            rt_idx = int(sp.real_time_index[gi])
            region_table = sp.region_table_for(float(item[2]), int(item[1]), item[4])
            _elapsed, out = run_cfg(1, item, rt_idx, region_table, census=1, filter_min=1 << 30)
            payload[f"stream_{gi}"] = np.ascontiguousarray(out[0])
        out_path = Path(args.dump_census)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(out_path, **payload)
        print(f"census streams written: {out_path} ({len(sp.prepared)} geometries)")
        return 0
    for cfg in range(6):
        run_cfg(cfg, warm_item, int(sp.real_time_index[0]), warm_table)
    run_production(warm_item, int(sp.real_time_index[0]), warm_table)

    totals = [0.0] * 6
    mismatches = 0
    sum_bucket = sum_region2 = sum_headloop = 0
    for gi, item in enumerate(sp.prepared):
        rt_idx = int(sp.real_time_index[gi])
        region_table = sp.region_table_for(float(item[2]), int(item[1]), item[4])
        prod = run_production(item, rt_idx, region_table)
        outs = []
        for cfg in range(6):
            best = None
            for _ in range(args.reps):
                elapsed, out = run_cfg(cfg, item, rt_idx, region_table)
                if best is None or elapsed < best[0]:
                    best = (elapsed, out)
            totals[cfg] += best[0]
            outs.append(best[1])
        if not np.array_equal(outs[0][0], prod[0]):
            mismatches += 1
            print(f"  !! cfg=0 OUTPUT MISMATCH vs production for geometry {gi}")
        sum_bucket += int(outs[0][8])
        sum_region2 += int(outs[0][9])
        sum_headloop += int(outs[0][10])

    if mismatches:
        raise SystemExit(f"{mismatches} cfg=0 mismatches -- split numbers are INVALID")
    print(f"\ncfg=0 output byte-identical to production for all {len(sp.prepared)} geometries")
    print(f"\n=== post-body phase split (sum over {len(sp.prepared)} geometries) ===")
    labels = [
        "full driver           ",
        "- final reduce+filter ",
        "- first region2 emit  ",
        "- bucket/first gen    ",
        "- head-state loop     ",
        "- body DP             ",
    ]
    for cfg in range(6):
        print(f"  cfg={cfg} {labels[cfg]}: {totals[cfg]:8.3f} s")
    full = totals[0]
    print("\n  phase costs (deltas):")
    print(f"    final reduce+envelope filter : {totals[0] - totals[1]:8.3f} s ({100 * (totals[0] - totals[1]) / full:5.1f}%)")
    print(f"    first-frontier region2 emit  : {totals[1] - totals[2]:8.3f} s ({100 * (totals[1] - totals[2]) / full:5.1f}%)")
    print(f"    bucket loop / first gen      : {totals[2] - totals[3]:8.3f} s ({100 * (totals[2] - totals[3]) / full:5.1f}%)")
    print(f"    head-state loop              : {totals[3] - totals[4]:8.3f} s ({100 * (totals[3] - totals[4]) / full:5.1f}%)")
    print(f"    body DP                      : {totals[4] - totals[5]:8.3f} s ({100 * (totals[4] - totals[5]) / full:5.1f}%)")
    print(f"    reachability/radix prepass   : {totals[5]:8.3f} s ({100 * totals[5] / full:5.1f}%)")
    print("\n  candidate counts: bucket/firstgen={:,} region2={:,} headloop={:,}".format(sum_bucket, sum_region2, sum_headloop))

    # Region2 stream census: how do the raw candidates group by head mask? Same-mask
    # groups admit the cheap integer (bf, ng, bfg) radix pre-reduce; the cone filter
    # only separates candidates whose masks differ.
    print("\n=== region2 raw-stream mask census ===")
    total_rows = 0
    total_groups = 0
    biggest_stream = 0
    kept_after_intra = 0
    for gi, item in enumerate(sp.prepared):
        rt_idx = int(sp.real_time_index[gi])
        region_table = sp.region_table_for(float(item[2]), int(item[1]), item[4])
        _elapsed, out = run_cfg(1, item, rt_idx, region_table, census=1, filter_min=1 << 30)
        rows = out[0]
        if int(rows.shape[0]) == 0:
            continue
        total_rows += int(rows.shape[0])
        biggest_stream = max(biggest_stream, int(rows.shape[0]))
        masks = np.ascontiguousarray(rows[:, :4])
        group_keys = masks.view([("", np.uint64)] * 4).reshape(-1)
        _uniq, inverse, counts = np.unique(group_keys, return_inverse=True, return_counts=True)
        total_groups += int(counts.shape[0])
        # Within-group integer Pareto width: exact count of rows not count-dominated by
        # another row of the SAME mask group ((bf ge, ng le, bfg le), first-wins ties).
        order = np.argsort(inverse, kind="stable")
        srows = rows[order]
        sinv = inverse[order]
        starts = np.searchsorted(sinv, np.arange(int(counts.shape[0])))
        ends = np.append(starts[1:], sinv.shape[0])
        for g0, g1 in zip(starts, ends):
            grp = srows[int(g0):int(g1)]
            bf = grp[:, 4].astype(np.int64)
            ng = (grp[:, 5] - grp[:, 6]).astype(np.int64)
            bfg = grp[:, 6].astype(np.int64)
            # Sequential insert-with-eviction = exact maximal set for this transitive
            # integer dominance (first occurrence wins ties); O(m * kept).
            kept: list[int] = []
            for i in range(int(grp.shape[0])):
                dominated = False
                for j in kept:
                    if bf[j] >= bf[i] and ng[j] <= ng[i] and bfg[j] <= bfg[i]:
                        dominated = True
                        break
                if dominated:
                    continue
                kept = [
                    j
                    for j in kept
                    if not (
                        bf[i] >= bf[j]
                        and ng[i] <= ng[j]
                        and bfg[i] <= bfg[j]
                        and (bf[i] != bf[j] or ng[i] != ng[j] or bfg[i] != bfg[j])
                    )
                ]
                kept.append(i)
            kept_after_intra += len(kept)
    if total_rows:
        print(f"  raw region2 rows (sum)        : {total_rows:,} (largest stream {biggest_stream:,})")
        print(f"  distinct head-mask groups     : {total_groups:,} (avg {total_rows / max(1, total_groups):.1f} rows/group)")
        print(
            f"  after same-mask count reduce  : {kept_after_intra:,} "
            f"({total_rows / max(1, kept_after_intra):.1f}x smaller)"
        )
    else:
        print("  no region2 candidates in this sample")

    # Fix simulation: production filter chain (reduce + envelope filter) applied to the
    # RAW region2 stream vs the same chain applied AFTER the same-mask pre-reduce. Byte
    # equality is required (soundness lemma: pre-reduce removals are a subset of
    # _numba_reduce's removals in each head-overlap class); the timing delta prices the
    # projected hot-phase fix.
    print("\n=== fix simulation: filter(reduce(raw)) vs filter(reduce(pre-reduced)) ===")
    t_raw_total = t_pre_total = t_prereduce_total = 0.0
    checked = 0
    for gi, item in enumerate(sp.prepared):
        rt_idx = int(sp.real_time_index[gi])
        region_table = sp.region_table_for(float(item[2]), int(item[1]), item[4])
        _elapsed, out = run_cfg(1, item, rt_idx, region_table, census=1, filter_min=1 << 30)
        rows = np.ascontiguousarray(out[0])
        if int(rows.shape[0]) == 0:
            continue
        group_keys = np.ascontiguousarray(rows[:, :4]).view([("", np.uint64)] * 4).reshape(-1)
        _uniq, inverse = np.unique(group_keys, return_inverse=True)
        inverse = np.ascontiguousarray(inverse.astype(np.int64))
        if checked == 0:
            _intra_mask_prereduce(rows, inverse, int(inverse.max()) + 1)
            _filter_rows_through_production(rows[:1], 100, int(_rb._HEAD_FILTER_MIN_SURFACES))
        t0 = time.perf_counter()
        keep = _intra_mask_prereduce(rows, inverse, int(inverse.max()) + 1)
        t_prereduce = time.perf_counter() - t0
        reduced_rows = np.ascontiguousarray(rows[np.asarray(keep, dtype=bool)])
        t0 = time.perf_counter()
        out_raw = _filter_rows_through_production(
            rows, min(sp.n, 100), int(_rb._HEAD_FILTER_MIN_SURFACES)
        )
        t_raw = time.perf_counter() - t0
        t0 = time.perf_counter()
        out_pre = _filter_rows_through_production(
            reduced_rows, min(sp.n, 100), int(_rb._HEAD_FILTER_MIN_SURFACES)
        )
        t_pre = time.perf_counter() - t0
        if not np.array_equal(out_raw, out_pre):
            raise SystemExit(
                f"fix-sim OUTPUT MISMATCH for geometry {gi}: raw={out_raw.shape} pre={out_pre.shape}"
            )
        t_raw_total += t_raw
        t_pre_total += t_pre
        t_prereduce_total += t_prereduce
        checked += 1
    if checked:
        print(f"  geometries checked            : {checked} (all outputs byte-identical)")
        print(f"  filter chain on RAW stream    : {t_raw_total:8.3f} s")
        print(f"  same-mask pre-reduce          : {t_prereduce_total:8.3f} s")
        print(f"  filter chain on PRE-REDUCED   : {t_pre_total:8.3f} s")
        print(
            f"  hot-phase speedup             : {t_raw_total / max(1e-9, t_prereduce_total + t_pre_total):6.1f}x"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
