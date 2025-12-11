"""
Unit tests for gear_optimizer.session module.
Tests the SolverSession class and its cache management.
"""
import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gear_optimizer.session import (
    SolverSession,
    get_default_session,
    reset_default_session,
)


class TestSolverSession:
    """Tests for SolverSession class."""

    def test_init_creates_empty_caches(self):
        """New session should have empty caches."""
        session = SolverSession()
        assert len(session.gem_solver_cache) == 0
        assert len(session.fever_timeline_cache) == 0
        assert len(session.fg_cache) == 0

    def test_custom_cache_sizes(self):
        """Session respects custom cache size limits."""
        session = SolverSession(gem_cache_size=10, timeline_cache_size=20, fg_cache_size=5)
        assert session.gem_solver_cache.maxsize == 10
        assert session.fever_timeline_cache.maxsize == 20
        assert session.fg_cache.maxsize == 5

    def test_clear_all_empties_caches(self):
        """clear_all should empty all caches."""
        session = SolverSession()
        # Add some data
        session.gem_solver_cache["key1"] = "value1"
        session.fever_timeline_cache["key2"] = "value2"
        session.fg_cache["key3"] = "value3"
        
        session.clear_all()
        
        assert len(session.gem_solver_cache) == 0
        assert len(session.fever_timeline_cache) == 0
        assert len(session.fg_cache) == 0

    def test_get_stats_returns_cache_info(self):
        """get_stats should return cache sizes and hit counts."""
        session = SolverSession()
        session.gem_solver_cache["test"] = 123
        
        stats = session.get_stats()
        
        assert stats["gem_cache_size"] == 1
        assert stats["timeline_cache_size"] == 0
        assert "gem_solver_hits" in stats
        assert "gem_solver_misses" in stats

    def test_record_hit_miss_updates_stats(self):
        """Hit/miss recording should update statistics."""
        session = SolverSession()
        
        session.record_gem_hit()
        session.record_gem_hit()
        session.record_gem_miss()
        
        stats = session.get_stats()
        assert stats["gem_solver_hits"] == 2
        assert stats["gem_solver_misses"] == 1

    def test_clear_also_resets_stats(self):
        """clear_all should also reset statistics."""
        session = SolverSession()
        session.record_gem_hit()
        session.record_timeline_miss()
        
        session.clear_all()
        
        stats = session.get_stats()
        assert stats["gem_solver_hits"] == 0
        assert stats["timeline_misses"] == 0


class TestDefaultSession:
    """Tests for global session management."""

    def test_get_default_session_returns_session(self):
        """get_default_session should return a SolverSession."""
        session = get_default_session()
        assert isinstance(session, SolverSession)

    def test_get_default_session_returns_same_instance(self):
        """get_default_session should return the same instance."""
        s1 = get_default_session()
        s2 = get_default_session()
        assert s1 is s2

    def test_reset_default_session_creates_new(self):
        """reset_default_session should create a fresh session."""
        s1 = get_default_session()
        s1.gem_solver_cache["test"] = 123
        
        reset_default_session()
        s2 = get_default_session()
        
        assert s1 is not s2
        assert len(s2.gem_solver_cache) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
