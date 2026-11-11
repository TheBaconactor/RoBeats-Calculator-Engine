"""A frontier's surfaces as the producer emits them: (n, 7) uint64 rows holding the head's fever mask and Great mask in
two 64-bit words each (low word first), then the body's fever, Great and fever-Great note counts."""

import numpy as np

from .types import FgResponseSurface

_LOW_WORD = np.uint64(0xFFFFFFFF)
_WORD_BITS = np.uint64(32)


def _surface_rows_from_numba_rows(rows: np.ndarray, out: np.ndarray | None = None) -> np.ndarray:
    """The rows as (n, 11) uint32 surface rows, FgResponseSurface's fields (into `out` when given): each mask word as
    two 32-bit words, low first, then the three body counts."""
    if out is None:
        out = np.empty((rows.shape[0], 11), dtype=np.uint32)
    out[:, 0:8:2] = rows[:, :4] & _LOW_WORD
    out[:, 1:8:2] = rows[:, :4] >> _WORD_BITS
    out[:, 8:] = rows[:, 4:]
    return out


class SurfaceRowsFirstFrontier:
    """One frontier's rows, read as a sequence of FgResponseSurface on demand."""

    __slots__ = ("_numba_rows", "_surfaces")

    def __init__(self, rows: np.ndarray) -> None:
        self._numba_rows = rows
        self._surfaces: tuple[FgResponseSurface, ...] | None = None

    def numba_rows(self) -> np.ndarray:
        return self._numba_rows

    def _as_tuple(self) -> tuple[FgResponseSurface, ...]:
        if self._surfaces is None:
            self._surfaces = tuple(
                FgResponseSurface(*row) for row in _surface_rows_from_numba_rows(self._numba_rows).tolist()
            )
        return self._surfaces

    def __bool__(self) -> bool:
        return self._numba_rows.shape[0] > 0

    def __len__(self) -> int:
        return self._numba_rows.shape[0]

    def __iter__(self):
        return iter(self._as_tuple())

    def __getitem__(self, idx: int) -> FgResponseSurface:
        return self._as_tuple()[idx]

    def __eq__(self, other: object) -> bool:
        if isinstance(other, SurfaceRowsFirstFrontier):
            return np.array_equal(self._numba_rows, other._numba_rows)
        try:
            return self._as_tuple() == tuple(other)  # type: ignore[arg-type]
        except TypeError:
            return NotImplemented
