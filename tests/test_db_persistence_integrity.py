import concurrent.futures
import json

import pytest

from gear_optimizer.data.database import get_db_connection, init_db, save_loadouts_batch


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "test_persistence.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(path))
    init_db()
    return str(path)


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
        song_row = conn.execute(
            "SELECT best_score, best_fg_score FROM songs WHERE name=?", (song,)
        ).fetchone()
        assert song_row["best_score"] == 1100
        assert song_row["best_fg_score"] == 5000

        fg_count = conn.execute(
            "SELECT COUNT(*) FROM fg_loadouts WHERE song_name=?", (song,)
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
            "SELECT COUNT(*) FROM loadouts WHERE song_name=?", (song,)
        ).fetchone()[0]
        fg_count = conn.execute(
            "SELECT COUNT(*) FROM fg_loadouts WHERE song_name=?", (song,)
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
            "SELECT COUNT(*) FROM loadouts WHERE song_name=?", (song,)
        ).fetchone()[0]
        fg_count = conn.execute(
            "SELECT COUNT(*) FROM fg_loadouts WHERE song_name=?", (song,)
        ).fetchone()[0]
        best_fg_score = conn.execute(
            "SELECT best_fg_score FROM songs WHERE name=?", (song,)
        ).fetchone()["best_fg_score"]
        assert loadouts_count == 1
        assert fg_count == 0
        assert best_fg_score == 0
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
            "SELECT score, fg_score, details_json, force_details_json FROM fg_loadouts WHERE song_name=?",
            (song,),
        ).fetchone()
        assert row["score"] == 100
        assert row["fg_score"] == 1000
        assert json.loads(row["details_json"])["tag"] == "best"
        assert json.loads(row["force_details_json"])["score"] == 1000
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
        row = conn.execute(
            "SELECT best_score FROM songs WHERE name=?", (song,)
        ).fetchone()
        assert row["best_score"] == max(scores)

        count = conn.execute(
            "SELECT COUNT(*) FROM loadouts WHERE song_name=?", (song,)
        ).fetchone()[0]
        assert count == len(scores)
    finally:
        conn.close()
