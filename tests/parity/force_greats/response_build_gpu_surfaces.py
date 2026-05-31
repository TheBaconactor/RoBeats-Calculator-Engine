import numpy as np

from gear_optimizer.solver.taichi_gem.force_greats.response_types import FgResponseFrontierResult, FgResponseSurface

_PackedSurface = tuple[int, int, int, int]

def _unpack_surface(surface: _PackedSurface) -> FgResponseSurface:
    fever, great, body_fever, body_great = surface
    return FgResponseSurface(
        int(fever) & 0xFFFFFFFF,
        (int(fever) >> 32) & 0xFFFFFFFF,
        (int(fever) >> 64) & 0xFFFFFFFF,
        (int(fever) >> 96) & 0xFFFFFFFF,
        int(great) & 0xFFFFFFFF,
        (int(great) >> 32) & 0xFFFFFFFF,
        (int(great) >> 64) & 0xFFFFFFFF,
        (int(great) >> 96) & 0xFFFFFFFF,
        int(body_fever),
        int(body_great),
    )


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
    )


def _combine_packed(edge: _PackedSurface, tail: _PackedSurface) -> _PackedSurface:
    return (
        int(edge[0]) | int(tail[0]),
        int(edge[1]) | int(tail[1]),
        int(edge[2]) + int(tail[2]),
        int(edge[3]) + int(tail[3]),
    )


def _append_packed_surface(bucket: list[_PackedSurface], surface: _PackedSurface) -> bool:
    cf, cg, cbf, cbg = surface
    for kept_surface in bucket:
        kf, kg, kbf, kbg = kept_surface
        if kbf >= cbf and kbg <= cbg and (cf & ~kf) == 0 and (kg & ~cg) == 0:
            return False
    write = 0
    for kept_surface in bucket:
        kf, kg, kbf, kbg = kept_surface
        if not (cbf >= kbf and cbg <= kbg and (kf & ~cf) == 0 and (cg & ~kg) == 0):
            bucket[write] = kept_surface
            write += 1
    del bucket[write:]
    bucket.append(surface)
    return True


def _reduce_packed_frontier(surfaces: list[_PackedSurface]) -> tuple[_PackedSurface, ...]:
    if not surfaces:
        return ((0, 0, 0, 0),)
    if len(surfaces) > 8:
        surfaces.sort(key=lambda surface: (-int(surface[2]), int(surface[3])))
    kept: list[_PackedSurface] = []
    seen: set[_PackedSurface] = set()
    for surface in surfaces:
        if surface in seen:
            continue
        seen.add(surface)
        _append_packed_surface(kept, surface)
    return tuple(kept)


def _append_edge_from_arrays(
    bucket: list[_PackedSurface],
    fever_masks: np.ndarray,
    great_masks: np.ndarray,
    body_counts: np.ndarray,
    row: int,
    action_idx: int,
) -> bool:
    surface = (
        int(fever_masks[row, action_idx, 0])
        | (int(fever_masks[row, action_idx, 1]) << 32)
        | (int(fever_masks[row, action_idx, 2]) << 64)
        | (int(fever_masks[row, action_idx, 3]) << 96),
        int(great_masks[row, action_idx, 0])
        | (int(great_masks[row, action_idx, 1]) << 32)
        | (int(great_masks[row, action_idx, 2]) << 64)
        | (int(great_masks[row, action_idx, 3]) << 96),
        int(body_counts[row, action_idx, 0]),
        int(body_counts[row, action_idx, 1]),
    )
    return _append_packed_surface(bucket, surface)


