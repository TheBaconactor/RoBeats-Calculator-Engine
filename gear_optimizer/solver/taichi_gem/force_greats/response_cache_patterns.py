from __future__ import annotations

import numpy as np


SURFACE_ROW_COLUMNS = 4
SURFACE_PATTERN_COLUMNS = 10
EXPANDED_SURFACE_COLUMNS = 11
EXPANDED_COEFF_COLUMNS = 4


def _intern_surface_row_words(
    surface_rows: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return row references, exact unique words, and their first source indices.

    ``np.unique(..., axis=0)`` remains the sole pattern-ID owner. Its lexicographic ordering is
    therefore unchanged from the original V30 writer, while callers that derive coefficients from
    head words can do that once per returned pattern instead of once per logical surface row.
    """
    rows = np.ascontiguousarray(np.asarray(surface_rows, dtype=np.uint32))
    if rows.ndim != 2 or rows.shape[1] != EXPANDED_SURFACE_COLUMNS:
        raise ValueError("FG response expanded surface rows must have shape (n, 11)")
    if int(rows.shape[0]) == 0:
        return (
            np.empty((0, SURFACE_ROW_COLUMNS), dtype=np.uint32),
            np.empty((0, 8), dtype=np.uint32),
            np.empty((0,), dtype=np.intp),
        )

    unique_words, first_indices, inverse = np.unique(
        rows[:, :8],
        axis=0,
        return_index=True,
        return_inverse=True,
    )
    pattern_count = int(unique_words.shape[0])
    if pattern_count > int(np.iinfo(np.int32).max):
        raise ValueError("FG response surface head-pattern count exceeds scorer int32 ID capacity")

    row_refs = np.empty((int(rows.shape[0]), SURFACE_ROW_COLUMNS), dtype=np.uint32)
    row_refs[:, 0] = np.asarray(inverse, dtype=np.uint32)
    row_refs[:, 1:4] = rows[:, 8:11]
    return (
        np.ascontiguousarray(row_refs),
        np.ascontiguousarray(unique_words, dtype=np.uint32),
        np.ascontiguousarray(first_indices, dtype=np.intp),
    )


def intern_surface_row_words(surface_rows: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Intern exact head words while retaining every logical row in producer order."""
    row_refs, unique_words, _first_indices = _intern_surface_row_words(surface_rows)
    return row_refs, unique_words


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


def intern_surface_rows(
    surface_rows: np.ndarray,
    surface_coeffs: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Intern exact head behavior without changing logical surface order.

    This row-coefficient entry remains the differential/oracle helper. The production writer
    derives coefficients from the exact unique words via ``intern_surface_row_words`` and
    ``pack_surface_patterns`` so equal masks cannot compute inconsistent coefficients in the first
    place. Structural equality and the V30 ``np.unique`` pattern ordering are shared by both paths.
    """
    row_refs, unique_words, first_indices = _intern_surface_row_words(surface_rows)
    coeffs = np.ascontiguousarray(np.asarray(surface_coeffs))
    if coeffs.ndim != 2 or coeffs.shape != (row_refs.shape[0], EXPANDED_COEFF_COLUMNS):
        raise ValueError("FG response surface coefficients must have shape (n, 4)")
    if coeffs.size:
        coeff_min = int(np.min(coeffs))
        coeff_max = int(np.max(coeffs))
        if coeff_min < 0 or coeff_max > int(np.iinfo(np.uint16).max):
            raise ValueError(
                f"FG response surface head coefficients exceed uint16 bounds: {coeff_min}..{coeff_max}"
            )
    coeffs_u16 = np.ascontiguousarray(coeffs, dtype=np.uint16)
    pattern_coeffs = np.ascontiguousarray(coeffs_u16[first_indices], dtype=np.uint16)
    pattern_ids = np.asarray(row_refs[:, 0], dtype=np.intp)
    if not np.array_equal(coeffs_u16, pattern_coeffs[pattern_ids]):
        raise ValueError("FG response equal head masks produced inconsistent scoring coefficients")
    return row_refs, pack_surface_patterns(unique_words, pattern_coeffs)


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


def expand_surface_rows(
    row_refs: np.ndarray,
    patterns: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Expand interned rows to the canonical scorer-facing arrays, preserving row order."""
    refs = np.ascontiguousarray(np.asarray(row_refs, dtype=np.uint32))
    pattern_rows = np.asarray(patterns, dtype=np.uint32)
    if refs.ndim != 2 or refs.shape[1] != SURFACE_ROW_COLUMNS:
        raise ValueError("FG response interned surface rows must have shape (n, 4)")
    if pattern_rows.ndim != 2 or pattern_rows.shape[1] != SURFACE_PATTERN_COLUMNS:
        raise ValueError("FG response surface patterns must have shape (n, 10)")
    if int(refs.shape[0]) == 0:
        return (
            np.empty((0, EXPANDED_SURFACE_COLUMNS), dtype=np.uint32),
            np.empty((0, EXPANDED_COEFF_COLUMNS), dtype=np.int32),
        )
    pattern_ids = np.asarray(refs[:, 0], dtype=np.uint64)
    if int(pattern_rows.shape[0]) <= 0 or bool(np.any(pattern_ids >= int(pattern_rows.shape[0]))):
        raise ValueError("FG response surface row references an invalid head-pattern ID")
    selected = pattern_rows[np.asarray(pattern_ids, dtype=np.intp)]
    rows = np.empty((int(refs.shape[0]), EXPANDED_SURFACE_COLUMNS), dtype=np.uint32)
    rows[:, :8] = selected[:, :8]
    rows[:, 8:11] = refs[:, 1:4]
    _words, coeffs = unpack_surface_patterns(selected)
    return np.ascontiguousarray(rows), coeffs
