from __future__ import annotations

from tests.curves_support import synthetic_curves
import os
import time
from pathlib import Path

import numpy as np
import pytest

from gear_optimizer.frontier.timeline_producer import build_timeline_frontier_grid_payload
from gear_optimizer.solver.timing_envelope import fever_durations, fever_fill_denominators, fever_fill_thresholds
from gear_optimizer.frontier import timeline_cache as timeline_api
from tests.songs_support import make_song


def test_timeline_cache_fingerprint_covers_shared_frontier_producer() -> None:
    sources = {path.name for path in timeline_api._TIMELINE_DP_SOURCES}

    assert {
        "timeline_producer.py",
        "timing_envelope.py",
        "fill_crossing.py",
        "producer_batch.py",
        "producer_kernels.py",
    }.issubset(sources)
    # Neither the FG scoring policy nor the trace reconstruction determines a cached payload.
    assert not {"fg_policy.py", "reconstruct.py", "activation_witness.py"} & sources


def _build_small_payload():
    decay_rates = np.linspace(0.0, 1.6, 161)
    # A fill base is never 0 in the game (its curve ends at 0.0769): a zero denominator has no fill threshold.
    fill_bases = np.linspace(0.01, 1.6, 161)
    timestamps = np.array([0.0, 0.0, 0.1, 0.1, 0.22, 0.22], dtype=np.float32)
    perfect_candidates = timestamps + np.float32(0.04)
    payload = build_timeline_frontier_grid_payload(
        timestamps=timestamps,
        perfect_candidate_timestamps=perfect_candidates,
        perfect_floor_timestamps=timestamps - np.float32(0.019),
        exit_ceiling_timestamps=np.minimum.accumulate(perfect_candidates[::-1])[::-1],
        lanes=np.arange(6, dtype=np.int32),
        fever_times=fever_durations(1.8, decay_rates),
        fever_fills=fever_fill_thresholds(fever_fill_denominators(6, fill_bases)),
    )
    return payload


def _forget_payloads() -> None:
    """Empty the process's memory tier, so the next load reads its file."""
    timeline_api._frontier_payload_memory.clear()


def _song(name: str):
    return make_song([0.0, 0.2, 0.4, 0.6], name=name, difficulty="Easy", last_note_time=0.6)


def _curves() -> dict[str, np.ndarray]:
    # A fill base is never 0 in the game (its curve ends at 0.0769): a zero denominator has no fill threshold.
    return synthetic_curves({
        "Fever Time": np.linspace(0.0, 1.6, 161, dtype=np.float32) * 0.15,
        "Fever Fill Rate": np.linspace(0.01, 1.6, 161, dtype=np.float32) * 0.333,
    })


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
    monkeypatch.setenv("TIMELINE_FRONTIER_CACHE_DIR", str(tmp_path))
    _forget_payloads()

    built = timeline_api.build_or_load_timeline_frontier_payload(_song("Compact Timeline"), _curves())
    assert built.cache_source == "built" and built.disk_path.exists()
    assert [path.name for path in tmp_path.iterdir()] == [built.disk_path.name]  # one file, no temporary left

    _forget_payloads()
    loaded = timeline_api.build_or_load_timeline_frontier_payload(_song("Compact Timeline"), _curves()).payload
    used = loaded.frontier_pool_used
    assert used > 0
    assert int(loaded.grid_count_body_fever.shape[0]) == 1
    for pool in (loaded.grid_frontier_body_fever_pool, loaded.grid_frontier_body_normal_pool, loaded.grid_frontier_masks_bits_pool):
        assert pool.shape[:2] == (1, used)  # the one song slot, only the rows in use
    with np.load(built.disk_path, allow_pickle=False) as data:
        assert set(data.files) == {"version", "frontier_pool_used", *_PAYLOAD_ARRAY_NAMES}


