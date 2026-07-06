import concurrent.futures
import json

import pytest

from gear_optimizer.data.database import (
    get_db_connection,
    get_song_counters,
    init_db,
    save_loadouts_batch,
    update_song_counters,
    _unpack_stats_after_load,
)


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "test_persistence.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(path))
    init_db()
    return str(path)


def _force_payload(
    fg_score: int,
    *,
    base_score: int,
    tag: str | None = None,
    config: dict | None = None,
    ft: int = 0,
    ff: int = 0,
    gem_counts: dict | None = None,
    base_stats: dict | None = None,
    selected: str = "Rush",
) -> dict:
    payload = {
        "Score": int(fg_score),
        "BaseScore": int(base_score),
        "FT": int(ft),
        "FF": int(ff),
        "GemCounts": dict(
            gem_counts or {"Perfect Points": 0, "Combo Multiplier": 0, "Fever Multiplier": 0, "Element": 0}
        ),
        "BaseStats": dict(
            base_stats
            or {
                "Perfect Points": 25,
                "Combo Multiplier": 0,
                "Fever Multiplier": 0,
                "Fever Fill Rate": 0,
                "Fever Time": 0,
                "Chill": 0,
                "Flow": 0,
                "Rush": 100,
                "Beat": 0,
                "Vibe": 0,
            }
        ),
        "Selected Element": selected,
        "ForceGreats": {"config": dict(config or {"NonFever1": 1}), "final_score": int(fg_score)},
    }
    if tag is not None:
        payload["tag"] = tag
    return payload


def test_save_loadouts_batch_unions_equivalent_mini_variants(db_path, monkeypatch):
    minis_by_name = {
        "MiniA": {
            "Name": "MiniA",
            "Chill": 0,
            "Flow": 0,
            "Rush": 0,
            "Beat": 0,
            "Vibe": 55,
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 0,
            "Fever Time": 0,
            "Fever Fill Rate": 0,
        },
        "MiniB": {
            "Name": "MiniB",
            "Chill": 0,
            "Flow": 30,  # irrelevant for Vibe/Vibe context
            "Rush": 0,
            "Beat": 0,
            "Vibe": 55,
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 0,
            "Fever Time": 0,
            "Fever Fill Rate": 0,
        },
    }

    # Avoid depending on real Data/Minis.csv in this unit test.
    monkeypatch.setattr("gear_optimizer.data.database.get_minis_by_name_cached", lambda: minis_by_name)

    song = "Mini Variant Union Song"
    details = {"PrimaryColor": "Vibe", "SecondaryColor": "Vibe", "SelectedElement": "Vibe"}

    save_loadouts_batch(
        song,
        [{"score": 100, "fg_score": 0, "gear": ["G1"], "minis": ["MiniA"], "details": details, "force": None}],
    )
    save_loadouts_batch(
        song,
        [{"score": 100, "fg_score": 0, "gear": ["G1"], "minis": ["MiniB"], "details": details, "force": None}],
    )

    conn = get_db_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT COUNT(*) FROM team_buff_loadouts WHERE song_name=? AND team_buff='T5'",
            (song,),
        ).fetchone()
        assert int(rows[0] or 0) == 1
    finally:
        conn.close()

    # Decode via the canonical read API (supports compact BLOB storage).
    from gear_optimizer.data.database import get_best_loadouts

    decoded = get_best_loadouts(song, limit=10, team_buff="T5", db_path=db_path)
    assert len(decoded) == 1
    assert decoded[0].get("mini_groups") == [["MiniA", "MiniB"]]


def test_save_loadouts_batch_persists_song_aware_mini_ascension_stats(db_path, monkeypatch):
    song = "Ascension Target by Artist"
    minis_by_name = {
        "Target Mini": {
            "Name": "Target Mini",
            "type": "Mini",
            "Rush": 50,
            "Flow": 0,
            "Chill": 0,
            "Beat": 0,
            "Vibe": 0,
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 0,
            "Fever Time": 0,
            "Fever Fill Rate": 0,
            "Song Target": [song],
            "Mini Ascension Enabled": True,
            "Mini Ascension Level": 10,
        }
    }
    monkeypatch.setattr("gear_optimizer.data.database.get_minis_by_name_cached", lambda: minis_by_name)

    details = {
        "PrimaryColor": "Rush",
        "SecondaryColor": "Flow",
        "SelectedElement": "Rush",
        "GemCounts": {"Perfect Points": 0, "Combo Multiplier": 0, "Fever Multiplier": 0, "Element": 0},
        "FT": 0,
        "FF": 0,
    }

    save_loadouts_batch(
        song,
        [{"score": 100, "fg_score": 0, "gear": [], "minis": ["Target Mini"], "details": details, "force": None}],
        db_path=db_path,
        team_buff="NONE",
    )

    conn = get_db_connection(db_path)
    try:
        row = conn.execute(
            """
            SELECT details_json
            FROM team_buff_loadouts
            WHERE song_name=? AND team_buff='NONE'
            """,
            (song,),
        ).fetchone()
        unpacked = _unpack_stats_after_load(json.loads(row["details_json"]))
        stats = unpacked["Stats"]
        assert stats["Perfect Points"] == 20
        assert stats["Rush"] == 100
    finally:
        conn.close()


