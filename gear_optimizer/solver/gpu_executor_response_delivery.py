from __future__ import annotations

from collections import defaultdict
import logging
import queue
import time
from typing import Any

from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuResponse

logger = logging.getLogger(__name__)


def order_responses_for_requests(
    requests: list[GpuRequest],
    responses: Any,
) -> list[GpuResponse | None]:
    by_id: dict[int, GpuResponse] = {}
    for response in responses or []:
        if response is None:
            continue
        try:
            by_id[int(response.request_id)] = response
        except (ValueError, TypeError, AttributeError):
            continue
    return [by_id.get(int(req.request_id)) for req in requests]


class ResponseDeliveryTracker:
    def __init__(self) -> None:
        self.failures_total = 0
        self.failures_by_worker = defaultdict(int)
        self.last_warn_monotonic = 0.0

    def reset(self) -> None:
        self.failures_total = 0
        self.failures_by_worker.clear()
        self.last_warn_monotonic = 0.0

    def try_put(
        self,
        response_queues: dict[int, Any],
        request: GpuRequest,
        response: GpuResponse,
    ) -> bool:
        try:
            q = response_queues.get(request.worker_id)
            if q is None:
                return False
            put_nowait = getattr(q, "put_nowait", None)
            if callable(put_nowait):
                put_nowait(response)
            else:
                q.put(response, block=False)
            return True
        except queue.Full:
            self._record_failure(request, "Response queue full; dropping response")
            return False
        except Exception as e:
            logger.debug(f"gpu_executor_response_delivery:try_put: {e}")
            self._record_failure(request, "Failed to deliver response")
            return False

    def _record_failure(self, request: GpuRequest, message: str) -> None:
        try:
            self.failures_total += 1
            self.failures_by_worker[int(request.worker_id)] += 1
            now = time.monotonic()
            if (now - float(self.last_warn_monotonic or 0.0)) < 5.0:
                return
            self.last_warn_monotonic = now
            logger.warning(
                "[GpuExecutor] %s (worker_id=%s request_id=%s type=%s total_failures=%s)",
                str(message),
                int(request.worker_id),
                int(getattr(request, "request_id", 0) or 0),
                str(getattr(getattr(request, "request_type", None), "value", "") or ""),
                int(self.failures_total),
            )
        except Exception as e:
            logger.debug(f"gpu_executor_response_delivery:_record_failure: {e}")
