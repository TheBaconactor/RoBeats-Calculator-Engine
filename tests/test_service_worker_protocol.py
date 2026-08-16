from __future__ import annotations

import json
import queue

from gear_optimizer import robeatsmeta_service as service


def test_persistent_worker_reuses_one_process(monkeypatch):
    starts = 0
    worker = service._PersistentSolveWorker()

    class FakeStdin:
        def write(self, line: str) -> int:
            payload = json.loads(line)
            worker._responses.put({"ok": True, "loadouts": [{"mode": payload["mode"]}]})
            return len(line)

        def flush(self) -> None:
            return None

        def close(self) -> None:
            return None

    class FakeProcess:
        stdin = FakeStdin()
        stdout = None
        stderr = None
        pid = 1

        @staticmethod
        def poll():
            return None

    def fake_start():
        nonlocal starts
        starts += 1
        worker._responses = queue.Queue()
        worker._proc = FakeProcess()
        return worker._proc

    monkeypatch.setattr(worker, "_start_locked", fake_start)

    assert worker.request({"mode": "default"}) == [{"mode": "default"}]
    assert worker.request({"mode": "zero_ms"}) == [{"mode": "zero_ms"}]
    assert starts == 1


def test_persistent_worker_stop_is_idempotent(monkeypatch):
    worker = service._PersistentSolveWorker()
    stopped: list[int] = []

    class FakeProcess:
        pid = 123
        stdin = None
        stdout = None
        stderr = None

        @staticmethod
        def poll():
            return None

        @staticmethod
        def wait(timeout=None):
            stopped.append(1)
            return 0

    worker._proc = FakeProcess()
    monkeypatch.setattr(service, "_kill_process_group", lambda _proc: stopped.append(1))

    worker.stop()
    worker.stop()

    assert stopped == [1, 1]
