"""Song Helpers - Database Context - the previous best record and the stored best scores of a song."""

import logging
import sqlite3

from ...settings import paths
from ...store import legacy, schema
from ...store.db import load_boards

logger = logging.getLogger(__name__)


def build_db_key(found_song_name: str) -> str:
    """A song's DB key: its name (timing models share one namespace)."""
    return str(found_song_name or "").strip()


def load_database_progress_baseline(found_song_name, *, team_buff: str = "T5"):
    """
    The song's previous best record and its boards' best scores.

    Returns:
        (prev_record, db_best_score, db_best_fg_score, baseline_valid): prev_record is the meta board's top
        entry (version 18 shaped, items as names) or None; baseline_valid is False when the database cannot
        be read (the app creates it at startup, so a readable empty database is a valid empty baseline).
    """
    song = str(found_song_name or "").strip()
    tier = str(team_buff or "T5")
    path = paths().database
    try:
        conn = schema.connect(path)
    except (sqlite3.Error, schema.StoreVersionError):
        logger.warning("[DB] cannot read %s", path, exc_info=True)
        return None, 0, 0, False
    try:
        entries = legacy.best_loadouts(conn, song, tier, limit=1)
        boards = load_boards(conn, song, tier)
    except sqlite3.Error:
        logger.warning("[DB] cannot read %s for %s", path, song, exc_info=True)
        return None, 0, 0, False
    finally:
        conn.close()
    best_score = max((x.score for x in boards.meta), default=0)
    best_fg_score = max((x.fg_score for x in boards.fg), default=0)
    return (entries[0] if entries else None), best_score, best_fg_score, True
