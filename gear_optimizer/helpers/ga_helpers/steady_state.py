from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from ..song_helpers.ga_entry_utils import canonicalize_genome_ids


@dataclass(frozen=True)
class SteadyStateSettings:
    enabled: bool
    epoch_count: int
    refresh_pct: float
    min_refresh: int
    refresh_count: int


@dataclass(frozen=True)
class SteadyStateRefreshStats:
    survivors_kept: int
    survivor_duplicates_dropped: int
    survivor_archive_rejected: int
    fresh_added: int
    fresh_archive_collisions: int
    fallback_archive_reused: int
    fallback_duplicates_added: int


def resolve_steady_state_settings(*, cfg_data: dict | None, epoch_count: int, n_genomes: int) -> SteadyStateSettings:
    cfg = dict(cfg_data or {})
    epoch_count_i = max(1, int(epoch_count))
    n_genomes_i = max(1, int(n_genomes))

    enabled_raw = cfg.get("ga_steady_state_enabled")
    if enabled_raw is None:
        enabled = epoch_count_i > 1
    else:
        enabled = bool(enabled_raw)

    try:
        refresh_pct = float(cfg.get("ga_steady_state_refresh_pct", 0.25) or 0.25)
    except Exception:
        refresh_pct = 0.25
    refresh_pct = max(0.0, min(0.75, float(refresh_pct)))

    try:
        min_refresh = int(cfg.get("ga_steady_state_min_refresh", 8) or 8)
    except Exception:
        min_refresh = 8
    min_refresh = max(0, min(int(n_genomes_i), int(min_refresh)))

    refresh_count = 0
    if enabled and epoch_count_i > 1:
        refresh_count = max(int(min_refresh), int(round(float(n_genomes_i) * float(refresh_pct))))
        refresh_count = max(0, min(int(n_genomes_i) - 1, int(refresh_count)))

    return SteadyStateSettings(
        enabled=bool(enabled and epoch_count_i > 1 and refresh_count > 0),
        epoch_count=int(epoch_count_i),
        refresh_pct=float(refresh_pct),
        min_refresh=int(min_refresh),
        refresh_count=int(refresh_count),
    )


def build_steady_state_initial_population_ids(
    initial_populations: Any,
    *,
    n_genomes: int,
    n_slots: int = 9,
) -> np.ndarray:
    src = np.asarray(initial_populations, dtype=np.int32)
    if src.ndim != 3:
        raise ValueError(f"initial_populations must be 3D; got ndim={src.ndim}")
    if int(src.shape[2]) < int(n_slots):
        raise ValueError(f"initial_populations has too few slots: {src.shape[2]} < {n_slots}")

    flat = src[:, :, : int(n_slots)].reshape(-1, int(n_slots))
    selected: list[np.ndarray] = []
    seen: set[tuple[int, ...]] = set()
    for row in flat:
        key = canonicalize_genome_ids(row)
        if key is None:
            key = tuple(int(x) for x in np.asarray(row, dtype=np.int32).tolist())
        if key in seen:
            continue
        seen.add(key)
        selected.append(np.asarray(row, dtype=np.int32).copy())
        if len(selected) >= int(n_genomes):
            break

    if len(selected) < int(n_genomes):
        for row in flat:
            selected.append(np.asarray(row, dtype=np.int32).copy())
            if len(selected) >= int(n_genomes):
                break

    if not selected:
        raise ValueError("initial_populations is empty")

    return np.asarray(selected[: int(n_genomes)], dtype=np.int32)


def _sample_fresh_population_row(
    *,
    rng: np.random.Generator,
    slot_start: np.ndarray,
    slot_count: np.ndarray,
    n_slots: int,
) -> np.ndarray:
    row = np.zeros((int(n_slots),), dtype=np.int32)
    for slot_idx in range(int(n_slots)):
        count = int(slot_count[slot_idx]) if slot_idx < int(slot_count.shape[0]) else 0
        start = int(slot_start[slot_idx]) if slot_idx < int(slot_start.shape[0]) else 0
        if count <= 0:
            row[slot_idx] = 0
            continue
        row[slot_idx] = int(start + int(rng.integers(0, count)))

    if int(n_slots) >= 9:
        mini_slot = 6
        mini_count = int(slot_count[mini_slot]) if int(slot_count.shape[0]) > mini_slot else 0
        mini_start = int(slot_start[mini_slot]) if int(slot_start.shape[0]) > mini_slot else 0
        if mini_count >= 3:
            picks = rng.choice(int(mini_count), size=3, replace=False).astype(np.int32)
            row[6:9] = int(mini_start) + picks
    return row


def _canonical_row_key(row: Any) -> tuple[int, ...]:
    canon = canonicalize_genome_ids(row)
    if canon is not None:
        return tuple(int(x) for x in canon)
    arr = np.asarray(row, dtype=np.int32).reshape(-1)
    return tuple(int(x) for x in arr.tolist())


def _normalize_seen_archive_keys(seen_archive_keys: Any) -> set[tuple[int, ...]]:
    out: set[tuple[int, ...]] = set()
    if seen_archive_keys is None:
        return out
    for value in seen_archive_keys:
        try:
            out.add(_canonical_row_key(value))
        except Exception:
            continue
    return out


