import numpy as np

from .response_types import FgResponseSurface


def _surface_rows_from_numba_rows(rows: np.ndarray, out: np.ndarray | None = None) -> np.ndarray:
    src = np.ascontiguousarray(np.asarray(rows, dtype=np.uint64).reshape((-1, 7)))
    if out is None:
        out = np.empty((int(src.shape[0]), 11), dtype=np.uint32)
    elif tuple(out.shape) != (int(src.shape[0]), 11) or out.dtype != np.uint32:
        raise ValueError("surface-row conversion output must be (rows, 11) uint32")
    fever_lo = src[:, 0]
    fever_hi = src[:, 1]
    great_lo = src[:, 2]
    great_hi = src[:, 3]
    out[:, 0] = np.asarray(fever_lo & np.uint64(0xFFFFFFFF), dtype=np.uint32)
    out[:, 1] = np.asarray((fever_lo >> np.uint64(32)) & np.uint64(0xFFFFFFFF), dtype=np.uint32)
    out[:, 2] = np.asarray(fever_hi & np.uint64(0xFFFFFFFF), dtype=np.uint32)
    out[:, 3] = np.asarray((fever_hi >> np.uint64(32)) & np.uint64(0xFFFFFFFF), dtype=np.uint32)
    out[:, 4] = np.asarray(great_lo & np.uint64(0xFFFFFFFF), dtype=np.uint32)
    out[:, 5] = np.asarray((great_lo >> np.uint64(32)) & np.uint64(0xFFFFFFFF), dtype=np.uint32)
    out[:, 6] = np.asarray(great_hi & np.uint64(0xFFFFFFFF), dtype=np.uint32)
    out[:, 7] = np.asarray((great_hi >> np.uint64(32)) & np.uint64(0xFFFFFFFF), dtype=np.uint32)
    out[:, 8:11] = np.asarray(src[:, 4:7], dtype=np.uint32)
    return out


class SurfaceRowsFirstFrontier:
    __slots__ = ("_numba_rows", "_surface_rows", "_surfaces")

    def __init__(self, rows: np.ndarray) -> None:
        self._numba_rows = np.ascontiguousarray(np.asarray(rows, dtype=np.uint64).reshape((-1, 7)))
        self._surface_rows: np.ndarray | None = None
        self._surfaces: tuple[FgResponseSurface, ...] | None = None

    def surface_rows(self) -> np.ndarray:
        rows = self._surface_rows
        if rows is None:
            rows = _surface_rows_from_numba_rows(self._numba_rows)
            self._surface_rows = rows
        return rows

    def numba_rows(self) -> np.ndarray:
        return self._numba_rows

    def _as_tuple(self) -> tuple[FgResponseSurface, ...]:
        surfaces = self._surfaces
        if surfaces is None:
            surfaces = tuple(_surface_from_numba_row(self._numba_rows[idx]) for idx in range(int(self._numba_rows.shape[0])))
            self._surfaces = surfaces
        return surfaces

    def __bool__(self) -> bool:
        return int(self._numba_rows.shape[0]) > 0

    def __len__(self) -> int:
        return int(self._numba_rows.shape[0])

    def __iter__(self):
        return iter(self._as_tuple())

    def __getitem__(self, idx: int) -> FgResponseSurface:
        return self._as_tuple()[int(idx)]

    def __eq__(self, other: object) -> bool:
        if isinstance(other, SurfaceRowsFirstFrontier):
            return bool(np.array_equal(self.surface_rows(), other.surface_rows()))
        try:
            return self._as_tuple() == tuple(other)  # type: ignore[arg-type]
        except TypeError:
            return self._as_tuple() == other


def _surface_from_numba_row(row: np.ndarray) -> FgResponseSurface:
    fever_lo = int(row[0])
    fever_hi = int(row[1])
    great_lo = int(row[2])
    great_hi = int(row[3])
    return FgResponseSurface(
        fever_lo & 0xFFFFFFFF,
        (fever_lo >> 32) & 0xFFFFFFFF,
        fever_hi & 0xFFFFFFFF,
        (fever_hi >> 32) & 0xFFFFFFFF,
        great_lo & 0xFFFFFFFF,
        (great_lo >> 32) & 0xFFFFFFFF,
        great_hi & 0xFFFFFFFF,
        (great_hi >> 32) & 0xFFFFFFFF,
        int(row[4]),
        int(row[5]),
        int(row[6]),
    )
