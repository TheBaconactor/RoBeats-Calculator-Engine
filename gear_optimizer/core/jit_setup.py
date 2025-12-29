"""
JIT (Just-In-Time) compilation setup for performance-critical functions.
Falls back gracefully if Numba is not available.
"""

# --- OPTIONAL JIT ACCELERATION ---
try:
    import os
    from pathlib import Path

    def _env_bool(name: str, default: bool) -> bool:
        val = os.environ.get(name)
        if val is None:
            return default
        return str(val).strip().lower() in ("1", "true", "yes", "y", "on")

    def _default_numba_cache_dir() -> str | None:
        """
        Return a stable cache dir for Numba, scoped to this repo.

        Using `bin/numba_cache/` keeps artifacts out of user profile dirs and
        makes cleanup straightforward.
        """
        try:
            repo_root = Path(__file__).resolve().parents[2]
            cache_dir = repo_root / "bin" / "numba_cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            return str(cache_dir)
        except Exception:
            return None

    from numba import jit as numba_jit

    HAS_NUMBA = True

    def jit(nopython=True, cache=True):
        """
        Create a JIT decorator.

        Disk caching is enabled by default (respects the `cache=` argument) and
        is redirected to `bin/numba_cache/` unless `NUMBA_CACHE_DIR` is already
        set. Disable globally via `NUMBA_DISK_CACHE=0`.
        """
        disk_cache_enabled = _env_bool("NUMBA_DISK_CACHE", True)
        use_cache = bool(cache) and disk_cache_enabled
        if use_cache and "NUMBA_CACHE_DIR" not in os.environ:
            cache_dir = _default_numba_cache_dir()
            if cache_dir:
                os.environ["NUMBA_CACHE_DIR"] = cache_dir
            else:
                use_cache = False
        return numba_jit(nopython=nopython, cache=use_cache)
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


__all__ = ["jit", "HAS_NUMBA"]