def test_save_loadouts_batch_unions_equivalent_mini_variants_with_missing_colors(db_path, monkeypatch):
    minis_by_name = {
        "MiniA": {
            "Name": "MiniA",
            "Chill": 0,
            "Flow": 0,
            "Rush": 0,
            "Beat": 0,
            "Vibe": 55,
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 0,
            "Fever Time": 0,
            "Fever Fill Rate": 0,
        },
        "MiniB": {
            "Name": "MiniB",
            "Chill": 0,
            "Flow": 30,  # irrelevant for Vibe/Vibe context
            "Rush": 0,
            "Beat": 0,
            "Vibe": 55,
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 0,
            "Fever Time": 0,
            "Fever Fill Rate": 0,
        },
    }

    monkeypatch.setattr("gear_optimizer.data.database.get_minis_by_name_cached", lambda: minis_by_name)

    song = "Mini Variant Union Song (Missing Colors)"
    details = {"PrimaryColor": "Vibe", "SecondaryColor": "Vibe", "SelectedElement": "Vibe"}

    # First write establishes song-context colors.
    save_loadouts_batch(
        song,
        [{"score": 100, "fg_score": 0, "gear": ["G1"], "minis": ["MiniA"], "details": details, "force": None}],
    )
    # A details-lite write omits colors but should still merge into the same effective hash.
    save_loadouts_batch(
        song,
        [{"score": 100, "fg_score": 0, "gear": ["G1"], "minis": ["MiniB"], "details": {"marker": True}, "force": None}],
    )

    conn = get_db_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT COUNT(*) FROM team_buff_loadouts WHERE song_name=? AND team_buff='T5'",
            (song,),
        ).fetchone()
        assert int(rows[0] or 0) == 1
    finally:
        conn.close()

    from gear_optimizer.data.database import get_best_loadouts

    decoded = get_best_loadouts(song, limit=10, team_buff="T5", db_path=db_path)
    assert len(decoded) == 1
    assert decoded[0].get("mini_groups") == [["MiniA", "MiniB"]]


def test_songs_best_scores_and_fg_scores_update(db_path):
    song = "Persistence Integrity Song"

    save_loadouts_batch(
        song,
        [
            {
                "score": 1000,
                "fg_score": 0,
                "gear": ["G1"],
                "minis": ["M1"],
                "details": {"tag": "base"},
                "force": None,
            },
            {
                "score": 900,
                "fg_score": 5000,
                "gear": ["G2"],
                "minis": ["M1"],
                "details": {"tag": "fg"},
                "force": _force_payload(5000, base_score=900),
            },
        ],
    )

    # Base improves, FG does not.
    save_loadouts_batch(
        song,
        [
            {
                "score": 1100,
                "fg_score": 4500,
                "gear": ["G3"],
                "minis": ["M1"],
                "details": {"tag": "base2"},
                "force": _force_payload(4500, base_score=1100),
            }
        ],
    )

    conn = get_db_connection(db_path)
    try:
        song_row = conn.execute("SELECT best_score, best_fg_score FROM songs WHERE name=?", (song,)).fetchone()
        assert song_row["best_score"] == 1100
        assert song_row["best_fg_score"] == 5000

        fg_count = conn.execute(
            "SELECT COUNT(*) FROM team_buff_fg_loadouts WHERE song_name=? AND team_buff='T5'",
            (song,),
        ).fetchone()[0]
        assert fg_count == 2  # two distinct FG-valid loadouts were inserted
    finally:
        conn.close()


