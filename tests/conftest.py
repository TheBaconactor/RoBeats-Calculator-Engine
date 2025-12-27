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

    is_gpu_module = any(
        token in test_path
        for token in (
            "test_gpu_",
            "test_fg_",
            "test_cpu_gpu_",
            "test_ga_",
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
