"""Song Helpers - Database Context - a song's stored best scores (the progress counter's baseline)."""

import logging
import sqlite3
from dataclasses import dataclass

from ...core.team_buff import OPTIMIZER_BASELINE_TEAM_BUFF
from ...settings import paths
from ...store import schema
from ...store.db import load_boards

logger = logging.getLogger(__name__)


def build_db_key(found_song_name: str) -> str:
    """A song's DB key: its name (timing models share one namespace)."""
    return str(found_song_name or "").strip()


@dataclass(frozen=True, slots=True)
class SongDbBaseline:
    """A song's stored best meta and FG scores. `valid` is False when the database cannot be read (the app creates
    it at startup, so a readable empty database is a valid empty baseline)."""

    db_key: str
    best_score: int
    best_fg_score: int
    valid: bool


def load_song_db_baseline(found_song_name: str, *, team_buff: str = OPTIMIZER_BASELINE_TEAM_BUFF) -> SongDbBaseline:
    key = build_db_key(found_song_name)
    path = paths().database
    try:
        conn = schema.connect(path)
    except (sqlite3.Error, schema.StoreVersionError):
        logger.warning("[DB] cannot read %s", path, exc_info=True)
        return SongDbBaseline(key, 0, 0, False)
    try:
        boards = load_boards(conn, key, team_buff)
    except sqlite3.Error:
        logger.warning("[DB] cannot read %s for %s", path, key, exc_info=True)
        return SongDbBaseline(key, 0, 0, False)
    finally:
        conn.close()
    best_score = max((x.score for x in boards.meta), default=0)
    best_fg_score = max((x.fg_score for x in boards.fg), default=0)
    return SongDbBaseline(key, best_score, best_fg_score, True)
