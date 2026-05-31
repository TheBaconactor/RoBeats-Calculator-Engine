from __future__ import annotations

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


def _action_arrays_signature(item: tuple) -> tuple[bytes, bytes, bytes, bytes]:
    return (
        np.ascontiguousarray(item[3], dtype=np.int32).tobytes(),
        np.ascontiguousarray(item[4], dtype=np.int32).tobytes(),
        np.ascontiguousarray(item[5], dtype=np.int32).tobytes(),
        np.ascontiguousarray(item[6], dtype=np.int32).tobytes(),
    )



def _canonicalize_first_only_prepared_items(
    *,
    prepared: list[tuple],
    timestamps: np.ndarray,
    great_candidate_timestamps: np.ndarray,
) -> tuple[list[tuple], dict[int, tuple[int, ...]]]:
    if len(prepared) <= 1:
        return prepared, {int(item[0]): (int(item[0]),) for item in prepared}

    real_times = np.asarray([item[2] for item in prepared], dtype=np.float32)
    real_time_index, timestamp_end_idx, great_end_idx = _precompute_end_indices(
        timestamps=timestamps,
        great_candidate_timestamps=great_candidate_timestamps,
        real_times=real_times,
    )
    end_class_by_index = np.empty((int(timestamp_end_idx.shape[0]),), dtype=np.int32)
    end_class_by_signature: dict[tuple[bytes, bytes], int] = {}
    for idx in range(int(timestamp_end_idx.shape[0])):
        signature = (
            np.ascontiguousarray(timestamp_end_idx[idx], dtype=np.int32).tobytes(),
            np.ascontiguousarray(great_end_idx[idx], dtype=np.int32).tobytes(),
        )
        class_idx = end_class_by_signature.get(signature)
        if class_idx is None:
            class_idx = len(end_class_by_signature)
            end_class_by_signature[signature] = int(class_idx)
        end_class_by_index[idx] = int(class_idx)

    canonical_items: list[tuple] = []
    duplicate_sources_by_source: dict[int, list[int]] = {}
    action_class_by_object: dict[tuple[int, int, int, int], int] = {}
    action_class_by_signature: dict[tuple[bytes, bytes, bytes, bytes], int] = {}
    canonical_by_signature: dict[tuple[int, int], int] = {}
    for local_idx, item in enumerate(prepared):
        source_idx = int(item[0])
        action_object_key = (id(item[3]), id(item[4]), id(item[5]), id(item[6]))
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
            continue
        duplicate_sources_by_source[int(canonical_source_idx)].append(int(source_idx))

    return canonical_items, {
        int(source_idx): tuple(int(value) for value in source_indices)
        for source_idx, source_indices in duplicate_sources_by_source.items()
    }



def _precompute_end_indices(
    *,
    timestamps: np.ndarray,
    great_candidate_timestamps: np.ndarray,
    real_times: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    unique_real_times, inverse = np.unique(np.asarray(real_times, dtype=np.float32), return_inverse=True)
    ts = np.ascontiguousarray(np.asarray(timestamps, dtype=np.float32).reshape(-1))
    great_ts = np.ascontiguousarray(np.asarray(great_candidate_timestamps, dtype=np.float32).reshape(-1))
    timestamp_end_idx = np.empty((int(unique_real_times.shape[0]), int(ts.shape[0])), dtype=np.int32)
    great_end_idx = np.empty_like(timestamp_end_idx)
    for idx, real_time in enumerate(unique_real_times):
        rt = np.float32(real_time)
        timestamp_end_idx[idx] = np.searchsorted(ts, np.asarray(ts + rt, dtype=np.float32), side="left").astype(
            np.int32,
            copy=False,
        )
        great_end_idx[idx] = np.searchsorted(ts, np.asarray(great_ts + rt, dtype=np.float32), side="left").astype(
            np.int32,
            copy=False,
        )
    return (
        np.ascontiguousarray(inverse.astype(np.int32, copy=False)),
        np.ascontiguousarray(timestamp_end_idx),
        np.ascontiguousarray(great_end_idx),
    )

