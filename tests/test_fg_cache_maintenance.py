"""The FG cache's directory maintenance: only a build or an authorized rotation purges and cleans."""

from pathlib import Path

import pytest

from gear_optimizer.solver import fg_response_frontier_cache_prebuild as prebuild
from gear_optimizer.solver.frontier_cache import FrontierCacheManifestPlan


@pytest.mark.parametrize(
    "missing,rotate,build_missing,maintained",
    [
        (False, False, True, False),  # hits only read or repair the manifest
        (True, False, False, False),  # nothing is built
        (True, False, True, True),
        (False, True, True, True),
    ],
)
def test_maintenance_runs_before_builds_and_authorized_rotations(
    monkeypatch, tmp_path: Path, missing, rotate, build_missing, maintained
):
    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    interrupted_write = tmp_path / "bundle.123.456.tmp.npz"
    interrupted_write.write_bytes(b"partial")
    chart = str(tmp_path / "Song.txt")
    plan = FrontierCacheManifestPlan(
        total_paths=1,
        hit_paths=() if missing else (chart,),
        missing_paths=(chart,) if missing else (),
        key_by_norm_path={},
    )

    prebuild.FG_RESPONSE_FRONTIER_PREBUILD.maintain(plan, build_missing, rotate)

    assert interrupted_write.exists() is not maintained
    assert (tmp_path / ".purged_version").exists() is maintained


def test_timeline_maintenance_removes_interrupted_writes_on_every_lock_entry(monkeypatch, tmp_path: Path):
    from gear_optimizer.solver.timeline_frontier_cache_prebuild import TIMELINE_FRONTIER_PREBUILD

    monkeypatch.setenv("TIMELINE_FRONTIER_CACHE_DIR", str(tmp_path))
    interrupted_write = tmp_path / "payload.123.456.tmp.npz"
    interrupted_write.write_bytes(b"partial")
    plan = FrontierCacheManifestPlan(total_paths=1, hit_paths=("Song.txt",), missing_paths=(), key_by_norm_path={})

    TIMELINE_FRONTIER_PREBUILD.maintain(plan, False, False)

    assert not interrupted_write.exists()
