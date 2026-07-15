from __future__ import annotations

import os
import time
from pathlib import Path

import numpy as np
import pytest

from gear_optimizer.solver.timeline_exact_frontier import build_timeline_frontier_grid_payload
from gear_optimizer.solver.taichi_gem.api import timeline as timeline_api


def test_timeline_cache_fingerprint_covers_shared_frontier_producer() -> None:
    sources = {path.name for path in timeline_api._TIMELINE_DP_SOURCES}

    assert {
        "timeline_exact_frontier.py",
        "timing_envelope.py",
        "response_builder.py",
        "response_build_gpu_batch.py",
        "response_build_gpu_numba.py",
    }.issubset(sources)


def _build_small_payload():
    ref_ft = np.linspace(0.0, 1.6, 161, dtype=np.float32)
    ref_ff = np.linspace(0.0, 1.6, 161, dtype=np.float32)
    timestamps = np.array([0.0, 0.0, 0.1, 0.1, 0.22, 0.22], dtype=np.float32)
    payload = build_timeline_frontier_grid_payload(
        song_slot=7,
        total_notes=6,
        long_notes=0,
        last_note_time=1.8,
        song_key="unit-test-song",
        timestamps=timestamps,
        perfect_candidate_timestamps=timestamps + np.float32(0.04),
        perfect_floor_timestamps=timestamps - np.float32(0.019),
        lanes=np.arange(6, dtype=np.int32),
        ref_ft=ref_ft,
        ref_ff=ref_ff,
    )
    return payload


def _ref_arrays() -> dict[str, np.ndarray]:
    return {
        "Fever Time": np.linspace(0.0, 1.6, 161, dtype=np.float32),
        "Fever Fill Rate": np.linspace(0.0, 1.6, 161, dtype=np.float32),
    }


def _apply_physical_timing(calc_song: dict) -> None:
    from gear_optimizer.solver.timing_envelope import apply_timing_envelope

    note_count = len(calc_song["song_data"]["timestamps"])
    calc_song["song_data"]["lanes"] = np.arange(note_count, dtype=np.int32)
    apply_timing_envelope(calc_song, mode="perfect_window")


def test_frontier_payload_build_is_single_slot_compact() -> None:
    payload = _build_small_payload()
    assert payload.frontier_pool_used > 0
    assert int(payload.grid_count_body_fever.shape[0]) == 1
    assert int(payload.grid_count_body_normal.shape[0]) == 1
    assert int(payload.grid_head_len.shape[0]) == 1
    assert int(payload.grid_fever_masks_bits.shape[0]) == 1
    assert int(payload.grid_frontier_count.shape[0]) == 1
    assert int(payload.grid_frontier_offset.shape[0]) == 1
    assert int(payload.grid_frontier_body_fever_pool.shape[0]) == 1
    assert int(payload.grid_frontier_body_normal_pool.shape[0]) == 1
    assert int(payload.grid_frontier_masks_bits_pool.shape[0]) == 1
    assert int(payload.grid_gap.shape[0]) == 1
    assert int(payload.grid_fever_activations.shape[0]) == 1