def test_details_payload_packs_gems_and_colors_but_loads_compatibly(db_path):
    song = "Compact Details Gems Colors Song"
    details = {
        "Stats": {
            "Perfect Points": 1,
            "Combo Multiplier": 2,
            "Fever Multiplier": 3,
            "Fever Fill Rate": 4,
            "Fever Time": 5,
            "Chill": 6,
            "Flow": 7,
            "Rush": 8,
            "Beat": 9,
            "Vibe": 10,
        },
        "GemCounts": {"Perfect Points": 11, "Combo Multiplier": 12, "Fever Multiplier": 13, "Element": 14},
        "SelectedElement": "Rush",
        "PrimaryColor": "Rush",
        "SecondaryColor": "Flow",
        "ForceGreats": {},
        "Difficulty": "Hard",
        "attempt_lifetime": 99,
        "attempts_first": 88,
    }

    save_loadouts_batch(
        song,
        [{"score": 1234, "fg_score": 0, "gear": ["G1"], "minis": ["M1"], "details": details, "force": None}],
    )

    from gear_optimizer.data.database import _unpack_stats_after_load

    conn = get_db_connection(db_path)
    try:
        row = conn.execute(
            "SELECT details_json FROM team_buff_loadouts WHERE song_name=? AND team_buff='T5'",
            (song,),
        ).fetchone()
        assert row is not None
        raw = json.loads(row["details_json"])
        assert "GemCounts" not in raw
        assert "SelectedElement" not in raw
        assert "PrimaryColor" not in raw
        assert "SecondaryColor" not in raw
        assert "ForceGreats" not in raw
        assert "Difficulty" not in raw
        assert "attempt_lifetime" not in raw
        assert raw["gc"] == [11, 12, 13, 14]
        assert raw["se"] == "Rush"
        assert raw["pc"] == "Rush"
        assert raw["sc"] == "Flow"

        unpacked = _unpack_stats_after_load(raw)
        assert unpacked["GemCounts"] == {
            "Perfect Points": 11,
            "Combo Multiplier": 12,
            "Fever Multiplier": 13,
            "Element": 14,
        }
        assert unpacked["SelectedElement"] == "Rush"
        assert unpacked["PrimaryColor"] == "Rush"
        assert unpacked["SecondaryColor"] == "Flow"
    finally:
        conn.close()


def test_fg_loadouts_requires_force_details(db_path):
    song = "FG Validity Song"

    save_loadouts_batch(
        song,
        [
            {
                "score": 123,
                "fg_score": 9999,
                "gear": ["G1"],
                "minis": ["M1"],
                "details": {"tag": "fg_without_force"},
                "force": None,
            }
        ],
    )

    conn = get_db_connection(db_path)
    try:
        loadouts_count = conn.execute(
            "SELECT COUNT(*) FROM team_buff_loadouts WHERE song_name=? AND team_buff='T5'",
            (song,),
        ).fetchone()[0]
        fg_count = conn.execute(
            "SELECT COUNT(*) FROM team_buff_fg_loadouts WHERE song_name=? AND team_buff='T5'",
            (song,),
        ).fetchone()[0]
        assert loadouts_count == 1
        assert fg_count == 0
    finally:
        conn.close()


def test_fg_loadouts_requires_fg_beats_base(db_path):
    song = "FG Worse Than Base Song"

    save_loadouts_batch(
        song,
        [
            {
                "score": 1000,
                "fg_score": 900,
                "gear": ["G1"],
                "minis": ["M1"],
                "details": {"tag": "fg_worse_than_base"},
                "force": _force_payload(900, base_score=1000),
            }
        ],
    )

    conn = get_db_connection(db_path)
    try:
        loadouts_count = conn.execute(
            "SELECT COUNT(*) FROM team_buff_loadouts WHERE song_name=? AND team_buff='T5'",
            (song,),
        ).fetchone()[0]
        fg_count = conn.execute(
            "SELECT COUNT(*) FROM team_buff_fg_loadouts WHERE song_name=? AND team_buff='T5'",
            (song,),
        ).fetchone()[0]
        best_fg_score = conn.execute("SELECT best_fg_score FROM songs WHERE name=?", (song,)).fetchone()[
            "best_fg_score"
        ]
        assert loadouts_count == 1
        assert fg_count == 0
        assert best_fg_score == 0
    finally:
        conn.close()


def test_fg_loadouts_compare_against_paired_base_score_not_best_base_score(db_path):
    song = "FG Paired Base Comparator Song"

    save_loadouts_batch(
        song,
        [
            {
                # Deferred/native FG saves can carry the current best base score
                # while the force payload owns the lower paired base allocation.
                "score": 10_000,
                "fg_score": 5_500,
                "fg_base_score": 5_000,
                "gear": ["G1"],
                "minis": ["M1"],
                "details": {"tag": "fg_different_base"},
                "force": _force_payload(5_500, base_score=5_000),
                "_deferred_fg_update": True,
            }
        ],
    )

    conn = get_db_connection(db_path)
    try:
        fg_row = conn.execute(
            """
            SELECT score, fg_score
            FROM team_buff_fg_loadouts
            WHERE song_name=? AND team_buff='T5'
            """,
            (song,),
        ).fetchone()
        assert fg_row["score"] == 5_000
        assert fg_row["fg_score"] == 5_500

        best_fg_score = conn.execute("SELECT best_fg_score FROM songs WHERE name=?", (song,)).fetchone()[
            "best_fg_score"
        ]
        assert best_fg_score == 5_500
    finally:
        conn.close()


