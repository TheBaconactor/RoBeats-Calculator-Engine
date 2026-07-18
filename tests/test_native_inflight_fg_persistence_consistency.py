import json

from tests.native_song_factory import make_native_song


def _stats(perfect_points: int) -> dict:
    return {
        "Perfect Points": int(perfect_points),
        "Combo Multiplier": 100,
        "Fever Multiplier": 100,
        "Fever Fill Rate": 100,
        "Fever Time": 100,
        "Rush": 100,
        "Flow": 100,
        "Beat": 100,
        "Vibe": 100,
        "Chill": 100,
    }


def _song_with_variants(variants: list[dict]):
    return make_native_song(
        fg_variants=variants,
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        effective_difficulty="Hard",
    )


def _force_payload(*, base_score=1000, fg_score=1200, base_stats=None, stats=None, include_surface=True):
    payload = {
        "BaseScore": int(base_score),
        "Score": int(fg_score),
        "FT": 9,
        "FF": 18,
        "GemCounts": {"Perfect Points": 1},
        "BaseStats": dict(base_stats or _stats(100)),
        "Selected Element": "Rush",
        "ForceGreats": {},
    }
    if include_surface:
        payload["response_surface"] = [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0]
    if stats is not None:
        payload["Stats"] = dict(stats)
    return payload


def test_native_inflight_fg_persist_entries_use_direct_variant_payload():
    from gear_optimizer.solver.native_inflight_fg_payload import build_fg_persist_entries

    # BaseStats IS the post-gem visible row; the persisted visible Stats equals it.
    visible = _stats(555)
    fake_song = _song_with_variants(
        [
            {
                "_is_ga": True,
                "score": 950,
                "base_score": 1000,
                "fg_score": 1200,
                "gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
                "minis": ["M1", "M2", "M3"],
                "data": _force_payload(base_stats=visible, stats=None),
            }
        ]
    )

    entries = build_fg_persist_entries(fake_song)

    assert len(entries) == 1
    assert entries[0]["score"] == 1000
    assert entries[0]["fg_score"] == 1200
    assert entries[0]["gear"] == ["G1", "G2", "G3", "G4", "G5", "G6"]
    assert entries[0]["minis"] == ["M1", "M2", "M3"]
    assert entries[0]["details"]["Stats"] == visible
    assert entries[0]["force"]["Stats"] == visible
    assert entries[0]["force"]["response_surface"] == [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0]
    assert "config" not in (entries[0]["force"].get("ForceGreats") or {})


def test_native_inflight_fg_persist_entries_treat_base_stats_as_post_gem_visible_row():
    # BaseStats is already the post-gem visible row: persistence must surface it
    # verbatim and must NOT re-apply gems on top (the 2026-07-11 Canon-in-D
    # double-count regression, where Vibe 1018 wrongly became 1432).
    from gear_optimizer.solver.native_inflight_fg_payload import build_fg_persist_entries
    from gear_optimizer.solver.scoring.stats_ops import apply_gems_to_base_stats

    visible = _stats(100)
    doubled = apply_gems_to_base_stats(visible, "Rush", 9, 18, 1, 0, 0, 0)
    assert doubled != visible  # sanity: re-applying gems WOULD change the row
    fake_song = _song_with_variants(
        [
            {
                "_is_ga": True,
                "score": 1000,
                "base_score": 1000,
                "fg_score": 1200,
                "gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
                "minis": ["M1", "M2", "M3"],
                "data": _force_payload(base_stats=visible, stats=None),
            }
        ]
    )

    entries = build_fg_persist_entries(fake_song)

    assert len(entries) == 1
    assert entries[0]["details"]["Stats"] == visible
    assert entries[0]["force"]["Stats"] == visible
    assert entries[0]["details"]["Stats"] != doubled
    assert entries[0]["force"]["Stats"] != doubled


def test_native_inflight_fg_persist_entries_accept_force_surface_when_data_is_not_force():
    from gear_optimizer.solver.native_inflight_fg_payload import build_fg_persist_entries

    # `data` is not a force payload, so the force surface is used; its BaseStats is
    # the post-gem visible row that gets persisted verbatim.
    visible = _stats(777)
    fake_song = _song_with_variants(
        [
            {
                "_is_ga": True,
                "score": 1000,
                "base_score": 1000,
                "fg_score": 1200,
                "gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
                "minis": ["M1", "M2", "M3"],
                "data": {"Stats": visible},
                "force": _force_payload(base_stats=visible, stats=None),
            }
        ]
    )

    entries = build_fg_persist_entries(fake_song)

    assert len(entries) == 1
    assert entries[0]["fg_score"] == 1200
    assert entries[0]["details"]["Stats"] == visible
    assert entries[0]["force"]["response_surface"] == [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0]


def test_native_inflight_fg_persist_entries_drop_non_force_variants():
    from gear_optimizer.solver.native_inflight_fg_payload import build_fg_persist_entries

    fake_song = _song_with_variants(
        [
            {
                "_is_ga": True,
                "score": 1000,
                "base_score": 1000,
                "fg_score": 1200,
                "gear": ["G1"],
                "minis": ["M1"],
                "data": _force_payload(include_surface=False),
            }
        ]
    )

    assert build_fg_persist_entries(fake_song) == []


def test_native_inflight_fg_persist_entries_save_direct_fg_row(tmp_path, monkeypatch):
    from gear_optimizer.data.database import get_db_connection, init_db, save_loadouts_batch
    from gear_optimizer.solver.native_inflight_fg_payload import build_fg_persist_entries

    db_path = tmp_path / "native_fg_direct.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))
    init_db()

    song_name = "pytest_native_inflight_fg_direct"
    entries = build_fg_persist_entries(
        _song_with_variants(
            [
                {
                    "_is_ga": True,
                    "score": 1000,
                    "base_score": 1000,
                    "fg_score": 1200,
                    "gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
                    "minis": ["M1", "M2", "M3"],
                    "data": _force_payload(),
                }
            ]
        )
    )

    save_loadouts_batch(song_name, entries)

    with get_db_connection(str(db_path)) as conn:
        row = conn.execute(
            "SELECT score, fg_score, force_details_json FROM team_buff_fg_loadouts "
            "WHERE song_name=? AND team_buff='T5'",
            (song_name,),
        ).fetchone()

    assert row is not None
    assert int(row["score"]) == 1000
    assert int(row["fg_score"]) == 1200
    force = json.loads(row["force_details_json"])
    assert force["response_surface"] == [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0]
    assert "config" not in (force.get("ForceGreats") or {})
