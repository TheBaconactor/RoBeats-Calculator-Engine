from gear_optimizer.solver.gpu_executor_refs import execute_load_refs
from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuRequestType


def _request(curves) -> GpuRequest:
    return GpuRequest(
        request_type=GpuRequestType.LOAD_CURVES,
        request_id=70,
        worker_id=0,
        payload={"curves": curves},
    )


def test_execute_load_refs_uploads_when_signature_changes():
    uploads = []
    curves = {"a": 1}

    outcome = execute_load_refs(
        _request(curves),
        last_curves_sig=b"old",
        load_curves_fn=lambda refs: uploads.append(refs),
        curves_sig_fn=lambda _refs: b"new",
    )

    assert outcome.response.success is True
    assert outcome.last_curves_sig == b"new"
    assert uploads == [curves]


def test_execute_load_refs_skips_upload_when_signature_matches():
    uploads = []

    outcome = execute_load_refs(
        _request({"a": 1}),
        last_curves_sig=b"same",
        load_curves_fn=lambda refs: uploads.append(refs),
        curves_sig_fn=lambda _refs: b"same",
    )

    assert outcome.response.success is True
    assert outcome.last_curves_sig == b"same"
    assert uploads == []


def test_execute_load_refs_uploads_when_signature_is_unknown():
    uploads = []
    curves = {"a": 1}

    outcome = execute_load_refs(
        _request(curves),
        last_curves_sig=None,
        load_curves_fn=lambda refs: uploads.append(refs),
        curves_sig_fn=lambda _refs: None,
    )

    assert outcome.response.success is True
    assert outcome.last_curves_sig is None
    assert uploads == [curves]