def test_team_buff_fg_loadouts_does_not_update_song_best_fg_score_for_non_t5_tiers(db_path):
    from gear_optimizer.data.database import save_team_buff_loadouts_batch

    song = "Tier FG Song"

    # Ensure the songs row exists so we can assert it remains unchanged by non-T5 tier writes.
    update_song_counters(song, processed_run=False, record_improved=False, db_path=db_path)

    save_team_buff_loadouts_batch(
        song,
        "T10",
        [
            {
                "score": 1000,
                "fg_score": 5000,
                "gear": ["G1"],
                "minis": ["M1"],
                "details": {"tag": "tier_fg"},
                "force": _force_payload(5000, base_score=1000),
            }
        ],
        db_path=db_path,
    )

    conn = get_db_connection(db_path)
    try:
        song_row = conn.execute("SELECT best_score, best_fg_score FROM songs WHERE name=?", (song,)).fetchone()
        assert song_row["best_score"] == 0
        assert song_row["best_fg_score"] == 0

        fg_row = conn.execute(
            "SELECT score, fg_score FROM team_buff_fg_loadouts WHERE song_name=? AND team_buff='T10'",
            (song,),
        ).fetchone()
        assert fg_row["score"] == 1000
        assert fg_row["fg_score"] == 5000
    finally:
        conn.close()


def test_get_best_loadouts_preserves_fg_base_score_pairing(db_path):
    """
    Regression guard: a single loadout hash can have:
    - best base score (from one gem allocation), and
    - best FG score + force payload (from a different allocation).

    `get_best_loadouts()` must preserve the FG table's paired base score so downstream
    FG comparisons use the correct (fg_score > fg_base_score) context.
    """

    from gear_optimizer.data.database import get_best_loadouts, save_team_buff_loadouts_batch

    song = "FG Base Pairing Song"
    gear = ["G1"]
    minis = ["M1"]

    fg_entry = {
        "score": 1000,
        "fg_score": 5000,
        "gear": gear,
        "minis": minis,
        "details": {"tag": "fg"},
        "force": _force_payload(5000, base_score=1000),
    }
    save_team_buff_loadouts_batch(song, "T5", [fg_entry], db_path=db_path)

    # Later, a higher base score is discovered for the same loadout hash (different gem allocation),
    # while the best FG payload remains the older one.
    base_only = {
        "score": 6000,
        "fg_score": 0,
        "gear": gear,
        "minis": minis,
        "details": {"tag": "base"},
        "force": None,
    }
    save_team_buff_loadouts_batch(song, "T5", [base_only], db_path=db_path)

    recs = get_best_loadouts(song, limit=1, team_buff="T5")
    assert recs
    rec = recs[0]
    assert int(rec.get("score") or 0) == 6000
    assert int(rec.get("fg_score") or 0) == 5000
    assert int(rec.get("fg_base_score") or 0) == 1000


def test_fg_score_recovers_from_force_details_when_wrapper_missing(db_path):
    song = "FG Score Recovery Song"

    save_loadouts_batch(
        song,
        [
            {
                "score": 900,
                "fg_score": 0,  # simulate missing wrapper fg_score
                "gear": ["G1"],
                "minis": ["M1"],
                "details": {"tag": "fg_missing_wrapper"},
                # both score locations are observed across pipeline variants
                "force": {**_force_payload(5000, base_score=900), "score": 5000},
            }
        ],
    )

    conn = get_db_connection(db_path)
    try:
        best_fg_score = conn.execute("SELECT best_fg_score FROM songs WHERE name=?", (song,)).fetchone()[
            "best_fg_score"
        ]
        assert best_fg_score == 5000

        row = conn.execute(
            "SELECT score, fg_score, force_details_json FROM team_buff_fg_loadouts WHERE song_name=? AND team_buff='T5'",
            (song,),
        ).fetchone()
        assert row["score"] == 900
        assert row["fg_score"] == 5000
        assert json.loads(row["force_details_json"])["Score"] == 5000
    finally:
        conn.close()


def test_fg_loadouts_keeps_details_for_best_fg_score(db_path):
    song = "FG Details Match Best Score Song"

    save_loadouts_batch(
        song,
        [
            {
                "score": 100,
                "fg_score": 1000,
                "gear": ["G1"],
                "minis": ["M1"],
                "details": {"tag": "best"},
                "force": _force_payload(1000, base_score=100),
            },
            {
                "score": 200,
                "fg_score": 900,
                "gear": ["G1"],
                "minis": ["M1"],
                "details": {"tag": "worse"},
                "force": _force_payload(900, base_score=200, config={"NonFever1": 2}),
            },
        ],
    )

    conn = get_db_connection(db_path)
    try:
        row = conn.execute(
            "SELECT score, fg_score, details_json, force_details_json FROM team_buff_fg_loadouts WHERE song_name=? AND team_buff='T5'",
            (song,),
        ).fetchone()
        assert row["score"] == 100
        assert row["fg_score"] == 1000
        details = _unpack_stats_after_load(json.loads(row["details_json"]))
        assert details["BaseScore"] == 100
        assert details["Stats"]["Rush"] == 100
        assert json.loads(row["force_details_json"])["Score"] == 1000
    finally:
        conn.close()


