from gear_optimizer.helpers.song_helpers.loadout_builder import build_loadout_entries


def test_build_loadout_entries_can_skip_db_query(monkeypatch):
    calls = {"n": 0}

    def _fake_get_best_loadouts(*args, **kwargs):
        calls["n"] += 1
        return []

    monkeypatch.setattr(
        "gear_optimizer.helpers.song_helpers.loadout_builder.get_best_loadouts",
        _fake_get_best_loadouts,
    )

    ga_candidates = [
        {
            "Score": 777,
            "BaseScore": 888,
            "Gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
            "Minis": ["M1", "M2", "M3"],
            "Data": {"Stats": {"Perfect Points": 1}},
        }
    ]

    out = build_loadout_entries(
        found_song_name="db-query-gate-song",
        use_evo_db=True,
        ga_candidates=ga_candidates,
        db_loadouts_limit=51,
        gears_by_name={},
        minis_by_name={},
        build_details_fn=lambda data: {"Stats": (data or {}).get("Stats", {})},
        allow_db_query=False,
    )

    assert calls["n"] == 0
    assert len(out) == 1
    entry = next(iter(out.values()))
    assert int(entry["score"]) == 888
