"""
Song Helpers Package - Song processing helper functions.

This package splits the monolithic song_helpers.py (1,327 lines) into 6 focused modules:
1. database_context.py - Database seeds and known loadouts loading
2. song_config.py - Song configuration setup
3. loadout_builder.py - Loadout entry building
4. force_greats.py - Force greats processing
5. persistence.py - Database payload and persistence entry building
6. results_printer.py - Results display

This __init__.py provides backward-compatible imports so existing code continues to work.
"""

# Import from database_context
try:
    from .database_context import load_database_context
except ImportError:
    pass

# Import from song_config
try:
    from .song_config import setup_song_config
except ImportError:
    pass

# Import from loadout_builder
try:
    from .loadout_builder import build_loadout_entries
except ImportError:
    pass

# Import from force_greats
try:
    from .force_greats import process_force_greats
except ImportError:
    pass

# Import from persistence
try:
    from .persistence import (
        build_db_payload,
        build_persistence_entries,
    )
except ImportError:
    pass

# Import from results_printer
try:
    from .results_printer import print_results
except ImportError:
    pass

# Export all public names for backward compatibility
__all__ = [
    # Database context
    "load_database_context",
    # Song config
    "setup_song_config",
    # Loadout builder
    "build_loadout_entries",
    # Force greats
    "process_force_greats",
    # Persistence
    "build_db_payload",
    "build_persistence_entries",
    # Results printer
    "print_results",
]
__all__: list[str] = []
