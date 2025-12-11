"""
Job queue management for the gear optimizer.

This module handles building filtering, and managing the queue of songs
to be processed. It encapsulates the directory scanning and filtering logic.
"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Iterator

from ..core.constants import PATHS, SCRIPT_DIR
from .song_processor import scan_song_header
from ..core.config import RunConfig
from ..core.utils import safe_int

logger = logging.getLogger(__name__)


@dataclass
class JobSpec:
    """Represents a single processing job (song)."""
    file_path: str
    song_name: str
    difficulty: str
    
    @property
    def key(self) -> str:
        """Unique key for the job (typically file path)."""
        return self.file_path


class JobQueue:
    """
    Manages the queue of songs to process.
    
    Handles scanning directories, applying filters, and tracking progress.
    """
    
    def __init__(
        self,
        paths: dict[str, str],
        cfg_parser: Any,  # configparser.ConfigParser
    ):
        """
        Initialize the job queue.
        
        Args:
            paths: Dictionary of path mappings
            cfg_parser: Raw ConfigParser for filter settings
        """
        self.paths = paths
        self._queue: list[JobSpec] = []
        
        # Parse filters from config
        # Accept both legacy [General] and current [CalculateSong] keys
        diff_raw = (
            cfg_parser.get("CalculateSong", "Difficulty", fallback="")
            or cfg_parser.get("General", "Difficulty", fallback="All")
            or "All"
        )
        self.diff_lower = diff_raw.strip().lower()

        filter_raw = (
            cfg_parser.get("CalculateSong", "Song_Name", fallback="")
            or cfg_parser.get("General", "Song_Name", fallback="")
            or ""
        )
        self.filter_search = filter_raw.strip().lower()
        
        # Parse color targets
        primary_targets = (
            cfg_parser.get("IterationEngine", "TargetPrimaryColors", fallback="")
            or cfg_parser.get("CalculateSong", "TargetPrimary", fallback="")
            or cfg_parser.get("CalculateSong", "TargetPrimaryColors", fallback="All")
        )
        secondary_targets = (
            cfg_parser.get("IterationEngine", "TargetSecondaryColors", fallback="")
            or cfg_parser.get("CalculateSong", "TargetSecondary", fallback="")
            or cfg_parser.get("CalculateSong", "TargetSecondaryColors", fallback="All")
        )
        
        self.target_primary_all, self.target_primary_colors = self._parse_color_targets(primary_targets)
        self.target_secondary_all, self.target_secondary_colors = self._parse_color_targets(secondary_targets)
        
        # Build the queue immediately
        self._build_queue()
        
    def _parse_color_targets(self, raw_val: str) -> tuple[bool, set[str]]:
        """Parse color target filter from config string."""
        tokens = [
            c.strip().lower()
            for c in re.split(r"[,\|/]", raw_val or "")
            if c and c.strip()
        ]
        is_all = not tokens or any(c in ("all", "any", "*") for c in tokens)
        return is_all, set() if is_all else set(tokens)

    def _detect_difficulty(self, name_lower: str, meta: dict) -> str:
        """Extract difficulty from song name or metadata."""
        if "(hard)" in name_lower:
            return "Hard"
        elif "(normal)" in name_lower:
            return "Normal"
        elif "(easy)" in name_lower:
            return "Easy"
        else:
            meta_diff_val = (meta.get("Difficulty") or "").strip().capitalize()
            if meta_diff_val in ("Hard", "Normal", "Easy"):
                return meta_diff_val
        return "Unknown"

    def _passes_filters(self, job: JobSpec, meta: dict) -> bool:
        """Check if a song passes all configured filters."""
        # Difficulty filter
        if self.diff_lower in ("easy", "normal", "hard"):
            if job.difficulty.lower() != self.diff_lower:
                return False

        # Color filters
        primary_color = (meta.get("Primary Color") or "").strip().lower()
        secondary_color = (meta.get("Secondary Color") or "").strip().lower()

        if not self.target_primary_all and (
            not primary_color or primary_color not in self.target_primary_colors
        ):
            return False

        if not self.target_secondary_all and (
            not secondary_color or secondary_color not in self.target_secondary_colors
        ):
            return False

        # Name filter
        if self.filter_search and self.filter_search not in job.song_name.lower():
            return False

        return True

    def _build_queue(self) -> None:
        """Scan directories and build the filtered song list."""
        search_dir = self.paths.get(self.diff_lower.capitalize(), SCRIPT_DIR)
        seen_paths = set()
        
        # If "All" is selected, search the entire Data folder
        if self.diff_lower not in ("easy", "normal", "hard"):
            data_root = PATHS.data_dir
            dirs_to_search = [data_root] if os.path.exists(data_root) else [SCRIPT_DIR]
        else:
            dirs_to_search = [search_dir]

        for d in dirs_to_search:
            if not os.path.exists(d):
                continue
                
            for root, _, files in os.walk(d):
                for f in files:
                    if not f.lower().endswith(".txt"):
                        continue

                    fp = os.path.join(root, f)
                    abs_fp = os.path.abspath(fp)
                    if abs_fp in seen_paths:
                        continue

                    meta = scan_song_header(fp)
                    if not meta:
                        continue

                    name = meta["Song Name"]
                    
                    # Create preliminary job spec to check difficulty
                    diff = self._detect_difficulty(name.lower(), meta)
                    job = JobSpec(file_path=fp, song_name=name, difficulty=diff)

                    # Apply filters
                    if self._passes_filters(job, meta):
                        self._queue.append(job)
                        seen_paths.add(abs_fp)
        
        logger.info(f"Built job queue with {len(self._queue)} songs")

    def __len__(self) -> int:
        return len(self._queue)

    def __iter__(self) -> Iterator[JobSpec]:
        return iter(self._queue)
    
    def get_jobs(self) -> list[JobSpec]:
        """Return the list of jobs."""
        return self._queue
