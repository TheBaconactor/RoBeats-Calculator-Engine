import numpy as np

from gear_optimizer.solver.gpu_executor import GpuExecutor
from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuRequestType
from gear_optimizer.solver.gpu_executor_registry_payloads import RegistryPayloadCache, load_registry_payload_cache_settings


def _request(payload: dict, *, worker_id: int = 11) -> GpuRequest:
    return GpuRequest(
        request_type=GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY,
        request_id=1,
        worker_id=worker_id,
        payload=payload,
    )


def _static_payload(handle: int = 123, *, inline: bool = True) -> dict:
    payload = {
        "registry_payload_handle": handle,
        "registry_payload_inline": inline,
        "population_indices": np.arange(9, dtype=np.int32).reshape(1, 9),
    }
    if inline:
        payload.update(
            {
                "item_stats": np.arange(40, dtype=np.int16).reshape(4, 10),
                "slot_start": np.arange(9, dtype=np.int32),
                "slot_count": np.ones(9, dtype=np.int32),
                "base_fixed_stats": np.arange(10, dtype=np.int32),
                "timeline_grid": {"song_data": {"timestamps": [0.0, 1.0]}, "metadata": {}},
                "ref_arrays": {"Perfect Points": [0.0] * 161},
            }
        )
    return payload


def test_registry_payload_cache_resolves_inline_then_handle_payload():
    cache = RegistryPayloadCache(max_entries=8)

    inline = _static_payload(inline=True)
    resolved, err = cache.resolve(_request(inline), inline)

    assert err is None
    assert resolved["item_stats"] is inline["item_stats"]

    handle_only = _static_payload(inline=False)
    resolved2, err2 = cache.resolve(_request(handle_only), handle_only)

    assert err2 is None
    assert np.array_equal(resolved2["item_stats"], inline["item_stats"])
    assert resolved2["timeline_grid"] == inline["timeline_grid"]
    assert resolved2["ref_arrays"] == inline["ref_arrays"]


def test_load_registry_payload_cache_settings_reads_and_clamps_env():
    low = load_registry_payload_cache_settings(env_get_fn=lambda _key, _default: "8")
    configured = load_registry_payload_cache_settings(env_get_fn=lambda _key, _default: "2048")
    invalid = load_registry_payload_cache_settings(env_get_fn=lambda _key, _default: "bad")

    assert low.max_entries == 64
    assert configured.max_entries == 2048
    assert invalid.max_entries == 1024


def test_registry_payload_cache_rejects_unknown_handle():
    cache = RegistryPayloadCache(max_entries=8)
    payload = _static_payload(handle=999, inline=False)

    resolved, err = cache.resolve(_request(payload), payload)

    assert resolved is payload
    assert err == "Unknown registry payload handle=999 for worker_id=11"


def test_gpu_executor_registry_payload_wrapper_delegates_to_cache_owner():
    ex = GpuExecutor()
    inline = _static_payload(inline=True)
    resolved, err = ex._resolve_registry_payload(_request(inline))

    assert err is None
    assert resolved["slot_count"] is inline["slot_count"]

    handle_only = _static_payload(inline=False)
    resolved2, err2 = ex._resolve_registry_payload(_request(handle_only))

    assert err2 is None
    assert np.array_equal(resolved2["base_fixed_stats"], inline["base_fixed_stats"])
