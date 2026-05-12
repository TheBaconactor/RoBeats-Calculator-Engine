from __future__ import annotations

import os
import typing
from typing import Any

from gear_optimizer.data.song_io import scan_song_header as _scan_song_header

def infer_song_difficulty_from_path(root: str) -> str:
    parent_folder = os.path.basename(str(root or "")).lower()
    if parent_folder == "hard":
        return "Hard"
    if parent_folder == "normal":
        return "Normal"
    if parent_folder == "easy":
        return "Easy"
    return "Unknown"


def song_index_roots(*, data_root: str, script_dir: str) -> list[str]:
    if os.path.exists(data_root):
        return [data_root]
    return [script_dir]


def scan_song_paths_for_index(
    roots: typing.Sequence[str],
    *,
    stop_requested: typing.Callable[[], bool],
    scan_song_header: typing.Callable[[str], dict | None],
) -> dict[str, list[dict[str, str]]]:
    index: dict[str, list[dict[str, str]]] = {}
    seen_paths: set[str] = set()
    for root_dir in roots:
        if not os.path.exists(root_dir):
            continue
        if stop_requested():
            break
        for current_root, _, files in os.walk(root_dir):
            if stop_requested():
                break
            for file_name in files:
                if stop_requested():
                    break
                if not str(file_name or "").lower().endswith(".txt"):
                    continue
                fp = os.path.join(current_root, file_name)
                abs_fp = os.path.abspath(fp)
                if abs_fp in seen_paths:
                    continue
                seen_paths.add(abs_fp)

                meta = scan_song_header(fp)
                if not meta:
                    continue
                song_name = str(meta.get("Song Name") or "").strip()
                if not song_name:
                    continue

                detected_diff = infer_song_difficulty_from_path(current_root)
                index.setdefault(song_name, []).append(
                    {
                        "fp": fp,
                        "abs_fp": abs_fp,
                        "song_name": song_name,
                        "song_name_lower": song_name.lower(),
                        "detected_diff": detected_diff,
                        "primary_color": str(meta.get("Primary Color") or "").strip().lower(),
                        "secondary_color": str(meta.get("Secondary Color") or "").strip().lower(),
                    }
                )
    return index


def ensure_song_path_index(app: Any, *, roots: tuple[str, ...], force: bool = False) -> None:
    with app._song_path_index_lock:
        if not force and app._song_path_index_ready and roots == app._song_path_index_roots:
            return
    index = scan_song_paths_for_index(
        roots,
        stop_requested=app._stop_requested_now,
        scan_song_header=_scan_song_header,
    )
    with app._song_path_index_lock:
        app._song_path_index = index
        app._song_path_index_ready = True
        app._song_path_index_roots = roots


def build_song_queue_from_pending_ids(
    app: Any,
    pending_song_ids: typing.Sequence[str],
    *,
    diff_lower: str,
    filter_search: str,
    target_primary_all: bool,
    target_primary_colors: set[str],
    target_secondary_all: bool,
    target_secondary_colors: set[str],
) -> tuple[list[tuple[str, str, str]], list[str]]:
    roots = tuple(app._song_index_roots())
    ensure_song_path_index(app, roots=roots, force=False)
    with app._song_path_index_lock:
        index_snapshot = dict(app._song_path_index)

    song_queue: list[tuple[str, str, str]] = []
    unresolved_song_ids: list[str] = []
    seen_paths: set[str] = set()
    for pending_song_id in pending_song_ids:
        song_id = str(pending_song_id or "").strip()
        if not song_id:
            continue
        entries = index_snapshot.get(song_id)
        if not isinstance(entries, list) or not entries:
            unresolved_song_ids.append(song_id)
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            detected_diff = str(entry.get("detected_diff") or "Unknown").strip() or "Unknown"
            if diff_lower in ("easy", "normal", "hard") and detected_diff.lower() != diff_lower:
                continue

            primary_color = str(entry.get("primary_color") or "").strip().lower()
            secondary_color = str(entry.get("secondary_color") or "").strip().lower()
            if not target_primary_all and (not primary_color or primary_color not in target_primary_colors):
                continue
            if not target_secondary_all and (not secondary_color or secondary_color not in target_secondary_colors):
                continue

            song_name_lower = str(entry.get("song_name_lower") or "").strip().lower()
            if filter_search and filter_search not in song_name_lower:
                continue

            fp = str(entry.get("fp") or "").strip()
            abs_fp = str(entry.get("abs_fp") or "").strip()
            if not fp:
                continue
            if abs_fp and abs_fp in seen_paths:
                continue
            if abs_fp:
                seen_paths.add(abs_fp)
            song_name = str(entry.get("song_name") or song_id).strip() or song_id
            song_queue.append((fp, song_name, detected_diff))
    return song_queue, unresolved_song_ids
