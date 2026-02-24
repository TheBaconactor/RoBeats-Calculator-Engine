from gear_optimizer.pipeline.song_processor import _attach_hitsim_delta_for_fg_variants


def test_attach_hitsim_delta_for_all_improved_fg_variants(monkeypatch):
    calls = {"count": 0}

    def _fake_summarize(_calc_song, _fg_data, _ref_arrays):
        calls["count"] += 1
        return 17

    monkeypatch.setattr(
        "gear_optimizer.solver.scoring.force_greats.summarize_hitsim_offset_delta_ms_for_fg_variant",
        _fake_summarize,
    )

    variants = [
        {
            "score": 100,
            "fg_score": 150,
            "data": {
                "Stats": {"Fever Fill Rate": 10, "Fever Time": 20},
                "ForceGreats": {"config": {"NonFever1": 1, "NonFever2": 0}},
                "details": {"ForceGreats": {"config": {"NonFever1": 1, "NonFever2": 0}}},
            },
        },
        {
            "score": 90,
            "fg_score": 140,
            "data": {
                "Stats": {"Fever Fill Rate": 10, "Fever Time": 20},
                "ForceGreats": {"config": {"NonFever1": 1, "NonFever2": 0}},
            },
        },
        {
            "score": 80,
            "fg_score": 120,
            "data": {
                "Stats": {"Fever Fill Rate": 10, "Fever Time": 20},
                "ForceGreats": {"config": {"NonFever1": 1}, "hitsim_offset_delta_ms": 9},
            },
        },
        {
            "score": 100,
            "fg_score": 100,
            "data": {
                "Stats": {"Fever Fill Rate": 10, "Fever Time": 20},
                "ForceGreats": {"config": {"NonFever1": 1}},
            },
        },
    ]

    _attach_hitsim_delta_for_fg_variants(calc_song={"song_data": {}}, fg_variants=variants, ref_arrays={"x": 1})

    assert variants[0]["data"]["ForceGreats"]["hitsim_offset_delta_ms"] == 17
    assert variants[0]["data"]["details"]["ForceGreats"]["hitsim_offset_delta_ms"] == 17
    assert variants[1]["data"]["ForceGreats"]["hitsim_offset_delta_ms"] == 17
    assert variants[2]["data"]["ForceGreats"]["hitsim_offset_delta_ms"] == 9
    assert "hitsim_offset_delta_ms" not in variants[3]["data"]["ForceGreats"]

    # Same (FF, FT, config) cache key should only invoke summarize once.
    assert calls["count"] == 1


def test_attach_hitsim_delta_materializes_missing_stats(monkeypatch):
    calls = {"count": 0}

    def _fake_apply_gems(_base_stats, _selected_element, _ft, _ff, _g_pp, _g_cm, _g_fm, _g_ov):
        return {"Fever Fill Rate": 9, "Fever Time": 13}

    def _fake_summarize(_calc_song, fg_data, _ref_arrays):
        calls["count"] += 1
        assert fg_data.get("Stats", {}).get("Fever Fill Rate") == 9
        assert fg_data.get("Stats", {}).get("Fever Time") == 13
        return -4

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
            "score": 100,
            "fg_score": 120,
            "data": {
                "BaseStats": {"Fever Fill Rate": 20, "Fever Time": 30},
                "GemCounts": {"Fever Fill Rate": 5, "Fever Time": 2, "Perfect Points": 0, "Combo Multiplier": 0},
                "FF": 5,
                "FT": 2,
                "Selected Element": "Rush",
                "ForceGreats": {"config": {"NonFever1": 1, "NonFever2": 0}},
            },
        }
    ]

    _attach_hitsim_delta_for_fg_variants(calc_song={"song_data": {}}, fg_variants=variants, ref_arrays={"x": 1})

    assert variants[0]["data"]["Stats"]["Fever Fill Rate"] == 9
    assert variants[0]["data"]["Stats"]["Fever Time"] == 13
    assert variants[0]["data"]["ForceGreats"]["hitsim_offset_delta_ms"] == -4
    assert calls["count"] == 1
