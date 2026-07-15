import pickle
import subprocess
import sys
from pathlib import Path

from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuRequestType, GpuResponse, build_shutdown_request


def test_gpu_request_envelopes_round_trip_through_pickle():
    request = GpuRequest(
        request_type=GpuRequestType.EXACT_BASE_SEARCH,
        request_id=17,
        worker_id=2,
        payload={"song": "pickle"},
        submit_perf_ns=123,
        dequeue_perf_ns=456,
    )
    response = GpuResponse(request_id=17, success=True, result={"ok": True})

    assert pickle.loads(pickle.dumps(request)) == request
    assert pickle.loads(pickle.dumps(response)) == response


def test_build_shutdown_request_uses_canonical_sentinel_envelope():
    request = build_shutdown_request()

    assert request.request_type == GpuRequestType.SHUTDOWN
    assert request.request_id == -1
    assert request.worker_id == -1
    assert request.payload == {}


def test_gpu_executor_types_import_does_not_load_executor_module():
    repo_root = Path(__file__).resolve().parents[1]
    script = (
        "import sys\n"
        "import gear_optimizer.solver.gpu_executor_types\n"
        "print('gear_optimizer.solver.gpu_executor' in sys.modules)\n"
    )

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout.strip() == "False"
