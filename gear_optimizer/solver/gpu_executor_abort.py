from __future__ import annotations

import threading

from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuResponse


class ExecutorAbortState:
    def __init__(self) -> None:
        self._event = threading.Event()
        self._reason = ""

    def request_abort(self, reason: str = "abort requested") -> None:
        try:
            reason_text = str(reason or "").strip()
        except (ValueError, TypeError):
            reason_text = ""
        self._reason = reason_text or "abort requested"
        self._event.set()

    def clear(self) -> None:
        self._reason = ""
        self._event.clear()

    def requested(self) -> bool:
        return bool(self._event.is_set())

    def error_message(self) -> str:
        reason = str(self._reason or "").strip()
        if not reason:
            reason = "abort requested"
        return f"GpuExecutor aborted: {reason}"

    def raise_if_requested(self) -> None:
        if self.requested():
            raise RuntimeError(self.error_message())

    def response(self, request: GpuRequest) -> GpuResponse:
        return GpuResponse(
            request_id=int(getattr(request, "request_id", 0) or 0),
            success=False,
            error=self.error_message(),
        )
