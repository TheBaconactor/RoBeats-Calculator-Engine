"""
Session management for solver state.

This module provides a SolverSession class that encapsulates all per-run state
including caches. This replaces the global cache pattern, improving testability
and preventing memory leaks between runs.
"""
from __future__ import annotations

from cachetools import LRUCache
from typing import Any

from ..core.constants import (
    MAX_TIMELINE_CACHE_GLOBAL,
    MAX_GEM_SOLVER_CACHE,
    MAX_FG_CACHE,
)


class SolverSession:
    """
    Manages per-run state including caches.
    
    Creating a new SolverSession and discarding the old one automatically
    garbage collects all cached data, preventing memory leaks in long-running
    processes like LoopForever mode.
    
    Usage:
        session = SolverSession()
        # ... use session.gem_solver_cache, etc. in solver calls ...
        session.clear_all()  # Optional explicit clear
        del session  # Or just let it go out of scope
    """
    
    def __init__(
        self,
        gem_cache_size: int = MAX_GEM_SOLVER_CACHE,
        timeline_cache_size: int = MAX_TIMELINE_CACHE_GLOBAL,
        fg_cache_size: int = MAX_FG_CACHE,
    ):
        """
        Initialize a new solver session with fresh caches.
        
        Args:
            gem_cache_size: Max entries for gem solver cache
            timeline_cache_size: Max entries for fever timeline cache
            fg_cache_size: Max entries for force greats cache
        """
        self.gem_solver_cache: LRUCache = LRUCache(maxsize=gem_cache_size)
        self.fever_timeline_cache: LRUCache = LRUCache(maxsize=timeline_cache_size)
        self.fg_cache: LRUCache = LRUCache(maxsize=fg_cache_size)
        
        # Statistics for debugging/profiling
        self._stats = {
            "gem_solver_hits": 0,
            "gem_solver_misses": 0,
            "timeline_hits": 0,
            "timeline_misses": 0,
        }
    
    def clear_all(self) -> None:
        """Clear all caches. Useful at start of a new optimization run."""
        self.gem_solver_cache.clear()
        self.fever_timeline_cache.clear()
        self.fg_cache.clear()
        self._reset_stats()
    
    def _reset_stats(self) -> None:
        """Reset hit/miss statistics."""
        for key in self._stats:
            self._stats[key] = 0
    
    def get_stats(self) -> dict[str, int]:
        """Return cache hit/miss statistics."""
        return {
            **self._stats,
            "gem_cache_size": len(self.gem_solver_cache),
            "timeline_cache_size": len(self.fever_timeline_cache),
            "fg_cache_size": len(self.fg_cache),
        }
    
    def record_gem_hit(self) -> None:
        """Record a gem solver cache hit."""
        self._stats["gem_solver_hits"] += 1
    
    def record_gem_miss(self) -> None:
        """Record a gem solver cache miss."""
        self._stats["gem_solver_misses"] += 1
    
    def record_timeline_hit(self) -> None:
        """Record a timeline cache hit."""
        self._stats["timeline_hits"] += 1
    
    def record_timeline_miss(self) -> None:
        """Record a timeline cache miss."""
        self._stats["timeline_misses"] += 1


# =============================================================================
# GLOBAL SESSION (for backwards compatibility during migration)
# =============================================================================

# This global instance provides backwards compatibility with existing code
# that imports caches directly. New code should create explicit sessions.
_default_session: SolverSession | None = None


def get_default_session() -> SolverSession:
    """
    Get the default global session, creating one if needed.
    
    This is for backwards compatibility. New code should create explicit
    SolverSession instances.
    """
    global _default_session
    if _default_session is None:
        _default_session = SolverSession()
    return _default_session


def reset_default_session() -> None:
    """
    Reset the global session by creating a fresh one.
    
    This is equivalent to clearing all caches and is useful at the start
    of a new optimization run in LoopForever mode.
    """
    global _default_session
    _default_session = SolverSession()
