"""
Solver interface definitions for CPU and GPU solvers.

This module defines a common interface (ISolver) that both the Numba-based CPU
solver and Taichi-based GPU solver implement. This reduces code duplication and
allows easy switching between implementations.
"""
from __future__ import annotations

from typing import Protocol, Any

import numpy as np

from ..data.models import SongContext, SolverParams
from ..core.constants import TOTAL_GEM_BUDGET


class ISolver(Protocol):
    """
    Protocol defining the common interface for gem solvers.
    
    Both CPU (Numba) and GPU (Taichi) solvers implement this interface,
    allowing code to work with either implementation transparently.
    """
    
    def solve(
        self,
        song_ctx: SongContext,
        params: SolverParams,
        initial_stats: dict[str, int],
        ref_arrays: dict[str, np.ndarray],
    ) -> dict[str, Any]:
        """
        Run the gem solver and return result dict.
        
        Args:
            song_ctx: Song context with metadata and timestamps
            params: Solver configuration parameters
            initial_stats: Initial stats dictionary
            ref_arrays: Reference lookup arrays
        
        Returns:
            dict: Result with Score, FT, FF, GemCounts, Stats, Selected Element
        """
        ...


class CpuSolver:
    """
    Numba-based CPU solver implementing ISolver.
    
    Uses JIT-compiled functions for the greedy gem allocation algorithm.
    This is the default solver and works on all systems.
    """
    
    def __init__(self) -> None:
        """Initialize the CPU solver."""
        pass  # No special initialization needed; Numba compiles on first call
    
    def solve(
        self,
        song_ctx: SongContext,
        params: SolverParams,
        initial_stats: dict[str, int],
        ref_arrays: dict[str, np.ndarray],
    ) -> dict[str, Any]:
        """
        Run the CPU gem solver.
        
        Delegates to solve_best_fever_combination with use_gpu=False.
        """
        from .scoring import solve_best_fever_combination
        
        calc_song = song_ctx.to_calc_song()
        override_cfg = params.to_cfg_data()
        override_cfg["use_gpu"] = False  # Force CPU
        
        return solve_best_fever_combination(
            cfg=None,
            initial_stats=initial_stats,
            calc_song=calc_song,
            ref_arrays=ref_arrays,
            silent=True,
            override_cfg=override_cfg,
        )


class GpuSolver:
    """
    Taichi-based GPU solver implementing ISolver.
    
    Uses GPU-accelerated kernels for parallel grid search.
    Requires Taichi and a compatible GPU.
    """
    
    def __init__(self) -> None:
        """Initialize the GPU solver and Taichi runtime."""
        try:
            from .. import taichi_accelerator
            taichi_accelerator.init_taichi()
            self._available = True
        except ImportError:
            self._available = False
    
    @property
    def is_available(self) -> bool:
        """Check if GPU solver is available."""
        return self._available
    
    def solve(
        self,
        song_ctx: SongContext,
        params: SolverParams,
        initial_stats: dict[str, int],
        ref_arrays: dict[str, np.ndarray],
    ) -> dict[str, Any]:
        """
        Run the GPU gem solver.
        
        Falls back to CPU if GPU is not available.
        """
        if not self._available:
            # Fallback to CPU
            cpu = CpuSolver()
            return cpu.solve(song_ctx, params, initial_stats, ref_arrays)
        
        from .scoring import solve_best_fever_combination
        
        calc_song = song_ctx.to_calc_song()
        override_cfg = params.to_cfg_data()
        override_cfg["use_gpu"] = True  # Force GPU
        
        return solve_best_fever_combination(
            cfg=None,
            initial_stats=initial_stats,
            calc_song=calc_song,
            ref_arrays=ref_arrays,
            silent=True,
            override_cfg=override_cfg,
        )


def get_solver(use_gpu: bool = False) -> ISolver:
    """
    Factory function to get the appropriate solver.
    
    Args:
        use_gpu: If True, attempt to use GPU solver (falls back to CPU if unavailable)
    
    Returns:
        ISolver: Either CpuSolver or GpuSolver instance
    """
    if use_gpu:
        solver = GpuSolver()
        if solver.is_available:
            return solver
        # Fall back to CPU
    return CpuSolver()
