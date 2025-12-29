from gear_optimizer.data.database import get_db_connection, prioritize_song_queue_missing_db


def test_prioritize_song_queue_missing_db_places_new_songs_first():
    song_in_db = "Already In DB (Hard)"
    song_missing = "Not In DB Yet (Hard)"

    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO songs (name, best_score, best_fg_score, last_updated) VALUES (?, ?, ?, ?)",
            (song_in_db, 123, 0, 0.0),
        )
        conn.commit()
    finally:
        conn.close()

    song_queue = [
        ("path_existing.txt", song_in_db, "Hard"),
        ("path_missing.txt", song_missing, "Hard"),
    ]

    prioritized = prioritize_song_queue_missing_db(song_queue)
    assert [item[1] for item in prioritized] == [song_missing, song_in_db]
