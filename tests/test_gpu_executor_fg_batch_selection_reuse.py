import sys
import types

import numpy as np

from gear_optimizer.solver.gpu_executor import GpuExecutor
from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuRequestType


def test_fg_batch_pack_reuses_selection_upload_for_equivalent_arrays(monkeypatch):
    """
    FG batch-pack should reuse top-K selection uploads for equivalent payloads,
    even when callers pass new numpy objects with the same values.
    """
    GpuExecutor._instance = None
    executor = GpuExecutor()
    executor._in_process_queues = True

    monkeypatch.setenv("FG_BREAKPOINTS_BATCH_PACK_MIN_PAYLOADS", "1")

    fake_fields_pkg = types.ModuleType("gear_optimizer.solver.taichi_gem.force_greats")
    fake_fields_pkg.__path__ = []
    fake_fields_pkg.fields = types.SimpleNamespace(FG_DOWNLOAD_BATCH_MAX=8)

    fake_api = types.ModuleType("gear_optimizer.solver.taichi_gem.force_greats.api")
    fake_api.fg_download_packed_topk_batch = lambda n_payloads: [
        {"cfg_counts": np.zeros((1, 1), dtype=np.int32)} for _ in range(int(n_payloads))
    ]

    monkeypatch.setitem(sys.modules, "gear_optimizer.solver.taichi_gem.force_greats", fake_fields_pkg)
    monkeypatch.setitem(sys.modules, "gear_optimizer.solver.taichi_gem.force_greats.api", fake_api)

    preupload_flags: list[bool] = []

    def _fake_run(payload, *, batch_pack_idx=None):
        preupload_flags.append(bool(payload.get("fg_selection_inputs_preuploaded", False)))
        return {"_packed_batch": True, "n_sections": 1, "implicit_cfgs": False}

    monkeypatch.setattr(executor, "_run_fg_solve_with_breakpoints_payload", _fake_run)

    base_scores = np.array([100, 200, 300, 400], dtype=np.int32)
    keep_mask = np.array([1, 0, 1, 0], dtype=np.int32)
    payload_a = {
        "genome_stats_list": [0, 1, 2, 3],
        "fg_download_topk": 2,
        "fg_download_base_scores": base_scores,
        "fg_download_keep_mask": keep_mask,
    }
    payload_b = {
        "genome_stats_list": [0, 1, 2, 3],
        "fg_download_topk": 2,
        "fg_download_base_scores": base_scores.copy(),
        "fg_download_keep_mask": keep_mask.copy(),
    }

    request = GpuRequest(
        request_type=GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH,
        request_id=777,
        worker_id=1,
        payload={"payloads": [payload_a, payload_b]},
    )
    response = executor._execute_fg_solve_with_breakpoints_batch(request)

    assert response.success is True
    assert isinstance(response.result, list)
    assert len(response.result) == 2
    assert preupload_flags == [False, True]
    GpuExecutor._instance = None


def test_fg_breakpoint_payload_reuses_pre_split_base_vectors(monkeypatch):
    """
    Fused FG payload builder should forward pre-split base_ft/base_ff vectors so
    downstream task prep can skip repeated `(n,2)->(n,)` host slicing.
    """
    GpuExecutor._instance = None
    executor = GpuExecutor()
    executor._in_process_queues = True

    monkeypatch.setenv("FG_IMPLICIT_CONFIGS", "1")
    monkeypatch.setenv("FG_MAX_FP_GPU_COMPUTE", "1")

    captured: dict[str, object] = {}
    fake_api = types.ModuleType("gear_optimizer.solver.taichi_gem.force_greats.api")

    def _fake_reset_global_best(*_args, **_kwargs):
        return None

    def _fake_solve_tasks(
        genome_stats_list,
        timestamps_np,
        great_candidate_timestamps_np,
        long_notes,
        last_note_time,
        *,
        fg_tasks,
        **_kwargs,
    ):
        captured["fg_tasks"] = fg_tasks
        return None

    def _fake_download_global_best(n_genomes, *, session_slot=0, topk=None, base_scores=None, keep_mask=None):
        n = int(n_genomes)
        return {
            "final_score": np.zeros((n,), dtype=np.int32),
            "base_score": np.zeros((n,), dtype=np.int32),
            "cfg_idx": np.zeros((n,), dtype=np.int32),
            "FT": np.zeros((n,), dtype=np.int32),
            "FF": np.zeros((n,), dtype=np.int32),
            "cfg_counts": np.zeros((n, 1), dtype=np.int32),
        }

    fake_api.fg_reset_global_best = _fake_reset_global_best
    fake_api.solve_force_greats_finder_gpu_tasks = _fake_solve_tasks
    fake_api.fg_download_global_best = _fake_download_global_best
    monkeypatch.setitem(sys.modules, "gear_optimizer.solver.taichi_gem.force_greats.api", fake_api)

    payload = {
        "n_sections": 3,
        "ftff_pairs": np.array([[0, 0], [2, 1]], dtype=np.int32),
        "base_stats_pairs": np.array([[100, 80], [110, 85]], dtype=np.int32),
        "non_fever_base_by_ff": np.zeros((161,), dtype=np.int16),
        "fp_cap_table": np.zeros((161, 51), dtype=np.int16),
        "genome_stats_list": np.array([[100, 100, 100, 200, 120, 80, 80]], dtype=np.int32),
        "timestamps_np": np.linspace(0.0, 5.0, 32, dtype=np.float32),
        "great_candidate_timestamps_np": None,
        "long_notes": 0,
        "last_note_time": 5.0,
        "solve_kwargs": {
            "n_sections": 3,
            "ref_arrays": {
                "Perfect Points": np.ones((161,), dtype=np.float32),
                "Combo Multiplier": np.ones((161,), dtype=np.float32),
                "Fever Multiplier": np.ones((161,), dtype=np.float32),
                "Fever Fill Rate": np.ones((161,), dtype=np.float32),
                "Fever Time": np.ones((161,), dtype=np.float32),
            },
        },
    }

    out = executor._run_fg_solve_with_breakpoints_payload(payload)
    assert isinstance(out, dict)

    fg_tasks = captured.get("fg_tasks")
    assert isinstance(fg_tasks, list)
    assert len(fg_tasks) == 1
    compute = (fg_tasks[0].get("counts_max_fp") or {}) if isinstance(fg_tasks[0], dict) else {}
    assert isinstance(compute, dict)
    base_ft = np.asarray(compute.get("base_ft"))
    base_ff = np.asarray(compute.get("base_ff"))
    assert base_ft.tolist() == [100, 110]
    assert base_ff.tolist() == [80, 85]

    GpuExecutor._instance = None
