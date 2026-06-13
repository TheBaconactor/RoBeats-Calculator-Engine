"""Diagnostics for the Issue #34 FG surface re-pack migration tool (tools/dev/repack_fg_surface_cache.py).

CPU-only; uses a temp cache dir and never touches bin/fg_response_frontier_cache.

Regression guard: a slim (already-re-packed) bundle .npz whose surface sidecar was deleted/mismatched
must raise the clear ``SlimBundleMissingSidecarError`` ("surfaces not recoverable from the slim .npz")
instead of falling through to the misleading "neither slim nor legacy-chunked" legacy-branch error.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest
from numpy.lib import format as np_format

from gear_optimizer.core.constants import TOTAL_ROWS
from gear_optimizer.solver.taichi_gem.force_greats import response_cache_store
from gear_optimizer.solver.taichi_gem.force_greats.response_cache_store import (
    _fg_response_disk_cache_path,
    _save_payload,
    _surface_sidecar_paths,
)
from gear_optimizer.solver.taichi_gem.force_greats.response_cache_types import FgResponseFrontierCachePayload
from gear_optimizer.solver.taichi_gem.force_greats.response_types import FgResponseFrontierResult, FgResponseSurface

pytestmark = pytest.mark.filterwarnings("ignore")

_REPO_ROOT = Path(__file__).resolve().parents[1]
_TOOL_PATH = _REPO_ROOT / "tools" / "dev" / "repack_fg_surface_cache.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("repack_fg_surface_cache_under_test", _TOOL_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_slim_bundle(cache_key: tuple, *, row_count: int = 24, total_notes: int = 80) -> Path:
    """Produce a real slim bundle (.npz + both sidecars) via the production writer."""
    rng = np.random.default_rng(2026_06_10)
    pool = np.empty((int(row_count), 11), dtype=np.uint32)
    pool[:, 0:8] = rng.integers(0, np.iinfo(np.uint32).max, size=(row_count, 8), dtype=np.uint64).astype(np.uint32)
    pool[:, 8] = np.arange(row_count, dtype=np.uint32) * 3 + 7
    pool[:, 9] = np.arange(row_count, dtype=np.uint32) * 2 + 1
    pool[:, 10] = np.arange(row_count, dtype=np.uint32)
    surfaces = tuple(FgResponseSurface(*(int(v) for v in pool[idx, :11])) for idx in range(int(row_count)))
    frontier = FgResponseFrontierResult(surfaces, {}, 1, 2, 3, 4, 5, 6, 7, 0.0)
    payload = FgResponseFrontierCachePayload(
        frontier_by_key={(0, 0): frontier},
        raw_fill_by_ff=np.zeros((TOTAL_ROWS + 1,), dtype=np.float64),
        non_fever_base_by_ff=np.zeros((TOTAL_ROWS + 1,), dtype=np.int32),
        real_time_by_ft=np.zeros((TOTAL_ROWS + 1,), dtype=np.float64),
        total_notes=int(total_notes),
        long_notes=0,
        use_forced_great_timing=True,
    )
    _save_payload(cache_key, payload)
    return _fg_response_disk_cache_path(cache_key)


def test_repack_idempotent_skip_then_clear_error_on_deleted_sidecar(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    response_cache_store.reset_fg_response_frontier_payload_cache()
    tool = _load_tool()

    cache_key = ("unit", "repack-deleted-sidecar")
    npz_path = _write_slim_bundle(cache_key)
    pool_sidecar, coeff_sidecar = _surface_sidecar_paths(npz_path)
    assert npz_path.exists() and pool_sidecar.exists() and coeff_sidecar.exists()

    # A fully-migrated slim bundle is left untouched (idempotent).
    assert tool.repack_bundle(npz_path) == "skipped"

    # Delete one sidecar: the slim .npz is now desynced from its (gone) surface data.
    pool_sidecar.unlink()

    with pytest.raises(tool.SlimBundleMissingSidecarError) as excinfo:
        tool.repack_bundle(npz_path)
    msg = str(excinfo.value)
    assert "not recoverable from the slim .npz" in msg
    assert "rebuilt by the optimizer" in msg
    assert pool_sidecar.name in msg
    # Must NOT misreport a slim bundle as un-classifiable.
    assert "neither slim nor legacy-chunked" not in msg


def test_repack_clear_error_on_shape_mismatched_sidecar(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    response_cache_store.reset_fg_response_frontier_payload_cache()
    tool = _load_tool()

    cache_key = ("unit", "repack-mismatched-sidecar")
    npz_path = _write_slim_bundle(cache_key, row_count=24)
    pool_sidecar, _coeff_sidecar = _surface_sidecar_paths(npz_path)

    # Overwrite the pool sidecar with a wrong row count -> shape mismatch vs first_surface_row_count.
    with open(pool_sidecar, "wb") as handle:
        np_format.write_array(handle, np.zeros((3, 11), dtype=np.uint32), allow_pickle=False)

    with pytest.raises(tool.SlimBundleMissingSidecarError) as excinfo:
        tool.repack_bundle(npz_path)
    msg = str(excinfo.value)
    assert "not recoverable from the slim .npz" in msg
    assert "neither slim nor legacy-chunked" not in msg
