import numpy as np

from gear_optimizer.solver.gpu_executor_fg_breakpoint_solve import (
    execute_fg_solve_with_breakpoints,
    execute_fg_solve_with_breakpoints_batch,
)
from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuRequestType


def _request(request_type, payload) -> GpuRequest:
    return GpuRequest(
        request_type=request_type,
        request_id=80,
        worker_id=0,
        payload=payload,
    )


def _batch_request(payload) -> GpuRequest:
    return _request(GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH, payload)


def _batch_execute(request, **overrides):
    funcs = {
        "in_process_queues": True,
        "raise_if_abort_requested": lambda: None,
        "run_payload_fn": lambda payload, **_kwargs: payload,
        "compute_max_fp_matrix_fn": lambda **_kwargs: np.zeros((1, 1), dtype=np.int16),
        "decode_cfg_counts_from_max_fp_matrix_fn": lambda *_args: np.asarray([[1]], dtype=np.int32),
        "decode_cfg_counts_from_windows_fn": lambda *_args: np.asarray([[2]], dtype=np.int32),
        "download_packed_topk_batch_fn": lambda n: [{} for _ in range(int(n))],
        "download_batch_max_fn": lambda: 8,
    }
    funcs.update(overrides)
    return execute_fg_solve_with_breakpoints_batch(request, **funcs)


def test_execute_fg_solve_with_breakpoints_requires_in_process_queues():
    response = execute_fg_solve_with_breakpoints(
        _request(GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS, {}),
        in_process_queues=False,
        raise_if_abort_requested=lambda: None,
        run_payload_fn=lambda _payload: "unused",
    )

    assert response.success is False
    assert "requires in-process queues" in str(response.error)


def test_execute_fg_solve_with_breakpoints_returns_payload_result():
    response = execute_fg_solve_with_breakpoints(
        _request(GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS, {"x": 1}),
        in_process_queues=True,
        raise_if_abort_requested=lambda: None,
        run_payload_fn=lambda payload: {"seen": payload},
    )

    assert response.success is True
    assert response.result == {"seen": {"x": 1}}


def test_execute_fg_solve_with_breakpoints_batch_requires_payloads_list():
    response = _batch_execute(_batch_request({"payloads": object()}))

    assert response.success is False
    assert "payloads: list[dict]" in str(response.error)


def test_execute_fg_solve_with_breakpoints_batch_falls_back_to_per_payload(monkeypatch):
    monkeypatch.setenv("FG_BREAKPOINTS_BATCH_PACK_MIN_PAYLOADS", "2")
    calls = []

    response = _batch_execute(
        _batch_request({"payloads": [{"x": 1}, {"x": 2}]}),
        run_payload_fn=lambda payload, **_kwargs: calls.append(payload) or payload["x"],
    )

    assert response.success is True
    assert response.result == [1, 2]
    assert calls == [{"x": 1}, {"x": 2}]


def test_execute_fg_solve_with_breakpoints_batch_reuses_selection_upload(monkeypatch):
    monkeypatch.setenv("FG_BREAKPOINTS_BATCH_PACK_MIN_PAYLOADS", "1")
    preupload_flags = []

    def run_payload(payload, *, batch_pack_idx=None):
        preupload_flags.append(bool(payload.get("fg_selection_inputs_preuploaded", False)))
        return {"_packed_batch": True, "n_sections": 1, "implicit_cfgs": False}

    base_scores = np.asarray([100, 200], dtype=np.int32)
    keep_mask = np.asarray([1, 0], dtype=np.int32)
    payloads = [
        {
            "genome_stats_list": [0, 1],
            "fg_download_topk": 1,
            "fg_download_base_scores": base_scores,
            "fg_download_keep_mask": keep_mask,
        },
        {
            "genome_stats_list": [0, 1],
            "fg_download_topk": 1,
            "fg_download_base_scores": base_scores.copy(),
            "fg_download_keep_mask": keep_mask.copy(),
        },
    ]

    response = _batch_execute(
        _batch_request({"payloads": payloads}),
        run_payload_fn=run_payload,
        download_packed_topk_batch_fn=lambda n: [{"cfg_counts": np.zeros((1, 1), dtype=np.int32)}] * int(n),
    )

    assert response.success is True
    assert len(response.result) == 2
    assert preupload_flags == [False, True]


def test_execute_fg_solve_with_breakpoints_batch_decodes_missing_cfg_counts(monkeypatch):
    monkeypatch.setenv("FG_BREAKPOINTS_BATCH_PACK_MIN_PAYLOADS", "1")

    def run_payload(_payload, *, batch_pack_idx=None):
        return {
            "_packed_batch": True,
            "n_sections": 1,
            "implicit_cfgs": True,
            "base_ft": np.asarray([0], dtype=np.int32),
            "base_ff": np.asarray([0], dtype=np.int32),
            "non_fever_base_by_ff": np.zeros((161,), dtype=np.int16),
            "fp_cap_table": np.zeros((161, 51), dtype=np.int16),
        }

    response = _batch_execute(
        _batch_request(
            {
                "payloads": [
                    {
                        "genome_stats_list": [0],
                        "fg_download_topk": 1,
                        "fg_download_base_scores": np.asarray([10], dtype=np.int32),
                    }
                ]
            }
        ),
        run_payload_fn=run_payload,
        download_packed_topk_batch_fn=lambda _n: [
            {
                "FT": np.asarray([1], dtype=np.int32),
                "FF": np.asarray([2], dtype=np.int32),
                "cfg_idx": np.asarray([0], dtype=np.int32),
            }
        ],
    )

    assert response.success is True
    np.testing.assert_array_equal(response.result[0]["cfg_counts"], np.asarray([[1]], dtype=np.int32))
