"""Shared GPU registry must match the last writer across GA/core transitions."""

import numpy as np
import pytest


@pytest.mark.gpu
def test_alternating_upload_paths_and_in_place_edits_reach_shared_fields():
    from gear_optimizer.solver.taichi_gem import api, fields
    from gear_optimizer.solver.taichi_gem.api.ga_operations import reset_ga_upload_caches
    from gear_optimizer.solver.taichi_gem.api.skyline_operations import reset_skyline_upload_caches
    api.ensure_ready()
    reset_ga_upload_caches()
    reset_skyline_upload_caches()
    a = np.arange(20, dtype=np.int32).reshape(2, 10)
    b = a + 50
    starts = np.zeros(9, dtype=np.int32)
    counts = np.full(9, 2, dtype=np.int32)
    starts_b = np.ones(9, dtype=np.int32)
    counts_b = np.ones(9, dtype=np.int32)
    base_a, base_b = np.arange(10, dtype=np.int32), np.arange(10, dtype=np.int32) + 20
    for upload, base_upload, items, base, offsets, sizes in [
        (api.ga_upload_item_stats, api.ga_upload_base_fixed_stats, a, base_a, starts, counts),
        (api.skyline_upload_item_stats, api.skyline_upload_base_fixed_stats, b, base_b, starts_b, counts_b),
        (api.ga_upload_item_stats, api.ga_upload_base_fixed_stats, a, base_a, starts, counts),
        (api.skyline_upload_item_stats, api.skyline_upload_base_fixed_stats, b, base_b, starts_b, counts_b),
    ]:
        upload(items, offsets, sizes)
        base_upload(base)
        assert np.array_equal(fields.item_stats.to_numpy()[:2], items)
        assert np.array_equal(fields.base_fixed_stats.to_numpy(), base)
        assert np.array_equal(fields.slot_start.to_numpy(), offsets)
        assert np.array_equal(fields.slot_count.to_numpy(), sizes)
    b[0, 0] += 1
    counts_b[0] = 0
    api.skyline_upload_item_stats(b, starts_b, counts_b)
    assert np.array_equal(fields.item_stats.to_numpy()[:2], b)
    assert np.array_equal(fields.slot_count.to_numpy(), counts_b)
