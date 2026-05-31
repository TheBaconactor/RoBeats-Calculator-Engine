from __future__ import annotations

import numpy as np
import pytest

from gear_optimizer.solver.scoring.runtime_state import _GPU_LOCK
from gear_optimizer.solver.taichi_gem import fields as gpu_fields
from gear_optimizer.solver.taichi_gem.api.ga_operations import ga_download_fg_selected_payload

pytestmark = pytest.mark.gpu


def _has_taichi() -> bool:
    try:
        import taichi as _  # noqa: F401
    except Exception:
        return False
    return True


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_gpu_ga_fg_selected_payload_header_uses_selected_top_base_row() -> None:
    from gear_optimizer.solver.taichi_gem.api.initialization import ensure_ready

    table_slot = 0
    with _GPU_LOCK:
        ensure_ready()
        packed = np.zeros(
            tuple(int(dim) for dim in gpu_fields.ga_fg_candidates_packed.shape),
            dtype=np.int32,
        )
        packed[table_slot, 0, 0, 0] = 10
        packed[table_slot, 0, 0, 1:10] = np.arange(100, 109, dtype=np.int32)
        packed[table_slot, 0, 0, 10:17] = np.asarray([10, 1, 1, 1, 1, 1, 1], dtype=np.int32)

        packed[table_slot, 0, 1, 0] = 100
        packed[table_slot, 0, 1, 1:10] = np.arange(200, 209, dtype=np.int32)
        packed[table_slot, 0, 1, 10:17] = np.asarray([100, 2, 2, 2, 2, 2, 2], dtype=np.int32)
        gpu_fields.ga_fg_candidates_packed.from_numpy(packed)

        selected_payload = ga_download_fg_selected_payload(table_slot=table_slot, n_runs=1, limit=1)

    assert int(selected_payload[0, 0]) == 1
    assert int(selected_payload[0, 1]) == 100
    assert np.array_equal(selected_payload[0, 2:11], np.arange(200, 209, dtype=np.int32))
    assert int(selected_payload[1, 2]) == 100
