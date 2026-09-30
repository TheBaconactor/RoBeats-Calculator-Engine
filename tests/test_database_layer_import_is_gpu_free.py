import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

# A fresh interpreter: this pytest session may already hold Taichi. Light processes (the :8765
# service, the website's optimizer queue worker) import only the results store and must not
# keep the Taichi/numba/FG solver stack resident.
_PROBE = (
    "import sys, gear_optimizer.store.legacy; "
    "heavy = sorted(m for m in sys.modules if m.split('.')[0] in {'taichi', 'numba', 'llvmlite'} "
    "or m.startswith('gear_optimizer.solver.taichi_gem')); "
    "assert not heavy, heavy"
)


def test_database_layer_import_does_not_load_the_gpu_stack():
    result = subprocess.run(
        [sys.executable, "-c", _PROBE],
        text=True,
        capture_output=True,
        check=False,
        cwd=str(REPO_ROOT),
    )

    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
