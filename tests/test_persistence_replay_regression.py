from __future__ import annotations

import json


def _make_entry(*, gear: list[str], minis: list[str], score: int, fg_score: int = 0, tag: str = "") -> dict:
    details = {"tag": tag} if tag else {}
    return {
        "gear": list(gear),
        "minis": list(minis),
        "score": int(score),
        "fg_score": int(fg_score),
        "details": details,
        "force": None,
    }


def test_build_persistence_entries_routes_retained_surface_through_shared_canonicalizer(monkeypatch):
    from gear_optimizer.helpers.song_helpers.persistence_canon import build_persistence_entries

    captured: dict[str, object] = {}

    def fake_build_team_buff_tier_db_batches(*, entries, calc_song, ref_arrays, cfg_dict, limit, tiers, **_kwargs):
        captured["entries"] = [dict(entry) for entry in entries]
        captured["calc_song"] = calc_song
        captured["ref_arrays"] = ref_arrays
        captured["cfg_dict"] = cfg_dict
        return {
            "T5": [
                {
                    "gear": ["TopGear"],
                    "minis": ["TopMini"],
                    "score": 500,
                    "fg_score": 0,
                    "details": {"tag": "top1", "Stats": {"Rush": 1}},
                    "force": None,
                },
                {
                    "gear": ["G1"],
                    "minis": ["M1"],
                    "score": 321,
                    "fg_score": 654,
                    "fg_base_score": 300,
                    "details": {"tag": "sentinel", "Stats": {"Rush": 2}},
                    "force": {"ForceGreats": {"config": {"NonFever1": 1}}},
                },
            ]
        }

    monkeypatch.setattr(
        "gear_optimizer.helpers.song_helpers.persistence_canon.build_team_buff_tier_db_batches",
        fake_build_team_buff_tier_db_batches,
    )
    monkeypatch.setattr(
        "gear_optimizer.helpers.song_helpers.persistence_canon.canonicalize_authoritative_fg_entries",
        lambda entries, *, calc_song, ref_arrays: list(entries),
    )

    db_payload = {
        "score": 500,
        "gear": ["TopGear"],
        "minis": ["TopMini"],
        "details": {"tag": "top1", "Stats": {"Rush": 1}},
        "force": None,
    }
    loadout_entries = {
        "retained-hash": {
            **_make_entry(gear=["G1"], minis=["M1"], score=11, tag="retained"),
            "details": {"tag": "retained", "Stats": {"Rush": 2}},
        }
    }

    out = build_persistence_entries(
        db_payload,
        ga_candidates=[],
        loadout_entries=loadout_entries,
        build_details_fn=lambda _data: {"tag": "top1"},
        calc_song={"metadata": {"Primary Color": "Rush", "Secondary Color": "Flow"}},
        ref_arrays={"Perfect Points": [0]},
        cfg_dict={
            "IterationEngine": {},
            "TeamContributionBuffConstant": {"TeamBuff": "T5"},
        },
    )

    row = next(e for e in out if e.get("gear") == ["G1"] and e.get("minis") == ["M1"])
    assert int(row.get("score", 0) or 0) == 321
    assert int(row.get("fg_score", 0) or 0) == 654
    assert int(row.get("fg_base_score", 0) or 0) == 300
    assert (row.get("details") or {}).get("tag") == "sentinel"
    assert isinstance(row.get("force"), dict)
    assert captured["calc_song"]["metadata"]["Primary Color"] == "Rush"
    assert captured["ref_arrays"] == {"Perfect Points": [0]}
    assert captured["cfg_dict"]["TeamContributionBuffConstant"]["TeamBuff"] == "T5"
    assert any(
        entry.get("gear") == ["G1"] and entry.get("minis") == ["M1"]
        for entry in captured["entries"]
    )


