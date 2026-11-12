"""What the FG cache tests share: frontiers from surfaces, and the cache's calls with stat keys given as pairs."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from gear_optimizer.frontier import fg_cache
from gear_optimizer.frontier.fg_cache_keys import fg_response_frontier_bundle_cache_key
from gear_optimizer.frontier.fg_cache_patterns import unpack_surface_patterns
from gear_optimizer.frontier.fg_cache_store import load_payload
from gear_optimizer.frontier.producer_surfaces import SurfaceRowsFirstFrontier


def surface_frontier(*surfaces) -> SurfaceRowsFirstFrontier:
    rows = [
        (s.fever0 | s.fever1 << 32, s.fever2 | s.fever3 << 32, s.great0 | s.great1 << 32, s.great2 | s.great3 << 32,
         s.body_fever, s.body_great, s.body_fever_great)
        for s in surfaces
    ]
    return SurfaceRowsFirstFrontier(np.asarray(rows, dtype=np.uint64).reshape(-1, 7))


def forget_scoring_bundles() -> None:
    """Empty the process's memory tier of decoded bundles, so the next load reads its file: tests reuse one song under
    many cache directories and versions."""
    fg_cache._scoring_bundle_memory.clear()


def stat_key_array(stat_keys) -> np.ndarray:
    return np.asarray(sorted({tuple(key) for key in stat_keys}), dtype=np.int32).reshape(-1, 2)


def ensure_cache(song, curves, *, stat_keys=None):
    keys = None if stat_keys is None else stat_key_array(stat_keys)
    return fg_cache.ensure_response_frontier_cache_for_song(song, curves, stat_keys=keys)


def load_scoring_bundle(song, curves, *, stat_keys=None):
    keys = None if stat_keys is None else stat_key_array(stat_keys)
    return fg_cache.load_response_frontier_scoring_bundle(song, curves, stat_keys=keys)


def build_or_load_payload(song, curves, *, stat_keys):
    """The song's bundle with `stat_keys` as a payload, narrowed to them, and how it was served."""
    source, build_ms, path = ensure_cache(song, curves, stat_keys=stat_keys)
    bundle_key = fg_response_frontier_bundle_cache_key(song, curves)
    bundle = load_payload(bundle_key)
    if bundle is None:  # a damaged file was deleted
        source, build_ms, path = ensure_cache(song, curves, stat_keys=stat_keys)
        bundle = load_payload(bundle_key)
    frontiers = {tuple(key): bundle.frontier_by_key[tuple(key)] for key in stat_key_array(stat_keys).tolist()}
    return SimpleNamespace(
        payload=SimpleNamespace(
            frontier_by_key=frontiers,
            frontiers=tuple({id(frontier): frontier for frontier in frontiers.values()}.values()),
            raw_fill_by_ff=bundle.raw_fill_by_ff,
            non_fever_base_by_ff=bundle.non_fever_base_by_ff,
            real_time_by_ft=bundle.real_time_by_ft,
            total_notes=bundle.total_notes,
            long_notes=bundle.long_notes,
            use_forced_great_timing=bundle.use_forced_great_timing,
            frontier_for_stats=lambda *, ft_stat, ff_stat: frontiers[(ft_stat, ff_stat)],
        ),
        cache_source=source,
        elapsed_ms=build_ms,
        disk_path=path,
    )


def expand_surface_rows(row_refs: np.ndarray, patterns: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Interned rows back to the producer's (n, 11) rows and their (n, 4) head coefficients, row order kept."""
    refs = np.asarray(row_refs, dtype=np.uint32)
    if not refs.shape[0]:
        return np.empty((0, 11), dtype=np.uint32), np.empty((0, 4), dtype=np.int32)
    ids = refs[:, 0].astype(np.int64)
    if not patterns.shape[0] or ids.max() >= patterns.shape[0]:
        raise ValueError("FG response surface row references an invalid head-pattern ID")
    selected = np.asarray(patterns, dtype=np.uint32)[ids]
    words, coeffs = unpack_surface_patterns(selected)
    return np.concatenate((words, refs[:, 1:4]), axis=1), coeffs
