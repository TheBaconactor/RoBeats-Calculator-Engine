from __future__ import annotations

import concurrent.futures
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest


def _calc_song() -> dict:
    return {
        "metadata": {
            "Song Name": "FG Cache Unit",
            "Difficulty": "Easy",
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Last Note Time": 0.4,
            "Long Notes": 0,
        },
        "song_data": {
            "timestamps": np.asarray([0.0, 0.2, 0.4], dtype=np.float32),
            "note_types": np.asarray([1, 1, 1], dtype=np.int16),
        },
    }


def _calc_song_named(name: str) -> dict:
    calc_song = _calc_song()
    calc_song["metadata"] = dict(calc_song["metadata"])
    calc_song["metadata"]["Song Name"] = str(name)
    return calc_song


def _ref_arrays() -> dict[str, np.ndarray]:
    return {
        "Fever Time": np.ones((161,), dtype=np.float32),
        "Fever Fill Rate": np.ones((161,), dtype=np.float32),
    }


def _varying_ref_arrays() -> dict[str, np.ndarray]:
    return {
        "Fever Time": np.linspace(1.0, 2.0, 161, dtype=np.float32),
        "Fever Fill Rate": np.linspace(1.0, 2.0, 161, dtype=np.float32),
    }


def _write_song(path: Path, *, extra_tail: str = "") -> None:
    lines = [
        "Song Name\tFG Cache Unit",
        "Difficulty\tEasy",
        "Primary Color\tRush",
        "Secondary Color\tFlow",
        "Last Note Time\t0.4",
        "Long Notes\t0",
        "Song Data",
        "0.000 0 0 1",
        "0.200 0 0 1",
        "0.400 0 0 1",
    ]
    if extra_tail:
        lines.append(str(extra_tail))
    path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def test_fg_response_frontier_payload_roundtrips_disk_cache(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache import (
        build_or_load_response_frontier_payload,
        reset_fg_response_frontier_payload_cache,
    )

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    reset_fg_response_frontier_payload_cache()

    first = build_or_load_response_frontier_payload(_calc_song(), _ref_arrays(), stat_keys=((0, 0),))
    assert first.cache_source == "built"
    assert first.disk_path.exists()
    assert len(first.payload.frontiers) == 1
    assert first.payload.frontier_for_stats(ft_stat=0, ff_stat=0).first_frontier

    reset_fg_response_frontier_payload_cache()
    second = build_or_load_response_frontier_payload(_calc_song(), _ref_arrays(), stat_keys=((0, 0),))
    assert second.cache_source == "disk"
    assert len(second.payload.frontiers) == 1
    assert second.payload.frontier_for_stats(ft_stat=0, ff_stat=0).first_frontier == (
        first.payload.frontier_for_stats(ft_stat=0, ff_stat=0).first_frontier
    )


def test_fg_response_frontier_sparse_bundle_is_single_disk_artifact(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    response_cache.reset_fg_response_frontier_payload_cache()
    keys = ((0, 0), (3, 0), (0, 3))

    first = response_cache.build_or_load_response_frontier_payload(_calc_song(), _ref_arrays(), stat_keys=keys)
    assert first.cache_source == "built"
    assert first.disk_path.exists()
    assert len(list(tmp_path.glob("*.npz"))) == 1
    with np.load(first.disk_path, allow_pickle=False) as data:
        assert data["first_surface_pool"].dtype == np.dtype("uint32")
        assert data["state_surface_pool"].dtype == np.dtype("uint32")

    def _raise_build(*_args, **_kwargs):
        raise AssertionError("warm sparse bundle should load without rebuilding frontiers")

    response_cache.reset_fg_response_frontier_payload_cache()
    monkeypatch.setattr(response_cache, "build_force_greats_response_first_frontiers_gpu_batch", _raise_build)
    second = response_cache.build_or_load_response_frontier_payload(_calc_song(), _ref_arrays(), stat_keys=keys)
    assert second.cache_source == "disk"
    assert set(second.payload.frontier_by_key) == set(keys)


def test_fg_response_frontier_scoring_bundle_does_not_unpack_payload_on_disk_hit(
    tmp_path: Path, monkeypatch
) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    response_cache.reset_fg_response_frontier_payload_cache()
    keys = ((0, 0), (3, 0), (0, 3))

    first = response_cache.build_or_load_response_frontier_payload(_calc_song(), _varying_ref_arrays(), stat_keys=keys)
    assert first.cache_source == "built"
    response_cache.reset_fg_response_frontier_payload_cache()
    monkeypatch.setattr(
        response_cache,
        "_load_payload",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("full payload unpack should not run")),
    )

    bundle = response_cache.load_response_frontier_scoring_bundle(
        _calc_song(),
        _varying_ref_arrays(),
        stat_keys=keys,
    )

    assert set(bundle.frontier_idx_by_key) == set(keys)
    assert int(bundle.surface_words.shape[0]) > 0


def test_fg_response_frontier_scoring_bundle_reuses_persisted_head_coeffs(
    tmp_path: Path, monkeypatch
) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache
    from gear_optimizer.solver.taichi_gem.force_greats import response_inner_host

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    response_cache.reset_fg_response_frontier_payload_cache()
    keys = ((0, 0), (3, 0), (0, 3))

    first = response_cache.build_or_load_response_frontier_payload(_calc_song(), _varying_ref_arrays(), stat_keys=keys)
    assert first.cache_source == "built"
    with np.load(first.disk_path, allow_pickle=False) as data:
        assert "first_surface_head_len" in data.files
        assert "first_surface_head_coeffs" in data.files

    response_cache.reset_fg_response_frontier_payload_cache()

    def _raise_recompute(*_args, **_kwargs):
        raise AssertionError("persisted song-only head coeffs should be reused")

    monkeypatch.setattr(response_inner_host, "_precompute_surface_head_coeffs", _raise_recompute)
    bundle = response_cache.load_response_frontier_scoring_bundle(
        _calc_song(),
        _varying_ref_arrays(),
        stat_keys=keys,
    )

    assert set(bundle.frontier_idx_by_key) == set(keys)
    assert bundle.surface_head_coeffs.shape == (bundle.surface_words.shape[0], 4)


def test_fg_response_frontier_scoring_bundle_disk_hit_skips_redundant_disk_info_probe(
    tmp_path: Path, monkeypatch
) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    response_cache.reset_fg_response_frontier_payload_cache()
    keys = ((0, 0), (3, 0), (0, 3))

    first = response_cache.build_or_load_response_frontier_payload(_calc_song(), _varying_ref_arrays(), stat_keys=keys)
    assert first.cache_source == "built"
    response_cache.reset_fg_response_frontier_payload_cache()
    monkeypatch.setattr(
        response_cache,
        "_payload_disk_info_if_complete",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("disk info probe should be skipped")),
    )

    bundle = response_cache.load_response_frontier_scoring_bundle(
        _calc_song(),
        _varying_ref_arrays(),
        stat_keys=keys,
    )

    assert set(bundle.frontier_idx_by_key) == set(keys)
    assert int(bundle.surface_words.shape[0]) > 0


