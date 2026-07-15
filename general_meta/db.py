from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

import sqlite3

from gear_optimizer.data.database import get_db_connection_readonly
from gear_optimizer.data.loadout_equivalence import representative_mini_names
from gear_optimizer.core.team_buff import normalize_team_buff, team_buff_query_values
from gear_optimizer.data.database import get_evolution_db_path


def _get_all_loadouts_rows(*, team_buff: str = "T5") -> list[dict[str, Any]]:
    resolved_team_buff = normalize_team_buff(team_buff, default="T5")
    query_team_buffs = team_buff_query_values(resolved_team_buff, default=resolved_team_buff)
    db_path = get_evolution_db_path()
    conn = get_db_connection_readonly(db_path)
    try:
        rows: list[dict[str, Any]] = []
        placeholders = ",".join("?" for _ in query_team_buffs)
        params = tuple(query_team_buffs)

        cursor = conn.execute(
            """
            SELECT song_name, score, fg_score, gear_ids_blob, minis_ids_blob, details_json
            FROM team_buff_loadouts
            WHERE UPPER(team_buff) IN ({placeholders})
            """.format(placeholders=placeholders),
            params,
        )
        rows.extend(_decode_loadout_rows(cursor, db_path=db_path))

        cursor = conn.execute(
            """
            SELECT song_name, score, fg_score, gear_ids_blob, minis_ids_blob, details_json
            FROM team_buff_fg_loadouts
            WHERE UPPER(team_buff) IN ({placeholders})
            """.format(placeholders=placeholders),
            params,
        )
        rows.extend(_decode_loadout_rows(cursor, db_path=db_path))
        return rows
    finally:
        conn.close()


def _decode_loadout_rows(cursor: Iterable[sqlite3.Row], *, db_path: str) -> list[dict[str, Any]]:
    from gear_optimizer.data.database import _load_piece_name_encoding_maps, _unpack_id_groups, _unpack_id_list

    conn = getattr(cursor, "connection", None)
    if conn is None:
        raise RuntimeError("SQLite cursor is missing its owning connection")
    maps = _load_piece_name_encoding_maps(conn, db_path=db_path)

    rows: list[dict[str, Any]] = []
    for row in cursor:
        gear_ids = _unpack_id_list(row["gear_ids_blob"]) if row["gear_ids_blob"] else []
        gear_names = [str(maps.gear_id_to_name.get(int(i), "") or "") for i in gear_ids if int(i) > 0]
        gear_names = [name for name in gear_names if name]

        mini_groups: list[list[str]] = []
        for group in _unpack_id_groups(row["minis_ids_blob"]) if row["minis_ids_blob"] else []:
            if not group:
                continue
            names = [str(maps.mini_id_to_name.get(int(i), "") or "") for i in group if int(i) > 0]
            names = [name for name in names if name]
            if names:
                mini_groups.append(names)

        rows.append(
            {
                "song_name": row["song_name"],
                "score": row["score"],
                "fg_score": row["fg_score"],
                "gear": gear_names,
                "mini_groups": mini_groups,
                "minis": representative_mini_names(mini_groups),
                "details_json": row["details_json"],
            }
        )
    return rows


def get_all_loadouts_from_db(*, team_buff: str = "T5") -> list[dict[str, Any]]:
    return _get_all_loadouts_rows(team_buff=team_buff)


def _replay_seed_limit(limit: int) -> int:
    """
    Oversample baseline DB rows before replaying them. Stored baseline scores can drift
    from the replay contract over time, so fetching exactly top-N by raw DB score can
    exclude rows that should bubble back into the canonical replayed ordering. Bounded to
    avoid pathological work.
    """
    limit_i = max(1, int(limit))
    return max(limit_i, min(512, max(limit_i * 8, 128)))


def prepare_team_buff_tier_replay(
    *,
    song_name: str,
    song_file: str,
    limit: int,
    element: str,
    team_color: str | None,
    cfg_dict: Mapping[str, Any] | None = None,
    ref_arrays: Mapping[str, Any] | None = None,
) -> tuple[dict, dict, list[dict], dict, str | None]:
    """
    Build the shared replay context for a song's on-demand TeamBuff tier views:
    (cfg_dict, Stats ref_arrays, canonicalized seed entries, calc_song, team-color override).

    Read-only seed preparation over persisted loadouts; all scoring stays on the existing
    GPU/Taichi replay path (`build_team_buff_tier_db_batches`). This function is the
    canonical shared replay-context owner.
    """
    from gear_optimizer.app_async_db import _get_team_buff_ref_arrays_cached
    from gear_optimizer.core.config import load_config
    from gear_optimizer.core.team_buff import resolve_baseline_team_buff_from_cfg_dict
    from gear_optimizer.core.utils import cfg_to_dict
    from gear_optimizer.data.database import get_best_loadouts
    from gear_optimizer.data.loadout_equivalence import get_gears_by_name_cached, get_minis_by_name_cached
    from gear_optimizer.data.song_io import clone_calc_song, get_base_calc_song
    from gear_optimizer.helpers.song_helpers.persistence_canon import (
        ReplayContext,
        canonicalize_baseline_entries,
    )

    cfg_dict_local = dict(cfg_dict) if cfg_dict is not None else cfg_to_dict(load_config())

    if ref_arrays is not None:
        ref_arrays_local = dict(ref_arrays)
    else:
        ref_arrays_local = _get_team_buff_ref_arrays_cached()
        if ref_arrays_local is None:
            raise RuntimeError("ref_arrays unavailable (failed to load Stats lookup tables)")

    baseline_team_buff = resolve_baseline_team_buff_from_cfg_dict(cfg_dict_local, default="T5")
    # The zero_ms/perfect_window tier re-solve path (_entry_loadout_items) requires each
    # seed entry's `gear`/`minis` to be full stat dicts, not name strings. Passing the
    # cached name->stats maps makes get_best_loadouts expand names into stat dicts.
    entries = get_best_loadouts(
        str(song_name),
        limit=_replay_seed_limit(int(limit)),
        gears_by_name=get_gears_by_name_cached(),
        minis_by_name=get_minis_by_name_cached(),
        team_buff=str(baseline_team_buff),
    )

    calc_song = clone_calc_song(get_base_calc_song(str(song_file), cfg_dict_local))
    entries = canonicalize_baseline_entries(
        list(entries),
        replay_ctx=ReplayContext(
            calc_song=calc_song,
            ref_arrays=ref_arrays_local,
            cfg_dict=cfg_dict_local,
        ),
    )

    target_team_color_override: str | None = None
    if team_color:
        target_team_color_override = str(team_color)
    else:
        mode = str(element or "selected").strip().lower()
        meta0 = (calc_song.get("metadata") or {}) if isinstance(calc_song, dict) else {}
        primary_color = str(meta0.get("Primary Color", "") or "").strip()
        secondary_color = str(meta0.get("Secondary Color", "") or "").strip()
        if mode == "primary" and primary_color:
            target_team_color_override = primary_color
        elif mode == "secondary":
            target_team_color_override = secondary_color or primary_color or None

    return cfg_dict_local, ref_arrays_local, entries, calc_song, target_team_color_override


__all__ = ["get_all_loadouts_from_db", "prepare_team_buff_tier_replay"]
