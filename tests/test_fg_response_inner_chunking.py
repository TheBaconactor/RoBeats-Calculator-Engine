from __future__ import annotations

import numpy as np


def test_response_inner_group_scoring_keeps_small_groups_on_group_kernel_and_chunks_only_oversized_groups(monkeypatch):
    from gear_optimizer.solver.taichi_gem.force_greats import response_inner

    batch_calls: list[dict[str, int]] = []
    group_calls: list[dict[str, int]] = []

    def fake_group_kernel(
        group_count,
        surface_words,
        surface_counts,
        group_offsets,
        group_lengths,
        group_meta,
        color_flags,
        ref_pp,
        ref_cm,
        ref_fm,
        out_rows,
    ):
        group_calls.append({"group_count": int(group_count)})
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
        row_meta,
        color_flags,
        ref_pp,
        ref_cm,
        ref_fm,
        out_rows,
    ):
        batch_calls.append(
            {
                "row_count": int(row_count),
            }
        )
        for row_idx in range(int(row_count)):
            out_rows[row_idx, 0] = int(surface_counts[row_idx, 0])

    monkeypatch.setattr(response_inner.gem_api, "ensure_ready", lambda: None)
    monkeypatch.setattr(response_inner.ti, "sync", lambda: None)
    monkeypatch.setattr(response_inner, "_fg_response_inner_group_kernel", fake_group_kernel)
    monkeypatch.setattr(response_inner, "_fg_response_inner_batch_kernel", fake_kernel)
    monkeypatch.setattr(response_inner, "_FG_RESPONSE_INNER_GPU_MAX_DISPATCH_WORK", 10)
    monkeypatch.setattr(response_inner, "_FG_RESPONSE_INNER_GPU_MAX_THREAD_WORK", 3)
    monkeypatch.setattr(response_inner, "_FG_RESPONSE_INNER_GPU_MAX_SURFACE_DISPATCH_ROWS", 3)
    monkeypatch.setattr(response_inner, "_FG_RESPONSE_INNER_GPU_MAX_SURFACE_DISPATCH_WORK", 3)

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
    assert group_calls == [{"group_count": 2}]
    assert len(batch_calls) > 1
    assert all(call["row_count"] <= 3 for call in batch_calls)
    assert rows[:, 0].tolist() == [7, 9, 8]
    assert rows[:, 1].tolist() == [1, 1, 0]


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
