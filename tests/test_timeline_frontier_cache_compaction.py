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
    assert "fg_policy.py" not in sources


def _build_small_payload():
    ref_ft = np.linspace(0.0, 1.6, 161, dtype=np.float32)
    ref_ff = np.linspace(0.0, 1.6, 161, dtype=np.float32)
    timestamps = np.array([0.0, 0.0, 0.1, 0.1, 0.22, 0.22], dtype=np.float32)
    payload = build_timeline_frontier_grid_payload(
        song_slot=7,
        total_notes=6,
        long_notes=0,
        last_note_time=1.8,
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

    loaded, _raw = timeline_api._load_frontier_payload_from_disk(key)
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


def test_issue161_perfect_edge_rotation_rejects_all_predecessors(
    tmp_path: Path,
    monkeypatch,
) -> None:
    payload = _build_small_payload()
    current_version = timeline_api._FRONTIER_DISK_CACHE_VERSION
    predecessor = "exact-frontier-v12+logic-be26caca62b4"
    deployed_version = "exact-frontier-v12+logic-920bc4af7ee6"
    assert current_version == "exact-frontier-v12+logic-e2108556084d"
    assert timeline_api.timeline_frontier_compatible_cache_versions() == (
        current_version,
        deployed_version,
        predecessor,
    )
    unsafe_predecessors = {
        "exact-frontier-v12+logic-1f182e5b89af",
        "exact-frontier-v12+logic-4c69b48f08bb",
        "exact-frontier-v12+logic-9dfe907e66fb",
    }
    ratified_predecessors = {
        version
        for versions in timeline_api._EXACT_COMPATIBLE_TIMELINE_PREDECESSOR_VERSIONS.values()
        for version in versions
    }
    assert unsafe_predecessors.isdisjoint(ratified_predecessors)
    predecessor = "exact-frontier-v12+logic-73245c017cbd"
    current_key = (current_version, "unit", "issue161-incompatible")
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
    assert not timeline_api.timeline_frontier_cache_file_is_complete(predecessor_path)
    assert timeline_api._live_frontier_disk_cache_path(current_key) is None
    assert timeline_api._load_frontier_payload_from_disk(current_key) is None


def test_frontier_entrypoint_canonicalizes_raw_precise_input_before_cache_lookup(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("TIMELINE_FRONTIER_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("TIMELINE_FRONTIER_DISK_CACHE", "1")
    timeline_api.reset_timeline_state()
    stale_key = tuple(["stale"] * 12)
    calc_song = {
        "metadata": {
            "Song Name": "Raw Precise Timeline",
            "Difficulty": "Hard",
            "Long Notes": 0,
            "Last Note Time": 0.6,
        },
        "song_data": {
            "timestamps": np.array([0.0, 0.2, 0.4, 0.6], dtype=np.float32),
            "note_types": np.array([1, 1, 1, 1], dtype=np.int16),
            "lanes": np.array([0, 1, 2, 3], dtype=np.int32),
        },
        "_gpu_timing_cache_key_frontier": stale_key,
    }

    result = timeline_api.build_or_load_timeline_frontier_payload(
        calc_song,
        _ref_arrays(),
        timing_mode="perfect_window",
    )

    song_data = calc_song["song_data"]
    assert calc_song["metadata"]["TimingEnvelopeMode"] == "perfect_window"
    assert len(song_data["fg_perfect_candidate_timestamps"]) == 4
    assert len(song_data["fg_perfect_floor_timestamps"]) == 4
    assert calc_song["_gpu_timing_cache_key_frontier"] != stale_key
    assert result.cache_source == "built"


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


_PAYLOAD_ARRAY_NAMES = (
    "grid_count_body_fever",
    "grid_count_body_normal",
    "grid_head_len",
    "grid_fever_masks_bits",
    "grid_frontier_count",
    "grid_frontier_offset",
    "grid_frontier_body_fever_pool",
    "grid_frontier_body_normal_pool",
    "grid_frontier_masks_bits_pool",
    "grid_frontier_head_coeffs_pool",
    "grid_gap",
    "grid_fever_activations",
)


def _warm_disk_timeline_song(name: str) -> dict:
    calc_song = {
        "metadata": {
            "Song Name": name,
            "Difficulty": "Easy",
            "Long Notes": 0,
            "Last Note Time": 0.6,
        },
        "song_data": {
            "timestamps": np.array([0.0, 0.0, 0.2, 0.4, 0.6], dtype=np.float32),
            "note_types": np.array([1, 1, 1, 1, 1], dtype=np.int16),
        },
    }
    _apply_physical_timing(calc_song)
    return calc_song


def _assert_payload_live_region_equal(left, right) -> None:
    used = int(left.frontier_pool_used)
    assert int(right.frontier_pool_used) == used
    for name in _PAYLOAD_ARRAY_NAMES:
        a = np.asarray(getattr(left, name))
        b = np.asarray(getattr(right, name))
        assert a.dtype == b.dtype, name
        if name.endswith("_pool"):
            a, b = a[:, :used], b[:, :used]
        np.testing.assert_array_equal(a, b, err_msg=name)


def test_frontier_payload_memory_hit_serves_the_built_and_disk_payload(tmp_path: Path, monkeypatch) -> None:
    """Built, memory-hit and disk-hit payloads agree on every array the consumers read (grids plus
    the pool rows below frontier_pool_used), so the memory tier cannot change a score."""
    monkeypatch.setenv("TIMELINE_FRONTIER_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("TIMELINE_FRONTIER_DISK_CACHE", "1")
    timeline_api.reset_timeline_state()
    calc_song = _warm_disk_timeline_song("Memory Tier Timeline")

    first = timeline_api.build_or_load_timeline_frontier_payload(calc_song, _ref_arrays())
    second = timeline_api.build_or_load_timeline_frontier_payload(calc_song, _ref_arrays())
    timeline_api.reset_timeline_state()
    third = timeline_api.build_or_load_timeline_frontier_payload(calc_song, _ref_arrays())

    assert (first.cache_source, second.cache_source, third.cache_source) == ("built", "memory", "disk")
    assert int(first.payload.frontier_pool_used) > 0
    _assert_payload_live_region_equal(first.payload, second.payload)
    _assert_payload_live_region_equal(second.payload, third.payload)


def test_frontier_payload_memory_tier_holds_compressed_disk_bytes(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TIMELINE_FRONTIER_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("TIMELINE_FRONTIER_DISK_CACHE", "1")
    timeline_api.reset_timeline_state()
    calc_song = _warm_disk_timeline_song("Compressed Memory Tier Timeline")

    first = timeline_api.build_or_load_timeline_frontier_payload(calc_song, _ref_arrays())
    assert first.cache_source == "built"
    cached = timeline_api._frontier_payload_cache[first.cache_key]
    assert isinstance(cached, bytes)
    assert len(cached) < 200_000
    assert cached == Path(first.disk_path).read_bytes()
    info = timeline_api.timeline_frontier_payload_cache_info(calc_song, _ref_arrays())
    assert info.cache_source == "memory"

    with monkeypatch.context() as no_disk:
        no_disk.setattr(
            timeline_api,
            "_live_frontier_disk_cache_path",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("memory hit must not touch disk")),
        )
        second = timeline_api.build_or_load_timeline_frontier_payload(calc_song, _ref_arrays())
    assert second.cache_source == "memory"

    timeline_api.reset_timeline_state()
    third = timeline_api.build_or_load_timeline_frontier_payload(calc_song, _ref_arrays())
    assert third.cache_source == "disk"
    assert timeline_api._frontier_payload_cache[third.cache_key] == cached
    # A memory hit decodes exactly the disk form: identical arrays, dtypes and (trimmed) shapes.
    for name in _PAYLOAD_ARRAY_NAMES:
        a = np.asarray(getattr(second.payload, name))
        b = np.asarray(getattr(third.payload, name))
        assert a.dtype == b.dtype and a.shape == b.shape, name
        np.testing.assert_array_equal(a, b, err_msg=name)
    assert int(second.payload.frontier_pool_used) == int(third.payload.frontier_pool_used)
    _assert_payload_live_region_equal(first.payload, second.payload)


def test_frontier_payload_memory_tier_survives_failed_disk_write(tmp_path: Path, monkeypatch) -> None:
    """A swallowed disk-write failure must not break the memory tier: the bytes are serialized
    before the write, so the next lookup is still a memory hit."""
    monkeypatch.setenv("TIMELINE_FRONTIER_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("TIMELINE_FRONTIER_DISK_CACHE", "1")
    timeline_api.reset_timeline_state()
    calc_song = _warm_disk_timeline_song("Failed Write Timeline")

    with monkeypatch.context() as failing_replace:

        def _raise_replace(self, target):
            raise OSError("simulated replace failure")

        failing_replace.setattr(Path, "replace", _raise_replace)
        first = timeline_api.build_or_load_timeline_frontier_payload(calc_song, _ref_arrays())
    assert first.cache_source == "built"
    assert not Path(first.disk_path).exists()

    second = timeline_api.build_or_load_timeline_frontier_payload(calc_song, _ref_arrays())
    assert second.cache_source == "memory"
    _assert_payload_live_region_equal(first.payload, second.payload)


def test_cache_info_reports_predecessor_disk_path_when_only_predecessor_exists(
    tmp_path: Path, monkeypatch
) -> None:
    """Regression (PR #159 review): when only a ratified predecessor-version file exists,
    cache_info must report THAT file as disk_path — returning the nonexistent
    current-version path made the prebuild manifest unable to validate/record the hit."""
    monkeypatch.setenv("TIMELINE_FRONTIER_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("TIMELINE_FRONTIER_DISK_CACHE", "1")
    monkeypatch.setattr(
        timeline_api,
        "_FRONTIER_DISK_CACHE_VERSION",
        "exact-frontier-v12+logic-73245c017cbd",
    )
    timeline_api.reset_timeline_state()
    calc_song = {
        "metadata": {
            "Song Name": "Predecessor Info Timeline",
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

    built = timeline_api.build_or_load_timeline_frontier_payload(calc_song, ref_arrays)
    assert built.cache_source == "built"
    current_path = Path(built.disk_path)
    assert current_path.exists()

    predecessor = timeline_api.timeline_frontier_compatible_cache_versions()[1]
    predecessor_key = (predecessor, *built.cache_key[1:])
    with monkeypatch.context() as predecessor_context:
        predecessor_context.setattr(timeline_api, "_FRONTIER_DISK_CACHE_VERSION", predecessor)
        timeline_api._save_frontier_payload_to_disk(predecessor_key, built.payload)
    predecessor_path = timeline_api._frontier_disk_cache_path(predecessor_key)
    assert predecessor_path.exists()
    current_path.unlink()

    timeline_api.reset_timeline_state()
    info = timeline_api.timeline_frontier_payload_cache_info(calc_song, ref_arrays)
    assert info.cache_source == "disk"
    assert Path(info.disk_path) == predecessor_path
    assert Path(info.disk_path).exists()


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
