from gear_optimizer.pipeline.song_processor import _attach_hitsim_delta_for_fg_variants


def test_attach_hitsim_delta_for_all_improved_fg_variants(monkeypatch):
    calls = {"count": 0}

    def _fake_summarize(_calc_song, _fg_data, _ref_arrays):
        calls["count"] += 1
        existing = (_fg_data.get("ForceGreats") or {}).get("hitsim_offset_delta_ms")
        try:
            existing_i = int(existing) if existing is not None else None
        except Exception:
            existing_i = None
        base = existing_i if existing_i is not None else 17
        return [base, base + 1]

    monkeypatch.setattr(
        "gear_optimizer.solver.scoring.force_greats.summarize_hitsim_offset_deltas_ms_for_fg_variant",
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

    assert variants[0]["data"]["ForceGreats"]["hitsim_offset_deltas_ms"] == [17, 18]
    assert variants[0]["data"]["details"]["ForceGreats"]["hitsim_offset_deltas_ms"] == [17, 18]
    assert variants[1]["data"]["ForceGreats"]["hitsim_offset_deltas_ms"] == [17, 18]
    assert variants[2]["data"]["ForceGreats"]["hitsim_offset_deltas_ms"] == [9, 10]
    assert "hitsim_offset_delta_ms" not in variants[3]["data"]["ForceGreats"]
    assert "hitsim_offset_deltas_ms" not in variants[3]["data"]["ForceGreats"]
    assert "hitsim_offset_delta_ms" not in variants[0]["data"]["ForceGreats"]
    assert "hitsim_offset_delta_ms" not in variants[0]["data"]["details"]["ForceGreats"]
    assert "hitsim_offset_delta_ms" not in variants[1]["data"]["ForceGreats"]
    assert "hitsim_offset_delta_ms" not in variants[2]["data"]["ForceGreats"]

    # Same (FF, FT, config) cache key should only invoke summarize once.
    assert calls["count"] == 2


def test_attach_hitsim_delta_materializes_missing_stats(monkeypatch):
    calls = {"count": 0}

    def _fake_apply_gems(_base_stats, _selected_element, _ft, _ff, _g_pp, _g_cm, _g_fm, _g_ov):
        return {"Fever Fill Rate": 9, "Fever Time": 13}

    def _fake_summarize(_calc_song, fg_data, _ref_arrays):
        calls["count"] += 1
        assert fg_data.get("Stats", {}).get("Fever Fill Rate") == 9
        assert fg_data.get("Stats", {}).get("Fever Time") == 13
        return [-4, -3]

    monkeypatch.setattr(
        "gear_optimizer.helpers.song_helpers.force_greats.result_application.apply_gems_to_base_fast",
        _fake_apply_gems,
    )
    monkeypatch.setattr(
        "gear_optimizer.solver.scoring.force_greats.summarize_hitsim_offset_deltas_ms_for_fg_variant",
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
    assert variants[0]["data"]["ForceGreats"]["hitsim_offset_deltas_ms"] == [-4, -3]
    assert "hitsim_offset_delta_ms" not in variants[0]["data"]["ForceGreats"]
    assert calls["count"] == 1
