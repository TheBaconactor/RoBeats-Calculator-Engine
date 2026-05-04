from __future__ import annotations

import threading
from typing import Any

import numpy as np
from cachetools import LRUCache

from ....core.utils import timing_envelope_timing_context


from gear_optimizer.core.parsing import env_get
_FG_CHART_SCORER_CACHE_MAX = max(1, int(env_get("FG_CHART_SCORER_CACHE_MAX", "64") or "64"))
_FG_CHART_SCORER_CACHE: LRUCache = LRUCache(maxsize=_FG_CHART_SCORER_CACHE_MAX)
_FG_CHART_SCORER_LOCK = threading.Lock()

_FG_ANALYTICAL_BREAKPOINTS_CACHE_MAX = max(1, int(env_get("FG_ANALYTICAL_BREAKPOINTS_CACHE_MAX", "64") or "64"))
_FG_ANALYTICAL_BREAKPOINTS_CACHE: LRUCache = LRUCache(maxsize=_FG_ANALYTICAL_BREAKPOINTS_CACHE_MAX)
_FG_ANALYTICAL_BREAKPOINTS_LOCK = threading.Lock()

_FG_BREAKPOINT_GROUP_CACHE_MAX = max(1, int(env_get("FG_BREAKPOINT_GROUP_CACHE_MAX", "64") or "64"))
_FG_BREAKPOINT_GROUPS_CACHE: LRUCache = LRUCache(maxsize=_FG_BREAKPOINT_GROUP_CACHE_MAX)
_FG_BREAKPOINT_GROUPS_LOCK = threading.Lock()

_FG_MAX_FP_MATRIX_CACHE_MAX = max(1, int(env_get("FG_MAX_FP_MATRIX_CACHE_MAX", "64") or "64"))
_FG_MAX_FP_MATRIX_CACHE: LRUCache = LRUCache(maxsize=_FG_MAX_FP_MATRIX_CACHE_MAX)
_FG_MAX_FP_MATRIX_LOCK = threading.Lock()


def chart_signature_key(calc_song: dict) -> tuple:
    meta = calc_song.get("metadata", {}) or {}
    song_data = calc_song.get("song_data", {}) or {}
    ts = song_data.get("timestamps", ())
    n = int(len(ts)) if ts is not None else 0
    if n > 0:
        try:
            first_ms = int(float(ts[0]) * 1000.0)
        except Exception:
            first_ms = 0
        try:
            last_ms = int(float(ts[-1]) * 1000.0)
        except Exception:
            last_ms = 0
    else:
        first_ms = 0
        last_ms = 0

    try:
        lnt = float(meta.get("Last Note Time", 0) or 0)
    except Exception:
        lnt = 0.0
    if lnt <= 0.0 and n > 0:
        try:
            lnt = float(ts[-1])
        except Exception:
            lnt = 0.0
    last_note_ms = int(lnt * 1000.0) if lnt > 0 else 0

    try:
        long_notes = int(meta.get("Long Notes", 0) or 0)
    except Exception:
        long_notes = 0

    return (
        str(meta.get("Song Name", "")),
        str(meta.get("Difficulty", "")),
        n,
        first_ms,
        last_ms,
        last_note_ms,
        long_notes,
    )


def get_cached_chart_scorer(calc_song: dict, ref_arrays: dict, create_chart_scorer_fn):
    key = chart_signature_key(calc_song)
    with _FG_CHART_SCORER_LOCK:
        scorer = _FG_CHART_SCORER_CACHE.get(key)
        if scorer is not None:
            return scorer, True

    scorer = create_chart_scorer_fn(calc_song, ref_arrays)
    with _FG_CHART_SCORER_LOCK:
        _FG_CHART_SCORER_CACHE[key] = scorer
    return scorer, False


