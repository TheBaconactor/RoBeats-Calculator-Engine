def test_build_persistence_entries_backfills_base_hitsim_delta(monkeypatch):
    # This unit test is intentionally CPU-only: we monkeypatch the summarizer
    # so we don't depend on real song data or Taichi/GPU paths.
    import gear_optimizer.solver.scoring.force_greats as fg
    from gear_optimizer.helpers.song_helpers.persistence import build_persistence_entries

    monkeypatch.setattr(fg, "summarize_hitsim_offset_deltas_ms_for_base", lambda _song, _data, _refs: [7, 9])

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
    # Derived HitSim per-window deltas are computed on demand (not persisted/backfilled by default).
    assert match[0]["details"].get("hitsim_offset_deltas_ms") is None
    assert "hitsim_offset_delta_ms" not in match[0]["details"]


def test_build_persistence_entries_backfills_top1_hitsim_deltas_when_missing(monkeypatch):
    import gear_optimizer.solver.scoring.force_greats as fg
    from gear_optimizer.helpers.song_helpers.persistence import build_persistence_entries

    monkeypatch.setattr(fg, "summarize_hitsim_offset_deltas_ms_for_base", lambda _song, _data, _refs: [3, 4])

    db_payload = {
        "score": 123,
        "fg_score": 0,
        "gear": ["Top1Gear"],
        "minis": ["Top1Mini"],
        "details": {
            "Stats": {"Fever Fill Rate": 1, "Fever Time": 1},
            "hitsim_offset_delta_ms": None,
            "hitsim_offset_deltas_ms": None,
        },
        "force": None,
    }

    out = build_persistence_entries(
        db_payload,
        ga_candidates=[],
        loadout_entries={},
        build_details_fn=lambda _d: {},
        calc_song={"metadata": {"HumanHitSimApplied": True, "HumanHitSimApplyTo": "ALL"}},
        ref_arrays={},
    )

    assert out
    assert out[0]["gear"] == ["Top1Gear"]
    assert out[0]["minis"] == ["Top1Mini"]
    assert out[0]["details"].get("hitsim_offset_deltas_ms") is None
    assert "hitsim_offset_delta_ms" not in out[0]["details"]


def test_build_persistence_entries_backfills_fg_hitsim_deltas_for_retained_rows(monkeypatch):
    import gear_optimizer.solver.scoring.force_greats as fg
    from gear_optimizer.helpers.song_helpers.persistence import build_persistence_entries

    calls = {"count": 0}

    def _fake_summarize(_song, fg_data, _refs):
        calls["count"] += 1
        assert (fg_data.get("ForceGreats") or {}).get("config") == {"NonFever1": 1}
        assert (fg_data.get("Stats") or {}).get("Fever Fill Rate") == 55
        assert (fg_data.get("Stats") or {}).get("Fever Time") == 10
        return [9, 8, 7]

    monkeypatch.setattr(fg, "summarize_hitsim_offset_deltas_ms_for_fg_variant", _fake_summarize)

    db_payload = {
        "score": 123,
        "fg_score": 0,
        "gear": ["Top1Gear"],
        "minis": ["Top1Mini"],
        "details": {"Stats": {"Fever Fill Rate": 1, "Fever Time": 1}},
        "force": None,
    }

    loadout_entries = {
        "hash1": {
            "base_score": 100,
            "score": 100,
            "fg_score": 150,
            "gear": ["G1"],
            "minis": ["M1"],
            "details": {
                "Stats": {"Fever Fill Rate": 55, "Fever Time": 10},
            },
            "force": {"ForceGreats": {"config": {"NonFever1": 1}, "hitsim_offset_delta_ms": 123}},
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
    force_out = match[0].get("force") or {}
    assert (force_out.get("ForceGreats") or {}).get("hitsim_offset_deltas_ms") is None
    assert (force_out.get("ForceGreats") or {}).get("hitsim_offset_delta_ms") is None
    assert calls["count"] == 0


def test_build_persistence_entries_persists_compact_hitsim_context():
    from gear_optimizer.helpers.song_helpers.persistence import build_persistence_entries

    db_payload = {
        "score": 123,
        "fg_score": 0,
        "gear": ["Top1Gear"],
        "minis": ["Top1Mini"],
        "details": {"Stats": {"Fever Fill Rate": 1, "Fever Time": 1}},
        "force": None,
    }

    out = build_persistence_entries(
        db_payload,
        ga_candidates=[],
        loadout_entries={},
        build_details_fn=lambda _d: {},
        calc_song={
            "metadata": {
                "HumanHitSimApplied": True,
                "HumanHitSimApplyTo": "ALL",
                "HumanHitSimSeed": 4242,
                "HumanHitSimDistribution": "uniform",
                "HumanHitSimGreatMode": "late",
            }
        },
        ref_arrays=None,
    )

    assert out
    assert out[0]["details"]["hs"] == [4242, 1, 0, 0]
