"""
JIT (Just-In-Time) compilation setup for performance-critical functions.
Falls back gracefully if Numba is not available.
"""

# --- OPTIONAL JIT ACCELERATION ---
try:
    from numba import jit as numba_jit
    HAS_NUMBA = True

    def jit(nopython=True, cache=True):
        """
        Create a JIT decorator with disabled disk cache.
        Disk cache is disabled to avoid filesystem churn and potential lock issues.
        """
        return numba_jit(nopython=nopython, cache=False)
except ImportError:
    HAS_NUMBA = False

    def jit(nopython=True, cache=True):
        """
        Fallback decorator when Numba is not available.
        Returns the function unchanged (no optimization).
        """
        def decorator(func):
            return func
        return decorator


__all__ = ['jit', 'HAS_NUMBA']
