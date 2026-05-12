import numpy as np

from gear_optimizer.solver import gpu_executor
from gear_optimizer.solver.gpu_executor import _minimize_calc_song_for_gpu_timeline_grid, _registry_base_fixed_stats_sig
from gear_optimizer.solver.gpu_executor_static_handles import (
    REGISTRY_STATIC_HANDLE_CACHE,
    clear_registry_static_handle_cache,
    minimize_calc_song_for_gpu_timeline_grid,
    registry_base_fixed_stats_sig,
    registry_static_handle_entry,
)


def test_registry_base_fixed_stats_signature_is_content_based():
    a = np.arange(10, dtype=np.int32)
    b = np.arange(10, dtype=np.int64)
    c = np.arange(10, dtype=np.int32)
    c[0] = 99

    assert registry_base_fixed_stats_sig(a) == registry_base_fixed_stats_sig(b)
    assert registry_base_fixed_stats_sig(a) != registry_base_fixed_stats_sig(c)


def test_gpu_executor_reexports_registry_base_fixed_stats_signature_for_compatibility():
    assert _registry_base_fixed_stats_sig is registry_base_fixed_stats_sig


def test_minimize_calc_song_for_gpu_timeline_grid_preserves_timing_metadata_and_signatures():
    calc_song = {
        "metadata": {
            "Song Name": "Song",
            "Difficulty": "Hard",
            "Long Notes": "2",
            "Last Note Time": "12.5",
            "TimingEnvelopeApplied": True,
            "TimingEnvelopeMode": "perfect_window",
            "TimingEnvelopeFGCarry": "late_upper",
            "Dropped": "large metadata",
        },
        "song_data": {
            "timestamps": np.array([0.0, 1.0], dtype=np.float64),
            "chart_timestamps": np.array([0.1, 1.1], dtype=np.float64),
            "note_types": np.array([1, 2], dtype=np.int64),
            "_timestamps_sig": b"1" * 16,
            "_chart_timestamps_sig": b"2" * 16,
            "_note_types_sig": b"3" * 16,
            "extra": "drop me",
        },
    }

    minimized = minimize_calc_song_for_gpu_timeline_grid(calc_song)

    assert minimized["metadata"] == {
        "Song Name": "Song",
        "Difficulty": "Hard",
        "Long Notes": 2,
        "Last Note Time": 12.5,
        "TimingEnvelopeApplied": True,
        "TimingEnvelopeMode": "perfect_window",
        "TimingEnvelopeFGCarry": "late_upper",
    }
    assert set(minimized["song_data"]) == {
        "timestamps",
        "chart_timestamps",
        "note_types",
        "_timestamps_sig",
        "_chart_timestamps_sig",
        "_note_types_sig",
    }
    assert minimized["song_data"]["timestamps"].dtype == np.float32
    assert minimized["song_data"]["chart_timestamps"].dtype == np.float32
    assert minimized["song_data"]["note_types"].dtype == np.int16


def test_gpu_executor_reexports_calc_song_minimizer_for_compatibility():
    assert _minimize_calc_song_for_gpu_timeline_grid is minimize_calc_song_for_gpu_timeline_grid


def test_registry_static_handle_entry_reuses_static_payload_owner_cache():
    clear_registry_static_handle_cache()
    item_stats = np.arange(40, dtype=np.int16).reshape(4, 10)
    slot_start = np.arange(9, dtype=np.int32)
    slot_count = np.ones(9, dtype=np.int32)
    base_fixed_stats = np.arange(10, dtype=np.int64)
    timeline_grid = {
        "metadata": {"Song Name": "Static", "Difficulty": "Hard"},
        "song_data": {"timestamps": np.array([0.0, 1.0], dtype=np.float32)},
    }
    ref_arrays = {"Perfect Points": [0.0] * 161}

    first = registry_static_handle_entry(
        item_stats=item_stats,
        slot_start=slot_start,
        slot_count=slot_count,
        base_fixed_stats=base_fixed_stats,
        timeline_grid=timeline_grid,
        ref_arrays=ref_arrays,
    )
    second = registry_static_handle_entry(
        item_stats=item_stats,
        slot_start=slot_start,
        slot_count=slot_count,
        base_fixed_stats=base_fixed_stats.astype(np.int32),
        timeline_grid=timeline_grid,
        ref_arrays=ref_arrays,
    )

    assert second is first
    assert len(REGISTRY_STATIC_HANDLE_CACHE) == 1


def test_gpu_executor_reexports_registry_static_handle_cache_for_compatibility():
    assert gpu_executor._registry_static_handle_entry is registry_static_handle_entry
    assert gpu_executor._REGISTRY_STATIC_HANDLE_CACHE is REGISTRY_STATIC_HANDLE_CACHE
