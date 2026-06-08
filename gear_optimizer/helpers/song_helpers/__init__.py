"""
Exports are loaded on first access so importing lightweight helpers does not pull
FG/GPU dispatch or Taichi into CPU-only code paths.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORTS: dict[str, tuple[str, str]] = {
    "load_database_context": ("database_context", "load_database_context"),
    "load_database_progress_baseline": ("database_context", "load_database_progress_baseline"),
    "resolve_database_baseline_team_buff": ("database_context", "resolve_database_baseline_team_buff"),
    "setup_song_config": ("song_config", "setup_song_config"),
    "run_force_greats_response_frontier_for_ga_candidates": (
        "force_greats",
        "run_force_greats_response_frontier_for_ga_candidates",
    ),
    "build_db_payload": ("persistence_payload", "build_db_payload"),
    "build_persistence_entries": ("persistence_canon", "build_persistence_entries"),
    "canonicalize_and_assemble": ("persistence_canon", "canonicalize_and_assemble"),
    "ReplayContext": ("persistence_canon", "ReplayContext"),
    "print_results": ("results_printer", "print_results"),
}

__all__ = list(_EXPORTS)


def __getattr__(name: str) -> Any:
    target = _EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = target
    value = getattr(import_module(f".{module_name}", __name__), attr_name)
    globals()[name] = value
    return value
