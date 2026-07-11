from __future__ import annotations

import numpy as np


SURFACE_ROW_COLUMNS = 4
SURFACE_PATTERN_COLUMNS = 10
EXPANDED_SURFACE_COLUMNS = 11
EXPANDED_COEFF_COLUMNS = 4


def intern_surface_rows(
    surface_rows: np.ndarray,
    surface_coeffs: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Intern exact head behavior without changing logical surface order.

    Returns ``(row_refs, patterns)``. ``row_refs`` is uint32 ``(rows, 4)`` with
    ``[pattern_id, body_fever, body_great, body_fever_great]``. ``patterns`` is uint32
    ``(patterns, 10)`` with eight mask words and two words packing four uint16 coefficients.
    Equality is structural: every mask word is compared, and the coefficient consistency check
    prevents a future scoring change from silently merging rows with equal masks but different
    derived coefficients.
    """
    rows = np.ascontiguousarray(np.asarray(surface_rows, dtype=np.uint32))
    coeffs = np.ascontiguousarray(np.asarray(surface_coeffs))
    if rows.ndim != 2 or rows.shape[1] != EXPANDED_SURFACE_COLUMNS:
        raise ValueError("FG response expanded surface rows must have shape (n, 11)")
    if coeffs.ndim != 2 or coeffs.shape != (rows.shape[0], EXPANDED_COEFF_COLUMNS):
        raise ValueError("FG response surface coefficients must have shape (n, 4)")
    if coeffs.size:
        coeff_min = int(np.min(coeffs))
        coeff_max = int(np.max(coeffs))
        if coeff_min < 0 or coeff_max > int(np.iinfo(np.uint16).max):
            raise ValueError(
                f"FG response surface head coefficients exceed uint16 bounds: {coeff_min}..{coeff_max}"
            )
    coeffs_u16 = np.ascontiguousarray(coeffs, dtype=np.uint16)
    if int(rows.shape[0]) == 0:
        return (
            np.empty((0, SURFACE_ROW_COLUMNS), dtype=np.uint32),
            np.empty((0, SURFACE_PATTERN_COLUMNS), dtype=np.uint32),
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
    pattern_coeffs = np.ascontiguousarray(coeffs_u16[first_indices], dtype=np.uint16)
    if not np.array_equal(coeffs_u16, pattern_coeffs[inverse]):
        raise ValueError("FG response equal head masks produced inconsistent scoring coefficients")

    row_refs = np.empty((int(rows.shape[0]), SURFACE_ROW_COLUMNS), dtype=np.uint32)
    row_refs[:, 0] = np.asarray(inverse, dtype=np.uint32)
    row_refs[:, 1:4] = rows[:, 8:11]

    patterns = np.empty((pattern_count, SURFACE_PATTERN_COLUMNS), dtype=np.uint32)
    patterns[:, :8] = np.asarray(unique_words, dtype=np.uint32)
    coeffs_u32 = np.asarray(pattern_coeffs, dtype=np.uint32)
    patterns[:, 8] = coeffs_u32[:, 0] | (coeffs_u32[:, 1] << np.uint32(16))
    patterns[:, 9] = coeffs_u32[:, 2] | (coeffs_u32[:, 3] << np.uint32(16))
    return np.ascontiguousarray(row_refs), np.ascontiguousarray(patterns)


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
