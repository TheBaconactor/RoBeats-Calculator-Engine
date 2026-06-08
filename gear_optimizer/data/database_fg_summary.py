"""Base-table embedded FG summary normalization and post-prune repair."""

from __future__ import annotations

import sqlite3
from typing import Any

from gear_optimizer.core.utils import safe_int
from gear_optimizer.data.database_codecs import _json_dumps_compact, _json_loads


def normalize_embedded_fg_force_summary(
    details: Any,
    *,
    score: int,
    fg_score: int,
    keep_fg: bool,
    preserve_attempt_meta: bool = False,
) -> dict:
    if not isinstance(details, dict):
        return {}
    out = dict(details)
    if not preserve_attempt_meta:
        out.pop("attempt_lifetime", None)
        out.pop("attempts_first", None)
    fg_meta = out.get("ForceGreats")
    if not isinstance(fg_meta, dict):
        return out
    if not keep_fg or int(fg_score or 0) <= int(score or 0):
        out.pop("ForceGreats", None)
        return out
    fg_out = dict(fg_meta)
    fg_out["final_score"] = int(fg_score)
    if out is details:
        out = dict(out)
    out["ForceGreats"] = fg_out
    return out


def normalize_details_for_persistence(
    details: Any,
    *,
    score: int,
    fg_score: int,
    force_data: Any,
    preserve_attempt_meta: bool = False,
) -> dict:
    return normalize_embedded_fg_force_summary(
        details,
        score=score,
        fg_score=fg_score,
        keep_fg=force_data is not None,
        preserve_attempt_meta=preserve_attempt_meta,
    )


def normalize_base_details_force_summary(
    details: Any,
    *,
    score: int,
    fg_score: int,
    has_paired_fg: bool,
) -> dict:
    return normalize_embedded_fg_force_summary(
        details,
        score=score,
        fg_score=fg_score,
        keep_fg=bool(has_paired_fg),
        preserve_attempt_meta=False,
    )


def repair_base_loadout_fg_summaries(conn: sqlite3.Connection, *, song_name: str, team_buff: str) -> None:
    """Re-sync base embedded FG summaries after FG row pruning."""
    rows = conn.execute(
        """
        SELECT
            b.loadout_hash,
            b.score,
            b.fg_score,
            b.details_json,
            COALESCE((
                SELECT MAX(f.fg_score)
                FROM team_buff_fg_loadouts f
                WHERE f.song_name = b.song_name
                AND f.team_buff = b.team_buff
                AND f.loadout_hash = b.loadout_hash
            ), 0) AS paired_fg_score
        FROM team_buff_loadouts b
        WHERE b.song_name = ?
        AND b.team_buff = ?
        AND (
            b.fg_score > b.score
            OR b.details_json LIKE '%ForceGreats%'
        )
        """,
        (song_name, team_buff),
    ).fetchall()
    updates: list[tuple[int, str | None, str, str, str]] = []
    for row in rows:
        score = safe_int(row["score"], 0)
        fg_score = safe_int(row["fg_score"], 0)
        paired_fg_score = safe_int(row["paired_fg_score"], 0)
        has_paired_fg = paired_fg_score > score
        normalized_fg_score = paired_fg_score if has_paired_fg else score

        details = _json_loads(row["details_json"]) if row["details_json"] else {}
        normalized_details = normalize_base_details_force_summary(
            details,
            score=score,
            fg_score=normalized_fg_score,
            has_paired_fg=has_paired_fg,
        )
        normalized_details_json = _json_dumps_compact(normalized_details) if normalized_details else None
        if int(normalized_fg_score) == int(fg_score) and normalized_details_json == row["details_json"]:
            continue
        updates.append(
            (
                int(normalized_fg_score),
                normalized_details_json,
                song_name,
                team_buff,
                str(row["loadout_hash"] or ""),
            )
        )
    if updates:
        conn.executemany(
            """
            UPDATE team_buff_loadouts
            SET fg_score = ?,
                details_json = ?
            WHERE song_name = ?
            AND team_buff = ?
            AND loadout_hash = ?
            """,
            updates,
        )
