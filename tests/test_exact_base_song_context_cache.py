from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import fields
import json
from pathlib import Path
import threading
from types import SimpleNamespace

import numpy as np
import pytest

from gear_optimizer.solver import exact_base_song_context as song_context
from gear_optimizer.solver import exact_base_song_context_cache as context_cache


_GRID = 161


def _timeline_payload() -> SimpleNamespace:
    return SimpleNamespace(
        grid_frontier_count=np.ones((1, _GRID, _GRID), dtype=np.int32),
        grid_frontier_offset=np.zeros((1, _GRID, _GRID), dtype=np.int32),
        grid_frontier_body_fever_pool=np.zeros((1, 1), dtype=np.int32),
        grid_frontier_body_normal_pool=np.ones((1, 1), dtype=np.int32),
        grid_frontier_masks_bits_pool=np.zeros((1, 1, 4), dtype=np.uint32),
        grid_frontier_head_coeffs_pool=np.zeros((1, 1, 4), dtype=np.int32),
        grid_head_len=np.zeros((1, _GRID, _GRID), dtype=np.int32),
        frontier_pool_used=1,
    )


def _context_inputs(
    *,
    total_notes: int = 1,
    flags: dict[str, int] | None = None,
    ref_arrays: dict[str, np.ndarray] | None = None,
    song_path: str = "Data/Songs/example.rbxl",
) -> song_context.ExactBaseSongContextInputs:
    references = np.ones(_GRID, dtype=np.float32)
    return song_context.ExactBaseSongContextInputs(
        calc_song={
            "metadata": {
                "Total Notes": int(total_notes),
                "Song Path": song_path,
            }
        },
        ref_arrays=ref_arrays
        or {
            "Perfect Points": references,
            "Combo Multiplier": references,
            "Fever Multiplier": references,
        },
        color_flags=flags or {},
    )


def _patch_zero_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(song_context, "TOTAL_GEM_BUDGET", 0)
    monkeypatch.setattr(context_cache, "TOTAL_GEM_BUDGET", 0)


def _context_arrays(context: song_context.ExactBaseSongContext) -> list[np.ndarray]:
    response = context.program_map.response_table
    arrays = [
        response.cells,
        response.cell_to_row,
        response.offsets_by_row,
        response.lengths_by_row,
        response.flat_ft,
        response.flat_ff,
    ]
    for container in (
        context.program_map,
        context.physical_programs,
        context.class_programs,
        context.multiplier_bounds,
    ):
        arrays.extend(
            value
            for field in fields(container)
            if isinstance(value := getattr(container, field.name), np.ndarray)
        )
    return arrays


