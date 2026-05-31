from __future__ import annotations

from typing import Any

import numpy as np

from .response_cache_keys import (
    _surface_from_row_cached,
    _surface_row,
    _surface_rows_array,
    fg_response_frontier_geometry_cache_key,
)
from .response_cache_store import (
    _frontier_is_complete,
    _load_bundle_array_members,
    _memory_get,
    _memory_put,
)
from .response_cache_types import (
    _FRONTIER_STATE_INDEX_ARRAY_NAMES,
    FgResponseFrontierScoringBundle,
    _normalize_stat_key,
)
from .response_types import FgResponseFrontierResult, FgResponseSurface


def _pack_frontiers(frontiers: tuple[FgResponseFrontierResult, ...]) -> dict[str, np.ndarray]:
    meta = np.zeros((len(frontiers), 7), dtype=np.int32)
    first_offsets = np.zeros((len(frontiers),), dtype=np.int32)
    first_counts = np.zeros((len(frontiers),), dtype=np.int32)
    state_offsets = np.zeros((len(frontiers),), dtype=np.int32)
    state_counts = np.zeros((len(frontiers),), dtype=np.int32)
    first_rows: list[tuple[int, ...]] = []
    state_keys: list[int] = []
    state_surface_offsets: list[int] = []
    state_surface_counts: list[int] = []
    state_surface_rows: list[tuple[int, ...]] = []

    for idx, frontier in enumerate(frontiers):
        meta[idx] = np.asarray(
            [
                int(frontier.states_evaluated),
                int(frontier.actions),
                int(frontier.transitions_evaluated),
                int(frontier.generated_surfaces),
                int(frontier.retained_surfaces_total),
                int(frontier.max_state_frontier),
                int(frontier.non_fever_base),
            ],
            dtype=np.int32,
        )
        first_offsets[idx] = len(first_rows)
        first_counts[idx] = len(frontier.first_frontier)
        first_rows.extend(_surface_row(surface) for surface in frontier.first_frontier)

        state_offsets[idx] = len(state_keys)
        sorted_states = sorted(int(state) for state in frontier.state_frontiers)
        state_counts[idx] = len(sorted_states)
        for state in sorted_states:
            surfaces = tuple(frontier.state_frontiers[state])
            state_keys.append(int(state))
            state_surface_offsets.append(len(state_surface_rows))
            state_surface_counts.append(len(surfaces))
            state_surface_rows.extend(_surface_row(surface) for surface in surfaces)

    return {
        "frontier_meta": meta,
        "first_offsets": first_offsets,
        "first_counts": first_counts,
        "first_surface_pool": _surface_rows_array(first_rows),
        "state_offsets": state_offsets,
        "state_counts": state_counts,
        "state_keys": np.asarray(state_keys, dtype=np.int32),
        "state_surface_offsets": np.asarray(state_surface_offsets, dtype=np.int32),
        "state_surface_counts": np.asarray(state_surface_counts, dtype=np.int32),
        "state_surface_pool": _surface_rows_array(state_surface_rows),
    }


