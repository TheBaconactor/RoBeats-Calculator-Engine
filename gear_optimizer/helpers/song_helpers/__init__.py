"""
Song Helpers Package - Song processing helper functions.

This package splits the monolithic song_helpers.py (1,327 lines) into focused modules:
- database_context.py: Database seeds and known loadouts loading
- song_config.py: Song configuration setup
- loadout_builder.py: Loadout entry building
- force_greats.py: Force greats processing
- persistence.py: DB payload and persistence entry building
- results_printer.py: Results display
"""

from .database_context import load_database_context, load_database_progress_baseline, resolve_database_baseline_team_buff
from .force_greats import process_force_greats
from .loadout_builder import build_loadout_entries
from .persistence import ReplayContext, build_db_payload, build_persistence_entries, canonicalize_and_assemble
from .results_printer import print_results
from .song_config import setup_song_config

__all__ = [
    "load_database_context",
    "load_database_progress_baseline",
    "resolve_database_baseline_team_buff",
    "setup_song_config",
    "build_loadout_entries",
    "process_force_greats",
    "build_db_payload",
    "build_persistence_entries",
    "canonicalize_and_assemble",
    "ReplayContext",
    "print_results",
]