def test_fg_response_frontier_scoring_bundle_builds_missing_canonical_cache(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    response_cache.reset_fg_response_frontier_payload_cache()

    bundle = response_cache.load_response_frontier_scoring_bundle(
        _calc_song(),
        _varying_ref_arrays(),
        stat_keys=((0, 0),),
    )

    assert set(bundle.frontier_idx_by_key) == {(0, 0)}
    assert int(bundle.surface_words.shape[0]) > 0
    assert len(list(tmp_path.glob("*.npz"))) == 1


def test_fg_response_frontier_payload_load_is_not_a_production_api() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache

    assert not hasattr(response_cache, "load_response_frontier_payload")


def test_response_frontier_job_prep_has_no_scoring_cache_prebuild_route() -> None:
    from gear_optimizer.helpers.song_helpers.force_greats import response_frontier_adapter

    assert not hasattr(response_frontier_adapter, "prebuild_response_frontier_job_caches")
    assert not hasattr(response_frontier_adapter, "prebuild_force_greats_response_frontier_candidate_cache")


def test_fg_response_frontier_selected_result_loads_exact_first_frontier_from_bundle(
    tmp_path: Path, monkeypatch
) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    response_cache.reset_fg_response_frontier_payload_cache()
    keys = ((0, 0), (1, 0))
    response_cache.build_or_load_response_frontier_payload(_calc_song(), _varying_ref_arrays(), stat_keys=keys)
    response_cache.reset_fg_response_frontier_payload_cache()
    monkeypatch.setattr(
        response_cache,
        "_load_payload",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("full payload unpack should not run")),
    )

    scoring_bundle = response_cache.load_response_frontier_scoring_bundle(
        _calc_song(),
        _varying_ref_arrays(),
        stat_keys=keys,
    )
    result = response_cache.frontier_result_from_scoring_bundle_for_stats(
        _calc_song(),
        _varying_ref_arrays(),
        scoring_bundle,
        ft_stat=1,
        ff_stat=0,
    )

    assert result.first_frontier
    assert repr(result.state_frontiers) == "{}"