def _frontier_from_edge_arrays(
    *,
    n: int,
    action_count: int,
    non_fever_base: int,
    later_valid: np.ndarray,
    later_next: np.ndarray,
    later_fever_masks: np.ndarray,
    later_great_masks: np.ndarray,
    later_body_counts: np.ndarray,
    first_valid: np.ndarray,
    first_next: np.ndarray,
    first_fever_masks: np.ndarray,
    first_great_masks: np.ndarray,
    first_body_counts: np.ndarray,
    seconds: float,
    materialize_state_frontiers: bool = True,
) -> FgResponseFrontierResult:
    reachable = np.zeros((n + 1,), dtype=np.bool_)
    reachable[n] = True
    empty_surface: _PackedSurface = (0, 0, 0, 0)
    state_frontiers: dict[int, tuple[_PackedSurface, ...]] = {n: (empty_surface,)}
    transitions = 0
    generated_surfaces = 0
    retained_total = 1
    max_state_frontier = 1

    first_edge_buckets: dict[int, list[_PackedSurface]] = {}
    for action_idx in range(action_count):
        if int(first_valid[0, action_idx]) == 0:
            continue
        e = int(first_next[0, action_idx])
        _append_edge_from_arrays(
            first_edge_buckets.setdefault(e, []),
            first_fever_masks,
            first_great_masks,
            first_body_counts,
            0,
            action_idx,
        )
    first_edges = [(int(e), surface) for e, bucket in first_edge_buckets.items() for surface in bucket]
    transitions += len(first_edges)
    for e, _edge in first_edges:
        reachable[int(e)] = True

    later_edges_by_state: dict[int, list[tuple[int, _PackedSurface]]] = {}
    for i in range(n):
        if not bool(reachable[i]):
            continue
        edge_buckets: dict[int, list[_PackedSurface]] = {}
        for action_idx in range(action_count):
            if int(later_valid[i, action_idx]) == 0:
                continue
            e = int(later_next[i, action_idx])
            _append_edge_from_arrays(
                edge_buckets.setdefault(e, []),
                later_fever_masks,
                later_great_masks,
                later_body_counts,
                i,
                action_idx,
            )
        edges = [(int(e), surface) for e, bucket in edge_buckets.items() for surface in bucket]
        transitions += len(edges)
        later_edges_by_state[int(i)] = edges
        for e, _edge in edges:
            reachable[int(e)] = True

    for i in range(n - 1, -1, -1):
        if not bool(reachable[i]):
            continue
        generated: list[_PackedSurface] = []
        for e, edge in later_edges_by_state.get(int(i), []):
            tail_frontier = state_frontiers.get(int(e))
            if tail_frontier is None:
                raise ValueError(f"missing tail frontier for reachable state {e}")
            for tail in tail_frontier:
                generated.append(_combine_packed(edge, tail))
        generated_surfaces += len(generated)
        frontier = _reduce_packed_frontier(generated)
        state_frontiers[int(i)] = frontier
        retained_total += len(frontier)
        max_state_frontier = max(max_state_frontier, len(frontier))

    first_generated: list[_PackedSurface] = []
    for e, edge in first_edges:
        tail_frontier = state_frontiers.get(int(e))
        if tail_frontier is None:
            raise ValueError(f"missing first-tail frontier for reachable state {e}")
        for tail in tail_frontier:
            first_generated.append(_combine_packed(edge, tail))
    generated_surfaces += len(first_generated)
    first_frontier = _reduce_packed_frontier(first_generated)
    retained_total += len(first_frontier)
    max_state_frontier = max(max_state_frontier, len(first_frontier))

    return FgResponseFrontierResult(
        first_frontier=tuple(_unpack_surface(surface) for surface in first_frontier),
        state_frontiers={
            int(state): tuple(_unpack_surface(surface) for surface in frontier)
            for state, frontier in state_frontiers.items()
        }
        if bool(materialize_state_frontiers)
        else {},
        states_evaluated=int(np.count_nonzero(reachable[:n])),
        actions=int(action_count),
        transitions_evaluated=int(transitions),
        generated_surfaces=int(generated_surfaces),
        retained_surfaces_total=int(retained_total),
        max_state_frontier=int(max_state_frontier),
        non_fever_base=max(0, int(non_fever_base)),
        seconds=float(seconds),
    )
