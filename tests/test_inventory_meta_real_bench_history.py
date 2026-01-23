import sqlite3
from pathlib import Path

from inventory_optimizer.real_bench import (
    build_benchmark_suite,
    compute_db_song_signature,
    find_previous_run,
    make_benchmark_config_sig,
)


def _make_min_db(path: Path, song_names: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    try:
        conn.execute(
            """
            CREATE TABLE songs (
                name TEXT PRIMARY KEY,
                best_score INTEGER DEFAULT 0,
                best_fg_score INTEGER DEFAULT 0,
                last_updated INTEGER DEFAULT 0
            );
            """
        )
        for name in song_names:
            conn.execute(
                "INSERT INTO songs(name, best_score, best_fg_score, last_updated) VALUES(?, 0, 0, 0)",
                (name,),
            )
        conn.commit()
    finally:
        conn.close()


def test_real_bench_suite_modes() -> None:
    suite_fast, _cfg_fast = build_benchmark_suite("fast")
    assert [lbl for (lbl, _el) in suite_fast] == ["Chill", "All"]

    suite_precise, _cfg_precise = build_benchmark_suite("precise")
    assert [lbl for (lbl, _el) in suite_precise] == ["Chill", "Vibe", "Flow", "Rush", "Beat", "All"]


def test_real_bench_db_song_signature_changes_when_songs_added(tmp_path: Path) -> None:
    db_path = tmp_path / "evolution.db"
    _make_min_db(db_path, ["a", "b"])
    sig1 = compute_db_song_signature(db_path)

    # Add a new song entry -> signature must change.
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("INSERT INTO songs(name, best_score, best_fg_score, last_updated) VALUES(?, 0, 0, 0)", ("c",))
        conn.commit()
    finally:
        conn.close()

    sig2 = compute_db_song_signature(db_path)
    assert sig1 != sig2
    assert sig2["songs_total"] == 3


def test_real_bench_ignores_previous_history_when_song_set_changes(tmp_path: Path) -> None:
    db_path = tmp_path / "evolution.db"
    _make_min_db(db_path, ["a", "b"])
    db_sig1 = compute_db_song_signature(db_path)

    _suite, cfg = build_benchmark_suite("fast")
    base_kwargs = {
        "gpu_full_witness_anchor_patterns": 24,
        "gpu_full_witness_seed_streams": 4,
        "gpu_full_witness_pattern_profile": 0,
        "gpu_full_wildcard_palette_size": 256,
    }
    config_sig = make_benchmark_config_sig(mode="fast", seed=1, inventory_cap=100, cfg=cfg, base_kwargs=base_kwargs)

    history = {
        "schema_version": 2,
        "runs": [
            {
                "db_path": str(db_path),
                "config_sig": config_sig,
                "db_song_signature": db_sig1,
                "results_by_label": {"Chill": {"songs_covered": 1}, "All": {"songs_covered": 2}},
                "ts_utc": "2026-01-01T00:00:00Z",
                "git_sha": "deadbeef",
            }
        ],
    }

    prev, reason = find_previous_run(history, db_path=db_path, config_sig=config_sig, db_sig=db_sig1)
    assert prev is not None
    assert reason is None

    # Change song set -> same config, but signature mismatch should invalidate comparisons.
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("INSERT INTO songs(name, best_score, best_fg_score, last_updated) VALUES(?, 0, 0, 0)", ("c",))
        conn.commit()
    finally:
        conn.close()

    db_sig2 = compute_db_song_signature(db_path)
    prev2, reason2 = find_previous_run(history, db_path=db_path, config_sig=config_sig, db_sig=db_sig2)
    assert prev2 is None
    assert reason2 == "db_song_signature_changed"