def _unpack_frontiers(data: object) -> tuple[FgResponseFrontierResult, ...]:
    meta = np.asarray(data["frontier_meta"], dtype=np.int32)
    first_offsets = np.asarray(data["first_offsets"], dtype=np.int32)
    first_counts = np.asarray(data["first_counts"], dtype=np.int32)
    first_pool = np.asarray(data["first_surface_pool"], dtype=np.uint32)
    state_offsets = np.asarray(data["state_offsets"], dtype=np.int32)
    state_counts = np.asarray(data["state_counts"], dtype=np.int32)
    state_keys = np.asarray(data["state_keys"], dtype=np.int32)
    state_surface_offsets = np.asarray(data["state_surface_offsets"], dtype=np.int32)
    state_surface_counts = np.asarray(data["state_surface_counts"], dtype=np.int32)
    state_surface_pool = np.asarray(data["state_surface_pool"], dtype=np.uint32)

    out: list[FgResponseFrontierResult] = []
    surface_cache: dict[tuple[int, ...], FgResponseSurface] = {}
    for idx in range(int(meta.shape[0])):
        first_start = int(first_offsets[idx])
        first_count = int(first_counts[idx])
        first_frontier = tuple(
            _surface_from_row_cached(first_pool[row_idx], surface_cache)
            for row_idx in range(first_start, first_start + first_count)
        )
        states: dict[int, tuple[FgResponseSurface, ...]] = {}
        state_start = int(state_offsets[idx])
        for pool_idx in range(state_start, state_start + int(state_counts[idx])):
            surface_start = int(state_surface_offsets[pool_idx])
            surface_count = int(state_surface_counts[pool_idx])
            states[int(state_keys[pool_idx])] = tuple(
                _surface_from_row_cached(state_surface_pool[row_idx], surface_cache)
                for row_idx in range(surface_start, surface_start + surface_count)
            )
        row = meta[idx]
        out.append(
            FgResponseFrontierResult(
                first_frontier=first_frontier,
                state_frontiers=states,
                states_evaluated=int(row[0]),
                actions=int(row[1]),
                transitions_evaluated=int(row[2]),
                generated_surfaces=int(row[3]),
                retained_surfaces_total=int(row[4]),
                max_state_frontier=int(row[5]),
                non_fever_base=int(row[6]),
                seconds=0.0,
            )
        )
    return tuple(out)


class _LazyResponseStateFrontiers(dict[int, tuple[FgResponseSurface, ...]]):
    __slots__ = (
        "_bundle_key",
        "_state_keys",
        "_state_surface_offsets",
        "_state_surface_counts",
        "_state_index_by_key",
        "_surface_cache",
    )

    def __init__(
        self,
        *,
        bundle_key: tuple,
        state_keys: np.ndarray,
        state_surface_offsets: np.ndarray,
        state_surface_counts: np.ndarray,
    ) -> None:
        super().__init__()
        self._bundle_key = bundle_key
        self._state_keys = np.ascontiguousarray(state_keys, dtype=np.int32)
        self._state_surface_offsets = np.ascontiguousarray(state_surface_offsets, dtype=np.int32)
        self._state_surface_counts = np.ascontiguousarray(state_surface_counts, dtype=np.int32)
        self._state_index_by_key: dict[int, int] | None = None
        self._surface_cache: dict[tuple[int, ...], FgResponseSurface] = {}

    def _state_index(self) -> dict[int, int]:
        index = self._state_index_by_key
        if index is None:
            index = {int(state): int(idx) for idx, state in enumerate(self._state_keys.tolist())}
            self._state_index_by_key = index
        return index

    def __bool__(self) -> bool:
        return int(self._state_keys.shape[0]) > 0

    def __len__(self) -> int:
        return int(self._state_keys.shape[0])

    def __iter__(self):
        return iter(self._state_index())

    def __contains__(self, key: object) -> bool:
        try:
            state = int(key)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return False
        return state in self._state_index()

    def _materialize_state(self, state: int) -> tuple[FgResponseSurface, ...]:
        existing = dict.get(self, int(state))
        if existing is not None:
            return existing
        local_idx = self._state_index().get(int(state))
        if local_idx is None:
            raise KeyError(state)
        surface_start = int(self._state_surface_offsets[int(local_idx)])
        surface_count = int(self._state_surface_counts[int(local_idx)])
        arrays = _load_bundle_array_members(self._bundle_key, names=("state_surface_pool",))
        state_surface_pool = np.asarray(arrays["state_surface_pool"], dtype=np.uint32)
        surfaces = tuple(
            _surface_from_row_cached(state_surface_pool[row_idx], self._surface_cache)
            for row_idx in range(surface_start, surface_start + surface_count)
        )
        dict.__setitem__(self, int(state), surfaces)
        return surfaces

    def __getitem__(self, key: int) -> tuple[FgResponseSurface, ...]:
        return self._materialize_state(int(key))

    def get(
        self,
        key: int,
        default: tuple[FgResponseSurface, ...] | None = None,
    ) -> tuple[FgResponseSurface, ...] | None:
        try:
            return self._materialize_state(int(key))
        except (KeyError, TypeError, ValueError):
            return default


