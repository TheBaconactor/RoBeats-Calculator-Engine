import json
import sqlite3
from pathlib import Path


def test_persistence_canonicalizes_stats_for_mini_equivalence_groups(monkeypatch, tmp_path: Path):
    """
    Regression: When minis are grouped by song-context equivalence, persisted Stats must be
    canonicalized to the representative mini names (legacy DB behavior), not whichever
    variant happened to be in the GA genome.

    This also catches "score correct but stats wrong" drift where off-element stats differ.
    """
    db_path = tmp_path / "evolution.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))

    import gear_optimizer.data.database as db

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

    monkeypatch.setattr(db, "get_minis_by_name_cached", lambda: fake_minis)
    monkeypatch.setattr(db, "get_gears_by_name_cached", lambda: {})

    db.init_db()

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

    db.save_loadouts_batch("pytest_song", [entry])

    con = sqlite3.connect(db_path)
    try:
        row = con.execute(
            "SELECT details_json FROM team_buff_loadouts WHERE song_name=? AND team_buff='T5' LIMIT 1",
            ("pytest_song",),
        ).fetchone()
        assert row is not None
        details = json.loads(row[0])
        details = db._unpack_stats_after_load(details) or {}
        stats = (details.get("Stats") or {}) if isinstance(details, dict) else {}
    finally:
        con.close()

    # Canonical rep for the equivalence group is lexicographically first ("BlackY"), so Flow must be 111.
    assert int(stats.get("Flow", 0) or 0) == 111
    # Config-taint-like off-element bump must not persist.
    assert int(stats.get("Vibe", 0) or 0) == 0


def test_persistence_rotates_representatives_for_duplicate_variant_groups(monkeypatch, tmp_path: Path):
    """
    Legacy minis grouping behavior: when two equipped minis share the same variant group,
    rotate representatives so the two slots use distinct first-elements when possible.
    """
    db_path = tmp_path / "evolution.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))

    import gear_optimizer.data.database as db

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

    monkeypatch.setattr(db, "get_minis_by_name_cached", lambda: fake_minis)
    monkeypatch.setattr(db, "get_gears_by_name_cached", lambda: {})

    db.init_db()

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

    db.save_loadouts_batch("pytest_song", [entry])

    con = sqlite3.connect(db_path)
    try:
        row = con.execute(
            "SELECT details_json FROM team_buff_loadouts WHERE song_name=? AND team_buff='T5' LIMIT 1",
            ("pytest_song",),
        ).fetchone()
        assert row is not None
        details = json.loads(row[0])
        details = db._unpack_stats_after_load(details) or {}
        stats = (details.get("Stats") or {}) if isinstance(details, dict) else {}
    finally:
        con.close()

    # Expect the combination (BlackY + Heavy Metal Starlet), not (BlackY + BlackY).
    assert int(stats.get("Flow", 0) or 0) == 20
    assert int(stats.get("Vibe", 0) or 0) == 35
