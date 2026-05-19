from __future__ import annotations

import os


def infer_song_difficulty_from_path(root: str) -> str:
    parent_folder = os.path.basename(str(root or "")).lower()
    if parent_folder == "hard":
        return "Hard"
    if parent_folder == "normal":
        return "Normal"
    if parent_folder == "easy":
        return "Easy"
    return "Unknown"
