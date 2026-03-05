from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from gear_optimizer.solver.registry_solve_request import (
    build_registry_solve_request,
    dispatch_registry_solve,
    representative_genomes_from_plan,
)


class _FakeRegistry:
    def __init__(self) -> None:
        self.encoded = None

    def encode_population(self, genomes):
        self.encoded = list(genomes)
        n = len(self.encoded)
        return np.arange(n * 9, dtype=np.int32).reshape(n, 9)

    def to_gpu_arrays(self):
        return {
            "item_stats": np.arange(40, dtype=np.int16).reshape(4, 10),
            "slot_start": np.arange(9, dtype=np.int32),
            "slot_count": np.ones(9, dtype=np.int32),
        }


class _FakeFuture:
    def __init__(self, result):
        self._result = result

    def result(self):
        return self._result


class _FakeClient:
    def __init__(self) -> None:
        self.payload = None

    def submit_solve_genomes_from_registry(self, payload):
        self.payload = dict(payload)
        return SimpleNamespace(future=_FakeFuture(["ok"]))


def _make_plan():
    return SimpleNamespace(
        uncached_genomes=[
            [{"Name": "A"}] * 9,
            [{"Name": "B"}] * 9,
            [{"Name": "C"}] * 9,
        ],
        unique_members=[[1], [0, 2]],
        base_stats_fixed={
            "Perfect Points": 100,
            "Combo Multiplier": 200,
            "Fever Multiplier": 300,
            "Fever Time": 400,
            "Fever Fill Rate": 500,
            "Beat": 600,
            "Vibe": 700,
            "Rush": 800,
            "Flow": 900,
            "Chill": 1000,
        },
        cfg_data={
            "selected_color": "Beat",
            "user_ft": 1,
            "user_ff": 0,
            "user_pp": 0,
            "user_cm": 0,
            "user_fm": 0,
            "static_elem_input": 2,
        },
        calc_song={"metadata": {"Song Name": "unit"}},
        ref_arrays={"Perfect Points": np.arange(4, dtype=np.float64)},
        flags={"is_p_ft": 1, "is_s_ff": 1},
        sel_color="Beat",
    )


def test_representative_genomes_from_plan_uses_first_member_of_each_unique_group() -> None:
    plan = _make_plan()

    out = representative_genomes_from_plan(plan)

    assert out == [plan.uncached_genomes[1], plan.uncached_genomes[0]]


def test_build_registry_solve_request_and_dispatch_via_client() -> None:
    plan = _make_plan()
    registry = _FakeRegistry()
    client = _FakeClient()

    request = build_registry_solve_request(plan=plan, registry=registry, song_slot=7)

    assert request is not None
    assert registry.encoded == [plan.uncached_genomes[1], plan.uncached_genomes[0]]
    assert request.song_slot == 7
    assert request.population_indices.shape == (2, 9)
    assert request.base_fixed_stats.shape == (10,)
    assert int(request.base_fixed_stats[3]) == 397
    assert int(request.base_fixed_stats[5]) == 585

    out = dispatch_registry_solve(request, gpu_client=client)

    assert out == ["ok"]
    assert client.payload is not None
    assert int(client.payload["song_slot"]) == 7
    assert int(client.payload["is_p_ft"]) == 1
    assert int(client.payload["is_s_ff"]) == 1
