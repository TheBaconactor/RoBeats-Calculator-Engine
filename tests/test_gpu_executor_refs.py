from gear_optimizer.solver.gpu_executor_registry import execute_load_refs
from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuRequestType


def _request(ref_arrays) -> GpuRequest:
    return GpuRequest(
        request_type=GpuRequestType.LOAD_REF_ARRAYS,
        request_id=70,
        worker_id=0,
        payload={"ref_arrays": ref_arrays},
    )


def test_execute_load_refs_uploads_when_signature_changes():
    uploads = []
    ref_arrays = {"a": 1}

    outcome = execute_load_refs(
        _request(ref_arrays),
        last_ref_arrays_sig=b"old",
        load_ref_arrays_fn=lambda refs: uploads.append(refs),
        ref_arrays_sig_fn=lambda _refs: b"new",
    )

    assert outcome.response.success is True
    assert outcome.last_ref_arrays_sig == b"new"
    assert uploads == [ref_arrays]


def test_execute_load_refs_skips_upload_when_signature_matches():
    uploads = []

    outcome = execute_load_refs(
        _request({"a": 1}),
        last_ref_arrays_sig=b"same",
        load_ref_arrays_fn=lambda refs: uploads.append(refs),
        ref_arrays_sig_fn=lambda _refs: b"same",
    )

    assert outcome.response.success is True
    assert outcome.last_ref_arrays_sig == b"same"
    assert uploads == []


def test_execute_load_refs_uploads_when_signature_is_unknown():
    uploads = []
    ref_arrays = {"a": 1}

    outcome = execute_load_refs(
        _request(ref_arrays),
        last_ref_arrays_sig=None,
        load_ref_arrays_fn=lambda refs: uploads.append(refs),
        ref_arrays_sig_fn=lambda _refs: None,
    )

    assert outcome.response.success is True
    assert outcome.last_ref_arrays_sig is None
    assert uploads == [ref_arrays]
