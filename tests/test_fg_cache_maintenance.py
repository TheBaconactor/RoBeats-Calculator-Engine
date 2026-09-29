from contextlib import contextmanager

import pytest

from gear_optimizer.solver import fg_response_frontier_cache_prebuild as prebuild
from gear_optimizer.solver.frontier_cache_manifest import FrontierCacheManifestPlan


@pytest.mark.parametrize(
    "missing,rotate,build_missing,expected",
    [
        (False, True, True, ["lock", "maintain:True"]),
        (True, False, True, ["lock", "maintain:False", "build", "save", "compress"]),
        (True, False, False, ["lock"]),
    ],
)
def test_cache_build_and_explicit_maintenance_remain_locked(
    monkeypatch, tmp_path, missing, rotate, build_missing, expected
):
    song = tmp_path / "Song.txt"
    song.write_text("test chart")
    paths = (str(song),)
    plan = FrontierCacheManifestPlan(
        total_paths=1,
        hit_paths=() if missing else paths,
        missing_paths=paths if missing else (),
        key_by_norm_path={},
    )
    calls = []

    @contextmanager
    def lock(*_args, **_kwargs):
        calls.append("lock")
        yield

    def build(*_args, **_kwargs):
        calls.append("build")
        return prebuild.FgResponseFrontierCachePrebuildSummary(completed=1, built=1), []

    monkeypatch.setattr(prebuild, "_manifest_records_current_cache_version", lambda: True)
    monkeypatch.setattr(prebuild, "_build_manifest_plan", lambda *_args, **_kwargs: plan)
    monkeypatch.setattr(prebuild, "FrontierBuildLock", lock)
    monkeypatch.setattr(
        prebuild,
        "_maintain_fg_response_frontier_cache_under_lock",
        lambda **kwargs: calls.append(f"maintain:{kwargs['authorize_destructive_rotation']}"),
    )
    monkeypatch.setattr(prebuild, "_run_missing_fg_prebuild", build)
    monkeypatch.setattr(prebuild, "_apply_manifest_results", lambda **_kwargs: calls.append("save"))
    monkeypatch.setattr(
        "gear_optimizer.solver.taichi_gem.force_greats.response_cache.compress_cache_dir_sidecars",
        lambda: calls.append("compress"),
    )

    summary = prebuild.run_fg_response_frontier_cache_prebuild(
        song_queue=[paths],
        ref_arrays={},
        data_root=tmp_path,
        authorize_destructive_rotation=rotate,
        build_missing=build_missing,
        timing_modes=("perfect_window",),
    )

    assert calls == expected
    assert summary.completed == int(not missing or build_missing)
    assert summary.failures == int(missing and not build_missing)
    assert summary.built == int(missing and build_missing)


def test_destructive_rotation_never_parses_the_manifest_for_its_version(monkeypatch, tmp_path):
    song = tmp_path / "Song.txt"
    song.write_text("test chart")
    paths = (str(song),)
    plan = FrontierCacheManifestPlan(total_paths=1, hit_paths=paths, missing_paths=(), key_by_norm_path={})

    def version_probe():
        raise AssertionError("a destructive-rotation prebuild must not parse the whole FG manifest")

    @contextmanager
    def lock(*_args, **_kwargs):
        yield

    monkeypatch.setattr(prebuild, "_manifest_records_current_cache_version", version_probe)
    monkeypatch.setattr(prebuild, "_build_manifest_plan", lambda *_args, **_kwargs: plan)
    monkeypatch.setattr(prebuild, "FrontierBuildLock", lock)
    monkeypatch.setattr(prebuild, "_maintain_fg_response_frontier_cache_under_lock", lambda **_kwargs: None)

    summary = prebuild.run_fg_response_frontier_cache_prebuild(
        song_queue=[paths],
        ref_arrays={},
        data_root=tmp_path,
        authorize_destructive_rotation=True,
        timing_modes=("perfect_window",),
    )

    assert summary.completed == 1
