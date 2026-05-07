from gear_optimizer.helpers.song_helpers.persistence import build_persistence_entries


def test_build_persistence_entries_dedup_prefers_best_base_score_and_preserves_best_fg_payload():
    """
    Regression: when the same loadout hash is emitted multiple times (e.g. best_fg fallback +
    GA candidates fallback), persistence must keep the best *base* score/details while also
    keeping the best FG score/force payload.
    """
    loadout_gear = ["G1", "G2", "G3", "G4", "G5", "G6"]
    loadout_minis = ["M1", "M2", "M3"]

    # Top1 can be unrelated; we only care about the duplicated best_fg vs GA candidate.
    db_payload = {
        "score": 999,
        "gear": ["TOP_GEAR"],
        "minis": ["TOP_M1", "TOP_M2", "TOP_M3"],
        "details": {"marker": "top1"},
        "fg_score": 0,
        "force": None,
        "best_fg": {
            # Best FG score for this loadout.
            "score": 2000,
            # Base score context for the FG allocation (can be lower than the loadout's best base).
            "base_score": 50,
            "gear": list(loadout_gear),
            "minis": list(loadout_minis),
            "details": {"marker": "fg"},
            "force": {"ForceGreats": {"config": {"NonFever1": 1, "NonFever2": 0}}},
        },
    }

    ga_candidates = [
        {
            # Higher base score for the same loadout hash should replace the FG fallback's base context/details.
            "BaseScore": 80,
            "Gear": list(loadout_gear),
            "Minis": list(loadout_minis),
            "Data": {"marker": "base"},
        }
    ]

    build_details_fn = lambda data: {"marker": (data or {}).get("marker")}  # noqa: E731

    out = build_persistence_entries(
        db_payload,
        ga_candidates,
        loadout_entries=None,
        build_details_fn=build_details_fn,
        calc_song=None,
        ref_arrays=None,
    )

    dup = [e for e in out if e.get("gear") == loadout_gear and e.get("minis") == loadout_minis]
    assert len(dup) == 1

    entry = dup[0]
    assert int(entry.get("score", 0) or 0) == 80
    assert int(entry.get("fg_score", 0) or 0) == 2000
    assert int(entry.get("fg_base_score", 0) or 0) == 50
    assert (entry.get("details") or {}).get("marker") == "base"
    assert isinstance(entry.get("force"), dict)


def test_build_persistence_entries_ga_fallback_preserves_effective_hash():
    out = build_persistence_entries(
        {
            "score": 999,
            "gear": ["TOP_GEAR"],
            "minis": ["TOP_M1", "TOP_M2", "TOP_M3"],
            "details": {"marker": "top1"},
            "fg_score": 0,
            "force": None,
        },
        [
            {
                "loadout_hash": "effective-ga-hash",
                "BaseScore": 123,
                "Gear": ["G1"],
                "Minis": ["RepresentativeMini"],
                "Data": {"marker": "ga"},
            }
        ],
        loadout_entries=None,
        build_details_fn=lambda data: {"marker": (data or {}).get("marker")},
        calc_song=None,
        ref_arrays=None,
    )

    matches = [entry for entry in out if entry.get("loadout_hash") == "effective-ga-hash"]
    assert len(matches) == 1
    assert int(matches[0].get("score", 0) or 0) == 123
    assert (matches[0].get("details") or {}).get("marker") == "ga"


def test_build_persistence_entries_retained_fg_without_force_drops_fg_score():
    """
    Retained rows must not carry an FG score unless they also carry a valid replayable FG payload.
    """
    gear = ["G1", "G2", "G3", "G4", "G5", "G6"]
    minis = ["M1", "M2", "M3"]

    out = build_persistence_entries(
        {
            "score": 999,
            "gear": ["TOP_GEAR"],
            "minis": ["TOP_M1", "TOP_M2", "TOP_M3"],
            "details": {"marker": "top1"},
            "fg_score": 0,
            "force": None,
        },
        ga_candidates=[],
        loadout_entries={
            "retained_hash": {
                "score": 120,
                "base_score": 120,
                "gear": list(gear),
                "minis": list(minis),
                "details": {"marker": "retained"},
                "fg_score": 145,
                "force": None,
            }
        },
        build_details_fn=lambda data: dict(data or {}),
        calc_song=None,
        ref_arrays=None,
    )

    entry = next(e for e in out if e.get("gear") == gear and e.get("minis") == minis)
    assert int(entry.get("score", 0) or 0) == 120
    assert int(entry.get("fg_score", 0) or 0) == 0
    assert entry.get("force") is None


def test_build_persistence_entries_top1_fg_without_force_drops_fg_score():
    """
    The top1 payload must not keep an FG score unless it also carries a valid replayable FG payload.
    """

    gear = ["G1", "G2", "G3", "G4", "G5", "G6"]
    minis = ["M1", "M2", "M3"]

    out = build_persistence_entries(
        {
            "score": 120,
            "gear": list(gear),
            "minis": list(minis),
            "details": {"marker": "top1"},
            "fg_score": 200,
            "force": None,
        },
        ga_candidates=[],
        loadout_entries=None,
        build_details_fn=lambda data: dict(data or {}),
        calc_song=None,
        ref_arrays=None,
    )

    assert len(out) == 1
    entry = out[0]
    assert int(entry.get("score", 0) or 0) == 120
    assert int(entry.get("fg_score", 0) or 0) == 0
    assert entry.get("force") is None