def get_cached_analytical_breakpoints(
    *,
    chart_key: tuple,
    num_sections: int,
    variant_key: tuple | None = None,
    compute_fn,
):
    key = (chart_key, int(num_sections), tuple(variant_key or ()))
    with _FG_ANALYTICAL_BREAKPOINTS_LOCK:
        cached = _FG_ANALYTICAL_BREAKPOINTS_CACHE.get(key)
        if cached is not None:
            return list(cached)

    computed = compute_fn()
    frozen = tuple(tuple(x) for x in (computed or []))
    with _FG_ANALYTICAL_BREAKPOINTS_LOCK:
        _FG_ANALYTICAL_BREAKPOINTS_CACHE[key] = frozen
    return list(frozen)


def normalize_pair_signature(pairs: Any) -> tuple[tuple[int, int], ...]:
    try:
        return tuple((int(str(a or 0)), int(str(b or 0))) for a, b in list(pairs or []))
    except Exception:
        return ()


def freeze_breakpoint_groups(groups: list[dict]) -> tuple[tuple[object, ...], ...]:
    frozen: list[tuple[object, ...]] = []
    for group in groups or []:
        if not isinstance(group, dict):
            continue
        frozen.append(
            (
                normalize_pair_signature(group.get("ftff_pairs")),
                tuple(tuple(int(v) for v in row) for row in list(group.get("counts_list") or [])),
                tuple(int(v) for v in list(group.get("counts_max_fp") or [])),
                tuple(tuple(int(v) for v in bp) for bp in list(group.get("section_breakpoints") or []))
                if group.get("section_breakpoints") is not None
                else None,
            )
        )
    return tuple(frozen)


def thaw_breakpoint_groups(frozen_groups: Any) -> list[dict]:
    groups: list[dict] = []
    for row in list(frozen_groups or []):
        if not isinstance(row, tuple) or len(row) != 4:
            continue
        ftff_pairs, counts_list, counts_max_fp, section_breakpoints = row
        groups.append(
            {
                "ftff_pairs": list(ftff_pairs or []),
                "counts_list": list(counts_list or []),
                "counts_max_fp": list(counts_max_fp or []),
                "section_breakpoints": tuple(section_breakpoints or ()) if section_breakpoints is not None else None,
            }
        )
    return groups


def _breakpoint_groups_cache_key(
    *,
    calc_song: dict,
    n_sections: int,
    ftff_pairs,
    base_stats_pairs,
    merge_threshold_cfgs: int,
    merge_threshold_threads: int,
    n_genomes: int,
    gem_scale_fever: int,
    mode: str,
) -> tuple[object, ...]:
    return (
        chart_signature_key(calc_song),
        timing_envelope_timing_context(calc_song),
        str(mode or ""),
        int(n_sections),
        normalize_pair_signature(ftff_pairs),
        normalize_pair_signature(base_stats_pairs),
        int(merge_threshold_cfgs),
        int(merge_threshold_threads),
        int(n_genomes),
        int(gem_scale_fever),
    )


def peek_cached_breakpoint_groups(
    *,
    calc_song: dict,
    n_sections: int,
    ftff_pairs,
    base_stats_pairs,
    merge_threshold_cfgs: int,
    merge_threshold_threads: int,
    n_genomes: int,
    gem_scale_fever: int,
    mode: str,
):
    key = _breakpoint_groups_cache_key(
        calc_song=calc_song,
        n_sections=n_sections,
        ftff_pairs=ftff_pairs,
        base_stats_pairs=base_stats_pairs,
        merge_threshold_cfgs=merge_threshold_cfgs,
        merge_threshold_threads=merge_threshold_threads,
        n_genomes=n_genomes,
        gem_scale_fever=gem_scale_fever,
        mode=mode,
    )
    with _FG_BREAKPOINT_GROUPS_LOCK:
        cached = _FG_BREAKPOINT_GROUPS_CACHE.get(key)
        if cached is None:
            return None
    return thaw_breakpoint_groups(cached)