def test_team_buff_loadouts_downgrade_unmaterializable_fg_score(db_path):
    from gear_optimizer.data.database import get_db_connection, save_team_buff_loadouts_batch

    song = "FG Phantom Score Song"

    save_team_buff_loadouts_batch(
        song,
        "T5",
        [
            {
                "score": 1000,
                "fg_score": 1500,
                "gear": ["G1"],
                "minis": ["M1"],
                "details": {"tag": "phantom", "ForceGreats": {"final_score": 1500}},
                "force": None,
            }
        ],
        db_path=db_path,
    )

    conn = get_db_connection(db_path)
    try:
        row = conn.execute(
            "SELECT score, fg_score, details_json FROM team_buff_loadouts WHERE song_name=? AND team_buff='T5'",
            (song,),
        ).fetchone()
        assert row["score"] == 1000
        assert row["fg_score"] == 1000
        assert "ForceGreats" not in json.loads(row["details_json"])

        fg_row = conn.execute(
            "SELECT score, fg_score FROM team_buff_fg_loadouts WHERE song_name=? AND team_buff='T5'",
            (song,),
        ).fetchone()
        assert fg_row is None
    finally:
        conn.close()


def test_team_buff_loadouts_downgrade_fg_score_after_fg_prune(db_path, monkeypatch):
    from gear_optimizer.data import database

    song = "FG Prune Phantom Score Song"
    monkeypatch.setattr(database, "LOADOUTS_PER_SONG_LIMIT", 1)

    database.save_team_buff_loadouts_batch(
        song,
        "T5",
        [
            {
                "score": 1000,
                "fg_score": 1100,
                "gear": ["G_high_base"],
                "minis": ["M1"],
                "details": {"tag": "high_base", "ForceGreats": {"final_score": 1100}},
                "force": _force_payload(1100, base_score=1000),
            },
            {
                "score": 900,
                "fg_score": 2000,
                "gear": ["G_best_fg"],
                "minis": ["M1"],
                "details": {"tag": "best_fg"},
                "force": _force_payload(2000, base_score=900),
            },
        ],
        db_path=db_path,
    )

    conn = get_db_connection(db_path)
    try:
        row = conn.execute(
            """
            SELECT score, fg_score, details_json, force_details_json
            FROM team_buff_loadouts
            WHERE song_name=? AND team_buff='T5'
            """,
            (song,),
        ).fetchone()
        assert row["score"] == 1000
        assert row["fg_score"] == 1000
        details = json.loads(row["details_json"])
        assert details["tag"] == "high_base"
        assert "ForceGreats" not in details
        assert row["force_details_json"] is None

        fg_row = conn.execute(
            """
            SELECT score, fg_score, force_details_json
            FROM team_buff_fg_loadouts
            WHERE song_name=? AND team_buff='T5'
            """,
            (song,),
        ).fetchone()
        assert fg_row["score"] == 900
        assert fg_row["fg_score"] == 2000
        assert json.loads(fg_row["force_details_json"])["Score"] == 2000
    finally:
        conn.close()


def test_fg_loadouts_details_match_paired_base_score_not_fg_reallocation(db_path):
    song = "FG Details Stay Base Song"
    base_stats = {
        "Perfect Points": 25,
        "Combo Multiplier": 10,
        "Fever Multiplier": 75,
        "Fever Fill Rate": 40,
        "Fever Time": 45,
        "Chill": 0,
        "Flow": 0,
        "Rush": 100,
        "Beat": 20,
        "Vibe": 0,
    }
    fg_base_stats = dict(base_stats)
    fg_base_stats["Fever Multiplier"] = 21
    fg_base_stats["Rush"] = 70

    save_loadouts_batch(
        song,
        [
            {
                "score": 1000,
                "fg_score": 2000,
                "fg_base_score": 1000,
                "gear": ["G1"],
                "minis": ["M1"],
                "details": {
                    "FT": 0,
                    "FF": 0,
                    "GemCounts": {"Fever Multiplier": 21, "Element": 60},
                    "Stats": base_stats,
                    "PrimaryColor": "Rush",
                    "SecondaryColor": "Beat",
                    "SelectedElement": "Rush",
                },
                "force": {
                    "BaseScore": 1000,
                    "Score": 2000,
                    "FT": 16,
                    "FF": 0,
                    "GemCounts": {"Fever Multiplier": 3, "Element": 71},
                    "BaseStats": fg_base_stats,
                    "Selected Element": "Rush",
                    "ForceGreats": {"config": {"NonFever1": 1}, "final_score": 2000},
                },
            }
        ],
    )

    conn = get_db_connection(db_path)
    try:
        row = conn.execute(
            """
            SELECT score, fg_score, details_json, force_details_json
            FROM team_buff_fg_loadouts
            WHERE song_name=? AND team_buff='T5'
            """,
            (song,),
        ).fetchone()
        assert row["score"] == 1000
        assert row["fg_score"] == 2000

        details = _unpack_stats_after_load(json.loads(row["details_json"]))
        assert details["FT"] == 16
        assert details["GemCounts"]["Element"] == 71
        assert details["Stats"]["Fever Time"] == 93
        assert details["Stats"]["Beat"] == 68

        force = json.loads(row["force_details_json"])
        assert force["FT"] == 16
        assert force["BaseStats"]["Fever Time"] == 45
        assert force["ForceGreats"]["final_score"] == 2000
    finally:
        conn.close()


