import queue

from gear_optimizer.solver.gpu_executor import clear_gpu_worker_mode, is_gpu_worker_mode, set_gpu_worker_mode
from gear_optimizer.solver.gpu_executor_worker_state import (
    WorkerModeState,
    default_song_slot_for_worker,
    register_executor_worker,
    unregister_executor_worker,
    worker_mode_state,
)


def test_worker_mode_state_tracks_mode_and_queues():
    state = WorkerModeState()
    request_q = queue.Queue()
    response_q = queue.Queue()

    assert state.enabled is False

    state.configure(42, request_q, response_q)

    assert state.enabled is True
    assert state.worker_id == 42
    assert state.require_request_queue() is request_q
    assert state.response_queue is response_q
    assert state.next_request_id() == 1
    assert state.next_request_id() == 2

    state.clear()

    assert state.enabled is False
    assert state.worker_id is None
    assert state.request_queue is None
    assert state.response_queue is None
    assert state.request_counter == 2


def test_gpu_executor_worker_mode_wrappers_delegate_to_state():
    request_q = queue.Queue()
    response_q = queue.Queue()
    clear_gpu_worker_mode()

    assert is_gpu_worker_mode() is False

    set_gpu_worker_mode(7, request_q, response_q)

    try:
        assert is_gpu_worker_mode() is True
        assert worker_mode_state.worker_id == 7
        assert worker_mode_state.request_queue is request_q
        assert worker_mode_state.response_queue is response_q
    finally:
        clear_gpu_worker_mode()

    assert is_gpu_worker_mode() is False


def test_register_executor_worker_allocates_queue_and_advances_id():
    request_q = queue.Queue()
    response_q = queue.Queue()
    response_queues = {}

    registered = register_executor_worker(
        next_worker_id=4,
        request_queue=request_q,
        response_queues=response_queues,
        response_queue_factory=lambda: response_q,
    )

    assert registered.worker_id == 4
    assert registered.request_queue is request_q
    assert registered.response_queue is response_q
    assert registered.next_worker_id == 5
    assert registered.as_tuple() == (4, request_q, response_q)
    assert response_queues == {4: response_q}


def test_unregister_executor_worker_removes_existing_worker_only():
    response_q = queue.Queue()
    response_queues = {2: response_q}

    assert unregister_executor_worker(worker_id=2, response_queues=response_queues) is True
    assert response_queues == {}
    assert unregister_executor_worker(worker_id=2, response_queues=response_queues) is False


def test_default_song_slot_for_worker_is_stable_nonzero():
    slot_a = default_song_slot_for_worker(0)
    slot_b = default_song_slot_for_worker(0)
    slot_c = default_song_slot_for_worker(5)

    assert slot_a == slot_b
    assert slot_a >= 1
    assert slot_c >= 1
