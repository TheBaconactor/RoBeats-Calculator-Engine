import atexit
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest

repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from gear_optimizer.store import schema


def _configure_test_db_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_db = repo_root / "evolution.db"

    tmp_dir = Path(tempfile.mkdtemp(prefix="gear_optimizer_tests_db_"))
    atexit.register(lambda: shutil.rmtree(tmp_dir, ignore_errors=True))

    tmp_db = tmp_dir / "evolution.db"
    if source_db.exists():
        shutil.copy2(source_db, tmp_db)

    os.environ["EVOLUTION_DB_PATH"] = str(tmp_db)

    # If the repo's evolution.db is corrupted/malformed, fall back to a clean DB for tests.
    def _is_db_healthy(path: Path) -> bool:
        if not path.exists():
            return True
        try:
            conn = sqlite3.connect(str(path))
            try:
                row = conn.execute("PRAGMA quick_check;").fetchone()
                return bool(row and str(row[0]).strip().lower() == "ok")
            finally:
                conn.close()
        except Exception:
            return False

    if not _is_db_healthy(tmp_db):
        try:
            tmp_db.unlink(missing_ok=True)
        except Exception:
            pass

    try:
        schema.ensure(tmp_db)
    except sqlite3.DatabaseError:
        # Retry once with a clean DB.
        try:
            tmp_db.unlink(missing_ok=True)
        except Exception:
            pass
        schema.ensure(tmp_db)


def _isolate_frontier_cache_dirs() -> None:
    """Redirect BOTH production frontier-cache dirs to a throwaway session dir.

    The timeline and FG-response frontier caches default to ``bin/timeline_frontier_cache``
    and ``bin/fg_response_frontier_cache`` when their env overrides are unset
    (``_frontier_disk_cache_dir`` / ``_fg_response_disk_cache_dir``). Any test that
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
        from gear_optimizer.solver.taichi_gem.api.timeline import build_or_load_timeline_frontier_payload

        build_or_load_timeline_frontier_payload(song, curves)

    return _run


# -----------------------------------------------------------------------------
# Taichi/Vulkan test isolation
# -----------------------------------------------------------------------------


@pytest.fixture(scope="module", autouse=True)
def _taichi_module_isolation(request):
    """
    Taichi (Vulkan) is prone to rare access violations when a single process runs
    many GPU-heavy modules back-to-back. Isolate GPU-related test modules by
    hard-resetting Taichi before and after the module runs.
    """
    try:
        test_path = str(getattr(request, "fspath", "") or "")
    except Exception:
        test_path = ""

    is_gpu_module = False
    try:
        node = getattr(request, "node", None)
        if node is not None:
            is_gpu_module = node.get_closest_marker("gpu") is not None
    except Exception:
        is_gpu_module = False

    if not is_gpu_module:
        is_gpu_module = any(
            token in test_path
            for token in (
                "test_gpu_",
                "test_fg_",
                "test_cpu_gpu_",
                "test_ga_",
                "test_taichi_",
                "test_parity_",
            )
        )

    if not is_gpu_module:
        yield
        return

    try:
        from gear_optimizer.solver.taichi_gem.api import hard_reset_taichi

        hard_reset_taichi(reason=f"pytest module isolation (setup): {test_path}")
        yield
        hard_reset_taichi(reason=f"pytest module isolation (teardown): {test_path}")
    except Exception:
        # Never fail tests due to reset issues; worst case Taichi crashes as before.
        yield