def test_force_payload_refreshes_on_tied_fg_score_when_new_payload_is_better(db_path):
    song = "FG Tie Force Payload Refresh Song"
    gear = ["G1"]
    minis = ["M1"]

    save_loadouts_batch(
        song,
        [
            {
                "score": 100,
                "fg_score": 200,
                "gear": gear,
                "minis": minis,
                "details": {"tag": "first"},
                "force": _force_payload(200, base_score=100, tag="first_force"),
            }
        ],
    )

    conn = get_db_connection(db_path)
    try:
        row0 = conn.execute(
            "SELECT force_details_json FROM team_buff_fg_loadouts WHERE song_name=? AND team_buff='T5'",
            (song,),
        ).fetchone()
        assert row0 is not None
        force0 = json.loads(row0["force_details_json"])
        assert force0.get("tag") == "first_force"
    finally:
        conn.close()

    save_loadouts_batch(
        song,
        [
            {
                "score": 100,
                "fg_score": 200,
                "gear": gear,
                "minis": minis,
                "details": {"tag": "second"},
                "force": _force_payload(200, base_score=100, tag="second_force"),
            }
        ],
    )

    conn = get_db_connection(db_path)
    try:
        row = conn.execute(
            "SELECT force_details_json FROM team_buff_fg_loadouts WHERE song_name=? AND team_buff='T5'",
            (song,),
        ).fetchone()
        assert row is not None
        force = json.loads(row["force_details_json"])
        assert force.get("tag") == "second_force"

        base_row = conn.execute(
            "SELECT force_details_json FROM team_buff_loadouts WHERE song_name=? AND team_buff='T5'",
            (song,),
        ).fetchone()
        assert base_row is not None
        assert base_row["force_details_json"] is None
    finally:
        conn.close()


def test_team_buff_fg_loadouts_force_gems_stay_in_force_payload(db_path, monkeypatch):
    monkeypatch.setattr("gear_optimizer.data.database.get_minis_by_name_cached", lambda: {})

    song = "FG Gem Sync Song"

    # Base details reflect the *base* gem allocation.
    base_details = {
        "tag": "base",
        "FT": 0,
        "FF": 15,
        "GemCounts": {"Perfect Points": 0, "Combo Multiplier": 0, "Fever Multiplier": 10, "Element": 65},
        "Stats": {"dummy": 1},
    }

    # Force payload reflects the *FG* gem allocation that produced the improved fg_score.
    force_details = {
        "score": 200,
        "Score": 200,
        "BaseStats": {"Fever Fill Rate": 10, "Fever Time": 20, "Beat": 5, "Vibe": 7},
        "Stats": {"Fever Fill Rate": 61, "Fever Time": 23, "Beat": 8, "Vibe": 430},
        "GemCounts": {"Perfect Points": 0, "Combo Multiplier": 0, "Fever Multiplier": 10, "Element": 62},
        "FT": 1,
        "FF": 17,
        "Selected Element": "Vibe",
        "ForceGreats": {
            "config": {"NonFever1": 2},
            "final_score": 200,
            "frontier_trace": [
                {
                    "section": 1,
                    "activation_index": 42,
                    "activation_hit_ms": 4200.0,
                    "activation_judgment": "late_great",
                    "fever_end_index": 57,
                }
            ],
        },
    }

    save_loadouts_batch(
        song,
        [
            {
                "score": 100,
                "fg_score": 200,
                "gear": ["G1"],
                "minis": ["M1"],
                "details": base_details,
                "force": force_details,
            }
        ],
    )

    conn = get_db_connection(db_path)
    try:
        row = conn.execute(
            "SELECT score, fg_score, details_json, force_details_json "
            "FROM team_buff_fg_loadouts WHERE song_name=? AND team_buff='T5'",
            (song,),
        ).fetchone()
        assert row is not None
        assert row["score"] == 100
        assert row["fg_score"] == 200

        stored_details = _unpack_stats_after_load(json.loads(row["details_json"])) or {}
        stored_force = json.loads(row["force_details_json"])

        assert stored_force["FT"] == 1
        assert stored_force["FF"] == 17
        assert stored_force["GemCounts"]["Element"] == 62
        assert "Stats" not in stored_force
        assert "score" not in stored_force
        assert stored_force["Score"] == 200
        assert stored_force["ForceGreats"]["frontier_trace"][0]["activation_index"] == 42
        assert stored_force["ForceGreats"]["frontier_trace"][0]["activation_judgment"] == "late_great"

        # The FG leaderboard row's details explain the paired base score for the
        # same FG allocation. The FG score/config replay lives in force_details_json.
        assert stored_details["FT"] == 1
        assert stored_details["FF"] == 17
        assert stored_details["GemCounts"]["Element"] == 62
        assert stored_details["Stats"]["Fever Time"] == 23
        assert "tag" not in stored_details
    finally:
        conn.close()