class _DeferredResponseStateFrontiers(dict[int, tuple[FgResponseSurface, ...]]):
    __slots__ = ("_bundle_key", "_frontier_idx", "_state_count_hint", "_delegate")

    def __init__(self, *, bundle_key: tuple, frontier_idx: int, state_count_hint: int) -> None:
        super().__init__()
        self._bundle_key = bundle_key
        self._frontier_idx = int(frontier_idx)
        self._state_count_hint = int(state_count_hint)
        self._delegate: _LazyResponseStateFrontiers | None = None

    def _load_delegate(self) -> _LazyResponseStateFrontiers:
        delegate = self._delegate
        if delegate is None:
            arrays = _load_bundle_array_members(self._bundle_key, names=_FRONTIER_STATE_INDEX_ARRAY_NAMES)
            state_offsets = np.asarray(arrays["state_offsets"], dtype=np.int32)
            state_counts = np.asarray(arrays["state_counts"], dtype=np.int32)
            idx = int(self._frontier_idx)
            if idx < 0 or idx >= int(state_offsets.shape[0]):
                raise ValueError("FG response cache frontier index is outside the state index bundle")
            state_start = int(state_offsets[idx])
            state_stop = state_start + int(state_counts[idx])
            delegate = _LazyResponseStateFrontiers(
                bundle_key=self._bundle_key,
                state_keys=np.asarray(arrays["state_keys"], dtype=np.int32)[state_start:state_stop],
                state_surface_offsets=np.asarray(arrays["state_surface_offsets"], dtype=np.int32)[state_start:state_stop],
                state_surface_counts=np.asarray(arrays["state_surface_counts"], dtype=np.int32)[state_start:state_stop],
            )
            self._delegate = delegate
        return delegate

    def __bool__(self) -> bool:
        return int(self._state_count_hint) > 0

    def __len__(self) -> int:
        if self._delegate is None:
            return int(self._state_count_hint)
        return len(self._delegate)

    def __iter__(self):
        return iter(self._load_delegate())

    def __contains__(self, key: object) -> bool:
        return key in self._load_delegate()

    def __getitem__(self, key: int) -> tuple[FgResponseSurface, ...]:
        return self._load_delegate()[int(key)]

    def get(
        self,
        key: int,
        default: tuple[FgResponseSurface, ...] | None = None,
    ) -> tuple[FgResponseSurface, ...] | None:
        return self._load_delegate().get(int(key), default)


class _LazyResponseFirstFrontier:
    __slots__ = ("_bundle_key", "_first_start", "_first_count", "_materialized", "_surface_cache")

    def __init__(self, *, bundle_key: tuple, first_start: int, first_count: int) -> None:
        self._bundle_key = bundle_key
        self._first_start = int(first_start)
        self._first_count = int(first_count)
        self._materialized: tuple[FgResponseSurface, ...] | None = None
        self._surface_cache: dict[tuple[int, ...], FgResponseSurface] = {}

    def _as_tuple(self) -> tuple[FgResponseSurface, ...]:
        materialized = self._materialized
        if materialized is None:
            arrays = _load_bundle_array_members(self._bundle_key, names=("first_surface_pool",))
            first_pool = np.asarray(arrays["first_surface_pool"], dtype=np.uint32)
            materialized = tuple(
                _surface_from_row_cached(first_pool[row_idx], self._surface_cache)
                for row_idx in range(self._first_start, self._first_start + self._first_count)
            )
            self._materialized = materialized
        return materialized

    def __bool__(self) -> bool:
        return int(self._first_count) > 0

    def __len__(self) -> int:
        return int(self._first_count)

    def __iter__(self):
        return iter(self._as_tuple())

    def __getitem__(self, idx: int) -> FgResponseSurface:
        return self._as_tuple()[int(idx)]

    def __eq__(self, other: object) -> bool:
        return self._as_tuple() == other


