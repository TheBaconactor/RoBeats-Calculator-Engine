import json
from pathlib import Path

from gear_optimizer.gamedata import STATS
from gear_optimizer.store import db, schema
from gear_optimizer.store.legacy import store_entries
from tests.items_support import minis_from_dicts


def _store(tmp_path: Path, song: str, entries: list[dict], fake_minis: dict):
    """Store entries against a fake minis catalog; return the song's (meta board, FG board)."""
    conn = schema.connect(tmp_path / "results.db", write=True)
    try:
        store_entries(conn, song, "T5", entries, gears={}, minis=minis_from_dicts(fake_minis))
        boards = db.load_boards(conn, song, "T5")
        traces = db.load_traces(conn, song, "T5", [x.loadout_hash for x in boards.meta + boards.fg])
    finally:
        conn.close()
    return boards, traces


def _stats(result) -> dict[str, int]:
    return dict(zip(STATS, result.stats))


def test_persistence_canonicalizes_stats_for_mini_equivalence_groups(tmp_path: Path):
    """
    Regression: When minis are grouped by song-context equivalence, persisted Stats must be
    canonicalized to the representative mini names (legacy DB behavior), not whichever
    variant happened to be in the GA genome.

    This also catches "score correct but stats wrong" drift where off-element stats differ.
    """
    # Two equivalent minis under (Primary=Beat, Secondary=Chill, Selected=Beat):
    # - identical PP/CM/FM/FT/FF + identical Beat/Chill
    # - differ only in Flow (off-element) so score can tie but Stats should be canonical.
    fake_minis = {
        "BlackY": {
            "Name": "BlackY",
            "type": "mini",
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 0,
            "Fever Time": 0,
            "Fever Fill Rate": 0,
            "Beat": 10,
            "Chill": 20,
            "Flow": 111,
        },
        "Heavy Metal Starlet": {
            "Name": "Heavy Metal Starlet",
            "type": "mini",
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 0,
            "Fever Time": 0,
            "Fever Fill Rate": 0,
            "Beat": 10,
            "Chill": 20,
            "Flow": 999,
        },
        "Solo A": {"Name": "Solo A", "type": "mini", "Beat": 1, "Chill": 2, "Flow": 0},
        "Solo B": {"Name": "Solo B", "type": "mini", "Beat": 2, "Chill": 3, "Flow": 0},
    }

    entry = {
        "score": 123,
        "fg_score": 0,
        "gear": [],
        "minis": ["Heavy Metal Starlet", "Solo A", "Solo B"],
        "details": {
            # Intentionally wrong/non-canonical Stats snapshot: picks the variant's off-element Flow
            # and includes a config-taint-like Vibe bump (should be removed by persistence recompute).
            "Stats": {"Flow": 999, "Vibe": 378, "Perfect Points": 0},
            "GemCounts": {"Perfect Points": 0, "Combo Multiplier": 0, "Fever Multiplier": 0, "Element": 0},
            "FT": 0,
            "FF": 0,
            "SelectedElement": "Beat",
            "PrimaryColor": "Beat",
            "SecondaryColor": "Chill",
        },
        "force": None,
    }

    boards, _traces = _store(tmp_path, "pytest_song", [entry], fake_minis)
    stats = _stats(boards.meta[0].meta)

    # Canonical rep for the equivalence group is lexicographically first ("BlackY"), so Flow must be 111.
    assert int(stats.get("Flow", 0) or 0) == 111
    # Config-taint-like off-element bump must not persist.
    assert int(stats.get("Vibe", 0) or 0) == 0


def test_persistence_rotates_representatives_for_duplicate_variant_groups(tmp_path: Path):
    """
    Legacy minis grouping behavior: when two equipped minis share the same variant group,
    rotate representatives so the two slots use distinct first-elements when possible.
    """
    fake_minis = {
        "BlackY": {
            "Name": "BlackY",
            "type": "mini",
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 0,
            "Fever Time": 0,
            "Fever Fill Rate": 0,
            "Beat": 10,
            "Chill": 20,
            "Flow": 20,
            "Vibe": 0,
        },
        "Heavy Metal Starlet": {
            "Name": "Heavy Metal Starlet",
            "type": "mini",
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 0,
            "Fever Time": 0,
            "Fever Fill Rate": 0,
            "Beat": 10,
            "Chill": 20,
            "Flow": 0,
            "Vibe": 35,
        },
        "Halloween Witch Teresa": {"Name": "Halloween Witch Teresa", "type": "mini", "Beat": 0, "Chill": 0},
    }

    entry = {
        "score": 123,
        "fg_score": 0,
        "gear": [],
        # Two equipped minis share the same signature => two duplicate variant groups.
        "minis": ["BlackY", "Heavy Metal Starlet", "Halloween Witch Teresa"],
        "details": {
            "Stats": {"Flow": 0, "Vibe": 0, "Perfect Points": 0},
            "GemCounts": {"Perfect Points": 0, "Combo Multiplier": 0, "Fever Multiplier": 0, "Element": 0},
            "FT": 0,
            "FF": 0,
            "SelectedElement": "Beat",
            "PrimaryColor": "Beat",
            "SecondaryColor": "Chill",
        },
        "force": None,
    }

    boards, _traces = _store(tmp_path, "pytest_song", [entry], fake_minis)
    stats = _stats(boards.meta[0].meta)
    mini_groups = [list(group) for group in boards.meta[0].minis]

    # Expect the combination (BlackY + Heavy Metal Starlet), not (BlackY + BlackY).
    assert int(stats.get("Flow", 0) or 0) == 20
    assert int(stats.get("Vibe", 0) or 0) == 35

    # Persisted mini groups should also encode the rotated representative order so consumers
    # that display `group[0]` don't show duplicates.
    assert ["Halloween Witch Teresa"] in mini_groups
    dupe_groups = [g for g in mini_groups if set(g) == {"BlackY", "Heavy Metal Starlet"}]
    assert len(dupe_groups) == 2
    assert dupe_groups[0][0] != dupe_groups[1][0]
    assert {dupe_groups[0][0], dupe_groups[1][0]} == {"BlackY", "Heavy Metal Starlet"}