def test_issue161_perfect_edge_rotation_rejects_all_predecessors(tmp_path: Path, monkeypatch) -> None:
    """A file of a version the current one does not list is not complete, not readable and not served."""
    monkeypatch.setenv("TIMELINE_FRONTIER_CACHE_DIR", str(tmp_path))
    _forget_payloads()
    with monkeypatch.context() as predecessor_context:
        predecessor_context.setattr(timeline_api, "_FRONTIER_DISK_CACHE_VERSION", "exact-frontier-v12+logic-73245c017cbd")
        predecessor = timeline_api.build_or_load_timeline_frontier_payload(_song("Unlisted Predecessor"), _curves())
    assert predecessor.disk_path.exists()
    _forget_payloads()

    assert not timeline_api.timeline_frontier_cache_file_is_complete(predecessor.disk_path)
    current_key = (timeline_api.TIMELINE_FRONTIER_CACHE.version(), *predecessor.cache_key[1:])
    assert timeline_api.TIMELINE_FRONTIER_CACHE.readable_path(current_key) is None
    assert timeline_api.build_or_load_timeline_frontier_payload(_song("Unlisted Predecessor"), _curves()).cache_source == "built"


def test_build_or_load_timeline_frontier_payload_disk_hit_reuses_compact_payload(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("TIMELINE_FRONTIER_CACHE_DIR", str(tmp_path))
    _forget_payloads()
    song = make_song([0.0, 0.2, 0.4, 0.6], name="Warm Disk Timeline", difficulty="Easy", last_note_time=0.6)
    curves = _curves()

    first = timeline_api.build_or_load_timeline_frontier_payload(song, curves)
    assert first.cache_source == "built"

    _forget_payloads()
    second = timeline_api.build_or_load_timeline_frontier_payload(song, curves)
    assert second.cache_source == "disk"


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


def _warm_disk_timeline_song(name: str):
    song = make_song([0.0, 0.0, 0.2, 0.4, 0.6], name=name, difficulty="Easy", last_note_time=0.6)
    return song


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
    _forget_payloads()
    song = _warm_disk_timeline_song("Memory Tier Timeline")

    first = timeline_api.build_or_load_timeline_frontier_payload(song, _curves())
    second = timeline_api.build_or_load_timeline_frontier_payload(song, _curves())
    _forget_payloads()
    third = timeline_api.build_or_load_timeline_frontier_payload(song, _curves())

    assert (first.cache_source, second.cache_source, third.cache_source) == ("built", "memory", "disk")
    assert int(first.payload.frontier_pool_used) > 0
    _assert_payload_live_region_equal(first.payload, second.payload)
    _assert_payload_live_region_equal(second.payload, third.payload)


def test_frontier_payload_memory_tier_holds_compressed_disk_bytes(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TIMELINE_FRONTIER_CACHE_DIR", str(tmp_path))
    _forget_payloads()
    song = _warm_disk_timeline_song("Compressed Memory Tier Timeline")

    first = timeline_api.build_or_load_timeline_frontier_payload(song, _curves())
    assert first.cache_source == "built"
    on_disk = Path(first.disk_path).read_bytes()
    # The tier keeps the file's compressed bytes (tens of KB), not the ~1.1 MB decoded payload.
    cached = timeline_api._frontier_payload_memory.get(first.cache_key)
    assert cached == on_disk and len(cached) < 200_000
    info = timeline_api.timeline_frontier_payload_cache_info(song, _curves())
    assert info.cache_source == "memory"

    Path(first.disk_path).unlink()  # a memory hit needs no file
    second = timeline_api.build_or_load_timeline_frontier_payload(song, _curves())
    assert second.cache_source == "memory"
    Path(first.disk_path).write_bytes(on_disk)

    _forget_payloads()
    third = timeline_api.build_or_load_timeline_frontier_payload(song, _curves())
    assert third.cache_source == "disk"
    assert timeline_api._frontier_payload_memory.get(third.cache_key) == cached
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
    _forget_payloads()
    song = _warm_disk_timeline_song("Failed Write Timeline")

    with monkeypatch.context() as failing_replace:

        def _raise_replace(self, target):
            raise OSError("simulated replace failure")

        failing_replace.setattr(Path, "replace", _raise_replace)
        first = timeline_api.build_or_load_timeline_frontier_payload(song, _curves())
    assert first.cache_source == "built"
    assert not Path(first.disk_path).exists()
    assert not list(tmp_path.iterdir())  # the temporary file of the failed write is gone too

    second = timeline_api.build_or_load_timeline_frontier_payload(song, _curves())
    assert second.cache_source == "memory"
    _assert_payload_live_region_equal(first.payload, second.payload)


def test_cache_info_reports_predecessor_disk_path_when_only_predecessor_exists(
    tmp_path: Path, monkeypatch
) -> None:
    """Regression (PR #159 review): when only a ratified predecessor-version file exists,
    cache_info must report THAT file as disk_path — returning the nonexistent
    current-version path made the prebuild manifest unable to validate/record the hit."""
    monkeypatch.setenv("TIMELINE_FRONTIER_CACHE_DIR", str(tmp_path))
    # A synthetic ratified pair: the mechanism, independent of which versions are ratified today.
    current, older = "exact-frontier-test+logic-current", "exact-frontier-test+logic-older"
    monkeypatch.setitem(timeline_api._EXACT_COMPATIBLE_TIMELINE_PREDECESSOR_VERSIONS, current, (older,))
    song, curves = _song("Predecessor Info Timeline"), _curves()
    _forget_payloads()
    monkeypatch.setattr(timeline_api, "_FRONTIER_DISK_CACHE_VERSION", older)
    predecessor_path = timeline_api.build_or_load_timeline_frontier_payload(song, curves).disk_path
    assert predecessor_path.exists()

    monkeypatch.setattr(timeline_api, "_FRONTIER_DISK_CACHE_VERSION", current)
    _forget_payloads()
    info = timeline_api.timeline_frontier_payload_cache_info(song, curves)

    assert info.cache_source == "disk"
    assert Path(info.disk_path) == predecessor_path
    assert timeline_api.build_or_load_timeline_frontier_payload(song, curves).cache_source == "disk"  # and it is served


def test_build_or_load_timeline_frontier_payload_reuses_old_disk_cache_without_ttl(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TIMELINE_FRONTIER_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("ROBEATSMETA_LIVE_CACHE_IDLE_TTL_SECONDS", "1800")
    _forget_payloads()
    song = make_song([0.0, 0.2, 0.4, 0.6], name="Stale Disk Timeline", difficulty="Easy", last_note_time=0.6)

    first = timeline_api.build_or_load_timeline_frontier_payload(song, _curves())
    assert first.cache_source == "built"
    stale_ts = time.time() - 3700.0
    os.utime(first.disk_path, (stale_ts, stale_ts))

    _forget_payloads()
    second = timeline_api.build_or_load_timeline_frontier_payload(song, _curves())
    assert second.cache_source == "disk"
    assert second.disk_path.exists()
    assert second.disk_path.stat().st_mtime == stale_ts


def test_build_or_load_timeline_frontier_payload_builds_and_persists_live_cache_miss(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("TIMELINE_FRONTIER_CACHE_DIR", str(tmp_path))
    _forget_payloads()
    song = make_song([0.0, 0.2, 0.4, 0.6], name="Runtime Missing Timeline", difficulty="Easy", last_note_time=0.6)

    built = timeline_api.build_or_load_timeline_frontier_payload(song, _curves())
    assert built.cache_source == "built"
    assert built.disk_path.exists()
    _forget_payloads()
    loaded = timeline_api.build_or_load_timeline_frontier_payload(song, _curves())
    assert loaded.cache_source == "disk"


def test_frontier_cache_key_ignores_unrelated_ref_arrays() -> None:
    song = make_song([0.0, 0.2, 0.4, 0.6], name="unit-test-song", difficulty="Hard", last_note_time=1.8)
    ref_ft = np.linspace(0.0, 1.6, 161, dtype=np.float32)
    ref_ff = np.linspace(0.0, 1.6, 161, dtype=np.float32)
    ref_base = synthetic_curves({
        "Fever Time": ref_ft,
        "Fever Fill Rate": ref_ff,
        "Perfect Points": np.arange(161, dtype=np.float32),
        "Combo Multiplier": np.arange(161, dtype=np.float32),
    })
    ref_variant = synthetic_curves({
        "Fever Time": ref_ft.copy(),
        "Fever Fill Rate": ref_ff.copy(),
        "Perfect Points": np.arange(161, dtype=np.float32) * 7.0,
        "Combo Multiplier": np.arange(161, dtype=np.float32) * 3.0,
    })

    info_base = timeline_api.timeline_frontier_payload_cache_info(song, ref_base)
    info_variant = timeline_api.timeline_frontier_payload_cache_info(song, ref_variant)

    assert info_base.cache_key == info_variant.cache_key
    assert info_base.disk_path == info_variant.disk_path
