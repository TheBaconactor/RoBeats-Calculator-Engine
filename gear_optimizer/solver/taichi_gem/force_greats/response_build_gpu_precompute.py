from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .fill_crossing import build_late_great_forbidden_mask, build_reachable_perfect_candidate

_GPU_EDGE_BATCH_MAX_BYTES = 4 * 1024 * 1024 * 1024

def _batch_chunk_size(*, n: int, action_count: int, geometry_count: int, bytes_per_edge: int = 64) -> int:
    denom = max(1, int(n) * max(1, int(action_count)) * bytes_per_edge)
    return max(1, min(int(geometry_count), int(_GPU_EDGE_BATCH_MAX_BYTES) // denom))



def _first_only_chunks(*, n: int, items: list[tuple]) -> list[tuple[int, list[tuple]]]:
    del n
    if not items:
        return []
    return [(0, list(items))]


def _action_arrays_signature(item: tuple) -> tuple[bytes, ...]:
    return tuple(np.ascontiguousarray(value, dtype=np.int32).tobytes() for value in item[3:])


@dataclass(frozen=True)
class FirstOnlyCanonicalization:
    prepared: list[tuple]
    duplicate_sources_by_source: dict[int, tuple[int, ...]]
    real_time_index_by_source: dict[int, int]
    timestamp_end_idx: np.ndarray
    perfect_end_idx: np.ndarray
    great_end_idx: np.ndarray
    great_floor_end_idx: np.ndarray


def _canonicalize_first_only_prepared_items_with_end_indices(
    *,
    prepared: list[tuple],
    timestamps: np.ndarray,
    perfect_candidate_timestamps: np.ndarray,
    great_candidate_timestamps: np.ndarray,
    perfect_floor_timestamps: np.ndarray,
    great_floor_timestamps: np.ndarray,
) -> FirstOnlyCanonicalization:
    if not prepared:
        empty = np.empty((0, 0), dtype=np.int32)
        empty3 = np.empty((0, 0, 2), dtype=np.int32)
        return FirstOnlyCanonicalization([], {}, {}, empty, empty, empty, empty3)
    real_times = np.asarray([item[2] for item in prepared], dtype=np.float64)
    real_time_index, timestamp_end_idx, perfect_end_idx, great_end_idx, great_floor_end_idx = _precompute_end_indices(
        timestamps=timestamps,
        perfect_candidate_timestamps=perfect_candidate_timestamps,
        great_candidate_timestamps=great_candidate_timestamps,
        perfect_floor_timestamps=perfect_floor_timestamps,
        great_floor_timestamps=great_floor_timestamps,
        real_times=real_times,
    )
    if len(prepared) == 1:
        source_idx = int(prepared[0][0])
        return FirstOnlyCanonicalization(
            prepared,
            {source_idx: (source_idx,)},
            {source_idx: int(real_time_index[0])},
            timestamp_end_idx,
            perfect_end_idx,
            great_end_idx,
            great_floor_end_idx,
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
        action_object_key = tuple(id(value) for value in item[3:])
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
        timestamp_end_idx,
        perfect_end_idx,
        great_end_idx,
        great_floor_end_idx,
    )



def _precompute_end_indices(
    *,
    timestamps: np.ndarray,
    perfect_candidate_timestamps: np.ndarray,
    great_candidate_timestamps: np.ndarray,
    perfect_floor_timestamps: np.ndarray,
    great_floor_timestamps: np.ndarray,
    real_times: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    unique_real_times, inverse = np.unique(np.asarray(real_times, dtype=np.float64), return_inverse=True)
    ts = np.ascontiguousarray(np.asarray(timestamps, dtype=np.float32).reshape(-1))
    perfect_ts = np.ascontiguousarray(np.asarray(perfect_candidate_timestamps, dtype=np.float32).reshape(-1))
    great_ts = np.ascontiguousarray(np.asarray(great_candidate_timestamps, dtype=np.float32).reshape(-1))
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
    reachable_perfect_ts64 = np.asarray(
        build_reachable_perfect_candidate(ts64, perfect_ts64, int(ts.shape[0])), dtype=np.float64)
    timestamp_end_idx = np.empty((int(unique_real_times.shape[0]), int(ts.shape[0])), dtype=np.int32)
    perfect_end_idx = np.empty_like(timestamp_end_idx)
    great_end_idx = np.empty_like(timestamp_end_idx)
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
    forbidden = build_late_great_forbidden_mask(ts64, perfect_ts64, great_ts64, int(ts.shape[0]))
    if bool(forbidden.any()):
        great_end_idx[:, forbidden] = perfect_end_idx[:, forbidden]
    return (
        np.ascontiguousarray(inverse.astype(np.int32, copy=False)),
        np.ascontiguousarray(timestamp_end_idx),
        np.ascontiguousarray(perfect_end_idx),
        np.ascontiguousarray(great_end_idx),
        np.ascontiguousarray(great_floor_end_idx),
    )
