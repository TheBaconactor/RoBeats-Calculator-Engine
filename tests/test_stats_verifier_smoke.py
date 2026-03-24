import json

from gear_optimizer.data.database import get_db_connection, init_db, save_loadouts_batch
from gear_optimizer.data.stats_verifier import verify_and_repair_stats


def test_stats_verifier_smoke(tmp_path, monkeypatch):
    """
    StatsVerifier should be a verifier (tests/tooling) rather than a production runtime step.

    This smoke test ensures:
    - persistence never leaves Stats empty when saving a loadout, and
    - the verifier reports a clean DB on a fresh temp database.
    """

    db_path = tmp_path / "evolution.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))
    init_db()

    song_name = "StatsVerifier Smoke Song"
    # Intentionally omit details["Stats"] to exercise the persistence fallback.
    save_loadouts_batch(
        song_name,
        [
            {
                "score": 1234,
                "fg_score": 0,
                # Use real item names from Data/Gear so stats reconstruction can succeed.
                "gear": ["The Games: Hidden Shine"],
                "minis": ["Monstercat"],
                "details": {
                    "GemCounts": {},
                    "FF": 0,
                    "FT": 0,
                    "PrimaryColor": "Rush",
                    "SecondaryColor": "Flow",
                    "SelectedElement": "Rush",
                },
                "force": None,
            }
        ],
        db_path=str(db_path),
    )

    with get_db_connection(str(db_path)) as conn:
        row = conn.execute(
            "SELECT details_json FROM team_buff_loadouts WHERE song_name = ? AND team_buff = 'T5'",
            (song_name,),
        ).fetchone()
        assert row is not None
        details = json.loads(str(row["details_json"] or "{}"))
        stats_obj = details.get("Stats")
        assert isinstance(stats_obj, dict) and stats_obj

    all_valid, stats = verify_and_repair_stats(dry_run=True, verbose=False, sample_size=0)
    assert all_valid
    assert int(stats.get("missing", 0) or 0) == 0
    assert int(stats.get("empty", 0) or 0) == 0
    assert int(stats.get("fg_empty", 0) or 0) == 0