def test_team_buff_loadouts_reconciles_phantom_fg_without_companion(db_path):
    from gear_optimizer.data.database import get_loadout_hash

    song = "Phantom FG Reconcile Song"
    gear = ["G1"]
    minis = ["M1"]

    save_loadouts_batch(
        song,
        [
            {
                "score": 100,
                "fg_score": 200,
                "gear": gear,
                "minis": minis,
                "details": {"tag": "fg"},
                "force": _force_payload(200, base_score=100),
            }
        ],
    )

    conn = get_db_connection(db_path)
    try:
        conn.execute(
            "DELETE FROM team_buff_fg_loadouts WHERE song_name=? AND team_buff='T5'",
            (song,),
        )
        conn.commit()
    finally:
        conn.close()

    save_loadouts_batch(
        song,
        [
            {
                "score": 50,
                "fg_score": 0,
                "gear": ["G2"],
                "minis": ["M2"],
                "details": {"tag": "base_only"},
                "force": None,
            }
        ],
    )

    conn = get_db_connection(db_path)
    try:
        row = conn.execute(
            "SELECT score, fg_score FROM team_buff_loadouts WHERE song_name=? AND team_buff='T5' AND loadout_hash=?",
            (song, get_loadout_hash(gear, minis)),
        ).fetchone()
        assert row["score"] == 100
        assert row["fg_score"] == 100
    finally:
        conn.close()


def test_base_row_conflict_updates_use_base_score_not_fg_score(db_path, monkeypatch):
    song = "Base Row Conflict Uses Score Not FG"

    # Force the two different loadouts into the same DB row to exercise ON CONFLICT update rules.
    monkeypatch.setattr("gear_optimizer.data.database._loadout_hash_from_names", lambda _g, _m: "CONST_HASH")

    save_loadouts_batch(
        song,
        [
            {
                "score": 200,
                "fg_score": 0,
                "gear": ["G_high"],
                "minis": ["M_high"],
                "details": {"tag": "high_base"},
                "force": None,
            },
            {
                "score": 100,
                "fg_score": 300,
                "gear": ["G_low"],
                "minis": ["M_low"],
                "details": {"tag": "low_base_high_fg"},
                "force": _force_payload(300, base_score=100),
            },
        ],
    )

    conn = get_db_connection(db_path)
    try:
        row = conn.execute(
            "SELECT score, fg_score, gear_ids_blob, details_json, force_details_json "
            "FROM team_buff_loadouts WHERE song_name=? AND team_buff='T5' AND loadout_hash='CONST_HASH'",
            (song,),
        ).fetchone()
        assert row is not None
        assert int(row["score"]) == 200
        assert int(row["fg_score"]) == 300
        from gear_optimizer.data.database import _load_piece_name_encoding_maps, _unpack_id_list

        maps = _load_piece_name_encoding_maps(conn, db_path=db_path)
        gear_ids = _unpack_id_list(row["gear_ids_blob"])
        gear_names = [maps.gear_id_to_name.get(int(i), "") for i in gear_ids]
        gear_names = [n for n in gear_names if n]
        assert gear_names == ["G_high"]
        assert json.loads(row["details_json"]).get("tag") == "high_base"
        assert row["force_details_json"] is None

        fg_row = conn.execute(
            "SELECT score, fg_score, force_details_json "
            "FROM team_buff_fg_loadouts WHERE song_name=? AND team_buff='T5' AND loadout_hash='CONST_HASH'",
            (song,),
        ).fetchone()
        assert fg_row is not None
        assert int(fg_row["score"]) == 100
        assert int(fg_row["fg_score"]) == 300
        assert json.loads(fg_row["force_details_json"]).get("Score") == 300
    finally:
        conn.close()


