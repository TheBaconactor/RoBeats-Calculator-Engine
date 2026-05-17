from __future__ import annotations

import sys
from concurrent.futures import Future
from types import SimpleNamespace


def test_native_force_greats_uses_full_section_count_surface() -> None:
    from gear_optimizer.solver.native_force_greats import _counts_list

    counts = _counts_list(num_sections=2, non_fever_base=100)

    assert len(counts) == 51 * 26
    assert (50, 25) in counts


def test_native_force_greats_materializes_forced_counts_from_fp_targets() -> None:
    from gear_optimizer.solver.native_force_greats import _materialize_best

    class FakeScorer:
        def get_fever_params(self, ft_stat: int, ff_stat: int):
            assert ft_stat == 0
            assert ff_stat == 0
            return 20, 0.0, 0, 10.2

    out = _materialize_best(
        {
            "base_score": 100,
            "final_score": 120,
            "cfg_idx": 0,
            "FT": 0,
            "FF": 0,
            "gem_counts": {},
        },
        counts=[(3, 0)],
        num_sections=2,
        non_fever_base=20,
        base_stats={"Fever Time": 0, "Fever Fill Rate": 0},
        fg_scorer=FakeScorer(),
    )

    assert out is not None
    assert out["fp_targets"] == [3, 0]
    assert out["config_counts"] == [6, 0]
    assert out["config_dict"] == {"NonFever1": 6, "NonFever2": 0}


def test_native_ga_force_greats_materializes_retained_variant(monkeypatch) -> None:
    from gear_optimizer.helpers.song_helpers.force_greats import native_ga_variants

    calls: dict[str, object] = {}

    def _fake_batch(**kwargs):
        calls.update(kwargs)
        return [
            {
                "base_score": 100,
                "final_score": 120,
                "config_dict": {"NonFever1": 1},
                "config_counts": [1],
                "gem_counts": {"Perfect Points": 1, "Combo Multiplier": 0, "Fever Multiplier": 0, "Element": 0},
                "FT": 0,
                "FF": 0,
            }
        ], {"gpu_batches": 1}

    monkeypatch.setattr(native_ga_variants, "solve_native_force_greats_gpu_batch", _fake_batch)

    loadout_entries: dict[str, dict] = {}
    candidate = {
        "BaseScore": 100,
        "Gear": ["G1"],
        "Minis": ["M1"],
        "Data": {
            "BaseStats": {
                "Perfect Points": 10,
                "Combo Multiplier": 0,
                "Fever Multiplier": 0,
                "Fever Time": 0,
                "Fever Fill Rate": 0,
                "Rush": 0,
                "Flow": 0,
            },
            "Selected Element": "Rush",
            "FT": 0,
            "FF": 0,
        },
    }

    records = native_ga_variants.build_native_fg_candidate_records(
        loadout_entries=loadout_entries,
        ga_candidates=[candidate],
        default_selected_color="Rush",
        primary_color="Rush",
        secondary_color="Flow",
    )
    variants = native_ga_variants.score_native_fg_candidate_records(
        records=records,
        loadout_entries=loadout_entries,
        calc_song={"metadata": {"Primary Color": "Rush", "Secondary Color": "Flow"}, "song_data": {}},
        ref_arrays={},
        search_radius=-1,
        gpu_client="owner-client",
    )

    assert calls["center_fts"] == [None]
    assert calls["center_ffs"] == [None]
    assert calls["search_radius"] is None
    assert calls["gpu_client"] == "owner-client"
    assert int(variants[0]["fg_score"]) == 120
    assert int(variants[0]["base_score"]) == 100
    assert variants[0]["data"]["ForceGreats"]["config"] == {"NonFever1": 1}
    assert int(candidate["fg_score"]) == 120
    assert loadout_entries


def test_native_force_greats_gpu_batch_uses_gpu_owner_client(monkeypatch) -> None:
    from gear_optimizer.solver import native_force_greats

    monkeypatch.setitem(
        sys.modules,
        "gear_optimizer.solver.taichi_gem.fields",
        SimpleNamespace(MAX_GENOMES=16),
    )
    monkeypatch.setitem(
        sys.modules,
        "gear_optimizer.solver.taichi_gem.force_greats.fields",
        SimpleNamespace(FG_MAX_FTFF=4096),
    )
    monkeypatch.setattr(native_force_greats, "_section_summary", lambda *_args, **_kwargs: (1, 1))
    monkeypatch.setattr(native_force_greats, "_counts_list", lambda *_args, **_kwargs: [(1,)])
    monkeypatch.setattr(native_force_greats, "_ftff_pairs", lambda *_args, **_kwargs: [(0, 0)])
    monkeypatch.setattr(native_force_greats, "_genome_stats_array", lambda *_args, **_kwargs: "genome-stats")
    monkeypatch.setattr(native_force_greats, "create_scorer_from_calc_song", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(native_force_greats, "_materialize_best", lambda best, **_kwargs: dict(best))

    class EmptyCandidateCache:
        def get(self, _key):
            return None

        def put(self, _key, _value):
            return False

    monkeypatch.setattr(native_force_greats.FgCandidateCacheShard, "load", lambda *_args, **_kwargs: EmptyCandidateCache())

    class FakeGpuClient:
        def __init__(self) -> None:
            self.solve_calls = []

        def submit_solve_force_greats_finder(self, *args, **kwargs):
            self.solve_calls.append((args, kwargs))
            future = Future()
            future.set_result([{"final_score": 120, "FT": 0, "FF": 0}])
            return SimpleNamespace(future=future)

    gpu_client = FakeGpuClient()

    results, stats = native_force_greats.solve_native_force_greats_gpu_batch(
        base_stats_list=[{"Fever Time": 0, "Fever Fill Rate": 0}],
        calc_song={
            "metadata": {"Primary Color": "Rush", "Secondary Color": "Flow", "Long Notes": 0, "Last Note Time": 0.0},
            "song_data": {"timestamps": [0.0]},
        },
        ref_arrays={
            "Perfect Points": [1.0],
            "Combo Multiplier": [1.0],
            "Fever Multiplier": [1.0],
            "Fever Fill Rate": [1.0],
            "Fever Time": [1.0],
        },
        selected_colors=["Rush"],
        center_fts=[0],
        center_ffs=[0],
        search_radius=0,
        gpu_client=gpu_client,
    )

    assert len(gpu_client.solve_calls) == 1
    assert results == [{"final_score": 120, "FT": 0, "FF": 0}]
    assert stats["gpu_batches"] == 1
