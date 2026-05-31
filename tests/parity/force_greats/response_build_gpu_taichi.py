import taichi as ti

@ti.func
def _edge_end_idx_precomputed(
    n,
    activation_idx,
    forced_start,
    forced_applied,
    use_forced_great_timing_i,
    timestamps: ti.template(),
    great_candidate_timestamps: ti.template(),
    timestamp_end_idx: ti.template(),
    great_end_idx: ti.template(),
    real_time_idx,
):
    forced_end = forced_start + forced_applied - 1
    start_time = timestamps[activation_idx]
    e = timestamp_end_idx[real_time_idx, activation_idx]
    if (
        use_forced_great_timing_i != 0
        and forced_applied > 0
        and forced_end >= forced_start
        and forced_end < activation_idx
        and forced_end < n
    ):
        forced_t = great_candidate_timestamps[forced_end]
        if forced_t > start_time:
            start_time = forced_t
            e = great_end_idx[real_time_idx, forced_end]
    if e <= activation_idx:
        e = activation_idx + 1
    if e > n:
        e = n
    return e, start_time


@ti.func
def _mask_word(start, end, n, word_idx):
    start_i = ti.max(ti.i32(0), ti.min(ti.min(start, n), ti.i32(100)))
    end_i = ti.max(ti.i32(0), ti.min(ti.min(end, n), ti.i32(100)))
    out = ti.u32(0)
    lo = word_idx * 32
    hi = ti.min(lo + 32, ti.i32(100))
    a = ti.max(start_i, lo)
    b = ti.min(end_i, hi)
    if b > a:
        width = b - a
        out = ti.cast((ti.u64(1) << width) - ti.u64(1), ti.u32) << (a - lo)
    return out


@ti.func
def _body_count(start, end, n):
    return ti.max(ti.i32(0), ti.min(end, n) - ti.max(start, ti.i32(100)))