def extend_seen_archive_keys(*, seen_archive_keys: set[tuple[int, ...]], population_ids: Any) -> None:
    pop_ids = np.asarray(population_ids, dtype=np.int32)
    if pop_ids.ndim != 2:
        raise ValueError(f"population_ids must be 2D; got ndim={pop_ids.ndim}")
    for row in pop_ids:
        seen_archive_keys.add(_canonical_row_key(row))


def build_steady_state_next_population_ids(
    *,
    current_population_ids: Any,
    scores: Any,
    slot_start: Any,
    slot_count: Any,
    refresh_count: int,
    seed: int,
    seen_archive_keys: Any = None,
    elite_keep_count: int = 0,
) -> tuple[np.ndarray, SteadyStateRefreshStats]:
    pop_ids = np.asarray(current_population_ids, dtype=np.int32)
    if pop_ids.ndim != 2:
        raise ValueError(f"current_population_ids must be 2D; got ndim={pop_ids.ndim}")
    n_genomes = int(pop_ids.shape[0])
    n_slots = int(pop_ids.shape[1])
    if n_genomes <= 0 or n_slots <= 0:
        raise ValueError("current_population_ids has invalid shape")

    scores_arr = np.asarray(scores, dtype=np.int32).reshape(-1)
    slot_start_arr = np.asarray(slot_start, dtype=np.int32).reshape(-1)
    slot_count_arr = np.asarray(slot_count, dtype=np.int32).reshape(-1)
    seen_archive = _normalize_seen_archive_keys(seen_archive_keys)

    refresh_count_i = max(0, min(int(n_genomes) - 1, int(refresh_count)))
    if refresh_count_i <= 0:
        return np.asarray(pop_ids, dtype=np.int32).copy(), SteadyStateRefreshStats(
            survivors_kept=int(n_genomes),
            survivor_duplicates_dropped=0,
            survivor_archive_rejected=0,
            fresh_added=0,
            fresh_archive_collisions=0,
            fallback_archive_reused=0,
            fallback_duplicates_added=0,
        )

    survivor_target = max(1, int(n_genomes) - int(refresh_count_i))
    elite_keep_target = max(0, min(int(survivor_target), int(elite_keep_count)))
    order = np.argsort(-scores_arr, kind="stable")

    selected: list[np.ndarray] = []
    selected_keys: set[tuple[int, ...]] = set()
    duplicate_survivors = 0
    archive_rejected = 0

    for idx in order.tolist():
        row = np.asarray(pop_ids[int(idx)], dtype=np.int32)
        key = _canonical_row_key(row)
        if key in selected_keys:
            duplicate_survivors += 1
            continue
        selected_keys.add(key)
        selected.append(row.copy())
        if len(selected) >= int(elite_keep_target):
            break

    for idx in order.tolist():
        row = np.asarray(pop_ids[int(idx)], dtype=np.int32)
        key = _canonical_row_key(row)
        if key in selected_keys:
            duplicate_survivors += 1
            continue
        if key in seen_archive:
            archive_rejected += 1
            continue
        selected_keys.add(key)
        selected.append(row.copy())
        if len(selected) >= int(survivor_target):
            break

    rng = np.random.default_rng(int(seed) & 0xFFFFFFFF)
    fresh_added = 0
    fresh_archive_collisions = 0
    attempts = 0
    max_attempts = max(256, int(refresh_count_i) * 64)
    while len(selected) < int(n_genomes) and attempts < int(max_attempts):
        candidate = _sample_fresh_population_row(
            rng=rng,
            slot_start=slot_start_arr,
            slot_count=slot_count_arr,
            n_slots=int(n_slots),
        )
        key = _canonical_row_key(candidate)
        attempts += 1
        if key in selected_keys or key in seen_archive:
            fresh_archive_collisions += 1
            continue
        selected_keys.add(key)
        selected.append(candidate)
        fresh_added += 1

    fallback_archive_reused = 0
    fallback_duplicates = 0
    if len(selected) < int(n_genomes):
        for idx in order.tolist():
            row = np.asarray(pop_ids[int(idx)], dtype=np.int32)
            key = _canonical_row_key(row)
            if key in selected_keys:
                continue
            selected_keys.add(key)
            selected.append(row.copy())
            fallback_archive_reused += 1
            if len(selected) >= int(n_genomes):
                break
    if len(selected) < int(n_genomes):
        for idx in order.tolist():
            selected.append(np.asarray(pop_ids[int(idx)], dtype=np.int32).copy())
            fallback_duplicates += 1
            if len(selected) >= int(n_genomes):
                break

    return np.asarray(selected[: int(n_genomes)], dtype=np.int32), SteadyStateRefreshStats(
        survivors_kept=min(int(survivor_target), len(selected)),
        survivor_duplicates_dropped=int(duplicate_survivors),
        survivor_archive_rejected=int(archive_rejected),
        fresh_added=int(fresh_added),
        fresh_archive_collisions=int(fresh_archive_collisions),
        fallback_archive_reused=int(fallback_archive_reused),
        fallback_duplicates_added=int(fallback_duplicates),
    )
