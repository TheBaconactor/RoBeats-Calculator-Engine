def test_build_persistence_entries_backfills_base_hitsim_delta(monkeypatch):
    # This unit test is intentionally CPU-only: we monkeypatch the summarizer
    # so we don't depend on real song data or Taichi/GPU paths.
    import gear_optimizer.solver.scoring.force_greats as fg
    from gear_optimizer.helpers.song_helpers.persistence import build_persistence_entries

    monkeypatch.setattr(fg, "summarize_hitsim_offset_delta_ms_for_base", lambda _song, _data, _refs: 7)

    db_payload = {
        "score": 123,
        "fg_score": 0,
        "gear": ["Top1Gear"],
        "minis": ["Top1Mini"],
        "details": {"Stats": {"Fever Fill Rate": 1, "Fever Time": 1}, "hitsim_offset_delta_ms": 0},
        "force": None,
    }

    # The union entry is missing base hitsim delta (None) and should be filled.
    loadout_entries = {
        "hash1": {
            "base_score": 100,
            "score": 100,
            "fg_score": 0,
            "gear": ["G1"],
            "minis": ["M1"],
            "details": {
                "Stats": {"Fever Fill Rate": 55, "Fever Time": 10},
                "ForceGreats": {"config": {}},
                "hitsim_offset_delta_ms": None,
            },
            "force": None,
            "eval_data": None,
        }
    }

    out = build_persistence_entries(
        db_payload,
        ga_candidates=[],
        loadout_entries=loadout_entries,
        build_details_fn=lambda _d: {},
        calc_song={"metadata": {"HumanHitSimApplied": True, "HumanHitSimApplyTo": "ALL"}},
        ref_arrays={},
    )

    match = [e for e in out if e.get("gear") == ["G1"] and e.get("minis") == ["M1"]]
    assert len(match) == 1
    assert match[0]["details"]["hitsim_offset_delta_ms"] == 7