def test_fg_payload_stats_match_the_persisted_mini_representative(tmp_path: Path):
    fake_minis = {
        "BlackY": {
            "Name": "BlackY",
            "type": "mini",
            "Beat": 10,
            "Chill": 20,
            "Flow": 111,
        },
        "Heavy Metal Starlet": {
            "Name": "Heavy Metal Starlet",
            "type": "mini",
            "Beat": 10,
            "Chill": 20,
            "Flow": 999,
        },
    }

    solved_stats = {
        "Perfect Points": 45,  # T5 25 + the mini's 20 ascension PP
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Beat": 40,
        "Chill": 20,
        "Flow": 999,
        "Rush": 0,
        "Vibe": 0,
    }
    gems = {"Perfect Points": 0, "Combo Multiplier": 0, "Fever Multiplier": 0, "Element": 0}
    boards, traces = _store(
        tmp_path,
        "pytest_fg_song",
        [
            {
                "score": 123,
                "fg_score": 130,
                "fg_base_score": 123,
                "gear": [],
                "minis": ["Heavy Metal Starlet"],
                "details": {
                    "Stats": dict(solved_stats),
                    "GemCounts": dict(gems),
                    "FT": 0,
                    "FF": 0,
                    "SelectedElement": "Beat",
                    "PrimaryColor": "Beat",
                    "SecondaryColor": "Chill",
                    "TimelineFrontier": {"frontier_trace": [{"forced_prefix_count": 3}]},
                    "ForceGreats": {"config": {"NonFever1": 3}, "enabled": True},
                },
                "force": {
                    "Score": 130,
                    "BaseScore": 123,
                    "Stats": dict(solved_stats),
                    "BaseStats": dict(solved_stats),
                    "GemCounts": dict(gems),
                    "SelectedElement": "Beat",
                    "forced_counts": [3, 0],
                    "response_surface": [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1],
                    "ForceGreats": {
                        "final_score": 130,
                        "config": {"NonFever1": 3},
                        "variant_applied": True,
                        "frontier_trace": [{"forced_prefix_count": 3}],
                    },
                },
            }
        ],
        fake_minis,
    )
    (row,) = boards.fg
    assert row.minis[0][0] == "BlackY"
    assert _stats(row.fg)["Flow"] == 111
    assert row.fg.stats == row.meta.stats  # same gems here
    persisted_json = json.dumps([traces[row.loadout_hash].meta, traces[row.loadout_hash].fg])
    assert '"frontier_trace"' in persisted_json
    assert '"forced_counts"' not in persisted_json
    assert '"forced_prefix_count"' not in persisted_json
    assert '"config"' not in persisted_json
    assert '"enabled"' not in persisted_json
    assert '"variant_applied"' not in persisted_json


def test_fg_representative_stats_use_fg_gems_not_paired_base_gems(tmp_path: Path):
    fake_minis = {
        "BlackY": {"Name": "BlackY", "type": "mini", "Beat": 10, "Chill": 20, "Flow": 111},
        "Heavy Metal Starlet": {
            "Name": "Heavy Metal Starlet",
            "type": "mini",
            "Beat": 10,
            "Chill": 20,
            "Flow": 999,
        },
    }

    base_stats = {
        "Perfect Points": 45,  # T5 25 + the mini's 20 ascension PP
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Beat": 40,
        "Chill": 20,
        "Flow": 999,
        "Rush": 0,
        "Vibe": 0,
    }
    fg_stats = {**base_stats, "Fever Fill Rate": 3, "Beat": 100}
    base_gems = {"Perfect Points": 0, "Combo Multiplier": 0, "Fever Multiplier": 0, "Element": 0}
    fg_gems = {**base_gems, "Element": 10}
    boards, _traces = _store(
        tmp_path,
        "pytest_fg_gem_surface",
        [
            {
                "score": 123,
                "fg_score": 130,
                "fg_base_score": 123,
                "gear": [],
                "minis": ["Heavy Metal Starlet"],
                "details": {
                    "Stats": base_stats,
                    "GemCounts": base_gems,
                    "FT": 0,
                    "FF": 0,
                    "SelectedElement": "Beat",
                    "PrimaryColor": "Beat",
                    "SecondaryColor": "Chill",
                },
                "force": {
                    "Score": 130,
                    "BaseScore": 123,
                    "Stats": fg_stats,
                    "BaseStats": fg_stats,
                    "GemCounts": fg_gems,
                    "FT": 0,
                    "FF": 1,
                    "SelectedElement": "Beat",
                    "response_surface": [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1],
                    "ForceGreats": {"final_score": 130, "frontier_trace": [{"next_state": 1}]},
                },
            }
        ],
        fake_minis,
    )
    fg_stats_stored = _stats(boards.fg[0].fg)
    assert fg_stats_stored["Fever Fill Rate"] == 3
    assert fg_stats_stored["Beat"] == 100
    assert fg_stats_stored["Flow"] == 111