def _npz_payload(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as data:
        return {name: np.array(data[name], copy=True) for name in data.files}


def test_exact_base_song_context_cache_roundtrips_and_indexes_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_zero_budget(monkeypatch)
    ctx = _context_inputs()
    timeline = _timeline_payload()

    first = context_cache.load_or_build_exact_base_song_context(
        ctx,
        timeline,
        cache_dir=tmp_path,
    )
    second = context_cache.load_or_build_exact_base_song_context(
        ctx,
        timeline,
        cache_dir=tmp_path,
    )

    assert first.cache_source == "built"
    assert second.cache_source == "disk"
    assert first.cache_key == second.cache_key
    assert first.disk_path == second.disk_path
    assert first.context.program_map.response_table.cache_key == (
        second.context.program_map.response_table.cache_key
    )
    first_arrays = _context_arrays(first.context)
    second_arrays = _context_arrays(second.context)
    assert len(first_arrays) == len(second_arrays)
    assert all(
        left.dtype == right.dtype and np.array_equal(left, right)
        for left, right in zip(first_arrays, second_arrays, strict=True)
    )
    assert all(not array.flags.writeable for array in second_arrays)

    explicit = context_cache.build_exact_base_song_context_for_cache(ctx, timeline)
    stored_path = context_cache.store_exact_base_song_context(
        ctx,
        timeline,
        explicit,
        cache_dir=tmp_path,
    )
    loaded = context_cache.load_exact_base_song_context(
        ctx,
        timeline,
        cache_dir=tmp_path,
    )
    assert stored_path == first.disk_path
    assert loaded is not None
    assert all(not array.flags.writeable for array in _context_arrays(loaded))

    manifest_path = context_cache.exact_base_song_context_manifest_path(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entry = manifest["entries"][first.disk_path.stem]
    assert entry["cache_file"] == first.disk_path.name
    assert Path(entry["cache_file"]).name == entry["cache_file"]
    assert not Path(entry["cache_file"]).is_absolute()
    assert Path(entry["multiplier_cache_file"]).name == entry["multiplier_cache_file"]
    multiplier_path = tmp_path / entry["multiplier_cache_file"]
    assert multiplier_path.is_file()
    assert len(list(tmp_path.glob("exact_base_multiplier_bounds_*.npz"))) == 1
    with np.load(first.disk_path, allow_pickle=False) as song_data:
        assert "multiplier_joint_cm_fm" not in song_data.files
    with np.load(multiplier_path, allow_pickle=False) as multiplier_data:
        assert "multiplier_joint_cm_fm" in multiplier_data.files
    assert context_cache.exact_base_song_context_cache_info(
        ctx,
        timeline,
        cache_dir=tmp_path,
    ).cache_source == "disk"
    assert context_cache.exact_base_song_context_cache_file_is_complete(first.disk_path)
    assert context_cache.load_prebuilt_exact_base_song_context(
        ctx,
        timeline,
        cache_dir=tmp_path,
    ).cache_source == "disk"


def test_exact_base_song_context_runtime_loader_rejects_startup_miss(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gear_optimizer.solver.frontier_cache_errors import MissingFrontierCacheError

    _patch_zero_budget(monkeypatch)
    with pytest.raises(MissingFrontierCacheError, match="Startup cache prebuild"):
        context_cache.load_prebuilt_exact_base_song_context(
            _context_inputs(),
            _timeline_payload(),
            cache_dir=tmp_path,
        )


def test_exact_base_song_context_cache_key_tracks_only_semantic_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_zero_budget(monkeypatch)
    timeline = _timeline_payload()
    base_ctx = _context_inputs(song_path="C:/first/location.rbxl")
    relocated_ctx = _context_inputs(song_path="D:/copied/location.rbxl")
    base_key = context_cache.exact_base_song_context_cache_key(base_ctx, timeline)

    assert (
        context_cache.exact_base_song_context_cache_key(relocated_ctx, timeline)
        == base_key
    )

    flag_ctx = _context_inputs(flags={"is_p_ft": 1})
    assert context_cache.exact_base_song_context_cache_key(flag_ctx, timeline) != base_key

    changed_refs = {
        name: np.array(values, copy=True)
        for name, values in base_ctx.ref_arrays.items()
    }
    changed_refs["Combo Multiplier"][-1] = 2.0
    ref_ctx = _context_inputs(ref_arrays=changed_refs)
    assert context_cache.exact_base_song_context_cache_key(ref_ctx, timeline) != base_key

    note_ctx = _context_inputs(total_notes=2)
    assert context_cache.exact_base_song_context_cache_key(note_ctx, timeline) != base_key

    changed_timeline = _timeline_payload()
    changed_timeline.grid_frontier_masks_bits_pool[0, 0, 0] = np.uint32(1)
    assert (
        context_cache.exact_base_song_context_cache_key(base_ctx, changed_timeline)
        != base_key
    )


def test_exact_base_song_context_cache_rejects_stale_shape_and_corrupt_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_zero_budget(monkeypatch)
    ctx = _context_inputs()
    timeline = _timeline_payload()
    result = context_cache.load_or_build_exact_base_song_context(
        ctx,
        timeline,
        cache_dir=tmp_path,
    )
    original = _npz_payload(result.disk_path)
    manifest = json.loads(
        context_cache.exact_base_song_context_manifest_path(tmp_path).read_text(
            encoding="utf-8"
        )
    )
    multiplier_path = tmp_path / manifest["entries"][result.disk_path.stem][
        "multiplier_cache_file"
    ]
    multiplier_original = _npz_payload(multiplier_path)

    bad_multiplier = dict(multiplier_original)
    bad_multiplier["multiplier_joint_cm_fm"] = bad_multiplier[
        "multiplier_joint_cm_fm"
    ][:, :, :-1]
    np.savez_compressed(multiplier_path, **bad_multiplier)
    context_cache.reset_exact_base_song_context_cache_memory()
    with pytest.raises(
        context_cache.ExactBaseSongContextCacheError,
        match="multiplier-bound cache is corrupt|invalid shape",
    ):
        context_cache.load_exact_base_song_context(
            ctx,
            timeline,
            cache_dir=tmp_path,
        )
    np.savez_compressed(multiplier_path, **multiplier_original)
    context_cache.reset_exact_base_song_context_cache_memory()

    wrong_shape = dict(original)
    wrong_shape["map_program_by_cell"] = wrong_shape["map_program_by_cell"][:-1]
    np.savez_compressed(result.disk_path, **wrong_shape)
    with pytest.raises(
        context_cache.ExactBaseSongContextCacheError,
        match="corrupt|does not cover",
    ):
        context_cache.load_exact_base_song_context(
            ctx,
            timeline,
            cache_dir=tmp_path,
        )

    stale = dict(original)
    stale["cache_version"] = np.frombuffer(b"stale-version", dtype=np.uint8).copy()
    np.savez_compressed(result.disk_path, **stale)
    with pytest.raises(
        context_cache.ExactBaseSongContextCacheError,
        match="logic version is stale",
    ):
        context_cache.load_exact_base_song_context(
            ctx,
            timeline,
            cache_dir=tmp_path,
        )

    result.disk_path.write_bytes(b"not a numpy archive")
    with pytest.raises(context_cache.ExactBaseSongContextCacheError, match="corrupt"):
        context_cache.load_exact_base_song_context(
            ctx,
            timeline,
            cache_dir=tmp_path,
        )


def test_exact_base_song_context_cache_build_lock_is_per_semantic_song(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_zero_budget(monkeypatch)
    timeline = _timeline_payload()
    first_ctx = _context_inputs()
    second_refs = {
        name: np.array(values, copy=True)
        for name, values in first_ctx.ref_arrays.items()
    }
    second_refs["Perfect Points"][-1] = 2.0
    second_ctx = _context_inputs(ref_arrays=second_refs)
    built_context = context_cache.build_exact_base_song_context_for_cache(
        first_ctx,
        timeline,
    )
    build_barrier = threading.Barrier(2)

    def _parallel_build(*_args: object, **_kwargs: object) -> song_context.ExactBaseSongContext:
        build_barrier.wait(timeout=10.0)
        return built_context

    monkeypatch.setattr(
        context_cache.song_context,
        "build_exact_base_song_context",
        _parallel_build,
    )
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(
                context_cache.load_or_build_exact_base_song_context,
                ctx,
                timeline,
                cache_dir=tmp_path,
            )
            for ctx in (first_ctx, second_ctx)
        ]
        results = [future.result(timeout=20.0) for future in futures]

    assert {result.cache_source for result in results} == {"built"}
    assert len({result.disk_path for result in results}) == 2
    assert len(list(tmp_path.glob("exact_base_multiplier_bounds_*.npz"))) == 1
    manifest = json.loads(
        context_cache.exact_base_song_context_manifest_path(tmp_path).read_text(
            encoding="utf-8"
        )
    )
    assert len(manifest["entries"]) == 2
