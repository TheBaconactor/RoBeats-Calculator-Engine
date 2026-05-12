from __future__ import annotations


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

    variants = native_ga_variants.score_native_ga_force_greats(
        loadout_entries=loadout_entries,
        ga_candidates=[candidate],
        calc_song={"metadata": {"Primary Color": "Rush", "Secondary Color": "Flow"}, "song_data": {}},
        ref_arrays={},
        default_selected_color="Rush",
        primary_color="Rush",
        secondary_color="Flow",
        search_radius=-1,
    )

    assert calls["center_fts"] == [None]
    assert calls["center_ffs"] == [None]
    assert calls["search_radius"] is None
    assert int(variants[0]["fg_score"]) == 120
    assert int(variants[0]["base_score"]) == 100
    assert variants[0]["data"]["ForceGreats"]["config"] == {"NonFever1": 1}
    assert int(candidate["fg_score"]) == 120
    assert loadout_entries
