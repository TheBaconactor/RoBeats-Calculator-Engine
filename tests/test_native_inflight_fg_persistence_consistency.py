import json

from gear_optimizer.solver.native_inflight_config import make_native_song


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


def _force_payload(*, base_score=1000, fg_score=1200, base_stats=None, stats=None, config=None):
    payload = {
        "BaseScore": int(base_score),
        "Score": int(fg_score),
        "FT": 9,
        "FF": 18,
        "GemCounts": {"Perfect Points": 1},
        "BaseStats": dict(base_stats or _stats(100)),
        "Selected Element": "Rush",
        "ForceGreats": {"config": dict({"NonFever1": 1} if config is None else config)},
    }
    if stats is not None:
        payload["Stats"] = dict(stats)
    return payload


def test_native_inflight_fg_persist_entries_use_direct_variant_payload():
    from gear_optimizer.solver.native_inflight_fg_payload import build_fg_persist_entries

    base_stats = _stats(100)
    fg_stats = _stats(999)
    fake_song = _song_with_variants(
        [
            {
                "_is_ga": True,
                "score": 950,
                "base_score": 1000,
                "fg_score": 1200,
                "gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
                "minis": ["M1", "M2", "M3"],
                "data": _force_payload(base_stats=base_stats, stats=fg_stats),
            }
        ]
    )

    entries = build_fg_persist_entries(fake_song)

    assert len(entries) == 1
    assert entries[0]["score"] == 1000
    assert entries[0]["fg_score"] == 1200
    assert entries[0]["gear"] == ["G1", "G2", "G3", "G4", "G5", "G6"]
    assert entries[0]["minis"] == ["M1", "M2", "M3"]
    assert entries[0]["details"]["Stats"] == fg_stats
    assert entries[0]["force"]["Stats"] == fg_stats
    assert (entries[0]["force"].get("ForceGreats") or {}).get("config") == {"NonFever1": 1}


def test_native_inflight_fg_persist_entries_materialize_stats_from_base_stats():
    from gear_optimizer.helpers.song_helpers.force_greats.result_application import apply_gems_to_base_fast
    from gear_optimizer.solver.native_inflight_fg_payload import build_fg_persist_entries

    base_stats = _stats(100)
    expected_stats = apply_gems_to_base_fast(
        base_stats,
        "Rush",
        9,
        18,
        1,
        0,
        0,
        0,
    )
    fake_song = _song_with_variants(
        [
            {
                "_is_ga": True,
                "score": 1000,
                "base_score": 1000,
                "fg_score": 1200,
                "gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
                "minis": ["M1", "M2", "M3"],
                "data": _force_payload(base_stats=base_stats, stats=None),
            }
        ]
    )

    entries = build_fg_persist_entries(fake_song)

    assert len(entries) == 1
    assert entries[0]["details"]["Stats"] == expected_stats
    assert entries[0]["force"]["Stats"] == expected_stats


def test_native_inflight_fg_persist_entries_accept_force_surface_when_data_is_not_force():
    from gear_optimizer.solver.native_inflight_fg_payload import build_fg_persist_entries

    base_stats = _stats(100)
    fg_stats = _stats(999)
    fake_song = _song_with_variants(
        [
            {
                "_is_ga": True,
                "score": 1000,
                "base_score": 1000,
                "fg_score": 1200,
                "gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
                "minis": ["M1", "M2", "M3"],
                "data": {"Stats": base_stats},
                "force": _force_payload(base_stats=base_stats, stats=fg_stats),
            }
        ]
    )

    entries = build_fg_persist_entries(fake_song)

    assert len(entries) == 1
    assert entries[0]["fg_score"] == 1200
    assert entries[0]["details"]["Stats"] == fg_stats
    assert (entries[0]["force"].get("ForceGreats") or {}).get("config") == {"NonFever1": 1}


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
                "data": _force_payload(config={}),
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
    assert (force.get("ForceGreats") or {}).get("config") == {"NonFever1": 1}
