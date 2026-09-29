from __future__ import annotations

from collections import deque
from collections.abc import Callable, MutableMapping, Sequence
from dataclasses import dataclass
import json
import os
from pathlib import Path
import logging
import queue
import threading
import traceback
import time
from typing import Any

from gear_optimizer.solver.gpu_executor_types import build_shutdown_request
from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuRequestType, GpuResponse



logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExecutorStartSettings:
    heartbeat_path: Path
    heartbeat_interval_sec: float
    enable_high_res_timer: bool


@dataclass(frozen=True)
class TaichiInitFailureReport:
    error: str
    trace_path: Path | None


def default_executor_heartbeat_path() -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / "bin" / "gpu_executor_heartbeat.json"


def load_executor_start_settings(
    *,
    in_process: bool,
    os_name: str,
    default_heartbeat_path_fn: Callable[[], Path] = default_executor_heartbeat_path,
) -> ExecutorStartSettings:
    # The in-process owner coalesces with a 2 ms after-first wait (see gpu_executor_batching),
    # which the default ~15.6 ms Windows timer would stretch; request 1 ms timer granularity there.
    enable_high_res_timer = bool(in_process) and str(os_name) == "nt"

    return ExecutorStartSettings(
        heartbeat_path=default_heartbeat_path_fn(),
        heartbeat_interval_sec=2.0,
        enable_high_res_timer=bool(enable_high_res_timer),
    )


def send_shutdown_request(
    request_queue: Any,
    *,
    request_factory: Callable[[], Any] = build_shutdown_request,
) -> None:
    request_queue.put(request_factory())


def build_taichi_init_failure_report(
    exc: BaseException,
    *,
    heartbeat_path: Path,
    traceback_format_fn: Callable[[], str] = traceback.format_exc,
) -> TaichiInitFailureReport:
    err = f"{type(exc).__name__}: {exc}"
    tb = traceback_format_fn()

    trace_path = None
    try:
        trace_path = heartbeat_path.with_name(heartbeat_path.stem + "_taichi_init_error.log")
        trace_path.parent.mkdir(parents=True, exist_ok=True)
        trace_path.write_text(tb, encoding="utf-8", errors="replace")
    except OSError:
        trace_path = None

    if trace_path is not None:
        err = f"{err} (trace: {trace_path})"
    return TaichiInitFailureReport(error=err, trace_path=trace_path)


class ExecutorAbortState:
    def __init__(self) -> None:
        self._event = threading.Event()
        self._reason = ""

    def request_abort(self, reason: str = "abort requested") -> None:
        self._reason = str(reason or "").strip() or "abort requested"
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


def stamp_request_dequeue(
    request: Any,
    *,
    perf_counter_ns_fn: Callable[[], int] = time.perf_counter_ns,
) -> Any:
    try:
        if int(getattr(request, "dequeue_perf_ns", 0) or 0) <= 0:
            request.dequeue_perf_ns = int(perf_counter_ns_fn())
    except (ValueError, TypeError, AttributeError):
        pass
    return request


def stage_request(
    staged_requests: deque,
    request: Any,
    *,
    front: bool = False,
    stamp_fn: Callable[[Any], Any] = stamp_request_dequeue,
) -> None:
    stamped = stamp_fn(request)
    if front:
        staged_requests.appendleft(stamped)
    else:
        staged_requests.append(stamped)


def pop_staged_request(staged_requests: deque, *, index: int = 0) -> Any:
    if index <= 0:
        return staged_requests.popleft()
    rotate_by = int(index)
    staged_requests.rotate(-rotate_by)
    try:
        return staged_requests.popleft()
    finally:
        staged_requests.rotate(rotate_by)


def staged_ga_recovery_index(
    staged_requests: Sequence[Any],
    *,
    is_ga_recovery_request: Callable[[Any], bool],
) -> int | None:
    if not staged_requests:
        return None
    first_request = staged_requests[0]
    if getattr(first_request, "request_type", None) != GpuRequestType.GPU_NATIVE_GA_RUN:
        return None

    for idx, staged in enumerate(staged_requests):
        if idx == 0:
            continue
        request_type = getattr(staged, "request_type", None)
        if request_type == GpuRequestType.SHUTDOWN:
            return int(idx)
        if is_ga_recovery_request(staged):
            return int(idx)
    return None


