from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from gear_optimizer.solver.frontier_cache_scope import (
    frontier_cache_is_ephemeral,
    scoped_frontier_cache_dir,
    temporary_frontier_cache_scope,
)


def test_temporary_frontier_scope_is_context_local_and_resets(tmp_path: Path) -> None:
    roots = [tmp_path / "one", tmp_path / "two"]

    def inspect(root: Path) -> tuple[Path | None, Path | None, bool]:
        with temporary_frontier_cache_scope(root):
            return (
                scoped_frontier_cache_dir("timeline"),
                scoped_frontier_cache_dir("fg_response"),
                frontier_cache_is_ephemeral(),
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(inspect, roots))

    assert results == [
        (roots[0] / "timeline", roots[0] / "fg_response", True),
        (roots[1] / "timeline", roots[1] / "fg_response", True),
    ]
    assert scoped_frontier_cache_dir("timeline") is None
    assert frontier_cache_is_ephemeral() is False


def test_temporary_frontier_scope_owns_both_real_disk_cache_paths(tmp_path: Path) -> None:
    from gear_optimizer.solver.taichi_gem.api.timeline import _frontier_disk_cache_dir
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_keys import (
        _fg_response_disk_cache_dir,
    )

    with temporary_frontier_cache_scope(tmp_path / "job"):
        assert _frontier_disk_cache_dir() == tmp_path / "job" / "timeline"
        assert _fg_response_disk_cache_dir() == tmp_path / "job" / "fg_response"