def test_team_buff_replay_keeps_force_origin_when_base_duplicate_follows(monkeypatch):
    from gear_optimizer.helpers.song_helpers.team_buff_tiers import build_team_buff_tier_db_batches

    stats = {
        "Perfect Points": 100,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Rush": 200,
        "Flow": 0,
        "Beat": 0,
        "Vibe": 0,
        "Chill": 0,
    }
    gear = ["G1", "G2", "G3", "G4", "G5", "G6"]
    minis = ["M1", "M2", "M3"]
    force_payload = {
        "BaseScore": 100,
        "Score": 120,
        "BaseStats": dict(stats),
        "GemCounts": {},
        "Selected Element": "Rush",
        "ForceGreats": {"config": {"NonFever1": 1}, "final_score": 120},
    }
    force_entry = {
        "loadout_hash": "same-loadout",
        "score": 100,
        "fg_score": 120,
        "fg_base_score": 100,
        "gear": list(gear),
        "minis": list(minis),
        "details": {"Stats": dict(stats), "SelectedElement": "Rush"},
        "force": force_payload,
    }
    base_duplicate = {
        "loadout_hash": "same-loadout",
        "score": 100,
        "fg_score": 0,
        "gear": list(gear),
        "minis": list(minis),
        "details": {"Stats": dict(stats), "SelectedElement": "Rush"},
        "force": None,
    }

    def fake_compute_team_buff_tier_leaderboards(**_kwargs):
        return {
            "meta": {"base_team_buff": "T5", "team_color": "Rush", "primary_color": "Rush", "secondary_color": "Flow"},
            "tiers": {
                "T5": {
                    "base_top51": [
                        {
                            "loadout_hash": "same-loadout",
                            "gear": list(gear),
                            "minis": list(minis),
                            "score": 100,
                            "fg_score": 120,
                        }
                    ],
                    "fg_top51": [
                        {
                            "loadout_hash": "same-loadout",
                            "gear": list(gear),
                            "minis": list(minis),
                            "score": 100,
                            "fg_base_score": 100,
                            "fg_score": 120,
                            "force_config": {"NonFever1": 1},
                        }
                    ],
                }
            },
            # The graft fails loud unless every hashed (tier, loadout) carries its re-solved
            # witness. Base witness (legal gems: FT + FF + PP + CM + FM + Element == 90).
            "resolved_base_by_tier_hash": {
                "T5": {
                    "same-loadout": {
                        "Stats": dict(stats),
                        "GemCounts": {
                            "Perfect Points": 40,
                            "Combo Multiplier": 0,
                            "Fever Multiplier": 0,
                            "Element": 40,
                        },
                        "FT": 5,
                        "FF": 5,
                        "Score": 100,
                        "Selected Element": "Rush",
                    }
                }
            },
            # The served FG force IS this re-solved witness: it must carry the FG origin
            # (config + Score) the assertion checks survives the base-duplicate dedupe.
            "resolved_fg_force_by_tier_hash": {
                "T5": {
                    "same-loadout": {
                        "Score": 120,
                        "BaseScore": 100,
                        "Stats": dict(stats),
                        "BaseStats": dict(stats),
                        "GemCounts": {
                            "Perfect Points": 40,
                            "Combo Multiplier": 0,
                            "Fever Multiplier": 0,
                            "Element": 40,
                        },
                        "Selected Element": "Rush",
                        "ForceGreats": {"config": {"NonFever1": 1}, "final_score": 120},
                        "response_surface": [1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
                    }
                }
            },
        }

    monkeypatch.setattr(
        "gear_optimizer.helpers.song_helpers.team_buff_tiers.compute_team_buff_tier_leaderboards",
        fake_compute_team_buff_tier_leaderboards,
    )

    rows = build_team_buff_tier_db_batches(
        entries=[force_entry, base_duplicate],
        calc_song={"metadata": {"Primary Color": "Rush", "Secondary Color": "Flow"}},
        ref_arrays={"Perfect Points": [0], "Combo Multiplier": [1], "Fever Multiplier": [1]},
        cfg_dict={"TeamContributionBuffConstant": {"TeamBuff": "T5", "TeamColor": "Rush"}},
        tiers=("T5",),
        limit=1,
    )["T5"]

    assert len(rows) == 1
    row = rows[0]
    assert int(row["fg_score"]) == 120
    assert row["force"]["ForceGreats"]["config"] == {"NonFever1": 1}
    assert int(row["force"]["Score"]) == 120


def _stale_00_hard_fg_force_payload() -> dict:
    return {
        "Score": 32521173,
        "FT": 1,
        "FF": 15,
        "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 13,
            "Element": 61,
        },
        "Selected Element": "Rush",
        "BaseScore": 32518595,
        "BaseStats": {
            "Perfect Points": 40,
            "Combo Multiplier": 50,
            "Fever Multiplier": 37,
            "Fever Time": 28,
            "Fever Fill Rate": 19,
            "Beat": 0,
            "Vibe": 44,
            "Rush": 321,
            "Flow": 29,
            "Chill": 33,
        },
        # Stale-schema payload: `BaseStats` above is the pre-gem base while `Stats`
        # below is the post-gem visible row (BaseStats + the solved gems, applied once).
        # The canonical reader prefers this explicit post-gem `Stats` and never
        # re-applies gems on top of it.
        "Stats": {
            "Perfect Points": 40,
            "Combo Multiplier": 50,
            "Fever Multiplier": 76,
            "Fever Time": 31,
            "Fever Fill Rate": 64,
            "Beat": 3,
            "Vibe": 89,
            "Rush": 726,
            "Flow": 29,
            "Chill": 33,
        },
        "ForceGreats": {
            "config": {"NonFever1": 5, "NonFever2": 0},
            "final_score": 32521173,
        },
        "forced_counts": [5, 0],
        # Canonical FG scoring replays the persisted response surface (head bits 0-99
        # fever + all 1090 body notes fever on the 1190-note chart). The stale Score /
        # final_score above are intentionally inconsistent; canonicalization repairs them.
        "response_surface": [4294967295, 4294967295, 4294967295, 15, 0, 0, 0, 0, 1090, 0, 0],
    }


