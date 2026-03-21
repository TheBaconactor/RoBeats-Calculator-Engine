import concurrent.futures
import json

import pytest

from gear_optimizer.data.database import (
    get_db_connection,
    get_song_counters,
    init_db,
    save_loadouts_batch,
    update_song_counters,
)


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "test_persistence.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(path))
    init_db()
    return str(path)


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
            "SELECT minis_json FROM team_buff_loadouts WHERE song_name=? AND team_buff='T5'",
            (song,),
        ).fetchall()
        assert len(rows) == 1
        groups = json.loads(rows[0]["minis_json"])
        assert groups == [["MiniA", "MiniB"]]
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
            "SELECT minis_json FROM team_buff_loadouts WHERE song_name=? AND team_buff='T5'",
            (song,),
        ).fetchall()
        assert len(rows) == 1
        groups = json.loads(rows[0]["minis_json"])
        assert groups == [["MiniA", "MiniB"]]
    finally:
        conn.close()


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
                "force": {"score": 5000, "details": {"ForceGreats": {"config": {"NonFever1": 1}}}},
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
                "force": {"score": 4500, "details": {"ForceGreats": {"config": {"NonFever1": 1}}}},
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
                "force": {"score": 900, "details": {"ForceGreats": {"config": {"NonFever1": 1}}}},
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
                "force": {"score": 5000, "details": {"ForceGreats": {"config": {"NonFever1": 1}}}},
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
        "force": {"score": 5000, "details": {"ForceGreats": {"config": {"NonFever1": 1}}}},
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
                "force": {
                    # both of these are observed shapes across pipeline variants
                    "score": 5000,
                    "details": {"ForceGreats": {"config": {"NonFever1": 1}, "final_score": 5000}},
                },
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
        assert json.loads(row["force_details_json"])["score"] == 5000
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
                "force": {"score": 1000, "details": {"ForceGreats": {"config": {"NonFever1": 1}}}},
            },
            {
                "score": 200,
                "fg_score": 900,
                "gear": ["G1"],
                "minis": ["M1"],
                "details": {"tag": "worse"},
                "force": {"score": 900, "details": {"ForceGreats": {"config": {"NonFever1": 2}}}},
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
        assert json.loads(row["details_json"])["tag"] == "best"
        assert json.loads(row["force_details_json"])["score"] == 1000
    finally:
        conn.close()


def test_force_payload_refreshes_on_tied_fg_score_when_new_payload_has_hitsim_delta(db_path):
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
                "force": {"score": 200, "ForceGreats": {"config": {"NonFever1": 1}}},
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
        assert (force0.get("ForceGreats") or {}).get("hitsim_offset_delta_ms") is None
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
                "force": {
                    "score": 200,
                    "ForceGreats": {"config": {"NonFever1": 1}, "hitsim_offset_delta_ms": 37},
                },
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
        assert (force.get("ForceGreats") or {}).get("hitsim_offset_delta_ms") == 37

        base_row = conn.execute(
            "SELECT force_details_json FROM team_buff_loadouts WHERE song_name=? AND team_buff='T5'",
            (song,),
        ).fetchone()
        assert base_row is not None
        base_force = json.loads(base_row["force_details_json"])
        assert (base_force.get("ForceGreats") or {}).get("hitsim_offset_delta_ms") == 37
    finally:
        conn.close()


def test_team_buff_fg_loadouts_details_syncs_force_gems_when_available(db_path, monkeypatch):
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
        "BaseStats": {"Fever Fill Rate": 10, "Fever Time": 20, "Beat": 5, "Vibe": 7},
        "GemCounts": {"Perfect Points": 0, "Combo Multiplier": 0, "Fever Multiplier": 10, "Element": 62},
        "FT": 1,
        "FF": 17,
        "Selected Element": "Vibe",
        "ForceGreats": {"config": {"NonFever1": 2}, "final_score": 200},
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

        stored_details = json.loads(row["details_json"])
        stored_force = json.loads(row["force_details_json"])

        assert stored_force["FT"] == 1
        assert stored_force["FF"] == 17
        assert stored_force["GemCounts"]["Element"] == 62

        # The FG leaderboard row should show the FG gem allocation (not the base one).
        assert stored_details["FT"] == 1
        assert stored_details["FF"] == 17
        assert stored_details["GemCounts"]["Element"] == 62
        assert stored_details["ForceGreats"]["final_score"] == 200

        stats = stored_details["Stats"]
        assert stats["Fever Time"] == 23  # 20 + 1*3
        assert stats["Fever Fill Rate"] == 61  # 10 + 17*3
        assert stats["Beat"] == 8  # 5 + 1*3
        assert stats["Vibe"] == 430  # 7 + 17*3 + 62*6
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
                "force": {"score": 300, "ForceGreats": {"config": {"NonFever1": 1}}},
            },
        ],
    )

    conn = get_db_connection(db_path)
    try:
        row = conn.execute(
            "SELECT score, fg_score, gear_json, details_json, force_details_json "
            "FROM team_buff_loadouts WHERE song_name=? AND team_buff='T5' AND loadout_hash='CONST_HASH'",
            (song,),
        ).fetchone()
        assert row is not None
        assert int(row["score"]) == 200
        assert int(row["fg_score"]) == 300
        assert json.loads(row["gear_json"]) == ["G_high"]
        assert json.loads(row["details_json"]).get("tag") == "high_base"
        assert json.loads(row["force_details_json"]).get("score") == 300
    finally:
        conn.close()


def test_base_row_force_payload_tracks_best_fg_not_best_base(db_path, monkeypatch):
    song = "Base Row Force Tracks Best FG"

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
                "force": {"score": 300, "ForceGreats": {"config": {"NonFever1": 1}}},
            },
            {
                "score": 200,
                "fg_score": 250,
                "gear": ["G_high_base_worse_fg"],
                "minis": ["M2"],
                "details": {"tag": "base_high"},
                "force": {"score": 250, "ForceGreats": {"config": {"NonFever1": 2}}},
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
        force = json.loads(row["force_details_json"])
        assert int(force.get("score", 0)) == 300
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
            "SELECT COUNT(*) FROM team_buff_fg_loadouts "
            "WHERE song_name=? AND team_buff='T5' AND fg_score <= score",
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