def store_cached_breakpoint_groups(
    *,
    calc_song: dict,
    n_sections: int,
    ftff_pairs,
    base_stats_pairs,
    merge_threshold_cfgs: int,
    merge_threshold_threads: int,
    n_genomes: int,
    gem_scale_fever: int,
    mode: str,
    groups: list[dict],
) -> None:
    key = _breakpoint_groups_cache_key(
        calc_song=calc_song,
        n_sections=n_sections,
        ftff_pairs=ftff_pairs,
        base_stats_pairs=base_stats_pairs,
        merge_threshold_cfgs=merge_threshold_cfgs,
        merge_threshold_threads=merge_threshold_threads,
        n_genomes=n_genomes,
        gem_scale_fever=gem_scale_fever,
        mode=mode,
    )
    frozen = freeze_breakpoint_groups(groups)
    with _FG_BREAKPOINT_GROUPS_LOCK:
        _FG_BREAKPOINT_GROUPS_CACHE[key] = frozen


def get_cached_breakpoint_groups(
    *,
    calc_song: dict,
    n_sections: int,
    ftff_pairs,
    base_stats_pairs,
    merge_threshold_cfgs: int,
    merge_threshold_threads: int,
    n_genomes: int,
    gem_scale_fever: int,
    mode: str,
    compute_fn,
):
    key = _breakpoint_groups_cache_key(
        calc_song=calc_song,
        n_sections=n_sections,
        ftff_pairs=ftff_pairs,
        base_stats_pairs=base_stats_pairs,
        merge_threshold_cfgs=merge_threshold_cfgs,
        merge_threshold_threads=merge_threshold_threads,
        n_genomes=n_genomes,
        gem_scale_fever=gem_scale_fever,
        mode=mode,
    )
    with _FG_BREAKPOINT_GROUPS_LOCK:
        cached = _FG_BREAKPOINT_GROUPS_CACHE.get(key)
        if cached is not None:
            return thaw_breakpoint_groups(cached), True

    computed = list(compute_fn() or [])
    frozen = freeze_breakpoint_groups(computed)
    with _FG_BREAKPOINT_GROUPS_LOCK:
        _FG_BREAKPOINT_GROUPS_CACHE[key] = frozen
    return computed, False


def get_cached_max_fp_matrix(
    *,
    calc_song: dict,
    n_sections: int,
    ftff_pairs,
    base_stats_pairs,
    gem_scale_fever: int,
    compute_fn,
):
    key = (
        chart_signature_key(calc_song),
        timing_envelope_timing_context(calc_song),
        int(n_sections),
        normalize_pair_signature(ftff_pairs),
        normalize_pair_signature(base_stats_pairs),
        int(gem_scale_fever),
    )
    with _FG_MAX_FP_MATRIX_LOCK:
        cached = _FG_MAX_FP_MATRIX_CACHE.get(key)
        if cached is not None:
            return np.array(cached, dtype=np.int16, copy=True), True

    computed = compute_fn()
    if computed is None:
        return None, False

    frozen = np.ascontiguousarray(np.asarray(computed, dtype=np.int16))
    with _FG_MAX_FP_MATRIX_LOCK:
        _FG_MAX_FP_MATRIX_CACHE[key] = frozen
    return np.array(frozen, dtype=np.int16, copy=True), False


__all__ = [
    "_FG_ANALYTICAL_BREAKPOINTS_CACHE",
    "_FG_ANALYTICAL_BREAKPOINTS_LOCK",
    "_FG_BREAKPOINT_GROUPS_CACHE",
    "_FG_BREAKPOINT_GROUPS_LOCK",
    "_FG_CHART_SCORER_CACHE",
    "_FG_CHART_SCORER_LOCK",
    "_FG_MAX_FP_MATRIX_CACHE",
    "_FG_MAX_FP_MATRIX_LOCK",
    "chart_signature_key",
    "freeze_breakpoint_groups",
    "get_cached_analytical_breakpoints",
    "get_cached_breakpoint_groups",
    "get_cached_chart_scorer",
    "get_cached_max_fp_matrix",
    "normalize_pair_signature",
    "peek_cached_breakpoint_groups",
    "store_cached_breakpoint_groups",
    "thaw_breakpoint_groups",
]
