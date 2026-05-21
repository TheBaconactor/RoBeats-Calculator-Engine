from __future__ import annotations

import os
from typing import Dict, List, Tuple

from gear_optimizer.core.constants import SCRIPT_DIR
from gear_optimizer.data.song_io import scan_song_header


def get_songs_by_elemental_combo(paths: dict) -> Dict[Tuple[str, str], List[dict]]:
    """
    Scan song files and group by (Primary Color, Secondary Color).

    Returns:
        Dict mapping (primary, secondary) tuples to lists of song info dicts
    """
    songs_by_combo: Dict[Tuple[str, str], List[dict]] = {}

    for diff in ["Hard", "Normal", "Easy"]:
        search_dir = paths.get(diff, SCRIPT_DIR)
        if not os.path.exists(search_dir):
            continue

        for root, _, files in os.walk(search_dir):
            for fname in files:
                if not fname.lower().endswith(".txt"):
                    continue

                fp = os.path.join(root, fname)
                meta = scan_song_header(fp)
                if not meta:
                    continue

                song_name = meta.get("Song Name", "")
                primary = (meta.get("Primary Color") or "").strip()
                secondary = (meta.get("Secondary Color") or "").strip()

                if not song_name or not primary:
                    continue

                key = (primary, secondary)
                songs_by_combo.setdefault(key, []).append(
                    {
                        "song_name": song_name,
                        "file_path": fp,
                        "difficulty": diff,
                        "primary": primary,
                        "secondary": secondary,
                    }
                )

    return songs_by_combo
