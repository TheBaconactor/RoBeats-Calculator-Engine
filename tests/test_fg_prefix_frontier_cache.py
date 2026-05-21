import numpy as np


def test_fg_prefix_frontier_cache_round_trip_and_effective_key(tmp_path, monkeypatch):
    from gear_optimizer.solver.taichi_gem.force_greats import prefix_frontier_cache as cache

    monkeypatch.setenv("FG_PREFIX_FRONTIER_CACHE_DIR", str(tmp_path))
    timestamps = np.linspace(0.0, 10.0, 24, dtype=np.float32)
    ref_arrays = {
        "Fever Time": np.linspace(1.0, 2.5, 161, dtype=np.float32),
        "Fever Fill Rate": np.linspace(1.0, 2.0, 161, dtype=np.float32),
    }
    base_key = cache.fg_prefix_frontier_base_cache_key(
        timestamps=timestamps,
        great_candidate_timestamps=timestamps,
        total_notes=len(timestamps),
        long_notes=0,
        n_sections=2,
        ref_arrays=ref_arrays,
    )
    key_a = cache.fg_prefix_frontier_cache_key(base_key, ft_idx=80, ff_idx=80)
    key_b = cache.fg_prefix_frontier_cache_key(base_key, ft_idx=81, ff_idx=80)
    assert key_a != key_b

    payload = cache.FgPrefixFrontierPayload(
        signatures=np.arange(22, dtype=np.int32).reshape(2, 11),
        forced_counts=np.asarray([[0, 1], [2, 3]], dtype=np.int32),
        count=2,
        n_sections=2,
    )
    cache.save_fg_prefix_frontier_payload(key_a, payload)
    loaded = cache.load_fg_prefix_frontier_payload(key_a)

    assert loaded is not None
    assert loaded.count == 2
    assert loaded.n_sections == 2
    np.testing.assert_array_equal(loaded.signatures, payload.signatures)
    np.testing.assert_array_equal(loaded.forced_counts, payload.forced_counts)