def test_fg_table_force_payload_tracks_best_fg_not_best_base(db_path, monkeypatch):
    song = "FG Table Force Tracks Best FG"

    monkeypatch.setattr("gear_optimizer.data.database._loadout_hash_from_names", lambda _g, _m: "CONST_HASH")

    save_loadouts_batch(
        song,
        [
            {
                "score": 100,
                "fg_score": 300,
                "gear": ["G_low_base_best_fg"],
                "minis": ["M1"],
                "details": {"tag": "base_low"},
                "force": _force_payload(300, base_score=100),
            },
            {
                "score": 200,
                "fg_score": 250,
                "gear": ["G_high_base_worse_fg"],
                "minis": ["M2"],
                "details": {"tag": "base_high"},
                "force": _force_payload(250, base_score=200, config={"NonFever1": 2}),
            },
        ],
    )

    conn = get_db_connection(db_path)
    try:
        row = conn.execute(
            "SELECT score, fg_score, force_details_json "
            "FROM team_buff_loadouts WHERE song_name=? AND team_buff='T5' AND loadout_hash='CONST_HASH'",
            (song,),
        ).fetchone()
        assert row is not None
        assert int(row["score"]) == 200
        assert int(row["fg_score"]) == 300
        assert row["force_details_json"] is None

        fg_row = conn.execute(
            "SELECT score, fg_score, force_details_json "
            "FROM team_buff_fg_loadouts WHERE song_name=? AND team_buff='T5' AND loadout_hash='CONST_HASH'",
            (song,),
        ).fetchone()
        assert fg_row is not None
        assert int(fg_row["score"]) == 100
        assert int(fg_row["fg_score"]) == 300
        force = json.loads(fg_row["force_details_json"])
        assert int(force.get("Score", 0)) == 300
        assert (force.get("ForceGreats") or {}).get("config") == {"NonFever1": 1}
    finally:
        conn.close()


def test_fg_table_invariant_cleanup_removes_equal_rows(db_path):
    song = "FG Invariant Equal Cleanup"

    save_loadouts_batch(
        song,
        [
            {
                "score": 100,
                "fg_score": 200,
                "gear": ["G1"],
                "minis": ["M1"],
                "details": {"tag": "valid_fg"},
                "force": {"score": 200, "ForceGreats": {"config": {"NonFever1": 1}}},
            }
        ],
    )

    conn = get_db_connection(db_path)
    try:
        conn.execute(
            "UPDATE team_buff_fg_loadouts SET fg_score = score WHERE song_name=? AND team_buff='T5'",
            (song,),
        )
        conn.commit()
    finally:
        conn.close()

    # Trigger invariant cleanup pass for this song.
    save_loadouts_batch(
        song,
        [
            {
                "score": 50,
                "fg_score": 0,
                "gear": ["G2"],
                "minis": ["M2"],
                "details": {"tag": "base_only"},
                "force": None,
            }
        ],
    )

    conn = get_db_connection(db_path)
    try:
        invalid = conn.execute(
            "SELECT COUNT(*) FROM team_buff_fg_loadouts WHERE song_name=? AND team_buff='T5' AND fg_score <= score",
            (song,),
        ).fetchone()[0]
        assert invalid == 0
    finally:
        conn.close()


def test_concurrent_save_loadouts_batch_no_corruption(db_path):
    song = "Concurrent Save Song"

    def _write(score: int) -> None:
        save_loadouts_batch(
            song,
            [
                {
                    "score": score,
                    "fg_score": 0,
                    "gear": [f"G{score}"],
                    "minis": ["M1"],
                    "details": {"score": score},
                    "force": None,
                }
            ],
        )

    scores = list(range(1000, 1010))
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
        futures = [ex.submit(_write, s) for s in scores]
        for f in futures:
            # Propagate exceptions (e.g. SQLITE_BUSY) into the test.
            f.result(timeout=20)

    conn = get_db_connection(db_path)
    try:
        row = conn.execute("SELECT best_score FROM songs WHERE name=?", (song,)).fetchone()
        assert row["best_score"] == max(scores)

        count = conn.execute(
            "SELECT COUNT(*) FROM team_buff_loadouts WHERE song_name=? AND team_buff='T5'",
            (song,),
        ).fetchone()[0]
        assert count == len(scores)
    finally:
        conn.close()


def test_song_attempt_counters_increment_and_reset(db_path):
    song = "Song Attempt Counters Semantics"

    assert get_song_counters(song) == (0, 0, 0, 0)

    # First processed run that establishes any record.
    update_song_counters(song, processed_run=True, record_improved=True)
    conn = get_db_connection(db_path)
    try:
        row = conn.execute("SELECT attempt_lifetime, attempts_first FROM songs WHERE name=?", (song,)).fetchone()
        assert row["attempt_lifetime"] == 1
        assert row["attempts_first"] == 1
    finally:
        conn.close()

    # Another processed run with no improvement.
    update_song_counters(song, processed_run=True, record_improved=False)
    conn = get_db_connection(db_path)
    try:
        row = conn.execute("SELECT attempt_lifetime, attempts_first FROM songs WHERE name=?", (song,)).fetchone()
        assert row["attempt_lifetime"] == 2
        assert row["attempts_first"] == 2
    finally:
        conn.close()

    # Deferred FG-only update: should not increment lifetime, but resets attempts_first on improvement.
    update_song_counters(song, processed_run=False, record_improved=True)
    conn = get_db_connection(db_path)
    try:
        row = conn.execute("SELECT attempt_lifetime, attempts_first FROM songs WHERE name=?", (song,)).fetchone()
        assert row["attempt_lifetime"] == 2
        assert row["attempts_first"] == 1
    finally:
        conn.close()
