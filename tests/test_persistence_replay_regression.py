from __future__ import annotations


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


def test_canonicalize_baseline_persist_entries_merges_replayed_rows_and_keeps_unmatched_rows(monkeypatch):
    from gear_optimizer.helpers.song_helpers.baseline_replay import canonicalize_baseline_persist_entries

    requested: dict[str, object] = {"limits": []}

    def fake_build_team_buff_tier_db_batches(
        *,
        entries,
        calc_song,
        ref_arrays,
        cfg_dict,
        limit,
        tiers,
        **_kwargs,
    ):
        requested["limit"] = int(limit)
        requested["limits"].append(int(limit))
        requested["tiers"] = tuple(tiers)
        requested["calc_song"] = calc_song
        requested["ref_arrays"] = ref_arrays
        requested["cfg_dict"] = cfg_dict
        entries_list = list(entries or [])
        if len(entries_list) == 1 and list(entries_list[0].get("gear") or []) == ["Other"]:
            return {"T10": []}
        return {
            "T10": [
                {
                    "gear": ["G1", "G2"],
                    "minis": ["M1"],
                    "score": 99,
                    "fg_score": 123,
                    "fg_base_score": 77,
                    "details": {"tag": "canonical"},
                    "force": {"ForceGreats": {"config": {"NonFever1": 1}}},
                }
            ]
        }

    monkeypatch.setattr(
        "gear_optimizer.helpers.song_helpers.baseline_replay.build_team_buff_tier_db_batches",
        fake_build_team_buff_tier_db_batches,
    )

    entries = [
        _make_entry(gear=["G1", "G2"], minis=["M1"], score=10, fg_score=4, tag="stale"),
        _make_entry(gear=["Other"], minis=["Else"], score=20, tag="keep"),
    ]
    out = canonicalize_baseline_persist_entries(
        entries,
        calc_song={"metadata": {"Primary Color": "Rush", "Secondary Color": "Flow"}},
        ref_arrays={"Perfect Points": [0]},
        cfg_dict={
            "IterationEngine": {"AutoSelectBuffAndColor": "false"},
            "TeamContributionBuffConstant": {"TeamBuff": "T10"},
        },
    )

    assert requested["limits"][0] == 2
    assert requested["tiers"] == ("T10",)
    assert out[0]["score"] == 99
    assert out[0]["fg_score"] == 123
    assert out[0]["fg_base_score"] == 77
    assert out[0]["details"]["tag"] == "canonical"
    assert out[0]["force"]["ForceGreats"]["config"]["NonFever1"] == 1
    assert out[1]["score"] == 20
    assert out[1]["details"]["tag"] == "keep"
    assert entries[0]["score"] == 10


def test_canonicalize_baseline_persist_entries_does_not_attach_fg_score_without_force(monkeypatch):
    from gear_optimizer.helpers.song_helpers.baseline_replay import canonicalize_baseline_persist_entries

    def fake_build_team_buff_tier_db_batches(
        *,
        entries,
        calc_song,
        ref_arrays,
        cfg_dict,
        limit,
        tiers,
        **_kwargs,
    ):
        return {
            "T10": [
                {
                    "gear": ["G1", "G2"],
                    "minis": ["M1"],
                    "score": 99,
                    "fg_score": 123,
                    "fg_base_score": 77,
                    "details": {"tag": "canonical"},
                    "force": None,
                }
            ]
        }

    monkeypatch.setattr(
        "gear_optimizer.helpers.song_helpers.baseline_replay.build_team_buff_tier_db_batches",
        fake_build_team_buff_tier_db_batches,
    )

    entries = [
        _make_entry(gear=["G1", "G2"], minis=["M1"], score=10, fg_score=0, tag="stale"),
    ]
    out = canonicalize_baseline_persist_entries(
        entries,
        calc_song={"metadata": {"Primary Color": "Rush", "Secondary Color": "Flow"}},
        ref_arrays={"Perfect Points": [0]},
        cfg_dict={
            "IterationEngine": {"AutoSelectBuffAndColor": "false"},
            "TeamContributionBuffConstant": {"TeamBuff": "T10"},
        },
    )

    assert out[0]["score"] == 99
    assert out[0]["fg_score"] == 0
    assert out[0].get("fg_base_score") is None
    assert out[0]["details"]["tag"] == "canonical"
    assert out[0]["force"] is None


def test_build_persistence_entries_routes_retained_surface_through_shared_canonicalizer(monkeypatch):
    from gear_optimizer.helpers.song_helpers.persistence import build_persistence_entries

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
            "IterationEngine": {"AutoSelectBuffAndColor": "false"},
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


def test_canonicalize_baseline_persist_entries_is_noop_without_replay_context():
    from gear_optimizer.helpers.song_helpers.baseline_replay import canonicalize_baseline_persist_entries

    entries = [_make_entry(gear=["G1"], minis=["M1"], score=42, tag="noop")]
    out = canonicalize_baseline_persist_entries(entries, calc_song=None, ref_arrays=None, cfg_dict=None)

    assert out is entries