def test_frontier_disk_cache_write_is_compact_and_leak_free(tmp_path: Path, monkeypatch) -> None:
    payload = _build_small_payload()
    key = ("unit", "compact", 1)
    monkeypatch.setenv("TIMELINE_FRONTIER_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("TIMELINE_FRONTIER_DISK_CACHE", "1")

    timeline_api._save_frontier_payload_to_disk(key, payload)
    saved = timeline_api._frontier_disk_cache_path(key)
    assert saved.exists()
    assert not list(tmp_path.glob("*.tmp.npz"))

    loaded = timeline_api._load_frontier_payload_from_disk(key)
    assert loaded is not None
    assert int(loaded.grid_count_body_fever.shape[0]) == 1
    assert int(loaded.grid_frontier_body_fever_pool.shape[0]) == 1
    assert int(loaded.grid_frontier_body_normal_pool.shape[0]) == 1
    assert int(loaded.grid_frontier_masks_bits_pool.shape[0]) == 1
    assert int(loaded.grid_frontier_body_fever_pool.shape[1]) == int(payload.frontier_pool_used)
    assert int(loaded.grid_frontier_body_normal_pool.shape[1]) == int(payload.frontier_pool_used)
    assert int(loaded.grid_frontier_masks_bits_pool.shape[1]) == int(payload.frontier_pool_used)
    with np.load(saved, allow_pickle=False) as data:
        assert set(data.files) == set(timeline_api._TIMELINE_FRONTIER_CACHE_ARRAY_NAMES)
        assert not any(name.startswith("group_") for name in data.files)


def test_frontier_disk_cache_reuses_exact_compatible_cleanup_predecessor(
    tmp_path: Path,
    monkeypatch,
) -> None:
    payload = _build_small_payload()
    current_version = timeline_api._FRONTIER_DISK_CACHE_VERSION
    assert current_version == "exact-frontier-v12+logic-1f182e5b89af"
    assert timeline_api.timeline_frontier_compatible_cache_versions() == (
        current_version,
        "exact-frontier-v12+logic-4c69b48f08bb",
        "exact-frontier-v12+logic-9dfe907e66fb",
    )
    predecessor = timeline_api.timeline_frontier_compatible_cache_versions()[1]
    current_key = (current_version, "unit", "cleanup-compatible")
    predecessor_key = (predecessor, *current_key[1:])
    monkeypatch.setenv("TIMELINE_FRONTIER_CACHE_DIR", str(tmp_path))

    with monkeypatch.context() as predecessor_context:
        predecessor_context.setattr(
            timeline_api,
            "_FRONTIER_DISK_CACHE_VERSION",
            predecessor,
        )
        timeline_api._save_frontier_payload_to_disk(predecessor_key, payload)

    predecessor_path = timeline_api._frontier_disk_cache_path(predecessor_key)
    assert predecessor_path.exists()
    assert timeline_api.timeline_frontier_cache_file_is_complete(predecessor_path)
    assert timeline_api._live_frontier_disk_cache_path(current_key) == predecessor_path
    loaded = timeline_api._load_frontier_payload_from_disk(current_key)
    assert loaded is not None
    assert loaded.frontier_pool_used == payload.frontier_pool_used


def test_build_or_load_timeline_frontier_payload_disk_hit_reuses_compact_payload(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("TIMELINE_FRONTIER_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("TIMELINE_FRONTIER_DISK_CACHE", "1")
    timeline_api.reset_timeline_state()
    calc_song = {
        "metadata": {
            "Song Name": "Warm Disk Timeline",
            "Difficulty": "Easy",
            "Long Notes": 0,
            "Last Note Time": 0.6,
        },
        "song_data": {
            "timestamps": np.array([0.0, 0.2, 0.4, 0.6], dtype=np.float32),
            "note_types": np.array([1, 1, 1, 1], dtype=np.int16),
        },
    }
    _apply_physical_timing(calc_song)
    ref_arrays = _ref_arrays()

    first = timeline_api.build_or_load_timeline_frontier_payload(calc_song, ref_arrays)
    assert first.cache_source == "built"

    timeline_api.reset_timeline_state()
    second = timeline_api.build_or_load_timeline_frontier_payload(calc_song, ref_arrays)
    assert second.cache_source == "disk"
    assert int(second.total_notes) == 4


def test_build_or_load_timeline_frontier_payload_reuses_old_disk_cache_without_ttl(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TIMELINE_FRONTIER_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("TIMELINE_FRONTIER_DISK_CACHE", "1")
    monkeypatch.setenv("ROBEATSMETA_LIVE_CACHE_IDLE_TTL_SECONDS", "1800")
    timeline_api.reset_timeline_state()
    calc_song = {
        "metadata": {
            "Song Name": "Stale Disk Timeline",
            "Difficulty": "Easy",
            "Long Notes": 0,
            "Last Note Time": 0.6,
        },
        "song_data": {
            "timestamps": np.array([0.0, 0.2, 0.4, 0.6], dtype=np.float32),
            "note_types": np.array([1, 1, 1, 1], dtype=np.int16),
        },
    }
    _apply_physical_timing(calc_song)

    first = timeline_api.build_or_load_timeline_frontier_payload(calc_song, _ref_arrays())
    assert first.cache_source == "built"
    stale_ts = time.time() - 3700.0
    os.utime(first.disk_path, (stale_ts, stale_ts))

    timeline_api.reset_timeline_state()
    second = timeline_api.build_or_load_timeline_frontier_payload(calc_song, _ref_arrays())
    assert second.cache_source == "disk"
    assert second.disk_path.exists()
    assert second.disk_path.stat().st_mtime == stale_ts


def test_load_timeline_frontier_payload_builds_and_persists_live_cache_miss(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TIMELINE_FRONTIER_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("TIMELINE_FRONTIER_DISK_CACHE", "1")
    timeline_api.reset_timeline_state()
    calc_song = {
        "metadata": {
            "Song Name": "Runtime Missing Timeline",
            "Difficulty": "Easy",
            "Long Notes": 0,
            "Last Note Time": 0.6,
        },
        "song_data": {
            "timestamps": np.array([0.0, 0.2, 0.4, 0.6], dtype=np.float32),
            "note_types": np.array([1, 1, 1, 1], dtype=np.int16),
        },
    }
    _apply_physical_timing(calc_song)

    built = timeline_api.load_timeline_frontier_payload(calc_song, _ref_arrays())
    assert built.cache_source == "built"
    assert built.disk_path.exists()
    timeline_api.reset_timeline_state()
    loaded = timeline_api.load_timeline_frontier_payload(calc_song, _ref_arrays())
    assert loaded.cache_source == "disk"
    assert int(loaded.total_notes) == 4


def test_frontier_disk_cache_cleans_tmp_when_replace_fails(tmp_path: Path, monkeypatch) -> None:
    payload = _build_small_payload()
    key = ("unit", "replace-fail", 2)
    monkeypatch.setenv("TIMELINE_FRONTIER_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("TIMELINE_FRONTIER_DISK_CACHE", "1")

    def _raise_replace(self, target):  # pragma: no cover - exercised by assertion side-effects
        raise OSError("simulated replace failure")

    monkeypatch.setattr(Path, "replace", _raise_replace)
    timeline_api._save_frontier_payload_to_disk(key, payload)

    assert not timeline_api._frontier_disk_cache_path(key).exists()
    assert not list(tmp_path.glob("*.tmp.npz"))


def test_frontier_cache_key_ignores_unrelated_ref_arrays() -> None:
    calc_song = {
        "metadata": {
            "Song Name": "unit-test-song",
            "Difficulty": "Hard",
            "Long Notes": 0,
            "Last Note Time": 1.8,
        },
        "song_data": {
            "timestamps": np.array([0.0, 0.2, 0.4, 0.6], dtype=np.float32),
            "note_types": np.array([1, 1, 1, 1], dtype=np.int16),
        },
    }
    _apply_physical_timing(calc_song)
    ref_ft = np.linspace(0.0, 1.6, 161, dtype=np.float32)
    ref_ff = np.linspace(0.0, 1.6, 161, dtype=np.float32)
    ref_base = {
        "Fever Time": ref_ft,
        "Fever Fill Rate": ref_ff,
        "Perfect Points": np.arange(161, dtype=np.float32),
        "Combo Multiplier": np.arange(161, dtype=np.float32),
    }
    ref_variant = {
        "Fever Time": ref_ft.copy(),
        "Fever Fill Rate": ref_ff.copy(),
        "Perfect Points": np.arange(161, dtype=np.float32) * 7.0,
        "Combo Multiplier": np.arange(161, dtype=np.float32) * 3.0,
    }

    info_base = timeline_api.timeline_frontier_payload_cache_info(calc_song, ref_base)
    info_variant = timeline_api.timeline_frontier_payload_cache_info(calc_song, ref_variant)

    assert info_base.cache_key == info_variant.cache_key
    assert info_base.disk_path == info_variant.disk_path