def prefetch_ga_recovery_requests(
    *,
    in_process_queues: bool,
    ga_owner_turn_streak: int,
    staged_requests: Any,
    deadline: float,
    batch_max_size: int,
    streak_cap: int,
    lookahead_limit: int,
    pop_queue_request: Callable[[float], Any],
    perf_counter_fn: Callable[[], float],
    is_ga_recovery_request: Callable[[Any], bool],
    empty_exception: type[BaseException],
) -> None:
    if not bool(in_process_queues):
        return
    if int(ga_owner_turn_streak) < int(streak_cap):
        return
    if not staged_requests:
        return
    try:
        first_request = staged_requests[0]
    except (IndexError, AttributeError):
        return
    if getattr(first_request, "request_type", None) != GpuRequestType.GPU_NATIVE_GA_RUN:
        return
    if staged_ga_recovery_index(
        list(staged_requests),
        is_ga_recovery_request=is_ga_recovery_request,
    ) is not None:
        return

    target = max(0, int(lookahead_limit))
    if target <= 0:
        return

    while len(staged_requests) < int(target):
        remaining = float(deadline - perf_counter_fn())
        if remaining <= 0.0:
            break
        try:
            request = pop_queue_request(remaining)
        except empty_exception:
            break
        staged_requests.append(request)
        if request.request_type == GpuRequestType.SHUTDOWN:
            break
        if is_ga_recovery_request(request):
            break


class ExecutorHeartbeatWriter:
    def __init__(self, *, path: Path, interval_sec: float) -> None:
        self.path = Path(path)
        self.interval_sec = max(0.1, float(interval_sec))
        self.last_write_monotonic = 0.0
        self.last_phase = ""

    def write(
        self,
        *,
        phase: str,
        batch: list[GpuRequest] | None = None,
        note: str = "",
        force: bool = False,
        ready: bool,
        running: bool,
        requests_processed: int,
        response_put_failures_total: int,
    ) -> None:
        now_monotonic = time.monotonic()
        if (
            not force
            and str(phase) == str(self.last_phase)
            and (now_monotonic - float(self.last_write_monotonic or 0.0)) < float(self.interval_sec)
        ):
            return

        type_counts, request_count = summarize_request_batch(batch)
        payload = {
            "pid": int(os.getpid()),
            "updated_at": int(time.time() * 1000.0),
            "phase": str(phase or "unknown"),
            "ready": bool(ready),
            "running": bool(running),
            "requests_processed": int(requests_processed),
            "request_count": int(request_count),
            "request_types": type_counts,
            "note": str(note or ""),
            "response_put_failures_total": int(response_put_failures_total),
        }

        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = self.path.with_suffix(self.path.suffix + ".tmp")
            tmp_path.write_text(
                json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")),
                encoding="utf-8",
            )
            os.replace(tmp_path, self.path)
            self.last_write_monotonic = now_monotonic
            self.last_phase = str(phase or "")
        except (OSError, ValueError, TypeError):
            return


def summarize_request_batch(batch: list[GpuRequest] | None) -> tuple[dict[str, int], int]:
    type_counts: dict[str, int] = {}
    request_count = 0
    for req in batch or []:
        if getattr(req, "request_type", None) == GpuRequestType.SHUTDOWN:
            continue
        req_name = str(getattr(getattr(req, "request_type", None), "value", "unknown") or "unknown")
        type_counts[req_name] = int(type_counts.get(req_name, 0)) + 1
        request_count += 1
    return type_counts, int(request_count)


# ---- merged from gpu_executor_queue_wait.py ----
import time
from dataclasses import dataclass
from time import perf_counter
from typing import Literal


NowaitFollowupAction = Literal["request", "fallback", "continue", "break"]


@dataclass(frozen=True)
class NowaitFollowupPoll:
    action: NowaitFollowupAction
    request: Any | None
    yields_left: int