@ti.kernel
def _build_fg_response_edges_batch_kernel(
    n: ti.i32,
    geometry_count: ti.i32,
    max_action_count: ti.i32,
    use_forced_great_timing_i: ti.i32,
    timestamps: ti.types.ndarray(dtype=ti.f32, ndim=1),
    great_candidate_timestamps: ti.types.ndarray(dtype=ti.f32, ndim=1),
    real_time_index: ti.types.ndarray(dtype=ti.i32, ndim=1),
    timestamp_end_idx: ti.types.ndarray(dtype=ti.i32, ndim=2),
    great_end_idx: ti.types.ndarray(dtype=ti.i32, ndim=2),
    action_count_by_geometry: ti.types.ndarray(dtype=ti.i32, ndim=1),
    later_fill: ti.types.ndarray(dtype=ti.i32, ndim=2),
    first_fill: ti.types.ndarray(dtype=ti.i32, ndim=2),
    later_forced: ti.types.ndarray(dtype=ti.i32, ndim=2),
    first_forced: ti.types.ndarray(dtype=ti.i32, ndim=2),
    later_valid: ti.types.ndarray(dtype=ti.i8, ndim=3),
    later_next: ti.types.ndarray(dtype=ti.i32, ndim=3),
    later_fever_masks: ti.types.ndarray(dtype=ti.u32, ndim=4),
    later_great_masks: ti.types.ndarray(dtype=ti.u32, ndim=4),
    later_body_counts: ti.types.ndarray(dtype=ti.i32, ndim=4),
    first_valid: ti.types.ndarray(dtype=ti.i8, ndim=2),
    first_next: ti.types.ndarray(dtype=ti.i32, ndim=2),
    first_fever_masks: ti.types.ndarray(dtype=ti.u32, ndim=3),
    first_great_masks: ti.types.ndarray(dtype=ti.u32, ndim=3),
    first_body_counts: ti.types.ndarray(dtype=ti.i32, ndim=3),
):
    for geometry_idx, state_i, action_idx in ti.ndrange(geometry_count, n, max_action_count):
        if action_idx < action_count_by_geometry[geometry_idx]:
            rt_idx = real_time_index[geometry_idx]
            fill = later_fill[geometry_idx, action_idx]
            forced = later_forced[geometry_idx, action_idx]
            activation = state_i + fill
            forced_start = state_i + 1
            edge_e = ti.i32(-1)
            start_time = ti.f32(-1.0)
            if activation < n:
                e, computed_start = _edge_end_idx_precomputed(
                    n,
                    activation,
                    forced_start,
                    forced,
                    use_forced_great_timing_i,
                    timestamps,
                    great_candidate_timestamps,
                    timestamp_end_idx,
                    great_end_idx,
                    rt_idx,
                )
                edge_e = e
                start_time = computed_start
                later_valid[geometry_idx, state_i, action_idx] = ti.i8(1)
                later_next[geometry_idx, state_i, action_idx] = e
                great_end = ti.min(n, forced_start + forced)
                for word in ti.static(range(4)):
                    later_fever_masks[geometry_idx, state_i, action_idx, word] = _mask_word(activation, e, n, word)
                    later_great_masks[geometry_idx, state_i, action_idx, word] = _mask_word(
                        forced_start, great_end, n, word
                    )
                later_body_counts[geometry_idx, state_i, action_idx, 0] = _body_count(activation, e, n)
                later_body_counts[geometry_idx, state_i, action_idx, 1] = _body_count(forced_start, great_end, n)

            if action_idx > 0 and later_valid[geometry_idx, state_i, action_idx] != 0:
                prev_fill = later_fill[geometry_idx, action_idx - 1]
                if fill == prev_fill:
                    prev_e, prev_start_time = _edge_end_idx_precomputed(
                        n,
                        state_i + prev_fill,
                        state_i + 1,
                        later_forced[geometry_idx, action_idx - 1],
                        use_forced_great_timing_i,
                        timestamps,
                        great_candidate_timestamps,
                        timestamp_end_idx,
                        great_end_idx,
                        rt_idx,
                    )
                    if start_time == prev_start_time or edge_e == prev_e:
                        later_valid[geometry_idx, state_i, action_idx] = ti.i8(0)

    for geometry_idx, action_idx in ti.ndrange(geometry_count, max_action_count):
        if action_idx < action_count_by_geometry[geometry_idx]:
            rt_idx = real_time_index[geometry_idx]
            fill = first_fill[geometry_idx, action_idx]
            forced = first_forced[geometry_idx, action_idx]
            activation = fill
            edge_e = ti.i32(-1)
            start_time = ti.f32(-1.0)
            if activation < n:
                e, computed_start = _edge_end_idx_precomputed(
                    n,
                    activation,
                    ti.i32(0),
                    forced,
                    use_forced_great_timing_i,
                    timestamps,
                    great_candidate_timestamps,
                    timestamp_end_idx,
                    great_end_idx,
                    rt_idx,
                )
                edge_e = e
                start_time = computed_start
                first_valid[geometry_idx, action_idx] = ti.i8(1)
                first_next[geometry_idx, action_idx] = e
                great_end = ti.min(n, forced)
                for word in ti.static(range(4)):
                    first_fever_masks[geometry_idx, action_idx, word] = _mask_word(activation, e, n, word)
                    first_great_masks[geometry_idx, action_idx, word] = _mask_word(0, great_end, n, word)
                first_body_counts[geometry_idx, action_idx, 0] = _body_count(activation, e, n)
                first_body_counts[geometry_idx, action_idx, 1] = _body_count(0, great_end, n)

            if action_idx > 0 and first_valid[geometry_idx, action_idx] != 0:
                prev_fill = first_fill[geometry_idx, action_idx - 1]
                if fill == prev_fill:
                    prev_e, prev_start_time = _edge_end_idx_precomputed(
                        n,
                        prev_fill,
                        ti.i32(0),
                        first_forced[geometry_idx, action_idx - 1],
                        use_forced_great_timing_i,
                        timestamps,
                        great_candidate_timestamps,
                        timestamp_end_idx,
                        great_end_idx,
                        rt_idx,
                    )
                    if start_time == prev_start_time or edge_e == prev_e:
                        first_valid[geometry_idx, action_idx] = ti.i8(0)

