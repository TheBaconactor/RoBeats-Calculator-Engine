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

from gear_optimizer.data.database import init_db


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
        init_db()
    except sqlite3.DatabaseError:
        # Retry once with a clean DB.
        try:
            tmp_db.unlink(missing_ok=True)
        except Exception:
            pass
        init_db()


_configure_test_db_path()


# -----------------------------------------------------------------------------
# Optional pytest-benchmark compatibility
# -----------------------------------------------------------------------------

try:
    import pytest_benchmark  # noqa: F401

    _HAS_PYTEST_BENCHMARK = True
except Exception:
    _HAS_PYTEST_BENCHMARK = False


if not _HAS_PYTEST_BENCHMARK:

    @pytest.fixture
    def benchmark():
        """
        Minimal fallback for environments without pytest-benchmark installed.

        The real plugin measures timings; for CI/codex runs we only need the
        benchmark tests to execute without failing collection.
        """

        def _runner(func, *args, **kwargs):
            return func(*args, **kwargs)

        return _runner


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