def _stale_00_hard_fg_entry() -> dict:
    return {
        "loadout_hash": "pytest-00-hard-fg",
        "score": 32518595,
        "fg_score": 32521173,
        "fg_base_score": 32518595,
        "gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
        "minis": ["M1", "M2", "M3"],
        "details": {
            "Stats": {
                "Perfect Points": 40,
                "Combo Multiplier": 50,
                "Fever Multiplier": 76,
                "Fever Time": 31,
                "Fever Fill Rate": 64,
                "Beat": 3,
                "Vibe": 89,
                "Rush": 726,
                "Flow": 29,
                "Chill": 33,
            },
            "PrimaryColor": "Rush",
            "SecondaryColor": "Rush",
            "SelectedElement": "Rush",
        },
        "force": _stale_00_hard_fg_force_payload(),
    }


def _prebuild_timeline_frontier(calc_song: dict, ref_arrays: dict) -> None:
    from gear_optimizer.solver.taichi_gem.api.timeline import build_or_load_timeline_frontier_payload

    build_or_load_timeline_frontier_payload(calc_song, ref_arrays)


def _expected_00_hard_surface_fg_score(calc_song: dict, ref_arrays: dict) -> int:
    from gear_optimizer.helpers.song_helpers.fg_config import require_response_surface
    from gear_optimizer.helpers.song_helpers.persistence_payload import normalize_force_payload
    from gear_optimizer.solver.scoring.exact_rescore import score_force_greats_response_surface_exact

    force_norm = normalize_force_payload(_stale_00_hard_fg_force_payload())
    return int(
        score_force_greats_response_surface_exact(
            force_norm["Stats"], calc_song, ref_arrays, require_response_surface(force_norm)
        )
    )


def test_authoritative_fg_canonicalization_replays_00_hard_force_payload_directly():
    from gear_optimizer.app_async_db import _get_team_buff_ref_arrays_cached
    from gear_optimizer.data.song_io import get_base_calc_song
    from gear_optimizer.helpers.song_helpers.persistence_authority import canonicalize_authoritative_fg_entries

    calc_song = get_base_calc_song("Data/Hard/00 (Hard) by garlagan.txt", {})
    ref_arrays = _get_team_buff_ref_arrays_cached()
    assert ref_arrays
    _prebuild_timeline_frontier(calc_song, ref_arrays)

    out = canonicalize_authoritative_fg_entries(
        [_stale_00_hard_fg_entry()],
        calc_song=calc_song,
        ref_arrays=ref_arrays,
    )

    row = out[0]
    force = row["force"]
    expected_fg = _expected_00_hard_surface_fg_score(calc_song, ref_arrays)
    assert row["score"] == 32367815
    assert row["fg_base_score"] == 32518595
    assert row["fg_score"] == expected_fg
    assert force["BaseScore"] == 32518595
    assert force["Score"] == expected_fg
    assert force["ForceGreats"]["final_score"] == expected_fg


def test_db_equal_fg_upsert_preserves_source_00_hard_paired_base_score(tmp_path, monkeypatch):
    from gear_optimizer.app_async_db import _get_team_buff_ref_arrays_cached
    from gear_optimizer.data.database import get_db_connection, init_db, save_loadouts_batch
    from gear_optimizer.data.song_io import get_base_calc_song
    from gear_optimizer.helpers.song_helpers.persistence_authority import canonicalize_authoritative_fg_entries

    db_path = tmp_path / "authoritative_fg_repair.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))
    init_db()

    song = "pytest 00 hard authoritative fg"
    stale = _stale_00_hard_fg_entry()
    save_loadouts_batch(song, [stale])

    calc_song = get_base_calc_song("Data/Hard/00 (Hard) by garlagan.txt", {})
    ref_arrays = _get_team_buff_ref_arrays_cached()
    assert ref_arrays
    _prebuild_timeline_frontier(calc_song, ref_arrays)
    expected_fg = _expected_00_hard_surface_fg_score(calc_song, ref_arrays)
    canonical = canonicalize_authoritative_fg_entries([stale], calc_song=calc_song, ref_arrays=ref_arrays)
    save_loadouts_batch(song, canonical)
    # Equal-fg upsert: a second canonical save must keep the SOURCE paired base.
    canonical_again = canonicalize_authoritative_fg_entries(
        [_stale_00_hard_fg_entry()], calc_song=calc_song, ref_arrays=ref_arrays
    )
    save_loadouts_batch(song, canonical_again)

    with get_db_connection(str(db_path)) as conn:
        row = conn.execute(
            "SELECT score, fg_score, details_json, force_details_json "
            "FROM team_buff_fg_loadouts WHERE song_name=? AND team_buff='T5'",
            (song,),
        ).fetchone()

    assert row is not None
    assert int(row["score"]) == 32518595
    assert int(row["fg_score"]) == expected_fg
    details = json.loads(row["details_json"])
    force = json.loads(row["force_details_json"])
    assert int(details["BaseScore"]) == 32518595
    assert int(force["BaseScore"]) == 32518595
    assert int(force["Score"]) == expected_fg
