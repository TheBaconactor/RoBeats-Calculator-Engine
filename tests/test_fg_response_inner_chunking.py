from __future__ import annotations

import numpy as np


def test_response_surface_head_coeffs_match_bruteforce():
    from gear_optimizer.solver.taichi_gem.force_greats import response_inner

    surface_words = np.asarray(
        [
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0, 0, 0, 0],
            [0b10101, 0x80000001, 0x0000FFFF, 0x0000000F, 0, 0, 0, 0],
            [0xAAAAAAAA, 0x55555555, 0x33333333, 0xCCCCCCCC, 0, 0, 0, 0],
        ],
        dtype=np.uint32,
    )

    for head_len in (0, 1, 31, 32, 33, 63, 64, 65, 96, 100, 120):
        expected = np.zeros((int(surface_words.shape[0]), 4), dtype=np.int32)
        head = max(0, min(int(head_len), 100))
        for row_idx, row in enumerate(surface_words):
            for pos0 in range(head):
                block = int(pos0 // 32)
                bit = int(pos0 % 32)
                is_fever = (int(row[block]) >> bit) & 1
                expected[row_idx, 1 if is_fever else 0] += 1
                expected[row_idx, 3 if is_fever else 2] += int(pos0 + 1)

        got = response_inner._precompute_surface_head_coeffs(surface_words, head_len=int(head_len))
        np.testing.assert_array_equal(got, expected)


def test_response_surface_head_coeffs_do_not_unpack_per_surface_bits(monkeypatch):
    from gear_optimizer.solver.taichi_gem.force_greats import response_inner

    surface_words = np.asarray(
        [
            [0xFFFFFFFF, 0, 0, 0, 0, 0, 0, 0],
            [0, 0xFFFFFFFF, 0, 0, 0, 0, 0, 0],
        ],
        dtype=np.uint32,
    )

    def fail_unpackbits(*_args, **_kwargs):
        raise AssertionError("head coeff precompute must use packed lookup tables")

    monkeypatch.setattr(response_inner.np, "unpackbits", fail_unpackbits)

    got = response_inner._precompute_surface_head_coeffs(surface_words, head_len=64)

    np.testing.assert_array_equal(
        got,
        np.asarray(
            [
                [32, 32, 1552, 528],
                [32, 32, 528, 1552],
            ],
            dtype=np.int32,
        ),
    )


def test_response_inner_group_scoring_uses_surface_chunks_when_whole_group_dispatch_exceeds_caps(monkeypatch):
    from gear_optimizer.solver.taichi_gem.force_greats import response_inner

    batch_calls: list[dict[str, int]] = []
    group_calls: list[dict[str, int]] = []

    def fake_group_kernel(
        group_count,
        surface_words,
        surface_counts,
        surface_head_coeffs,
        group_offsets,
        group_lengths,
        group_meta,
        color_flags,
        ref_pp,
        ref_cm,
        ref_fm,
        out_rows,
        allow_pp_template,
    ):
        group_calls.append({"group_count": int(group_count), "allow_pp": bool(allow_pp_template)})
        for local_idx in range(int(group_count)):
            offset = int(group_offsets[local_idx])
            length = int(group_lengths[local_idx])
            segment = surface_counts[offset : offset + length, 0]
            best_local = int(np.argmax(segment))
            out_rows[local_idx, 0] = int(segment[best_local])
            out_rows[local_idx, 1] = int(best_local)

    def fake_kernel(
        row_count,
        surface_words,
        surface_counts,
        surface_head_coeffs,
        group_offsets,
        logical_owners,
        logical_surfaces,
        row_meta,
        color_flags,
        ref_pp,
        ref_cm,
        ref_fm,
        out_scores,
        out_details,
        allow_pp_template,
    ):
        batch_calls.append(
            {
                "row_count": int(row_count),
                "allow_pp": bool(allow_pp_template),
                "surface_pool_rows": int(surface_counts.shape[0]),
            }
        )
        for row_idx in range(int(row_count)):
            owner = int(logical_owners[row_idx])
            local_surface = int(logical_surfaces[row_idx])
            surface_row = int(group_offsets[owner]) + int(local_surface)
            out_scores[row_idx] = int(surface_counts[surface_row, 0])

    monkeypatch.setattr(response_inner.gem_api, "ensure_ready", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(response_inner.ti, "sync", lambda: None)
    monkeypatch.setattr(response_inner, "_fg_response_inner_group_kernel", fake_group_kernel)
    monkeypatch.setattr(response_inner, "_fg_response_inner_batch_kernel", fake_kernel)
    monkeypatch.setattr(response_inner, "_FG_RESPONSE_INNER_GPU_MAX_DISPATCH_WORK", 10)
    monkeypatch.setattr(response_inner, "_FG_RESPONSE_INNER_GPU_MAX_THREAD_WORK", 3)
    monkeypatch.setattr(response_inner, "_FG_RESPONSE_INNER_GPU_MAX_SURFACE_DISPATCH_ROWS", 3)
    monkeypatch.setattr(response_inner, "_FG_RESPONSE_INNER_GPU_MAX_SURFACE_DISPATCH_WORK", 3)
    monkeypatch.setattr(
        response_inner.np,
        "concatenate",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("surface chunk path must use the canonical preallocated owner buffer")
        ),
    )

    group_meta = np.zeros((3, 8), dtype=np.int32)
    group_offsets = np.asarray([0, 4, 7], dtype=np.int32)
    group_lengths = np.asarray([4, 3, 2], dtype=np.int32)
    surface_words = np.zeros((9, 8), dtype=np.uint32)
    surface_counts = np.asarray(
        [
            [1, 0],
            [7, 0],
            [7, 0],
            [6, 0],
            [3, 0],
            [9, 0],
            [9, 0],
            [8, 0],
            [8, 0],
        ],
        dtype=np.int32,
    )
    ref_arrays = {
        "Perfect Points": np.ones(4, dtype=np.float32),
        "Combo Multiplier": np.ones(4, dtype=np.float32),
        "Fever Multiplier": np.ones(4, dtype=np.float32),
    }

    rows, logical_surface_rows = response_inner._score_response_group_meta_gpu(
        group_meta=group_meta,
        group_offsets=group_offsets,
        group_lengths=group_lengths,
        primary_color="Rush",
        secondary_color="Flow",
        selected_color="Rush",
        ref_arrays=ref_arrays,
        surface_words=surface_words,
        surface_counts=surface_counts,
    )

    assert logical_surface_rows == 9
    assert group_calls == []
    assert len(batch_calls) > 1
    assert all(call["row_count"] <= 3 for call in batch_calls)
    assert all(not call["allow_pp"] for call in batch_calls)
    assert all(call["surface_pool_rows"] == 9 for call in batch_calls)
    assert rows[:, 0].tolist() == [7, 9, 8]
    assert rows[:, 1].tolist() == [1, 1, 0]


def test_response_inner_groups_above_thread_budget_use_surface_batch_lane(monkeypatch):
    from gear_optimizer.solver.taichi_gem.force_greats import response_inner

    group_calls: list[int] = []
    batch_calls: list[int] = []

    def fake_group_kernel(
        group_count,
        surface_words,
        surface_counts,
        surface_head_coeffs,
        group_offsets,
        group_lengths,
        group_meta,
        color_flags,
        ref_pp,
        ref_cm,
        ref_fm,
        out_rows,
        allow_pp_template,
    ):
        group_calls.append(int(group_count))

    def fake_batch_kernel(
        row_count,
        surface_words,
        surface_counts,
        surface_head_coeffs,
        group_offsets,
        logical_owners,
        logical_surfaces,
        row_meta,
        color_flags,
        ref_pp,
        ref_cm,
        ref_fm,
        out_scores,
        out_details,
        allow_pp_template,
    ):
        batch_calls.append(int(row_count))
        out_scores[:] = 1

    monkeypatch.setattr(response_inner.gem_api, "ensure_ready", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(response_inner.ti, "sync", lambda: None)
    monkeypatch.setattr(response_inner, "_fg_response_inner_group_kernel", fake_group_kernel)
    monkeypatch.setattr(response_inner, "_fg_response_inner_batch_kernel", fake_batch_kernel)
    monkeypatch.setattr(response_inner, "_FG_RESPONSE_INNER_GPU_MAX_DISPATCH_WORK", 1)
    monkeypatch.setattr(response_inner, "_FG_RESPONSE_INNER_GPU_MAX_THREAD_WORK", 1)
    monkeypatch.setattr(response_inner, "_FG_RESPONSE_INNER_GPU_MAX_SURFACE_DISPATCH_ROWS", 10)
    monkeypatch.setattr(response_inner, "_FG_RESPONSE_INNER_GPU_MAX_SURFACE_DISPATCH_WORK", 10)

    group_meta = np.zeros((1, 8), dtype=np.int32)
    group_offsets = np.asarray([0], dtype=np.int32)
    group_lengths = np.asarray([4], dtype=np.int32)
    surface_words = np.zeros((4, 8), dtype=np.uint32)
    surface_counts = np.zeros((4, 2), dtype=np.int32)
    ref_arrays = {
        "Perfect Points": np.ones(4, dtype=np.float32),
        "Combo Multiplier": np.ones(4, dtype=np.float32),
        "Fever Multiplier": np.ones(4, dtype=np.float32),
    }

    response_inner._score_response_group_meta_gpu(
        group_meta=group_meta,
        group_offsets=group_offsets,
        group_lengths=group_lengths,
        primary_color="Rush",
        secondary_color="Flow",
        selected_color="Rush",
        ref_arrays=ref_arrays,
        surface_words=surface_words,
        surface_counts=surface_counts,
    )

    assert group_calls == []
    assert batch_calls == [4]


def test_response_inner_default_surface_work_cap_keeps_safe_large_batch_together(monkeypatch):
    from gear_optimizer.solver.taichi_gem.force_greats import response_inner

    group_calls: list[int] = []
    batch_calls: list[int] = []

    def fake_group_kernel(
        group_count,
        surface_words,
        surface_counts,
        surface_head_coeffs,
        group_offsets,
        group_lengths,
        group_meta,
        color_flags,
        ref_pp,
        ref_cm,
        ref_fm,
        out_rows,
        allow_pp_template,
    ):
        group_calls.append(int(group_count))

    def fake_batch_kernel(
        row_count,
        surface_words,
        surface_counts,
        surface_head_coeffs,
        group_offsets,
        logical_owners,
        logical_surfaces,
        row_meta,
        color_flags,
        ref_pp,
        ref_cm,
        ref_fm,
        out_scores,
        out_details,
        allow_pp_template,
    ):
        batch_calls.append(int(row_count))
        out_scores[:] = 1

    monkeypatch.setattr(response_inner.gem_api, "ensure_ready", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(response_inner.ti, "sync", lambda: None)
    monkeypatch.setattr(response_inner, "_fg_response_inner_group_kernel", fake_group_kernel)
    monkeypatch.setattr(response_inner, "_fg_response_inner_batch_kernel", fake_batch_kernel)

    surface_count = 20_000
    group_meta = np.zeros((1, 8), dtype=np.int32)
    group_meta[0, 0] = 90
    group_offsets = np.asarray([0], dtype=np.int32)
    group_lengths = np.asarray([surface_count], dtype=np.int32)
    surface_words = np.zeros((surface_count, 8), dtype=np.uint32)
    surface_counts = np.zeros((surface_count, 2), dtype=np.int32)
    ref_arrays = {
        "Perfect Points": np.ones(161, dtype=np.float32),
        "Combo Multiplier": np.ones(161, dtype=np.float32),
        "Fever Multiplier": np.ones(161, dtype=np.float32),
    }

    response_inner._score_response_group_meta_gpu(
        group_meta=group_meta,
        group_offsets=group_offsets,
        group_lengths=group_lengths,
        primary_color="Rush",
        secondary_color="Flow",
        selected_color="Rush",
        ref_arrays=ref_arrays,
        surface_words=surface_words,
        surface_counts=surface_counts,
    )

    assert group_calls == []
    assert batch_calls == [surface_count]


def test_response_inner_default_surface_work_cap_keeps_high_work_batch_together(monkeypatch):
    from gear_optimizer.solver.taichi_gem.force_greats import response_inner

    batch_calls: list[int] = []

    def fake_batch_kernel(
        row_count,
        surface_words,
        surface_counts,
        surface_head_coeffs,
        group_offsets,
        logical_owners,
        logical_surfaces,
        row_meta,
        color_flags,
        ref_pp,
        ref_cm,
        ref_fm,
        out_scores,
        out_details,
        allow_pp_template,
    ):
        batch_calls.append(int(row_count))
        out_scores[:] = np.arange(int(row_count), dtype=np.int32)

    monkeypatch.setattr(response_inner.gem_api, "ensure_ready", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(response_inner.ti, "sync", lambda: None)
    monkeypatch.setattr(response_inner, "_fg_response_inner_batch_kernel", fake_batch_kernel)
    monkeypatch.setattr(
        response_inner,
        "_response_inner_combo_counts",
        lambda *_args, **_kwargs: np.asarray([1_000_000_000], dtype=np.int64),
    )

    surface_count = 16
    group_meta = np.zeros((1, 8), dtype=np.int32)
    group_offsets = np.asarray([0], dtype=np.int32)
    group_lengths = np.asarray([surface_count], dtype=np.int32)
    surface_words = np.zeros((surface_count, 8), dtype=np.uint32)
    surface_counts = np.zeros((surface_count, 2), dtype=np.int32)
    ref_arrays = {
        "Perfect Points": np.ones(161, dtype=np.float32),
        "Combo Multiplier": np.ones(161, dtype=np.float32),
        "Fever Multiplier": np.ones(161, dtype=np.float32),
    }

    response_inner._score_response_group_meta_gpu(
        group_meta=group_meta,
        group_offsets=group_offsets,
        group_lengths=group_lengths,
        primary_color="Rush",
        secondary_color="Flow",
        selected_color="Rush",
        ref_arrays=ref_arrays,
        surface_words=surface_words,
        surface_counts=surface_counts,
    )

    assert batch_calls == [surface_count]


def test_response_inner_chill_colors_route_to_pp_template(monkeypatch):
    from gear_optimizer.solver.taichi_gem.force_greats import response_inner

    seen_allow_pp: list[bool] = []

    def fake_group_kernel(
        group_count,
        surface_words,
        surface_counts,
        surface_head_coeffs,
        group_offsets,
        group_lengths,
        group_meta,
        color_flags,
        ref_pp,
        ref_cm,
        ref_fm,
        out_rows,
        allow_pp_template,
    ):
        seen_allow_pp.append(bool(allow_pp_template))
        out_rows[: int(group_count), 0] = 1

    monkeypatch.setattr(response_inner.gem_api, "ensure_ready", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(response_inner.ti, "sync", lambda: None)
    monkeypatch.setattr(response_inner, "_fg_response_inner_group_kernel", fake_group_kernel)

    group_meta = np.zeros((1, 8), dtype=np.int32)
    group_offsets = np.asarray([0], dtype=np.int32)
    group_lengths = np.asarray([1], dtype=np.int32)
    surface_words = np.zeros((1, 8), dtype=np.uint32)
    surface_counts = np.zeros((1, 2), dtype=np.int32)
    ref_arrays = {
        "Perfect Points": np.ones(4, dtype=np.float32),
        "Combo Multiplier": np.ones(4, dtype=np.float32),
        "Fever Multiplier": np.ones(4, dtype=np.float32),
    }

    rows, logical_surface_rows = response_inner._score_response_group_meta_gpu(
        group_meta=group_meta,
        group_offsets=group_offsets,
        group_lengths=group_lengths,
        primary_color="Chill",
        secondary_color="Flow",
        selected_color="Rush",
        ref_arrays=ref_arrays,
        surface_words=surface_words,
        surface_counts=surface_counts,
    )

    assert logical_surface_rows == 1
    assert rows[0, 0] == 1
    assert seen_allow_pp == [True]


def test_response_inner_combo_estimator_reuses_duplicate_group_meta(monkeypatch):
    from gear_optimizer.solver.taichi_gem.force_greats import response_inner

    seen_inputs: list[tuple[int, int, int, int, bool]] = []

    def fake_combo_count(*, residual_budget, cur_pp, cur_cm, cur_fm, allow_pp):
        seen_inputs.append((int(residual_budget), int(cur_pp), int(cur_cm), int(cur_fm), bool(allow_pp)))
        return 1

    monkeypatch.setattr(response_inner, "_response_inner_combo_count", fake_combo_count)

    group_meta = np.asarray(
        [
            [5, 10, 20, 30, 100, 200, 7, 8],
            [5, 10, 20, 30, 999, 888, 9, 10],
            [6, 10, 20, 30, 100, 200, 7, 8],
        ],
        dtype=np.int32,
    )

    combo_counts = response_inner._response_inner_combo_counts(group_meta, allow_pp=True)

    np.testing.assert_array_equal(combo_counts, np.asarray([1, 1, 1], dtype=np.int64))
    assert seen_inputs == [
        (5, 10, 20, 30, True),
        (6, 10, 20, 30, True),
    ]


def test_response_inner_combo_count_matches_bruteforce():
    from gear_optimizer.core.constants import GEM_SCALE_FEVER, GEM_SCALE_NORMAL, MAX_STAT_INDEX
    from gear_optimizer.solver.taichi_gem.force_greats import response_inner

    def brute_combo_count(*, residual_budget: int, cur_pp: int, cur_cm: int, cur_fm: int, allow_pp: bool) -> int:
        residual = max(0, int(residual_budget))

        max_pp_gems = 0
        if bool(allow_pp) and int(cur_pp) < MAX_STAT_INDEX:
            rem_pp = MAX_STAT_INDEX - int(cur_pp)
            max_pp_gems = rem_pp // GEM_SCALE_NORMAL
            if rem_pp % GEM_SCALE_NORMAL != 0:
                max_pp_gems += 1

        max_cm_gems = 0
        if int(cur_cm) < MAX_STAT_INDEX:
            rem_cm = MAX_STAT_INDEX - int(cur_cm)
            max_cm_gems = rem_cm // GEM_SCALE_NORMAL
            if rem_cm % GEM_SCALE_NORMAL != 0:
                max_cm_gems += 1

        max_fm_gems = 0
        if int(cur_fm) < MAX_STAT_INDEX:
            rem_fm = MAX_STAT_INDEX - int(cur_fm)
            max_fm_gems = rem_fm // GEM_SCALE_FEVER
            if rem_fm % GEM_SCALE_FEVER != 0:
                max_fm_gems += 1

        max_pp_gems = min(int(max_pp_gems), int(residual))
        max_cm_gems = min(int(max_cm_gems), int(residual))
        max_fm_gems = min(int(max_fm_gems), int(residual))

        count = 0
        for g_cm in range(int(max_cm_gems) + 1):
            leftover_after_cm = int(residual) - int(g_cm)
            if leftover_after_cm < 0:
                break
            g_fm_max = min(int(max_fm_gems), int(leftover_after_cm))
            for g_fm in range(int(g_fm_max) + 1):
                leftover_after_fm = int(leftover_after_cm) - int(g_fm)
                count += min(int(max_pp_gems), int(leftover_after_fm)) + 1
        return max(1, int(count))

    rng = np.random.default_rng(1337)
    for _ in range(2000):
        residual = int(rng.integers(0, 91))
        cur_pp = int(rng.integers(0, 161))
        cur_cm = int(rng.integers(0, 161))
        cur_fm = int(rng.integers(0, 161))
        allow_pp = bool(int(rng.integers(0, 2)))
        expected = brute_combo_count(
            residual_budget=residual,
            cur_pp=cur_pp,
            cur_cm=cur_cm,
            cur_fm=cur_fm,
            allow_pp=allow_pp,
        )
        got = response_inner._response_inner_combo_count(
            residual_budget=residual,
            cur_pp=cur_pp,
            cur_cm=cur_cm,
            cur_fm=cur_fm,
            allow_pp=allow_pp,
        )
        assert int(got) == int(expected)
