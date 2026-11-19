import atexit
import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from gear_optimizer.store import schema


def _configure_test_db_path() -> None:
    tmp_dir = Path(tempfile.mkdtemp(prefix="gear_optimizer_tests_db_"))
    atexit.register(lambda: shutil.rmtree(tmp_dir, ignore_errors=True))

    tmp_db = tmp_dir / "evolution.db"
    os.environ["EVOLUTION_DB_PATH"] = str(tmp_db)
    schema.ensure(tmp_db)


def _isolate_frontier_cache_dirs() -> None:
    """Redirect BOTH production frontier-cache dirs to a throwaway session dir.

    The timeline and FG-response frontier caches default to ``bin/timeline_frontier_cache``
    and ``bin/fg_response_frontier_cache`` when their env overrides are unset
    (``_frontier_disk_cache_dir`` / ``fg_response_disk_cache_dir``). Any test that
    exercises a real cache code path -- a timeline build/load, a cache-info probe, or
    the FG cache prebuild (whose maintenance purges superseded versions, compresses sidecars and
    removes temporary files) -- without setting its override
    would read, prune, purge, or rebuild the developer's PRODUCTION cache under ``bin/``.

    Pinning both overrides for the whole session (env is read live via ``env_get``, so a
    process-wide ``os.environ`` assignment is honored by every worker on first access)
    makes the real dirs unreachable by construction. Per-test ``monkeypatch.setenv`` for
    these vars still works: monkeypatch snapshots this session value and restores it on
    teardown, keeping isolation intact.
    """
    tmp_dir = Path(tempfile.mkdtemp(prefix="gear_optimizer_tests_frontier_cache_"))
    atexit.register(lambda: shutil.rmtree(tmp_dir, ignore_errors=True))

    timeline_dir = tmp_dir / "timeline_frontier_cache"
    fg_response_dir = tmp_dir / "fg_response_frontier_cache"
    timeline_dir.mkdir(parents=True, exist_ok=True)
    fg_response_dir.mkdir(parents=True, exist_ok=True)

    os.environ["TIMELINE_FRONTIER_CACHE_DIR"] = str(timeline_dir)
    os.environ["FG_RESPONSE_FRONTIER_CACHE_DIR"] = str(fg_response_dir)


_configure_test_db_path()
_isolate_frontier_cache_dirs()


@pytest.fixture
def prebuild_timeline_frontier():
    """
    Prebuild the candidate-independent timeline frontier before GPU exact replay.

    Isolated GPU unit tests do not run the full-app startup prebuild; tests that call
    score_stats_exact must invoke this first or they
    raise MissingFrontierCacheError.
    """

    def _run(song, curves) -> None:
        from gear_optimizer.frontier.timeline_cache import build_or_load_timeline_frontier_payload

        build_or_load_timeline_frontier_payload(song, curves)

    return _run


# -----------------------------------------------------------------------------
# Taichi/Vulkan test isolation
# -----------------------------------------------------------------------------


@pytest.fixture(scope="module", autouse=True)
def _taichi_module_isolation(request):
    """
    Taichi (Vulkan) is prone to rare access violations when a single process runs
    many GPU-heavy modules back-to-back. Isolate GPU-marked test modules by
    resetting an initialized Taichi runtime before and after the module runs.
    """
    node = getattr(request, "node", None)
    if node is None or node.get_closest_marker("gpu") is None:
        yield
        return

    test_path = str(getattr(request, "fspath", "") or "")

    def _reset_if_loaded(phase: str) -> None:
        runtime = sys.modules.get("gear_optimizer.gpu.runtime")
        if runtime is not None and getattr(runtime, "_ti_initialized", False):
            runtime.reset_taichi(reason=f"pytest module isolation ({phase}): {test_path}")

    _reset_if_loaded("setup")
    try:
        yield
    finally:
        _reset_if_loaded("teardown")
