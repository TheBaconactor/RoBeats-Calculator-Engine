from __future__ import annotations

import numpy as np

from gear_optimizer.core.jit_setup import jit


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


@jit(nopython=True, cache=True, nogil=True, inline="always")
def _hash_8u32(table: np.ndarray, idx: int) -> np.uint64:
    w0 = np.uint64(table[idx, 0]) | (np.uint64(table[idx, 1]) << np.uint64(32))
    w1 = np.uint64(table[idx, 2]) | (np.uint64(table[idx, 3]) << np.uint64(32))
    w2 = np.uint64(table[idx, 4]) | (np.uint64(table[idx, 5]) << np.uint64(32))
    w3 = np.uint64(table[idx, 6]) | (np.uint64(table[idx, 7]) << np.uint64(32))
    h = w0 * np.uint64(0x9E3779B97F4A7C15)
    h = (h ^ (h >> np.uint64(29)) ^ w1) * np.uint64(0xBF58476D1CE4E5B9)
    h = (h ^ (h >> np.uint64(31)) ^ w2) * np.uint64(0x94D049BB133111EB)
    h = (h ^ (h >> np.uint64(29)) ^ w3) * np.uint64(0x9E3779B97F4A7C15)
    return h ^ (h >> np.uint64(32))


@jit(nopython=True, cache=True, nogil=True)
def _intern_head_words_numba(surface_rows: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """O(R) open-addressing hash interning of the 8-word head masks in `surface_rows[:, :8]`."""
    n = surface_rows.shape[0]
    raw_pid = np.empty(n, dtype=np.uint32)
    cap = 64
    slots = np.full(cap, -1, dtype=np.int32)
    uniq = np.empty((32, 8), dtype=np.uint32)
    count = 0
    for i in range(n):
        h = _hash_8u32(surface_rows, i)
        mask = cap - 1
        slot = np.int64(h & np.uint64(mask))
        while True:
            pid = int(slots[slot])
            if pid < 0:
                if 2 * (count + 1) > cap:
                    cap *= 2
                    mask = cap - 1
                    slots = np.full(cap, -1, dtype=np.int32)
                    for prev in range(count):
                        ps = np.int64(_hash_8u32(uniq, prev) & np.uint64(mask))
                        while slots[ps] >= 0:
                            ps = (ps + 1) & mask
                        slots[ps] = np.int32(prev)
                    slot = np.int64(h & np.uint64(mask))
                    while slots[slot] >= 0:
                        slot = (slot + 1) & mask
                if count >= uniq.shape[0]:
                    grown = np.empty((2 * uniq.shape[0], 8), dtype=np.uint32)
                    grown[:count] = uniq[:count]
                    uniq = grown
                for c in range(8):
                    uniq[count, c] = surface_rows[i, c]
                slots[slot] = np.int32(count)
                raw_pid[i] = np.uint32(count)
                count += 1
                break
            same = True
            for c in range(8):
                if uniq[pid, c] != surface_rows[i, c]:
                    same = False
                    break
            if same:
                raw_pid[i] = np.uint32(pid)
                break
            slot = (slot + 1) & mask
    return raw_pid, uniq[:count].copy()


@jit(nopython=True, cache=True, nogil=True)
def _pack_row_refs_numba(surface_rows: np.ndarray, raw_pid: np.ndarray, inv_rank: np.ndarray) -> np.ndarray:
    n = surface_rows.shape[0]
    row_refs = np.empty((n, SURFACE_ROW_COLUMNS), dtype=np.uint32)
    for i in range(n):
        row_refs[i, 0] = inv_rank[raw_pid[i]]
        row_refs[i, 1] = surface_rows[i, 8]
        row_refs[i, 2] = surface_rows[i, 9]
        row_refs[i, 3] = surface_rows[i, 10]
    return row_refs


def intern_surface_row_words(surface_rows: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(n, 11) uint32 surface rows with their head words interned, every logical row kept in producer order: (row
    references, unique words). Unique words are sorted lexicographically so persisted pattern IDs match
    ``np.unique(..., axis=0)`` in O(R + P log P) instead of O(R log R)."""
    rows = np.ascontiguousarray(surface_rows, dtype=np.uint32)
    if rows.shape[0] == 0:
        return np.empty((0, SURFACE_ROW_COLUMNS), dtype=np.uint32), np.empty((0, 8), dtype=np.uint32)
    raw_pid, uniq_raw = _intern_head_words_numba(rows)
    n_uniq = uniq_raw.shape[0]
    if n_uniq <= 1:
        unique_words = uniq_raw
        inv_rank = np.zeros(n_uniq, dtype=np.uint32)
    else:
        order = np.lexsort(tuple(uniq_raw[:, c] for c in range(7, -1, -1)))
        unique_words = np.ascontiguousarray(uniq_raw[order])
        inv_rank = np.empty(n_uniq, dtype=np.uint32)
        inv_rank[order] = np.arange(n_uniq, dtype=np.uint32)
    row_refs = _pack_row_refs_numba(rows, raw_pid, inv_rank)
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
