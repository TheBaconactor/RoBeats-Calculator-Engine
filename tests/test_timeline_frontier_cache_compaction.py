from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from gear_optimizer.solver.timeline_exact_frontier import build_timeline_frontier_grid_payload
from gear_optimizer.solver.taichi_gem.api import timeline as timeline_api


def _build_small_payload():
    group_starts = np.array([0, 2, 4], dtype=np.int32)
    group_ends = np.array([2, 4, 6], dtype=np.int32)
    group_base_t_ms = np.array([0, 100, 220], dtype=np.int32)
    group_low_ms = np.array([0, -10, -5], dtype=np.int32)
    group_high_ms = np.array([20, 30, 25], dtype=np.int32)
    note_group_idx = np.array([0, 0, 1, 1, 2, 2], dtype=np.int32)
    ref_ft = np.linspace(0.0, 1.6, 161, dtype=np.float32)
    ref_ff = np.linspace(0.0, 1.6, 161, dtype=np.float32)
    payload = build_timeline_frontier_grid_payload(
        song_slot=7,
        total_notes=6,
        long_notes=0,
        last_note_time=1.8,
        song_key="unit-test-song",
        group_starts=group_starts,
        group_ends=group_ends,
        group_base_t_ms=group_base_t_ms,
        group_low_ms=group_low_ms,
        group_high_ms=group_high_ms,
        note_group_idx=note_group_idx,
        ref_ft=ref_ft,
        ref_ff=ref_ff,
    )
    return payload


def _ref_arrays() -> dict[str, np.ndarray]:
    return {
        "Fever Time": np.linspace(0.0, 1.6, 161, dtype=np.float32),
        "Fever Fill Rate": np.linspace(0.0, 1.6, 161, dtype=np.float32),
    }


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


def test_frontier_disk_cache_persists_group_payload_and_reuses_it(tmp_path: Path, monkeypatch) -> None:
    payload = _build_small_payload()
    key = ("unit", "group-payload", 3)
    monkeypatch.setenv("TIMELINE_FRONTIER_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("TIMELINE_FRONTIER_DISK_CACHE", "1")

    group_payload = {
        "n": 6,
        "group_count": 3,
        "group_starts": np.array([0, 2, 4], dtype=np.int32),
        "group_ends": np.array([2, 4, 6], dtype=np.int32),
        "group_base_t_ms": np.array([0, 100, 220], dtype=np.int32),
        "group_low_ms": np.array([0, -10, -5], dtype=np.int32),
        "group_high_ms": np.array([20, 30, 25], dtype=np.int32),
        "note_group_idx": np.array([0, 0, 1, 1, 2, 2], dtype=np.int32),
    }
    timeline_api._save_frontier_payload_to_disk(key, payload, group_payload=group_payload)

    loaded_group = timeline_api._load_group_payload_from_frontier_disk(key, expected_n=6)
    assert loaded_group is not None
    assert int(loaded_group["n"]) == 6
    assert int(loaded_group["group_count"]) == 3
    assert np.array_equal(loaded_group["group_ends"], group_payload["group_ends"])
    assert np.array_equal(loaded_group["note_group_idx"], group_payload["note_group_idx"])

    timeline_api.reset_timeline_state()
    calc_song = {
        "metadata": {
            "Song Name": "Unit Disk Group",
            "Difficulty": "Easy",
            "Long Notes": 0,
            "Last Note Time": 0.6,
        },
        "song_data": {
            "timestamps": np.array([0.0, 0.2, 0.4, 0.6, 0.8, 1.0], dtype=np.float32),
            "note_types": np.array([1, 1, 1, 1, 1, 1], dtype=np.int16),
        },
    }
    ref_arrays = {
        "Fever Time": np.linspace(0.0, 1.6, 161, dtype=np.float32),
        "Fever Fill Rate": np.linspace(0.0, 1.6, 161, dtype=np.float32),
    }
    song_key = timeline_api._song_timing_cache_key(calc_song)
    cache_key = timeline_api._frontier_payload_cache_key(song_key, ref_arrays["Fever Time"], ref_arrays["Fever Fill Rate"])
    saved_path = timeline_api._frontier_disk_cache_path(cache_key)
    timeline_api._frontier_disk_cache_path(key).replace(saved_path)

    def _raise_group_build(*_args, **_kwargs):
        raise AssertionError("group payload should come from disk cache")

    monkeypatch.setattr(timeline_api, "_get_or_build_frontier_group_payload", _raise_group_build)
    context = timeline_api._timeline_payload_context(calc_song, ref_arrays, ref_sig=None)
    loaded = context["group_payload"]
    assert int(loaded["n"]) == 6
    assert int(loaded["group_count"]) == 3
    assert np.array_equal(loaded["group_ends"], group_payload["group_ends"])


def test_build_or_load_timeline_frontier_payload_disk_hit_skips_redundant_group_disk_probe(
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
    ref_arrays = _ref_arrays()

    first = timeline_api.build_or_load_timeline_frontier_payload(calc_song, ref_arrays)
    assert first.cache_source == "built"

    timeline_api.reset_timeline_state()
    monkeypatch.setattr(
        timeline_api,
        "_load_group_payload_from_frontier_disk",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("group payload disk probe should be skipped")),
    )
    second = timeline_api.build_or_load_timeline_frontier_payload(calc_song, ref_arrays)
    assert second.cache_source == "disk"
    assert int(second.total_notes) == 4


def test_load_timeline_frontier_payload_requires_startup_built_cache(tmp_path: Path, monkeypatch) -> None:
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

    with pytest.raises(ValueError, match="Startup cache prebuild must build"):
        timeline_api.load_timeline_frontier_payload(calc_song, _ref_arrays())
    assert list(tmp_path.glob("*.npz")) == []

    built = timeline_api.build_or_load_timeline_frontier_payload(calc_song, _ref_arrays())
    assert built.cache_source == "built"
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
