from __future__ import annotations

import numpy as np


SURFACE_ROW_COLUMNS = 4
SURFACE_PATTERN_COLUMNS = 10
EXPANDED_SURFACE_COLUMNS = 11
EXPANDED_COEFF_COLUMNS = 4

# Per 16-bit half of a head fever word: how many head notes it marks and the sum of their 1-based positions.
_U16_BITS = np.unpackbits(
    np.arange(1 << 16, dtype=np.uint16).view(np.uint8).reshape(-1, 2), axis=1, bitorder="little"
).astype(np.int32)
_U16_COUNT = np.sum(_U16_BITS, axis=1, dtype=np.int32)
_U16_POS_SUM = np.sum(_U16_BITS * np.arange(1, 17, dtype=np.int32), axis=1, dtype=np.int32)
del _U16_BITS


def surface_head_coeffs(pattern_words: np.ndarray, *, head_len: int) -> np.ndarray:
    """(n, 4) int32 per head pattern over its first min(head_len, 100) notes: normal notes, fever notes, the sum of
    the normal notes' 1-based positions, the sum of the fever notes' (from the pattern's four fever words)."""
    words = np.asarray(pattern_words, dtype=np.uint32)
    coeffs = np.zeros((int(words.shape[0]), EXPANDED_COEFF_COLUMNS), dtype=np.int32)
    head = max(0, min(int(head_len), 100))
    for block in range(4):
        start = 32 * block
        take = min(32, head - start)
        if take <= 0:
            break
        block_words = words[:, block]
        low = (block_words & np.uint32((1 << min(16, take)) - 1)).astype(np.uint16)
        fever = _U16_COUNT[low]
        position_sum = _U16_POS_SUM[low]
        if take > 16:
            high = ((block_words >> np.uint32(16)) & np.uint32((1 << (take - 16)) - 1)).astype(np.uint16)
            fever = fever + _U16_COUNT[high]
            position_sum = position_sum + _U16_POS_SUM[high] + 16 * _U16_COUNT[high]
        fever_position_sum = position_sum + start * fever
        coeffs[:, 0] += take - fever
        coeffs[:, 1] += fever
        coeffs[:, 2] += take * (2 * start + take + 1) // 2 - fever_position_sum
        coeffs[:, 3] += fever_position_sum
    return coeffs


def surface_head_greats(pattern_words: np.ndarray) -> np.ndarray:
    """(n, 2) int32 per head pattern: its Great notes outside fever, its Great notes in fever."""
    words = np.asarray(pattern_words, dtype=np.uint32)
    fever, great = words[:, :4], words[:, 4:8]

    def count(masks: np.ndarray) -> np.ndarray:
        return (_U16_COUNT[masks & np.uint32(0xFFFF)] + _U16_COUNT[masks >> np.uint32(16)]).sum(axis=1)

    return np.stack((count(great & ~fever), count(great & fever)), axis=1).astype(np.int32)


def intern_surface_row_words(surface_rows: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Exact head words interned, every logical row kept in producer order: (row references, unique words).
    ``np.unique(..., axis=0)`` owns the pattern IDs, so their lexicographic order is the persisted one."""
    rows = np.ascontiguousarray(np.asarray(surface_rows, dtype=np.uint32))
    if rows.ndim != 2 or rows.shape[1] != EXPANDED_SURFACE_COLUMNS:
        raise ValueError("FG response expanded surface rows must have shape (n, 11)")
    if int(rows.shape[0]) == 0:
        return np.empty((0, SURFACE_ROW_COLUMNS), dtype=np.uint32), np.empty((0, 8), dtype=np.uint32)
    unique_words, inverse = np.unique(rows[:, :8], axis=0, return_inverse=True)
    pattern_count = int(unique_words.shape[0])
    if pattern_count > int(np.iinfo(np.int32).max):
        raise ValueError("FG response surface head-pattern count exceeds scorer int32 ID capacity")
    row_refs = np.empty((int(rows.shape[0]), SURFACE_ROW_COLUMNS), dtype=np.uint32)
    row_refs[:, 0] = np.asarray(inverse, dtype=np.uint32)
    row_refs[:, 1:4] = rows[:, 8:11]
    return np.ascontiguousarray(row_refs), np.ascontiguousarray(unique_words, dtype=np.uint32)


def pack_surface_patterns(
    pattern_words: np.ndarray,
    pattern_coeffs: np.ndarray,
) -> np.ndarray:
    """Pack one exact coefficient row for each already-interned head pattern."""
    words = np.ascontiguousarray(np.asarray(pattern_words, dtype=np.uint32))
    coeffs = np.ascontiguousarray(np.asarray(pattern_coeffs))
    if words.ndim != 2 or words.shape[1] != 8:
        raise ValueError("FG response surface pattern words must have shape (n, 8)")
    if coeffs.ndim != 2 or coeffs.shape != (words.shape[0], EXPANDED_COEFF_COLUMNS):
        raise ValueError("FG response surface pattern coefficients must have shape (n, 4)")
    if int(words.shape[0]) > int(np.iinfo(np.int32).max):
        raise ValueError("FG response surface head-pattern count exceeds scorer int32 ID capacity")
    if coeffs.size:
        coeff_min = int(np.min(coeffs))
        coeff_max = int(np.max(coeffs))
        if coeff_min < 0 or coeff_max > int(np.iinfo(np.uint16).max):
            raise ValueError(
                f"FG response surface head coefficients exceed uint16 bounds: {coeff_min}..{coeff_max}"
            )
    coeffs_u16 = np.ascontiguousarray(coeffs, dtype=np.uint16)

    patterns = np.empty((int(words.shape[0]), SURFACE_PATTERN_COLUMNS), dtype=np.uint32)
    patterns[:, :8] = words
    coeffs_u32 = np.asarray(coeffs_u16, dtype=np.uint32)
    patterns[:, 8] = coeffs_u32[:, 0] | (coeffs_u32[:, 1] << np.uint32(16))
    patterns[:, 9] = coeffs_u32[:, 2] | (coeffs_u32[:, 3] << np.uint32(16))
    return np.ascontiguousarray(patterns)


def unpack_surface_patterns(patterns: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return exact mask words and widened coefficients from persisted pattern rows."""
    pattern_rows = np.asarray(patterns, dtype=np.uint32)
    if pattern_rows.ndim != 2 or pattern_rows.shape[1] != SURFACE_PATTERN_COLUMNS:
        raise ValueError("FG response surface patterns must have shape (n, 10)")
    words = np.ascontiguousarray(pattern_rows[:, :8], dtype=np.uint32)
    coeffs = np.empty((int(pattern_rows.shape[0]), EXPANDED_COEFF_COLUMNS), dtype=np.int32)
    packed01 = pattern_rows[:, 8]
    packed23 = pattern_rows[:, 9]
    coeffs[:, 0] = np.asarray(packed01 & np.uint32(0xFFFF), dtype=np.int32)
    coeffs[:, 1] = np.asarray(packed01 >> np.uint32(16), dtype=np.int32)
    coeffs[:, 2] = np.asarray(packed23 & np.uint32(0xFFFF), dtype=np.int32)
    coeffs[:, 3] = np.asarray(packed23 >> np.uint32(16), dtype=np.int32)
    return words, np.ascontiguousarray(coeffs)