def test_build_persistence_entries_canonicalizes_baseline_scores_for_replay(monkeypatch):
    """
    Baseline persistence must store the replay-canonical score/details for the retained loadout.

    This prevents SQLite rows from carrying a stale optimizer score that cannot be reproduced by the
    TeamBuff replay path.
    """
    gear = ["G1", "G2", "G3", "G4", "G5", "G6"]
    minis = ["M1", "M2", "M3"]

    db_payload = {
        "score": 10,
        "gear": ["TOP_GEAR"],
        "minis": ["TOP_M1", "TOP_M2", "TOP_M3"],
        "details": {"marker": "top1"},
        "fg_score": 0,
        "force": None,
    }

    loadout_entries = {
        "stale_hash": {
            "score": 77477622,
            "base_score": 77477622,
            "gear": list(gear),
            "minis": list(minis),
            "details": {"marker": "stale"},
            "fg_score": 0,
            "force": None,
            "_deferred_fg_update": True,
        }
    }

    captured: dict[str, object] = {}

    def _fake_batches(**kwargs):
        captured["tiers"] = tuple(kwargs.get("tiers") or ())
        captured["limit"] = kwargs.get("limit")
        return {
            "T5": [
                {
                    "score": 64849540,
                    "fg_score": 0,
                    "gear": list(gear),
                    "minis": list(minis),
                    "details": {"marker": "canonical"},
                    "force": None,
                }
            ]
        }

    monkeypatch.setattr(
        "gear_optimizer.helpers.song_helpers.baseline_replay.build_team_buff_tier_db_batches",
        _fake_batches,
    )

    out = build_persistence_entries(
        db_payload,
        ga_candidates=[],
        loadout_entries=loadout_entries,
        build_details_fn=lambda data: dict(data or {}),
        calc_song={"metadata": {"Primary Color": "Rush", "Secondary Color": "Vibe"}, "song_data": {}},
        ref_arrays={"Perfect Points": [0]},
        cfg_dict={"TeamContributionBuffConstant": {"TeamBuff": "T5", "TeamColor": "Rush"}},
    )

    entry = next(e for e in out if e.get("gear") == gear and e.get("minis") == minis)
    assert captured["tiers"] == ("T5",)
    assert int(captured["limit"]) == len(out)
    assert int(entry.get("score", 0) or 0) == 64849540
    assert (entry.get("details") or {}).get("marker") == "canonical"


def test_build_persistence_entries_precanonicalizes_retained_loadout_entries(monkeypatch):
    """
    Deferred/pre-persistence callers inspect the retained frontier before the final DB write.

    Regression: seeded loadout entries could carry a stale base score/details pairing until the
    final baseline canonicalizer ran, which meant the deferred surface did not match replay.
    Normalize the retained entries first so both surfaces share the same score contract.
    """
    gear = ["G1", "G2", "G3", "G4", "G5", "G6"]
    minis = ["M1", "M2", "M3"]

    db_payload = {
        "score": 999,
        "gear": ["TOP_GEAR"],
        "minis": ["TOP_M1", "TOP_M2", "TOP_M3"],
        "details": {"marker": "top1"},
        "fg_score": 0,
        "force": None,
    }

    loadout_entries = {
        "stale_hash": {
            "score": 100,
            "base_score": 100,
            "gear": list(gear),
            "minis": list(minis),
            "details": {"marker": "stale"},
            "fg_score": 130,
            "force": {"ForceGreats": {"config": {"NonFever1": 1, "NonFever2": 0}}},
        }
    }

    calls = {"count": 0}

    def _fake_canonicalize(entries, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            assert len(entries) == 1
            row = dict(entries[0])
            row["score"] = 120
            row["details"] = {"marker": "precanonical"}
            row["fg_base_score"] = 110
            return [row]
        return entries

    monkeypatch.setattr(
        "gear_optimizer.helpers.song_helpers.baseline_replay.canonicalize_baseline_persist_entries",
        _fake_canonicalize,
    )

    out = build_persistence_entries(
        db_payload,
        ga_candidates=[],
        loadout_entries=loadout_entries,
        build_details_fn=lambda data: dict(data or {}),
        calc_song={"metadata": {"Primary Color": "Rush", "Secondary Color": "Vibe"}, "song_data": {}},
        ref_arrays={"Perfect Points": [0]},
        cfg_dict={"TeamContributionBuffConstant": {"TeamBuff": "T5", "TeamColor": "Rush"}},
    )

    entry = next(e for e in out if e.get("gear") == gear and e.get("minis") == minis)
    assert calls["count"] == 2
    assert int(entry.get("score", 0) or 0) == 120
    assert int(entry.get("fg_base_score", 0) or 0) == 110
    assert (entry.get("details") or {}).get("marker") == "precanonical"
