import queue

from gear_optimizer.solver.gpu_executor import GpuRequestType
from gear_optimizer.solver.gpu_service import GpuServiceClient


class _DummyExecutor:
    def __init__(self):
        self.is_running = True
        self._request_q = queue.Queue()
        self._response_q = queue.Queue()

    def register_worker(self):
        return 0, self._request_q, self._response_q

    def unregister_worker(self, _worker_id: int):
        return None


def test_submit_registry_payload_reuses_static_handle_after_first_request():
    executor = _DummyExecutor()
    client = GpuServiceClient(executor=executor)
    client.start(start_executor=False, in_process_queues=True)
    try:
        static_item_stats = [[1, 2], [3, 4]]
        static_slot_start = [0] * 9
        static_slot_count = [1] * 9
        static_base_fixed = [1] * 10
        static_timeline_grid = {"metadata": {}, "song_data": {}}
        static_ref_arrays = {"Perfect Points": [1.0, 2.0]}

        payload_first = {
            "population_indices": [[0] * 9],
            "item_stats": static_item_stats,
            "slot_start": static_slot_start,
            "slot_count": static_slot_count,
            "base_fixed_stats": static_base_fixed,
            "timeline_grid": static_timeline_grid,
            "ref_arrays": static_ref_arrays,
            "is_p_ft": 0,
            "is_s_ft": 0,
            "is_p_ff": 0,
            "is_s_ff": 0,
            "is_p_pp": 0,
            "is_s_pp": 0,
            "is_p_cm": 0,
            "is_s_cm": 0,
            "is_p_fm": 0,
            "is_s_fm": 0,
            "is_p_ov": 0,
            "is_s_ov": 0,
            "total_budget": 90,
            "gem_scale_fever": 3,
            "song_slot": 1,
        }
        payload_second = dict(payload_first)
        payload_second["population_indices"] = [[1] * 9]

        client.submit_solve_genomes_from_registry(payload_first)
        client.submit_solve_genomes_from_registry(payload_second)

        req1 = executor._request_q.get_nowait()
        req2 = executor._request_q.get_nowait()

        assert req1.request_type == GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY
        assert req2.request_type == GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY

        pl1 = req1.payload
        pl2 = req2.payload
        assert pl1["registry_payload_inline"] is True
        assert pl2["registry_payload_inline"] is False
        assert int(pl1["registry_payload_handle"]) == int(pl2["registry_payload_handle"])

        assert "item_stats" in pl1 and "item_stats" not in pl2
        assert "slot_start" in pl1 and "slot_start" not in pl2
        assert "slot_count" in pl1 and "slot_count" not in pl2
        assert "base_fixed_stats" in pl1 and "base_fixed_stats" not in pl2
        assert "timeline_grid" in pl1 and "timeline_grid" not in pl2
        assert "ref_arrays" in pl1 and "ref_arrays" not in pl2
    finally:
        client.close(timeout=0.2)


def test_submit_solve_payload_reuses_static_handle_after_first_request():
    executor = _DummyExecutor()
    client = GpuServiceClient(executor=executor)
    client.start(start_executor=False, in_process_queues=True)
    try:
        static_timeline_grid = {"metadata": {"Song Name": "x"}, "song_data": {}}
        static_ref_arrays = {"Perfect Points": [1.0, 2.0]}

        payload_first = {
            "genome_stats_list": [{"base_pp": 100}],
            "timeline_grid": static_timeline_grid,
            "ref_arrays": static_ref_arrays,
            "total_budget": 90,
            "gem_scale_fever": 3,
            "song_slot": 1,
        }
        payload_second = dict(payload_first)
        payload_second["genome_stats_list"] = [{"base_pp": 101}]

        client.submit_solve_genomes(payload_first)
        client.submit_solve_genomes(payload_second)

        req1 = executor._request_q.get_nowait()
        req2 = executor._request_q.get_nowait()

        assert req1.request_type == GpuRequestType.SOLVE_GENOMES_WITH_FTFF
        assert req2.request_type == GpuRequestType.SOLVE_GENOMES_WITH_FTFF

        pl1 = req1.payload
        pl2 = req2.payload
        assert pl1["solve_static_inline"] is True
        assert pl2["solve_static_inline"] is False
        assert int(pl1["solve_static_handle"]) == int(pl2["solve_static_handle"])

        assert "timeline_grid" in pl1 and "timeline_grid" not in pl2
        assert "ref_arrays" in pl1 and "ref_arrays" not in pl2
    finally:
        client.close(timeout=0.2)