def test_fg_response_frontier_bundle_version_change_invalidates_legacy_disk_bundle(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    response_cache.reset_fg_response_frontier_payload_cache()
    keys = ((0, 0), (1, 0))

    monkeypatch.setattr(response_cache, "_FG_RESPONSE_CACHE_VERSION", "fg-response-frontier-legacy-v1")
    legacy = response_cache.build_or_load_response_frontier_payload(_calc_song(), _varying_ref_arrays(), stat_keys=keys)
    assert legacy.cache_source == "built"

    response_cache.reset_fg_response_frontier_payload_cache()
    build_calls: list[int] = []
    real_build = response_cache.build_force_greats_response_first_frontiers_gpu_batch

    def _record_build(*args, **kwargs):
        build_calls.append(len(tuple(kwargs.get("geometries") or ())))
        return real_build(*args, **kwargs)

    monkeypatch.setattr(response_cache, "build_force_greats_response_first_frontiers_gpu_batch", _record_build)
    monkeypatch.setattr(response_cache, "_FG_RESPONSE_CACHE_VERSION", "fg-response-frontier-sparse-bundle-v2-test")
    current = response_cache.build_or_load_response_frontier_payload(_calc_song(), _varying_ref_arrays(), stat_keys=keys)

    assert current.cache_source == "built"
    assert build_calls == [2]
    assert len(list(tmp_path.glob("*.npz"))) == 2


def test_fg_response_frontier_disk_bundle_reuses_overlapping_stat_keys(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache
    from gear_optimizer.solver.taichi_gem.force_greats.response_types import (
        FgResponseFrontierResult,
        FgResponseSurface,
    )

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    response_cache.reset_fg_response_frontier_payload_cache()
    calls: list[tuple[tuple[float, int, float], ...]] = []

    def _fake_build(*, geometries, **_kwargs):
        rows = tuple((float(row[0]), int(row[1]), float(row[2])) for row in geometries)
        calls.append(rows)
        return tuple(
            FgResponseFrontierResult(
                first_frontier=(FgResponseSurface(idx, 0, 0, 0, 0, 0, 0, 0, 0, 0),),
                state_frontiers={3: (FgResponseSurface(idx, 0, 0, 0, 0, 0, 0, 0, 0, 0),)},
                states_evaluated=1,
                actions=1,
                transitions_evaluated=1,
                generated_surfaces=1,
                retained_surfaces_total=1,
                max_state_frontier=1,
                non_fever_base=0,
                seconds=0.0,
            )
            for idx, _row in enumerate(rows, start=1)
        )

    monkeypatch.setattr(response_cache, "build_force_greats_response_first_frontiers_gpu_batch", _fake_build)
    ref_arrays = _varying_ref_arrays()

    first = response_cache.build_or_load_response_frontier_payload(
        _calc_song(),
        ref_arrays,
        stat_keys=((0, 0), (1, 0)),
    )
    assert first.cache_source == "built"
    assert [len(call) for call in calls] == [2]

    response_cache.reset_fg_response_frontier_payload_cache()
    second = response_cache.build_or_load_response_frontier_payload(
        _calc_song(),
        ref_arrays,
        stat_keys=((1, 0), (2, 0)),
    )

    assert second.cache_source == "built"
    assert set(second.payload.frontier_by_key) == {(1, 0), (2, 0)}
    assert [len(call) for call in calls] == [2, 1]
    assert len(list(tmp_path.glob("*.npz"))) == 1


def test_fg_response_frontier_bundle_builds_are_single_owner(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache
    from gear_optimizer.solver.taichi_gem.force_greats.response_types import (
        FgResponseFrontierResult,
        FgResponseSurface,
    )

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    response_cache.reset_fg_response_frontier_payload_cache()
    active = 0
    max_active = 0
    lock = threading.Lock()

    def _fake_build(*, geometries, **_kwargs):
        nonlocal active, max_active
        rows = tuple(geometries or ())
        with lock:
            active += 1
            max_active = max(int(max_active), int(active))
        try:
            time.sleep(0.05)
            return tuple(
                FgResponseFrontierResult(
                    first_frontier=(FgResponseSurface(idx, 0, 0, 0, 0, 0, 0, 0, 0, 0),),
                    state_frontiers={},
                    states_evaluated=1,
                    actions=1,
                    transitions_evaluated=1,
                    generated_surfaces=1,
                    retained_surfaces_total=1,
                    max_state_frontier=1,
                    non_fever_base=0,
                    seconds=0.0,
                )
                for idx, _row in enumerate(rows, start=1)
            )
        finally:
            with lock:
                active -= 1

    monkeypatch.setattr(response_cache, "build_force_greats_response_first_frontiers_gpu_batch", _fake_build)
    ref_arrays = _varying_ref_arrays()

    def _build(name: str) -> None:
        response_cache.build_or_load_response_frontier_payload(
            _calc_song_named(name),
            ref_arrays,
            stat_keys=((0, 0), (1, 0), (2, 0)),
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(_build, "FG Cache Unit A"), executor.submit(_build, "FG Cache Unit B")]
        for future in futures:
            future.result()

    assert max_active == 1


def test_fg_response_frontier_bundle_build_does_not_populate_geometry_lru(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache
    from gear_optimizer.solver.taichi_gem.force_greats.response_types import (
        FgResponseFrontierResult,
        FgResponseSurface,
    )

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    response_cache.reset_fg_response_frontier_payload_cache()

    def _fake_build(*, geometries, **_kwargs):
        return tuple(
            FgResponseFrontierResult(
                first_frontier=(FgResponseSurface(idx, 0, 0, 0, 0, 0, 0, 0, 0, 0),),
                state_frontiers={},
                states_evaluated=1,
                actions=1,
                transitions_evaluated=1,
                generated_surfaces=1,
                retained_surfaces_total=1,
                max_state_frontier=1,
                non_fever_base=0,
                seconds=0.0,
            )
            for idx, _row in enumerate(tuple(geometries), start=1)
        )

    def _forbid_geometry_lru(*_args, **_kwargs):
        raise AssertionError("response bundle build must not populate the obsolete per-stat geometry LRU")

    monkeypatch.setattr(response_cache, "build_force_greats_response_first_frontiers_gpu_batch", _fake_build)
    monkeypatch.setattr(response_cache, "_memory_put", _forbid_geometry_lru)

    result = response_cache.build_or_load_response_frontier_payload(
        _calc_song(),
        _varying_ref_arrays(),
        stat_keys=((0, 0), (1, 0), (2, 0)),
    )

    assert result.cache_source == "built"
    assert set(result.payload.frontier_by_key) == {(0, 0), (1, 0), (2, 0)}


def test_fg_response_frontier_payload_loads_slim_scoring_frontiers(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    response_cache.reset_fg_response_frontier_payload_cache()
    ref_arrays = _varying_ref_arrays()
    keys = ((0, 0), (1, 0))

    full = response_cache.build_or_load_response_frontier_payload(_calc_song(), ref_arrays, stat_keys=keys)
    assert all(frontier.first_frontier for frontier in full.payload.frontiers)
    assert all(not frontier.state_frontiers for frontier in full.payload.frontiers)

    response_cache.reset_fg_response_frontier_payload_cache()
    warm = response_cache.build_or_load_response_frontier_payload(_calc_song(), ref_arrays, stat_keys=keys)
    assert warm.cache_source == "disk"
    assert all(frontier.first_frontier for frontier in warm.payload.frontiers)
    assert all(not frontier.state_frontiers for frontier in warm.payload.frontiers)

    restored = response_cache.build_or_load_response_frontier_payload(_calc_song(), ref_arrays, stat_keys=((1, 0),))
    restored_frontier = restored.payload.frontier_for_stats(ft_stat=1, ff_stat=0)
    assert restored_frontier.first_frontier
    assert not restored_frontier.state_frontiers
    assert restored_frontier.first_frontier == full.payload.frontier_for_stats(ft_stat=1, ff_stat=0).first_frontier


def test_fg_response_frontier_cache_rejects_incomplete_frontiers(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache
    from gear_optimizer.solver.taichi_gem.force_greats.response_types import (
        FgResponseFrontierResult,
        FgResponseSurface,
    )

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    response_cache.reset_fg_response_frontier_payload_cache()
    calls: list[int] = []

    def _fake_build(*, geometries, **_kwargs):
        rows = tuple(geometries)
        calls.append(len(rows))
        out = []
        for idx, _geometry in enumerate(rows, start=1):
            surface = FgResponseSurface(idx, 0, 0, 0, 0, 0, 0, 0, 0, 0)
            out.append(
                FgResponseFrontierResult(
                    first_frontier=(),
                    state_frontiers={},
                    states_evaluated=1,
                    actions=1,
                    transitions_evaluated=1,
                    generated_surfaces=1,
                    retained_surfaces_total=1,
                    max_state_frontier=1,
                    non_fever_base=0,
                    seconds=0.0,
                )
            )
        return tuple(out)

    monkeypatch.setattr(response_cache, "build_force_greats_response_first_frontiers_gpu_batch", _fake_build)
    keys = ((0, 0), (1, 0))
    ref_arrays = _varying_ref_arrays()

    with pytest.raises(ValueError, match="requires first-frontier surfaces"):
        response_cache.build_or_load_response_frontier_payload(_calc_song(), ref_arrays, stat_keys=keys)
    assert calls == [2]


def test_fg_response_frontier_payload_memory_cache_precedes_disk(tmp_path: Path, monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    response_cache.reset_fg_response_frontier_payload_cache()
    keys = ((0, 0), (3, 0), (0, 3))

    first = response_cache.build_or_load_response_frontier_payload(_calc_song(), _ref_arrays(), stat_keys=keys)
    assert first.cache_source == "built"

    def _raise_disk_load(_cache_key):
        raise AssertionError("resident response-frontier payload should not hit disk")

    monkeypatch.setattr(response_cache, "_load_payload", _raise_disk_load)
    info = response_cache.fg_response_frontier_payload_cache_info(_calc_song(), _ref_arrays(), stat_keys=keys)
    assert info.cache_source == "memory"

    second = response_cache.build_or_load_response_frontier_payload(_calc_song(), _ref_arrays(), stat_keys=keys)
    assert second.cache_source == "memory"
    assert second.payload is first.payload


def test_fg_response_frontier_cache_info_ignores_obsolete_geometry_lru(monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache
    from gear_optimizer.solver.taichi_gem.force_greats.response_types import (
        FgResponseFrontierResult,
        FgResponseSurface,
    )

    response_cache.reset_fg_response_frontier_payload_cache()
    surface = FgResponseSurface(1, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    complete_frontier = FgResponseFrontierResult(
        first_frontier=(surface,),
        state_frontiers={0: (surface,)},
        states_evaluated=1,
        actions=1,
        transitions_evaluated=1,
        generated_surfaces=1,
        retained_surfaces_total=1,
        max_state_frontier=1,
        non_fever_base=0,
        seconds=0.0,
    )
    keys = ((0, 0), (1, 0))
    first_key = response_cache.fg_response_frontier_geometry_cache_key(
        _calc_song(),
        _ref_arrays(),
        ft_stat=0,
        ff_stat=0,
    )
    response_cache._memory_put(first_key, complete_frontier)

    info = response_cache.fg_response_frontier_payload_cache_info(
        _calc_song(),
        _ref_arrays(),
        stat_keys=keys,
    )

    assert info.cache_source == "missing"
    assert info.frontier_count == 0


def test_fg_response_frontier_prebuild_has_no_public_flags() -> None:
    forbidden = (
        "FGResponseFrontierCachePrebuildScope",
        "FGResponseFrontierCachePrebuildWorkers",
        "FGResponseFrontierCachePrebuildMaxSongs",
        "FGResponseFrontierCachePrebuildExecutor",
        "FGResponseFrontierCachePrebuildStatKeys",
        "FG_RESPONSE_FRONTIER_CACHE_PREBUILD",
        "FG_RESPONSE_FRONTIER_DISK_CACHE",
        "include_state_frontiers",
    )
    paths = list(Path("gear_optimizer").rglob("*.py")) + [Path("config.ini"), Path("config.profile.ini")]
    offenders: list[tuple[str, str]] = []
    for path in paths:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for token in forbidden:
            if token in text:
                offenders.append((str(path), token))
    assert offenders == []


def test_fg_response_frontier_cache_build_has_single_production_owner() -> None:
    allowed = {
        Path("gear_optimizer/solver/taichi_gem/force_greats/response_cache.py"),
    }
    offenders: list[str] = []
    for path in Path("gear_optimizer").rglob("*.py"):
        if path in allowed:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "build_or_load_response_frontier_payload" in text:
            offenders.append(str(path))

    assert offenders == []


def test_packed_scoring_does_not_require_state_frontiers_without_forced_counts(monkeypatch) -> None:
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.solver.taichi_gem.force_greats import response_frontier
    from gear_optimizer.solver.taichi_gem.force_greats.response_types import (
        FgResponseFrontierResult,
        FgResponseSurface,
    )

    surface = FgResponseSurface(0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    frontier_idx_by_stat = np.full((TOTAL_ROWS + 1, TOTAL_ROWS + 1), -1, dtype=np.int32)
    frontier_idx_by_stat[0, 0] = 0
    bundle = SimpleNamespace(
        frontier_idx_by_stat=frontier_idx_by_stat,
        frontier_offsets=np.asarray([0], dtype=np.int32),
        frontier_lengths=np.asarray([1], dtype=np.int32),
        surface_words=np.zeros((1, 8), dtype=np.uint32),
        surface_counts=np.zeros((1, 2), dtype=np.int32),
        surface_head_coeffs=np.zeros((1, 4), dtype=np.int32),
        raw_fill_by_ff=np.zeros((TOTAL_ROWS + 1,), dtype=np.float64),
        real_time_by_ft=np.ones((TOTAL_ROWS + 1,), dtype=np.float64),
    )
    batch = response_frontier.FgResponseFrontierPackedScoringBatch(
        started=0.0,
        stats_inputs=({"Perfect Points": 0, "Combo Multiplier": 0, "Fever Multiplier": 0, "Rush": 0, "Flow": 0},),
        calc_song={"song_data": {"timestamps": np.asarray([0.0], dtype=np.float32)}},
        song_inputs=SimpleNamespace(
            timestamps=np.asarray([0.0], dtype=np.float32),
            great_candidates=np.asarray([0.0], dtype=np.float32),
            use_forced_great_timing=True,
        ),
        ref_arrays={},
        selected_color="Rush",
        primary_color="Rush",
        secondary_color="Flow",
        kept_stat_keys=((0, 0),),
        scoring_bundle=bundle,
        scoring_bundle_ms=0.0,
        group_meta=np.asarray([[0, 0, 0, 0, 0, 0, 1, 0]], dtype=np.int32),
        group_ft=np.asarray([0], dtype=np.int32),
        group_ff=np.asarray([0], dtype=np.int32),
        group_ft_stat=np.asarray([0], dtype=np.int32),
        group_ff_stat=np.asarray([0], dtype=np.int32),
        candidate_slices=((0, 1),),
        scoring_surface_words=np.zeros((1, 8), dtype=np.uint32),
        scoring_surface_counts=np.zeros((1, 2), dtype=np.int32),
        scoring_surface_head_coeffs=np.zeros((1, 4), dtype=np.int32),
        scoring_group_offsets=np.asarray([0], dtype=np.int32),
        scoring_group_lengths=np.asarray([1], dtype=np.int32),
        scoring_logical_owners=np.asarray([0], dtype=np.int32),
        scoring_logical_surfaces=np.asarray([0], dtype=np.int32),
        scoring_logical_work_cumsum=np.asarray([0, 1], dtype=np.int64),
        scoring_unique_frontiers=1,
        scoring_surface_compact_ms=0.0,
        scoring_surface_head_coeff_ms=0.0,
    )

    def _score_must_not_load_bundle(*_args, **_kwargs):
        raise AssertionError("prepared response-frontier scoring must not build or load cache on the GPU owner")

    monkeypatch.setattr(response_frontier, "load_response_frontier_scoring_bundle", _score_must_not_load_bundle)

    def _score_must_receive_prepared_surfaces(**kwargs):
        assert kwargs["group_offsets"].tolist() == [0]
        assert kwargs["group_lengths"].tolist() == [1]
        assert kwargs["surface_words"].shape == (1, 8)
        assert kwargs["surface_counts"].shape == (1, 2)
        assert kwargs["surface_head_coeffs"].shape == (1, 4)
        return np.asarray([[123, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]], dtype=np.int32), 1

    monkeypatch.setattr(
        response_frontier,
        "_score_response_group_meta_gpu",
        _score_must_receive_prepared_surfaces,
    )
    monkeypatch.setattr(
        response_frontier,
        "frontier_result_from_scoring_bundle_for_stats",
        lambda *_a, **_k: FgResponseFrontierResult((surface,), {}, 1, 1, 0, 1, 1, 1, 0, 0.0),
    )

    result = response_frontier.score_prepared_force_greats_response_frontier_batch_gpu(
        batch,
        include_forced_counts=False,
    )

    assert result[0].best_score == 123
    assert result[0].forced_counts == ()


def test_packed_scoring_batch_loads_prebuilt_bundle_during_prepare(monkeypatch) -> None:
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.solver.taichi_gem.force_greats import response_frontier

    song_inputs = SimpleNamespace(
        total_notes=1,
        long_notes=0,
        last_note_time=1.0,
        use_forced_great_timing=True,
        primary_color="Rush",
        secondary_color="Flow",
        timestamps=np.asarray([0.0], dtype=np.float32),
        great_candidates=np.asarray([0.0], dtype=np.float32),
    )
    seen: dict[str, object] = {}

    monkeypatch.setattr(response_frontier, "extract_fg_song_inputs", lambda _song: song_inputs)

    def _fake_build_bundle(calc_song, ref_arrays, *, stat_keys):
        seen["calc_song"] = calc_song
        seen["ref_arrays"] = ref_arrays
        seen["stat_keys"] = tuple(stat_keys)
        frontier_idx_by_stat = np.full((TOTAL_ROWS + 1, TOTAL_ROWS + 1), -1, dtype=np.int32)
        for ft_stat, ff_stat in tuple(stat_keys):
            frontier_idx_by_stat[int(ft_stat), int(ff_stat)] = 0
        surface_words = np.zeros((1, 8), dtype=np.uint32)
        bundle = SimpleNamespace(
            frontier_idx_by_key={key: 0 for key in tuple(stat_keys)},
            frontier_idx_by_stat=frontier_idx_by_stat,
            frontier_offsets=np.asarray([0], dtype=np.int32),
            frontier_lengths=np.asarray([1], dtype=np.int32),
            surface_words=surface_words,
            surface_counts=np.zeros((1, 2), dtype=np.int32),
            surface_head_coeffs=np.zeros((1, 4), dtype=np.int32),
            total_notes=1,
        )
        seen["bundle"] = bundle
        return bundle

    monkeypatch.setattr(response_frontier, "load_response_frontier_scoring_bundle", _fake_build_bundle)

    batch = response_frontier.prepare_force_greats_response_frontier_scoring_batch(
        base_stats_list=({"Perfect Points": 0, "Combo Multiplier": 0, "Fever Multiplier": 0},),
        calc_song={"song_data": {}},
        ref_arrays={"ref": object()},
        selected_color="Rush",
        total_budget=1,
    )

    assert batch.scoring_bundle is seen["bundle"]
    assert seen["calc_song"] == {"song_data": {}}
    assert seen["ref_arrays"] == {"ref": batch.ref_arrays["ref"]}
    assert len(seen["stat_keys"]) == (TOTAL_ROWS + 1) * (TOTAL_ROWS + 1)
    assert set(batch.kept_stat_keys).issubset(set(seen["stat_keys"]))
    assert batch.scoring_bundle_ms >= 0.0
    assert batch.scoring_surface_words.shape == (1, 8)
    assert batch.scoring_surface_head_coeffs is seen["bundle"].surface_head_coeffs
    assert batch.scoring_surface_counts.shape == (1, 2)
    assert batch.scoring_surface_head_coeffs.shape == (1, 4)
    assert batch.scoring_group_offsets.shape == batch.group_ft.shape
    assert batch.scoring_group_lengths.shape == batch.group_ft.shape


def test_packed_scoring_batch_uses_supplied_prewarmed_bundle(monkeypatch) -> None:
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.solver.taichi_gem.force_greats import response_frontier

    song_inputs = SimpleNamespace(
        total_notes=1,
        long_notes=0,
        last_note_time=1.0,
        use_forced_great_timing=True,
        primary_color="Rush",
        secondary_color="Flow",
        timestamps=np.asarray([0.0], dtype=np.float32),
        great_candidates=np.asarray([0.0], dtype=np.float32),
    )
    frontier_idx_by_stat = np.full((TOTAL_ROWS + 1, TOTAL_ROWS + 1), -1, dtype=np.int32)
    frontier_idx_by_stat[0, 0] = 0
    prewarmed_bundle = SimpleNamespace(
        frontier_idx_by_key={(0, 0): 0},
        frontier_idx_by_stat=frontier_idx_by_stat,
        frontier_offsets=np.asarray([0], dtype=np.int32),
        frontier_lengths=np.asarray([1], dtype=np.int32),
        surface_words=np.zeros((1, 8), dtype=np.uint32),
        surface_counts=np.zeros((1, 2), dtype=np.int32),
        surface_head_coeffs=np.zeros((1, 4), dtype=np.int32),
        total_notes=1,
    )

    monkeypatch.setattr(response_frontier, "extract_fg_song_inputs", lambda _song: song_inputs)
    monkeypatch.setattr(
        response_frontier,
        "load_response_frontier_scoring_bundle",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("must use prewarmed bundle")),
    )

    batch = response_frontier.prepare_force_greats_response_frontier_scoring_batch(
        base_stats_list=({"Perfect Points": 0, "Combo Multiplier": 0, "Fever Multiplier": 0},),
        calc_song={"song_data": {}},
        ref_arrays={"ref": object()},
        selected_color="Rush",
        total_budget=0,
        scoring_bundle=prewarmed_bundle,
    )

    assert batch.scoring_bundle is prewarmed_bundle
    assert batch.kept_stat_keys == ((0, 0),)
    assert batch.scoring_surface_head_coeffs is prewarmed_bundle.surface_head_coeffs


def test_packed_scoring_batch_reuses_canonical_bundle_surface_pool_without_repacking(monkeypatch) -> None:
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.solver.taichi_gem.force_greats import response_frontier

    song_inputs = SimpleNamespace(
        total_notes=3,
        long_notes=0,
        last_note_time=1.0,
        use_forced_great_timing=True,
        primary_color="Rush",
        secondary_color="Flow",
        timestamps=np.asarray([0.0, 0.1, 0.2], dtype=np.float32),
        great_candidates=np.asarray([0.0, 0.1, 0.2], dtype=np.float32),
    )
    frontier_idx_by_stat = np.full((TOTAL_ROWS + 1, TOTAL_ROWS + 1), -1, dtype=np.int32)
    frontier_idx_by_stat[0, 0] = 1
    surface_words = np.arange(24, dtype=np.uint32).reshape(3, 8)
    surface_counts = np.arange(6, dtype=np.int32).reshape(3, 2)
    surface_head_coeffs = np.full((3, 4), 3, dtype=np.int32)
    prewarmed_bundle = SimpleNamespace(
        frontier_idx_by_key={(0, 0): 1},
        frontier_idx_by_stat=frontier_idx_by_stat,
        frontier_offsets=np.asarray([0, 2], dtype=np.int32),
        frontier_lengths=np.asarray([2, 1], dtype=np.int32),
        surface_words=surface_words,
        surface_counts=surface_counts,
        surface_head_coeffs=surface_head_coeffs,
        total_notes=3,
    )

    monkeypatch.setattr(response_frontier, "extract_fg_song_inputs", lambda _song: song_inputs)

    batch = response_frontier.prepare_force_greats_response_frontier_scoring_batch(
        base_stats_list=({"Perfect Points": 0, "Combo Multiplier": 0, "Fever Multiplier": 0},),
        calc_song={"song_data": {}},
        ref_arrays={"ref": object()},
        selected_color="Rush",
        total_budget=0,
        scoring_bundle=prewarmed_bundle,
    )

    assert batch.scoring_surface_words is surface_words
    assert batch.scoring_surface_counts is surface_counts
    assert batch.scoring_group_offsets.tolist() == [2]
    assert batch.scoring_group_lengths.tolist() == [1]
    assert batch.scoring_surface_head_coeffs is surface_head_coeffs