@dataclass(frozen=True)
class ShortWaitSpinSettings:
    short_wait_spin_sec: float
    short_wait_spin_yield_rounds: int


def load_short_wait_spin_settings() -> ShortWaitSpinSettings:
    # Hardwired GPU-owner queue short-wait spin tuning
    # (was GPU_EXECUTOR_SHORT_WAIT_SPIN_MS=3.0 / _YIELD_ROUNDS=8).
    return ShortWaitSpinSettings(
        short_wait_spin_sec=0.003,
        short_wait_spin_yield_rounds=8,
    )


def safe_qsize(request_queue: Any) -> int:
    if request_queue is None:
        return -1
    try:
        size = request_queue.qsize()
    except (NotImplementedError, AttributeError):
        return -1
    except (OSError, ValueError):
        return -1
    try:
        return max(0, int(size))
    except (ValueError, TypeError):
        return -1


def get_with_short_wait_spin(
    request_queue: Any,
    *,
    timeout: float,
    in_process_queues: bool,
    short_wait_spin_sec: float,
    short_wait_spin_yield_rounds: int,
    perf_counter_fn: Callable[[], float] = perf_counter,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> Any:
    wait_timeout = max(0.0, float(timeout))
    if wait_timeout <= 0.0:
        return request_queue.get(timeout=0.0)

    if not in_process_queues or wait_timeout > float(short_wait_spin_sec):
        return request_queue.get(timeout=wait_timeout)

    get_nowait = getattr(request_queue, "get_nowait", None)
    if not callable(get_nowait):
        return request_queue.get(timeout=wait_timeout)

    deadline = perf_counter_fn() + wait_timeout
    yields = 0
    max_yields = int(short_wait_spin_yield_rounds or 0)
    while True:
        try:
            return get_nowait()
        except queue.Empty:
            now = perf_counter_fn()
            if now >= deadline:
                raise
            remaining = float(deadline - now)
            if yields < max_yields:
                yields += 1
                sleep_fn(0)
                continue

            block_s = min(remaining, 0.001)
            if block_s <= 0.0:
                raise
            try:
                return request_queue.get(timeout=block_s)
            except queue.Empty:
                continue


def poll_inprocess_followup_nowait(
    request_queue: Any,
    *,
    deadline_s: float,
    yields_left: int,
    stamp_fn: Callable[[Any], Any],
    perf_counter_fn: Callable[[], float] = perf_counter,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> NowaitFollowupPoll:
    get_nowait = getattr(request_queue, "get_nowait", None)
    if not callable(get_nowait):
        return NowaitFollowupPoll(action="fallback", request=None, yields_left=int(yields_left))

    try:
        return NowaitFollowupPoll(
            action="request",
            request=stamp_fn(get_nowait()),
            yields_left=int(yields_left),
        )
    except queue.Empty:
        if perf_counter_fn() >= float(deadline_s) or int(yields_left) <= 0:
            return NowaitFollowupPoll(action="break", request=None, yields_left=int(yields_left))
        sleep_fn(0)
        return NowaitFollowupPoll(action="continue", request=None, yields_left=int(yields_left) - 1)

# ---- merged from gpu_executor_worker_responses.py ----
from collections import OrderedDict
import time



class WorkerResponseRouter:
    def __init__(self, *, pending_ttl_sec: float, pending_max: int) -> None:
        self._pending: OrderedDict[int, tuple[GpuResponse, float]] = OrderedDict()
        self._cond = threading.Condition()
        self._pending_ttl_sec = max(0.0, float(pending_ttl_sec))
        self._pending_max = max(0, int(pending_max))
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def reset(self) -> None:
        self._stop_thread()
        self.clear_pending()

    def restart(self) -> None:
        self._stop_thread()
        self._stop.clear()
        self.clear_pending()

    def clear_pending(self) -> None:
        with self._cond:
            self._pending = OrderedDict()
            self._cond.notify_all()

    def prune(self, now: float | None = None) -> None:
        with self._cond:
            self._prune_locked(now)

    def ensure_started(self, response_queue_getter: Callable[[], Any | None], *, label: str) -> None:
        thread = self._thread
        if thread is not None and thread.is_alive():
            return
        self._stop.clear()
        thread = threading.Thread(
            target=self._loop,
            args=(response_queue_getter,),
            name=f"GpuWorkerResponseRouter[{label}]",
            daemon=True,
        )
        self._thread = thread
        thread.start()

    def wait(self, request_id: int, timeout: float) -> GpuResponse:
        deadline = time.monotonic() + float(timeout)
        with self._cond:
            while True:
                self._prune_locked()
                if request_id in self._pending:
                    response, _ts = self._pending.pop(request_id)
                    return response
                remaining = float(deadline - time.monotonic())
                if remaining <= 0:
                    raise RuntimeError(f"GPU executor timeout after {timeout}s")
                self._cond.wait(timeout=remaining)

    def store(self, response: GpuResponse) -> None:
        with self._cond:
            self._store_locked(response)
            self._cond.notify_all()

    def _stop_thread(self) -> None:
        self._stop.set()
        with self._cond:
            self._cond.notify_all()
        thread = self._thread
        if thread is not None:
            try:
                thread.join(timeout=0.25)
            except Exception:
                pass
        self._thread = None

    def _loop(self, response_queue_getter: Callable[[], Any | None]) -> None:
        while True:
            if self._stop.is_set():
                return
            response_queue = response_queue_getter()
            if response_queue is None:
                time.sleep(0.01)
                continue
            try:
                response = response_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            except (OSError, ValueError):
                time.sleep(0.05)
                continue
            if response is None:
                continue
            self.store(response)

    def _store_locked(self, response: GpuResponse) -> None:
        request_id = int(getattr(response, "request_id", 0) or 0)
        now = time.monotonic()
        self._pending[request_id] = (response, now)
        self._pending.move_to_end(request_id)
        self._prune_locked(now)

    def _prune_locked(self, now: float | None = None) -> None:
        if not self._pending:
            return
        if now is None:
            now = time.monotonic()
        if self._pending_ttl_sec > 0.0:
            while self._pending:
                _response, ts = next(iter(self._pending.values()))
                if (now - ts) <= self._pending_ttl_sec:
                    break
                self._pending.popitem(last=False)
        if self._pending_max > 0:
            while len(self._pending) > self._pending_max:
                self._pending.popitem(last=False)


worker_response_router = WorkerResponseRouter(
    pending_ttl_sec=300.0,
    pending_max=2048,
)

@dataclass(frozen=True)
class RegisteredWorker:
    worker_id: int
    request_queue: Any
    response_queue: Any
    next_worker_id: int

    def as_tuple(self) -> tuple[int, Any, Any]:
        return self.worker_id, self.request_queue, self.response_queue


@dataclass
class WorkerModeState:
    enabled: bool = False
    worker_id: int | None = None
    request_queue: Any | None = None
    response_queue: Any | None = None

    def configure(self, worker_id: int, request_queue: Any, response_queue: Any) -> None:
        self.enabled = True
        self.worker_id = int(worker_id)
        self.request_queue = request_queue
        self.response_queue = response_queue

    def clear(self) -> None:
        self.enabled = False
        self.worker_id = None
        self.request_queue = None
        self.response_queue = None


worker_mode_state = WorkerModeState()


def register_executor_worker(
    *,
    next_worker_id: int,
    request_queue: Any,
    response_queues: MutableMapping[int, Any],
    response_queue_factory: Callable[[], Any],
) -> RegisteredWorker:
    worker_id = int(next_worker_id)
    response_queue = response_queue_factory()
    response_queues[worker_id] = response_queue
    return RegisteredWorker(
        worker_id=worker_id,
        request_queue=request_queue,
        response_queue=response_queue,
        next_worker_id=worker_id + 1,
    )


def unregister_executor_worker(
    *,
    worker_id: int,
    response_queues: MutableMapping[int, Any],
) -> bool:
    return response_queues.pop(int(worker_id), None) is not None

