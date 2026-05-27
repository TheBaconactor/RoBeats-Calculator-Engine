from __future__ import annotations

import numpy as np


def precompute_response_surface_head_coeffs(
    surface_words: np.ndarray,
    *,
    head_len: int,
) -> np.ndarray:
    words = np.ascontiguousarray(np.asarray(surface_words, dtype=np.uint32))
    row_count = int(words.shape[0])
    coeffs = np.zeros((row_count, 4), dtype=np.int32)
    if row_count <= 0:
        return coeffs
    head = max(0, min(int(head_len), 100))
    if head <= 0:
        return coeffs
    if int(words.ndim) != 2 or int(words.shape[1]) < 4:
        raise ValueError("response frontier GPU head-coeff precompute requires packed fever words")

    for block in range(4):
        start = int(block * 32)
        if start >= int(head):
            break
        take = min(32, int(head) - int(start))
        if take <= 0:
            continue
        block_words = np.ascontiguousarray(words[:, block], dtype=np.uint32)
        block_bytes = np.ascontiguousarray(block_words.view(np.uint8).reshape(row_count, 4), dtype=np.uint8)
        block_bits = np.unpackbits(block_bytes, axis=1, bitorder="little")[:, : int(take)].astype(np.int32, copy=False)
        fever_count = np.sum(block_bits, axis=1, dtype=np.int32)
        coeffs[:, 1] += fever_count
        coeffs[:, 0] += int(take) - fever_count
        positions = np.arange(int(start) + 1, int(start) + int(take) + 1, dtype=np.int32)
        sigma_hf = np.sum(block_bits * positions.reshape(1, -1), axis=1, dtype=np.int32)
        coeffs[:, 3] += sigma_hf
        coeffs[:, 2] += int(np.sum(positions, dtype=np.int32)) - sigma_hf
    return np.ascontiguousarray(coeffs, dtype=np.int32)
