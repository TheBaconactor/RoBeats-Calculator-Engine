from gear_optimizer.solver.native_inflight_orchestrator import _attach_hitsim_delta_for_fg_variant


def test_native_inflight_attach_hitsim_delta_for_all_improved_variants(monkeypatch):
    calls = {"count": 0}

    def _fake_summarize(_calc_song, _fg_data, _ref_arrays):
        calls["count"] += 1
        return 11

    monkeypatch.setattr(
        "gear_optimizer.solver.scoring.force_greats.summarize_hitsim_offset_delta_ms_for_fg_variant",
        _fake_summarize,
    )

    variants = [
        {
            "score": 100,
            "fg_score": 130,
            "data": {
                "Stats": {"Fever Fill Rate": 10, "Fever Time": 20},
                "ForceGreats": {"config": {"NonFever1": 1, "NonFever2": 0}},
            },
        },
        {
            "score": 90,
            "fg_score": 120,
            "data": {
                "Stats": {"Fever Fill Rate": 10, "Fever Time": 20},
                "ForceGreats": {"config": {"NonFever1": 1, "NonFever2": 0}},
            },
        },
        {
            "score": 80,
            "fg_score": 80,
            "data": {
                "Stats": {"Fever Fill Rate": 10, "Fever Time": 20},
                "ForceGreats": {"config": {"NonFever1": 1, "NonFever2": 0}},
            },
        },
        {
            "score": 70,
            "fg_score": 100,
            "data": {
                "Stats": {"Fever Fill Rate": 11, "Fever Time": 21},
                "ForceGreats": {"config": {"NonFever1": 1}, "hitsim_offset_delta_ms": 5},
            },
        },
    ]

    _attach_hitsim_delta_for_fg_variant(calc_song={"song_data": {}}, fg_variants=variants, ref_arrays={"x": 1})

    assert variants[0]["data"]["ForceGreats"]["hitsim_offset_delta_ms"] == 11
    assert variants[1]["data"]["ForceGreats"]["hitsim_offset_delta_ms"] == 11
    assert "hitsim_offset_delta_ms" not in variants[2]["data"]["ForceGreats"]
    assert variants[3]["data"]["ForceGreats"]["hitsim_offset_delta_ms"] == 5
    assert calls["count"] == 1


def test_native_inflight_attach_hitsim_delta_materializes_stats(monkeypatch):
    calls = {"count": 0}

    def _fake_apply_gems(_base_stats, _selected_element, _ft, _ff, _g_pp, _g_cm, _g_fm, _g_ov):
        return {"Fever Fill Rate": 6, "Fever Time": 14}

    def _fake_summarize(_calc_song, fg_data, _ref_arrays):
        calls["count"] += 1
        assert fg_data.get("Stats", {}).get("Fever Fill Rate") == 6
        assert fg_data.get("Stats", {}).get("Fever Time") == 14
        return -2

    monkeypatch.setattr(
        "gear_optimizer.helpers.song_helpers.force_greats.result_application.apply_gems_to_base_fast",
        _fake_apply_gems,
    )
    monkeypatch.setattr(
        "gear_optimizer.solver.scoring.force_greats.summarize_hitsim_offset_delta_ms_for_fg_variant",
        _fake_summarize,
    )

    variants = [
        {
            "score": 50,
            "fg_score": 70,
            "data": {
                "BaseStats": {"Fever Fill Rate": 12, "Fever Time": 22},
                "GemCounts": {
                    "Fever Fill Rate": 3,
                    "Fever Time": 1,
                    "Perfect Points": 0,
                    "Combo Multiplier": 0,
                    "Fever Multiplier": 0,
                    "Element": 0,
                },
                "FF": 3,
                "FT": 1,
                "Selected Element": "Rush",
                "ForceGreats": {"config": {"NonFever1": 1}},
            },
        }
    ]

    _attach_hitsim_delta_for_fg_variant(calc_song={"song_data": {}}, fg_variants=variants, ref_arrays={"x": 1})

    assert variants[0]["data"]["Stats"]["Fever Fill Rate"] == 6
    assert variants[0]["data"]["Stats"]["Fever Time"] == 14
    assert variants[0]["data"]["ForceGreats"]["hitsim_offset_delta_ms"] == -2
    assert calls["count"] == 1
