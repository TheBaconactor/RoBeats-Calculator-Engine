from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def _region_hit_value_universe(
    timestamps: np.ndarray,
    perfect_candidate_timestamps: np.ndarray,
    great_candidate_timestamps: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Intern every exact float64 value the canonical region hit selector can return.

    Tokens are laid out as chart / Perfect / Great / capped-Perfect / capped-Great, each with
    ``n`` note slots. The selector's cap is always one of those values; the returned token-to-ID
    map therefore replaces repeated table timestamps without reconstructing game-engine semantics.
    """
    chart = np.ascontiguousarray(np.asarray(timestamps, dtype=np.float32).reshape(-1))
    perfect = np.ascontiguousarray(
        np.asarray(perfect_candidate_timestamps, dtype=np.float32).reshape(-1)
    )
    great = np.ascontiguousarray(
        np.asarray(great_candidate_timestamps, dtype=np.float32).reshape(-1)
    )
    if int(perfect.shape[0]) != int(chart.shape[0]) or int(great.shape[0]) != int(chart.shape[0]):
        raise ValueError("FG region hit-universe timestamp arrays must align")
    if int(chart.shape[0]) > np.iinfo(np.int32).max // 5:
        raise OverflowError("FG region hit-universe token count exceeds int32 capacity")
    if not (
        np.all(np.isfinite(chart))
        and np.all(np.isfinite(perfect))
        and np.all(np.isfinite(great))
    ):
        raise ValueError("FG region hit-universe timestamps must be finite")
    chart64 = chart.astype(np.float64)
    perfect64 = perfect.astype(np.float64)
    great64 = great.astype(np.float64)
    token_values = np.concatenate(
        (
            chart64,
            perfect64,
            great64,
            perfect64 - 1.0e-6,
            great64 - 1.0e-6,
        )
    )
    unique_values, token_to_id = np.unique(token_values, return_inverse=True)
    if int(unique_values.shape[0]) > np.iinfo(np.int32).max:
        raise OverflowError("FG region hit-universe ID count exceeds int32 capacity")
    return (
        np.ascontiguousarray(unique_values, dtype=np.float64),
        np.ascontiguousarray(token_to_id, dtype=np.int32),
    )


def _region_hit_end_index_tables(
    hit_values: np.ndarray,
    unique_real_times: np.ndarray,
    perfect_floor_timestamps: np.ndarray,
    great_floor_timestamps: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Resolve every interned region hit once per distinct fever time for the whole song."""
    values = np.ascontiguousarray(np.asarray(hit_values, dtype=np.float64).reshape(-1))
    real_times = np.ascontiguousarray(
        np.asarray(unique_real_times, dtype=np.float64).reshape(-1)
    )
    perfect_floor = np.ascontiguousarray(
        np.asarray(perfect_floor_timestamps, dtype=np.float32).reshape(-1)
    )
    great_floor = np.ascontiguousarray(
        np.asarray(great_floor_timestamps, dtype=np.float32).reshape(-1)
    )
    if int(perfect_floor.shape[0]) != int(great_floor.shape[0]):
        raise ValueError("FG region endpoint floor arrays must align")
    if int(perfect_floor.shape[0]) > np.iinfo(np.int32).max:
        raise OverflowError("FG region endpoint count exceeds int32 capacity")
    if not np.all(np.isfinite(real_times)):
        raise ValueError("FG region real-time table contains a non-finite value")
    if real_times.shape[0] > 1 and np.any(real_times[1:] <= real_times[:-1]):
        raise ValueError("FG region real-time table must be strictly increasing")

    shape = (int(real_times.shape[0]), int(values.shape[0]))
    perfect_end = np.empty(shape, dtype=np.int32)
    great_end = np.empty(shape, dtype=np.int32)
    for real_time_idx, real_fever_time in enumerate(real_times):
        cutoffs = np.asarray(values + float(real_fever_time), dtype=np.float32)
        perfect_end[int(real_time_idx)] = np.searchsorted(
            perfect_floor,
            cutoffs,
            side="left",
        )
        great_end[int(real_time_idx)] = np.searchsorted(
            great_floor,
            cutoffs,
            side="left",
        )
    return perfect_end, great_end


def _first_only_region_groups(items: list[tuple]) -> dict[tuple[float, int], list[tuple]]:
    """Partition canonical prepared items by their region-core-table key.

    The region-run core work depends on the geometry only through
    ``(raw_fever_fill, non_fever_base)`` — item slots 2 and 1 — never ``real_fever_time``, so all
    fever-time variants of one key share one table. Keys keep first-appearance order and items
    keep their canonical order within a key, so the batch scheduler can build tables serially,
    reduce admitted groups concurrently, and restore canonical result order deterministically.
    """
    groups: dict[tuple[float, int], list[tuple]] = {}
    for item in items:
        groups.setdefault((float(item[2]), int(item[1])), []).append(item)
    return groups


def _action_arrays_signature(item: tuple) -> tuple[bytes, ...]:
    return tuple(np.ascontiguousarray(value, dtype=np.int32).tobytes() for value in item[4:])


@dataclass(frozen=True)
class FirstOnlyCanonicalization:
    prepared: list[tuple]
    duplicate_sources_by_source: dict[int, tuple[int, ...]]
    real_time_index_by_source: dict[int, int]
    unique_real_times: np.ndarray
    timestamp_end_idx: np.ndarray
    perfect_end_idx: np.ndarray
    great_end_idx: np.ndarray
    great_floor_end_idx: np.ndarray
    capped_perfect_edge_e: np.ndarray
    capped_late_edge_e: np.ndarray
    capped_eg_perfect_e: np.ndarray
    capped_eg_late_e: np.ndarray


def _canonicalize_first_only_prepared_items_with_end_indices(
    *,
    prepared: list[tuple],
    timestamps: np.ndarray,
    perfect_candidate_timestamps: np.ndarray,
    great_candidate_timestamps: np.ndarray,
    perfect_floor_timestamps: np.ndarray,
    great_floor_timestamps: np.ndarray,
    prefix_perfect_hit: np.ndarray,
    prefix_late_hit: np.ndarray,
    lanes: np.ndarray | None = None,
) -> FirstOnlyCanonicalization:
    if not prepared:
        empty = np.empty((0, 0), dtype=np.int32)
        empty3 = np.empty((0, 0, 2), dtype=np.int32)
        return FirstOnlyCanonicalization(
            [],
            {},
            {},
            np.empty(0, dtype=np.float64),
            empty,
            empty,
            empty,
            empty3,
            empty,
            empty,
            empty,
            empty,
        )
    real_times = np.asarray([item[3] for item in prepared], dtype=np.float64)
    unique_real_times = np.unique(real_times)
    (
        real_time_index,
        timestamp_end_idx,
        perfect_end_idx,
        great_end_idx,
        great_floor_end_idx,
        capped_perfect_edge_e,
        capped_late_edge_e,
        capped_eg_perfect_e,
        capped_eg_late_e,
    ) = _precompute_end_indices(
        timestamps=timestamps,
        perfect_candidate_timestamps=perfect_candidate_timestamps,
        great_candidate_timestamps=great_candidate_timestamps,
        perfect_floor_timestamps=perfect_floor_timestamps,
        great_floor_timestamps=great_floor_timestamps,
        prefix_perfect_hit=prefix_perfect_hit,
        prefix_late_hit=prefix_late_hit,
        lanes=lanes,
        real_times=real_times,
    )
    if len(prepared) == 1:
        source_idx = int(prepared[0][0])
        return FirstOnlyCanonicalization(
            prepared,
            {source_idx: (source_idx,)},
            {source_idx: int(real_time_index[0])},
            unique_real_times,
            timestamp_end_idx,
            perfect_end_idx,
            great_end_idx,
            great_floor_end_idx,
            capped_perfect_edge_e,
            capped_late_edge_e,
            capped_eg_perfect_e,
            capped_eg_late_e,
        )
    end_class_by_index = np.empty((int(timestamp_end_idx.shape[0]),), dtype=np.int32)
    end_class_by_signature: dict[tuple[bytes, bytes, bytes, bytes], int] = {}
    for idx in range(int(timestamp_end_idx.shape[0])):
        signature = (
            np.ascontiguousarray(timestamp_end_idx[idx], dtype=np.int32).tobytes(),
            np.ascontiguousarray(perfect_end_idx[idx], dtype=np.int32).tobytes(),
            np.ascontiguousarray(great_end_idx[idx], dtype=np.int32).tobytes(),
            # Issue #44: the early-Great extended fever-end is part of an item's end-class, so
            # geometries that differ ONLY in their great_floor boundary are not wrongly deduped.
            np.ascontiguousarray(great_floor_end_idx[idx], dtype=np.int32).tobytes(),
        )
        class_idx = end_class_by_signature.get(signature)
        if class_idx is None:
            class_idx = len(end_class_by_signature)
            end_class_by_signature[signature] = int(class_idx)
        end_class_by_index[idx] = int(class_idx)

    canonical_items: list[tuple] = []
    duplicate_sources_by_source: dict[int, list[int]] = {}
    action_class_by_object: dict[tuple[int, ...], int] = {}
    action_class_by_signature: dict[tuple[bytes, ...], int] = {}
    canonical_by_signature: dict[tuple[int, int], int] = {}
    real_time_index_by_source: dict[int, int] = {}
    for local_idx, item in enumerate(prepared):
        source_idx = int(item[0])
        action_object_key = tuple(id(value) for value in item[4:])
        action_class = action_class_by_object.get(action_object_key)
        if action_class is None:
            action_signature = _action_arrays_signature(item)
            action_class = action_class_by_signature.get(action_signature)
            if action_class is None:
                action_class = len(action_class_by_signature)
                action_class_by_signature[action_signature] = int(action_class)
            action_class_by_object[action_object_key] = int(action_class)
        signature = (
            int(action_class),
            int(end_class_by_index[int(real_time_index[int(local_idx)])]),
        )
        canonical_source_idx = canonical_by_signature.get(signature)
        if canonical_source_idx is None:
            canonical_by_signature[signature] = int(source_idx)
            canonical_items.append(item)
            duplicate_sources_by_source[int(source_idx)] = [int(source_idx)]
            real_time_index_by_source[int(source_idx)] = int(real_time_index[int(local_idx)])
            continue
        duplicate_sources_by_source[int(canonical_source_idx)].append(int(source_idx))

    return FirstOnlyCanonicalization(
        canonical_items,
        {
            int(source_idx): tuple(int(value) for value in source_indices)
            for source_idx, source_indices in duplicate_sources_by_source.items()
        },
        real_time_index_by_source,
        unique_real_times,
        timestamp_end_idx,
        perfect_end_idx,
        great_end_idx,
        great_floor_end_idx,
        capped_perfect_edge_e,
        capped_late_edge_e,
        capped_eg_perfect_e,
        capped_eg_late_e,
    )



def _precompute_end_indices(
    *,
    timestamps: np.ndarray,
    perfect_candidate_timestamps: np.ndarray,
    great_candidate_timestamps: np.ndarray,
    perfect_floor_timestamps: np.ndarray,
    great_floor_timestamps: np.ndarray,
    real_times: np.ndarray,
    prefix_perfect_hit: np.ndarray,
    prefix_late_hit: np.ndarray,
    lanes: np.ndarray | None = None,
) -> tuple[np.ndarray, ...]:
    unique_real_times, inverse = np.unique(np.asarray(real_times, dtype=np.float64), return_inverse=True)
    ts = np.ascontiguousarray(np.asarray(timestamps, dtype=np.float32).reshape(-1))
    perfect_ts = np.ascontiguousarray(np.asarray(perfect_candidate_timestamps, dtype=np.float32).reshape(-1))
    great_ts = np.ascontiguousarray(np.asarray(great_candidate_timestamps, dtype=np.float32).reshape(-1))
    if lanes is None:
        raise ValueError("lanes are required for input-engine-aware FG precompute")
    if int(np.asarray(lanes, dtype=np.int32).reshape(-1).shape[0]) != int(ts.shape[0]):
        raise ValueError("lanes length must match timestamps")
    # Endpoint-early fever inclusion (issue #42): a later note is in fever iff its EARLIEST
    # legal hit precedes the cutoff, so the fever boundary searches the monotone earliest-
    # Perfect floor envelope, not chart. `floor_ts` is prebuilt prefix-max-monotone and shares
    # the candidate's quantized int-ms lattice (bit-consistent with the searched values).
    floor_ts = np.ascontiguousarray(np.asarray(perfect_floor_timestamps, dtype=np.float32).reshape(-1))
    if int(floor_ts.shape[0]) != int(ts.shape[0]):
        raise ValueError("perfect_floor_timestamps length must match timestamps")
    # Greats-side endpoint-early fever inclusion (issue #44): a boundary note 20-95ms past the
    # cutoff is out of Perfect reach but reachable into fever as a GREAT, so its EXTENDED fever
    # boundary searches the earliest-Great floor (chart - 95 / held tail -190, prefix-max; the
    # cumulative perfect_lower + great_lower_extra edge). It is pointwise <= the Perfect floor, so
    # great_floor_end_idx >= perfect/great_end_idx -- a
    # pure additional reachable end the kernel emits as a great-in-fever surface.
    great_floor_ts = np.ascontiguousarray(np.asarray(great_floor_timestamps, dtype=np.float32).reshape(-1))
    if int(great_floor_ts.shape[0]) != int(ts.shape[0]):
        raise ValueError("great_floor_timestamps length must match timestamps")
    ts64 = np.asarray(ts, dtype=np.float64)
    perfect_ts64 = np.asarray(perfect_ts, dtype=np.float64)
    great_ts64 = np.asarray(great_ts, dtype=np.float64)
    # Hit-time reachability of the PERFECT activation clock: a held-tail Perfect activation (+80)
    # whose narrower later-indexed sibling (+40) is hit first over-extends the drain window. Cap the
    # perfect-activation clock to the reachable value; the Perfect fever-end table below searches this
    # capped clock. Off overlap it equals perfect_ts64 exactly -> bit-identical. (The GREAT clock is
    # handled by the forbid clamp; each note's own uncapped hit stays in perfect_ts64 for reach checks.)
    # The legacy global perfect cap was lane-blind. Input-engine-aware production keeps each note's
    # own latest Perfect hit and lets reconstruction/persistence enforce the lane-aware owner.
    reachable_perfect_ts64 = perfect_ts64
    # Capped-hit activation clocks (rt-invariant, built once per chart): the per-activation latest
    # reachable Perfect / late-Great hit the kernel would otherwise re-derive with a live binary
    # search per (state, action). The four capped_* tables below memoize those searches per unique
    # real_fever_time, CLAMPED to (activation, n] exactly like `_numba_clamped_end_idx`, so a kernel
    # lookup `capped_*[rt_idx, a]` is bit-identical to
    # `_numba_edge_end_idx_at_hit` / `_numba_great_floor_extended_end_at_hit` at the prefix hit.
    prefix_perfect64 = np.ascontiguousarray(np.asarray(prefix_perfect_hit, dtype=np.float64).reshape(-1))
    prefix_late64 = np.ascontiguousarray(np.asarray(prefix_late_hit, dtype=np.float64).reshape(-1))
    if int(prefix_perfect64.shape[0]) != int(ts.shape[0]) or int(prefix_late64.shape[0]) != int(ts.shape[0]):
        raise ValueError("prefix activation-hit tables length must match timestamps")
    # clamp lower bound per activation column a is a+1; upper bound is n (same order as
    # `_numba_clamped_end_idx`: max(e, a+1) then min(e, n)).
    capped_clamp_lo = np.arange(1, int(ts.shape[0]) + 1, dtype=np.int64)
    timestamp_end_idx = np.empty((int(unique_real_times.shape[0]), int(ts.shape[0])), dtype=np.int32)
    perfect_end_idx = np.empty_like(timestamp_end_idx)
    great_end_idx = np.empty_like(timestamp_end_idx)
    capped_perfect_edge_e = np.empty_like(timestamp_end_idx)
    capped_late_edge_e = np.empty_like(timestamp_end_idx)
    capped_eg_perfect_e = np.empty_like(timestamp_end_idx)
    capped_eg_late_e = np.empty_like(timestamp_end_idx)
    # [..., 0] = extended end for a Perfect activation (cutoff = perfect_candidate + rt);
    # [..., 1] = extended end for a late-Great activation (cutoff = great_candidate + rt).
    great_floor_end_idx = np.empty((int(unique_real_times.shape[0]), int(ts.shape[0]), 2), dtype=np.int32)
    for idx, real_time in enumerate(unique_real_times):
        rt = float(real_time)
        perfect_cutoff = np.asarray(reachable_perfect_ts64 + rt, dtype=np.float32)
        great_cutoff = np.asarray(great_ts64 + rt, dtype=np.float32)
        timestamp_end_idx[idx] = np.searchsorted(floor_ts, np.asarray(ts64 + rt, dtype=np.float32), side="left").astype(
            np.int32,
            copy=False,
        )
        perfect_end_idx[idx] = np.searchsorted(floor_ts, perfect_cutoff, side="left").astype(np.int32, copy=False)
        great_end_idx[idx] = np.searchsorted(floor_ts, great_cutoff, side="left").astype(np.int32, copy=False)
        great_floor_end_idx[idx, :, 0] = np.searchsorted(great_floor_ts, perfect_cutoff, side="left").astype(
            np.int32, copy=False
        )
        great_floor_end_idx[idx, :, 1] = np.searchsorted(great_floor_ts, great_cutoff, side="left").astype(
            np.int32, copy=False
        )
        # Capped-hit fever ends: float64 add then float32 needle, matching the kernel's
        # `np.float32(float(hit) + float(real_fever_time))` bit for bit; invalid activations
        # (prefix_*_valid == 0) get the same deterministic formula -- the kernel never reads them.
        capped_perfect_cutoff = np.asarray(prefix_perfect64 + rt, dtype=np.float32)
        capped_late_cutoff = np.asarray(prefix_late64 + rt, dtype=np.float32)
        capped_perfect_edge_e[idx] = np.clip(
            np.searchsorted(floor_ts, capped_perfect_cutoff, side="left"), capped_clamp_lo, int(ts.shape[0])
        ).astype(np.int32, copy=False)
        capped_late_edge_e[idx] = np.clip(
            np.searchsorted(floor_ts, capped_late_cutoff, side="left"), capped_clamp_lo, int(ts.shape[0])
        ).astype(np.int32, copy=False)
        capped_eg_perfect_e[idx] = np.clip(
            np.searchsorted(great_floor_ts, capped_perfect_cutoff, side="left"), capped_clamp_lo, int(ts.shape[0])
        ).astype(np.int32, copy=False)
        capped_eg_late_e[idx] = np.clip(
            np.searchsorted(great_floor_ts, capped_late_cutoff, side="left"), capped_clamp_lo, int(ts.shape[0])
        ).astype(np.int32, copy=False)
    # Hit-time reachability (chord + notes-ahead): a late-Great activation is UNREACHABLE when an
    # earlier-hit note (a same-timestamp sibling, or an on-time note within the ~late-Great window
    # after it) completes the fever bar first -- delaying the activation to its late hit lets those
    # notes register before it. Clamping great_end_idx down to perfect_end_idx at those indices makes
    # the late-Great end `late_e <= perfect_e`, which EVERY build path already treats as "no
    # late-Great" (the `late_e <= perfect_e -> return` / `activation_e > edge_e` guards), so the
    # phantom late-Great is never emitted or selected -- the search falls back to the reachable
    # Perfect crossing it already enumerates. Off overlap (no forbidden index, e.g. sparse-tail or
    # non-chord charts) great_end_idx is UNCHANGED -> byte-identical frontier. The mask is a pure
    # function of the per-note windows (loadout-independent), computed once here.
    # The legacy global late-Great forbidden mask was lane-blind and loadout-independent. Do not
    # clamp here; exact activation legality is checked by the lane-aware reconstruction owner.
    return (
        np.ascontiguousarray(inverse.astype(np.int32, copy=False)),
        np.ascontiguousarray(timestamp_end_idx),
        np.ascontiguousarray(perfect_end_idx),
        np.ascontiguousarray(great_end_idx),
        np.ascontiguousarray(great_floor_end_idx),
        np.ascontiguousarray(capped_perfect_edge_e),
        np.ascontiguousarray(capped_late_edge_e),
        np.ascontiguousarray(capped_eg_perfect_e),
        np.ascontiguousarray(capped_eg_late_e),
    )
