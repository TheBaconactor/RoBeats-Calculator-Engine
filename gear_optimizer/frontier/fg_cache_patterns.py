from __future__ import annotations

import numpy as np


SURFACE_ROW_COLUMNS = 4
SURFACE_PATTERN_COLUMNS = 10
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
    """(n, 11) uint32 surface rows with their head words interned, every logical row kept in producer order: (row
    references, unique words). ``np.unique(..., axis=0)`` owns the pattern IDs, so their lexicographic order is the
    persisted one."""
    unique_words, inverse = np.unique(surface_rows[:, :8], axis=0, return_inverse=True)
    row_refs = np.empty((surface_rows.shape[0], SURFACE_ROW_COLUMNS), dtype=np.uint32)
    row_refs[:, 0] = inverse
    row_refs[:, 1:4] = surface_rows[:, 8:11]
    return row_refs, unique_words


def pack_surface_patterns(pattern_words: np.ndarray, pattern_coeffs: np.ndarray) -> np.ndarray:
    """One row per interned head pattern: its eight words, then its four head coefficients (each below 2^16, the
    counts and position sums of at most 100 head notes) packed two to a word."""
    coeffs = pattern_coeffs.astype(np.uint32)
    patterns = np.empty((pattern_words.shape[0], SURFACE_PATTERN_COLUMNS), dtype=np.uint32)
    patterns[:, :8] = pattern_words
    patterns[:, 8] = coeffs[:, 0] | (coeffs[:, 1] << np.uint32(16))
    patterns[:, 9] = coeffs[:, 2] | (coeffs[:, 3] << np.uint32(16))
    return patterns


def unpack_surface_patterns(patterns: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return exact mask words and widened coefficients from persisted pattern rows."""
    words = np.ascontiguousarray(patterns[:, :8])
    coeffs = np.empty((patterns.shape[0], EXPANDED_COEFF_COLUMNS), dtype=np.int32)
    packed01 = patterns[:, 8]
    packed23 = patterns[:, 9]
    coeffs[:, 0] = packed01 & np.uint32(0xFFFF)
    coeffs[:, 1] = packed01 >> np.uint32(16)
    coeffs[:, 2] = packed23 & np.uint32(0xFFFF)
    coeffs[:, 3] = packed23 >> np.uint32(16)
    return words, coeffs