def _frontier_result_from_bundle_arrays(
    *,
    bundle_key: tuple,
    arrays: dict[str, np.ndarray],
    frontier_idx: int,
) -> FgResponseFrontierResult:
    idx = int(frontier_idx)
    meta = np.asarray(arrays["frontier_meta"], dtype=np.int32)
    if idx < 0 or idx >= int(meta.shape[0]):
        raise ValueError("FG response cache frontier index is outside the bundle")
    first_offsets = np.asarray(arrays["first_offsets"], dtype=np.int32)
    first_counts = np.asarray(arrays["first_counts"], dtype=np.int32)
    first_start = int(first_offsets[idx])
    first_count = int(first_counts[idx])
    first_frontier = _LazyResponseFirstFrontier(
        bundle_key=bundle_key,
        first_start=int(first_start),
        first_count=int(first_count),
    )
    state_offsets = np.asarray(arrays["state_offsets"], dtype=np.int32)
    state_counts = np.asarray(arrays["state_counts"], dtype=np.int32)
    state_start = int(state_offsets[idx])
    state_stop = state_start + int(state_counts[idx])
    state_frontiers = _LazyResponseStateFrontiers(
        bundle_key=bundle_key,
        state_keys=np.asarray(arrays["state_keys"], dtype=np.int32)[state_start:state_stop],
        state_surface_offsets=np.asarray(arrays["state_surface_offsets"], dtype=np.int32)[state_start:state_stop],
        state_surface_counts=np.asarray(arrays["state_surface_counts"], dtype=np.int32)[state_start:state_stop],
    )
    row = meta[idx]
    return FgResponseFrontierResult(
        first_frontier=first_frontier,
        state_frontiers=state_frontiers,
        states_evaluated=int(row[0]),
        actions=int(row[1]),
        transitions_evaluated=int(row[2]),
        generated_surfaces=int(row[3]),
        retained_surfaces_total=int(row[4]),
        max_state_frontier=int(row[5]),
        non_fever_base=int(row[6]),
        seconds=0.0,
    )


def frontier_result_from_scoring_bundle(
    scoring_bundle: FgResponseFrontierScoringBundle,
    *,
    frontier_idx: int,
) -> FgResponseFrontierResult:
    idx = int(frontier_idx)
    meta = np.asarray(scoring_bundle.frontier_meta, dtype=np.int32)
    if idx < 0 or idx >= int(meta.shape[0]):
        raise ValueError("FG response scoring bundle frontier index is outside the bundle")
    first_start = int(scoring_bundle.frontier_offsets[idx])
    first_count = int(scoring_bundle.frontier_lengths[idx])
    row = meta[idx]
    return FgResponseFrontierResult(
        first_frontier=_LazyResponseFirstFrontier(
            bundle_key=scoring_bundle.cache_key,
            first_start=int(first_start),
            first_count=int(first_count),
        ),
        state_frontiers=_DeferredResponseStateFrontiers(
            bundle_key=scoring_bundle.cache_key,
            frontier_idx=int(idx),
            state_count_hint=int(row[0]),
        ),
        states_evaluated=int(row[0]),
        actions=int(row[1]),
        transitions_evaluated=int(row[2]),
        generated_surfaces=int(row[3]),
        retained_surfaces_total=int(row[4]),
        max_state_frontier=int(row[5]),
        non_fever_base=int(row[6]),
        seconds=0.0,
    )


def frontier_result_from_scoring_bundle_for_stats(
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    scoring_bundle: FgResponseFrontierScoringBundle,
    *,
    ft_stat: int,
    ff_stat: int,
) -> FgResponseFrontierResult:
    key = _normalize_stat_key((int(ft_stat), int(ff_stat)))
    geometry_cache_key = fg_response_frontier_geometry_cache_key(
        calc_song,
        ref_arrays,
        ft_stat=int(key[0]),
        ff_stat=int(key[1]),
    )
    cached = _memory_get(geometry_cache_key)
    if _frontier_is_complete(cached):
        return cached
    frontier_idx = scoring_bundle.frontier_idx_by_key.get(key)
    if frontier_idx is None:
        raise ValueError(f"FG response frontier scoring bundle is missing stat key: {key}")
    frontier = frontier_result_from_scoring_bundle(scoring_bundle, frontier_idx=int(frontier_idx))
    _memory_put(geometry_cache_key, frontier)
    return frontier
