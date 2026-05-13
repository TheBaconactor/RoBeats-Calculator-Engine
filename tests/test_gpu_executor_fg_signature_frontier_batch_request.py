import sys
import types

import numpy as np

from gear_optimizer.solver.gpu_executor import GpuExecutor
from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuRequestType


def _install_fake_taichi_deps_for_frontier_batch(monkeypatch):
    calls: dict[str, list] = {"payloads": []}

    fake_parent = types.ModuleType("gear_optimizer.solver.taichi_gem")
    fake_parent.__path__ = []

    fake_force_parent = types.ModuleType("gear_optimizer.solver.taichi_gem.force_greats")
    fake_force_parent.__path__ = []

    fake_force_api = types.ModuleType("gear_optimizer.solver.taichi_gem.force_greats.api")

    def _fake_select(payloads):
        calls["payloads"].append(payloads)
        out = []
        for payload in payloads:
            limit = int(payload.get("limit", 0) or 0)
            out.append(np.arange(limit, dtype=np.int32))
        return out

    fake_force_api.fg_select_signature_frontier_batch = _fake_select
    fake_force_parent.api = fake_force_api
    fake_parent.force_greats = fake_force_parent

    monkeypatch.setitem(sys.modules, "gear_optimizer.solver.taichi_gem", fake_parent)
    monkeypatch.setitem(sys.modules, "gear_optimizer.solver.taichi_gem.force_greats", fake_force_parent)
    monkeypatch.setitem(sys.modules, "gear_optimizer.solver.taichi_gem.force_greats.api", fake_force_api)
    return calls


def test_gpu_executor_fg_signature_frontier_batch_request(monkeypatch):
    calls = _install_fake_taichi_deps_for_frontier_batch(monkeypatch)

    ex = GpuExecutor()
    ex._in_process_queues = True

    payloads = [
        {
            "base_scores": np.asarray([10, 9, 8], dtype=np.int32),
            "proxy_scores": np.asarray([1, 2, 3], dtype=np.int32),
            "priorities": np.asarray([0, 0, 1], dtype=np.int32),
            "force_keep": np.asarray([0, 1, 0], dtype=np.int32),
            "center_bucket_ft": np.asarray([0, 1, 2], dtype=np.int32),
            "center_bucket_ff": np.asarray([2, 1, 0], dtype=np.int32),
            "timing_bucket": np.asarray([0, 1, 1], dtype=np.int32),
            "limit": 2,
            "top_base_keep": 2,
        }
    ]

    req = GpuRequest(
        request_type=GpuRequestType.FG_SELECT_SIGNATURE_FRONTIER_BATCH,
        request_id=1,
        worker_id=1,
        payload={"payloads": payloads},
    )
    resp = ex._execute_request(req)
    assert resp.success
    assert isinstance(resp.result, list)
    assert np.array_equal(resp.result[0], np.asarray([0, 1], dtype=np.int32))
    assert calls["payloads"] == [payloads]
