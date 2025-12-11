"""
Unit tests for gear_optimizer.solver_interface module.
Tests the ISolver protocol, CpuSolver, and GpuSolver classes.
"""
import pytest
import numpy as np
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gear_optimizer.solver_interface import (
    ISolver,
    CpuSolver,
    GpuSolver,
    get_solver,
)
from gear_optimizer.models import SongContext, SolverParams


class TestCpuSolver:
    """Tests for CpuSolver class."""

    def test_implements_protocol(self):
        """CpuSolver should implement ISolver protocol."""
        solver = CpuSolver()
        assert hasattr(solver, "solve")

    def test_init_no_errors(self):
        """CpuSolver initialization should not raise errors."""
        solver = CpuSolver()
        assert solver is not None


class TestGpuSolver:
    """Tests for GpuSolver class."""

    def test_implements_protocol(self):
        """GpuSolver should implement ISolver protocol."""
        solver = GpuSolver()
        assert hasattr(solver, "solve")
        assert hasattr(solver, "is_available")

    def test_has_availability_check(self):
        """GpuSolver should report availability."""
        solver = GpuSolver()
        # is_available should be a bool
        assert isinstance(solver.is_available, bool)


class TestGetSolver:
    """Tests for get_solver factory function."""

    def test_returns_cpu_solver_by_default(self):
        """get_solver() without args should return CpuSolver."""
        solver = get_solver(use_gpu=False)
        assert isinstance(solver, CpuSolver)

    def test_returns_solver_with_solve_method(self):
        """Returned solver should have solve method."""
        solver = get_solver()
        assert callable(getattr(solver, "solve", None))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
