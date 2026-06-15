from __future__ import annotations

from dataclasses import dataclass

import numpy as np

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


def _canonicalize_first_only_prepared_items_with_end_indices(
    *,
    prepared: list[tuple],
    timestamps: np.ndarray,
    perfect_candidate_timestamps: np.ndarray,
    great_candidate_timestamps: np.ndarray,
    perfect_floor_timestamps: np.ndarray,
) -> FirstOnlyCanonicalization:
    if not prepared:
        empty = np.empty((0, 0), dtype=np.int32)
        return FirstOnlyCanonicalization([], {}, {}, empty, empty, empty)
    real_times = np.asarray([item[2] for item in prepared], dtype=np.float64)
    real_time_index, timestamp_end_idx, perfect_end_idx, great_end_idx = _precompute_end_indices(
        timestamps=timestamps,
        perfect_candidate_timestamps=perfect_candidate_timestamps,
        great_candidate_timestamps=great_candidate_timestamps,
        perfect_floor_timestamps=perfect_floor_timestamps,
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
        )
    end_class_by_index = np.empty((int(timestamp_end_idx.shape[0]),), dtype=np.int32)
    end_class_by_signature: dict[tuple[bytes, bytes, bytes], int] = {}
    for idx in range(int(timestamp_end_idx.shape[0])):
        signature = (
            np.ascontiguousarray(timestamp_end_idx[idx], dtype=np.int32).tobytes(),
            np.ascontiguousarray(perfect_end_idx[idx], dtype=np.int32).tobytes(),
            np.ascontiguousarray(great_end_idx[idx], dtype=np.int32).tobytes(),
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
    )



def _precompute_end_indices(
    *,
    timestamps: np.ndarray,
    perfect_candidate_timestamps: np.ndarray,
    great_candidate_timestamps: np.ndarray,
    perfect_floor_timestamps: np.ndarray,
    real_times: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
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
    ts64 = np.asarray(ts, dtype=np.float64)
    perfect_ts64 = np.asarray(perfect_ts, dtype=np.float64)
    great_ts64 = np.asarray(great_ts, dtype=np.float64)
    timestamp_end_idx = np.empty((int(unique_real_times.shape[0]), int(ts.shape[0])), dtype=np.int32)
    perfect_end_idx = np.empty_like(timestamp_end_idx)
    great_end_idx = np.empty_like(timestamp_end_idx)
    for idx, real_time in enumerate(unique_real_times):
        rt = float(real_time)
        timestamp_end_idx[idx] = np.searchsorted(floor_ts, np.asarray(ts64 + rt, dtype=np.float32), side="left").astype(
            np.int32,
            copy=False,
        )
        perfect_end_idx[idx] = np.searchsorted(
            floor_ts,
            np.asarray(perfect_ts64 + rt, dtype=np.float32),
            side="left",
        ).astype(
            np.int32,
            copy=False,
        )
        great_end_idx[idx] = np.searchsorted(floor_ts, np.asarray(great_ts64 + rt, dtype=np.float32), side="left").astype(
            np.int32,
            copy=False,
        )
    return (
        np.ascontiguousarray(inverse.astype(np.int32, copy=False)),
        np.ascontiguousarray(timestamp_end_idx),
        np.ascontiguousarray(perfect_end_idx),
        np.ascontiguousarray(great_end_idx),
    )
