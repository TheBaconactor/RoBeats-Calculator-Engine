from __future__ import annotations

from typing import Any

import numpy as np

from gear_optimizer.core.constants import MAX_STAT_INDEX
from gear_optimizer.core.utils import safe_int
from gear_optimizer.solver.fever_timeline import calculate_fever_timeline_indices
from gear_optimizer.solver.solver_common import GEAR_SLOTS


def _clamp_stat(value: int) -> int:
    if value < 0:
        return 0
    if value > MAX_STAT_INDEX:
        return MAX_STAT_INDEX
    return int(value)


def _load_ref_arr(ref_arrays: dict[str, Any], key: str) -> np.ndarray:
    arr = np.asarray((ref_arrays or {}).get(key, []), dtype=np.float32)
    need = int(MAX_STAT_INDEX) + 1
    if arr.size >= need:
        return arr
    out = np.zeros(need, dtype=np.float32)
    if arr.size > 0:
        out[: int(arr.size)] = arr
    return out


def _item_stats6(item: dict[str, Any], *, p_color: str, s_color: str) -> np.ndarray:
    pp = int(item.get("Perfect Points", 0) or 0)
    cm = int(item.get("Combo Multiplier", 0) or 0)
    fm = int(item.get("Fever Multiplier", 0) or 0)
    ft = int(item.get("Fever Time", 0) or 0)
    ff = int(item.get("Fever Fill Rate", 0) or 0)
    p_val = int(item.get(p_color, 0) or 0) if p_color else 0
    s_val = int(item.get(s_color, 0) or 0) if s_color and s_color != p_color else 0
    base_lane = (2 * p_val) + s_val
    return np.array((pp, cm, fm, ft, ff, base_lane), dtype=np.int32)


def _read_cfg_int(
    cfg: Any,
    key: str,
    *,
    default: int,
    min_value: int,
    max_value: int,
) -> int:
    raw: Any = default
    if cfg is not None:
        try:
            raw = cfg.get("IterationEngine", key, fallback=default)
        except Exception:
            raw = default
    value = safe_int(raw, default)
    return max(int(min_value), min(int(max_value), int(value)))


def read_marginal_prune_settings(cfg: Any) -> dict[str, int]:
    return {
        "k": _read_cfg_int(cfg, "MarginalPruneK", default=3, min_value=1, max_value=12),
        "iterations": _read_cfg_int(cfg, "MarginalPruneIterations", default=5, min_value=1, max_value=20),
    }


class _ProxyScorer:
    def __init__(self, calc_song: dict[str, Any], ref_arrays: dict[str, Any]) -> None:
        self.ref_pp = _load_ref_arr(ref_arrays, "Perfect Points")
        self.ref_cm = _load_ref_arr(ref_arrays, "Combo Multiplier")
        self.ref_fm = _load_ref_arr(ref_arrays, "Fever Multiplier")
        self.ref_ff = _load_ref_arr(ref_arrays, "Fever Fill Rate")
        self.ref_ft = _load_ref_arr(ref_arrays, "Fever Time")

        song_data = (calc_song or {}).get("song_data", {}) if isinstance(calc_song, dict) else {}
        metadata = (calc_song or {}).get("metadata", {}) if isinstance(calc_song, dict) else {}

        timestamps = song_data.get("timestamps", [])
        self.timestamps = np.asarray(timestamps, dtype=np.float64)
        self.total_notes = int(len(self.timestamps))
        self.long_notes = int(metadata.get("Long Notes", 0) or 0)
        self.last_note_time = float(metadata.get("Last Note Time", 0.0) or 0.0)
        self.fever_buf = np.zeros(self.total_notes, dtype=np.bool_)
        self.timeline_cache: dict[tuple[int, int], tuple[int, int]] = {}

    def naive_item_score(self, row: np.ndarray) -> float:
        pp = _clamp_stat(int(row[0]))
        cm = _clamp_stat(int(row[1]))
        fm = _clamp_stat(int(row[2]))
        base = float(int(row[5])) + float(self.ref_pp[pp])
        return float(base * float(self.ref_cm[cm]) * float(self.ref_fm[fm]))

    def score(self, pp: int, cm: int, fm: int, ft: int, ff: int, base_lane: int) -> float:
        pp_c = _clamp_stat(pp)
        cm_c = _clamp_stat(cm)
        fm_c = _clamp_stat(fm)
        ft_c = _clamp_stat(ft)
        ff_c = _clamp_stat(ff)

        base = float(base_lane) + float(self.ref_pp[pp_c])
        combo = float(self.ref_cm[cm_c])
        fever = float(self.ref_fm[fm_c])

        if self.total_notes <= 0:
            return float(base * combo * fever)

        key = (ft_c, ff_c)
        cached = self.timeline_cache.get(key)
        if cached is None:
            ff_factor = float(self.ref_ff[ff_c])
            ft_factor = float(self.ref_ft[ft_c])
            _, cbf, cbn, _, _ = calculate_fever_timeline_indices(
                self.timestamps,
                self.total_notes,
                ff_factor,
                ft_factor,
                self.long_notes,
                self.last_note_time,
                self.fever_buf,
            )
            cached = (int(cbf), int(cbn))
            self.timeline_cache[key] = cached

        cbf, cbn = cached
        return float(base * combo * (float(cbn) + float(cbf) * fever))


def _naive_rank_per_slot(slot_stats: dict[str, np.ndarray], *, scorer: _ProxyScorer) -> dict[str, list[int]]:
    ranks: dict[str, list[int]] = {}
    for slot in GEAR_SLOTS:
        stats = slot_stats.get(slot)
        if stats is None or int(stats.shape[0]) == 0:
            ranks[slot] = []
            continue
        scores = np.array([scorer.naive_item_score(stats[idx]) for idx in range(int(stats.shape[0]))], dtype=np.float64)
        order = np.argsort(-scores, kind="stable")
        ranks[slot] = order.astype(np.int64, copy=False).tolist()
    return ranks


def _marginal_rank_per_slot(
    slot_stats: dict[str, np.ndarray],
    *,
    scorer: _ProxyScorer,
    naive_rankings: dict[str, list[int]],
    iterations: int,
) -> dict[str, list[int]]:
    current: dict[str, int] = {}
    for slot in GEAR_SLOTS:
        base_rank = naive_rankings.get(slot) or []
        current[slot] = int(base_rank[0]) if base_rank else 0

    total = np.zeros(6, dtype=np.int32)
    for slot in GEAR_SLOTS:
        stats = slot_stats.get(slot)
        if stats is None or int(stats.shape[0]) == 0:
            continue
        total += stats[int(current[slot])]

    rankings = {slot: list(naive_rankings.get(slot) or []) for slot in GEAR_SLOTS}
    for _ in range(int(iterations)):
        changed = False
        for slot in GEAR_SLOTS:
            stats = slot_stats.get(slot)
            if stats is None or int(stats.shape[0]) == 0:
                rankings[slot] = []
                continue

            cur_idx = int(current[slot])
            base_total = total - stats[cur_idx]
            scored: list[tuple[float, int]] = []
            for idx in range(int(stats.shape[0])):
                row = base_total + stats[idx]
                scored.append(
                    (
                        scorer.score(
                            int(row[0]),
                            int(row[1]),
                            int(row[2]),
                            int(row[3]),
                            int(row[4]),
                            int(row[5]),
                        ),
                        int(idx),
                    )
                )
            scored.sort(key=lambda item: item[0], reverse=True)
            rankings[slot] = [idx for _, idx in scored]
            best_idx = int(scored[0][1]) if scored else cur_idx
            if best_idx != cur_idx:
                current[slot] = best_idx
                total = base_total + stats[best_idx]
                changed = True
        if not changed:
            break

    return rankings


def _union_topk_per_slot(
    naive_rankings: dict[str, list[int]],
    marginal_rankings: dict[str, list[int]],
    *,
    top_k: int,
) -> dict[str, list[int]]:
    out: dict[str, list[int]] = {}
    k = max(1, int(top_k))
    for slot in GEAR_SLOTS:
        rank: dict[int, int] = {}
        for pos, idx in enumerate((naive_rankings.get(slot) or [])[:k]):
            rank[int(idx)] = min(rank.get(int(idx), 1_000_000), int(pos))
        for pos, idx in enumerate((marginal_rankings.get(slot) or [])[:k]):
            rank[int(idx)] = min(rank.get(int(idx), 1_000_000), int(pos))
        out[slot] = sorted(rank.keys(), key=lambda idx: (rank[idx], idx))
    return out


def prune_gear_pool_marginal(
    gear_pool: dict[str, list[dict]],
    calc_song: dict,
    ref_arrays: dict,
    *,
    p_color: str,
    s_color: str,
    k: int = 3,
    iterations: int = 5,
) -> dict[str, list[dict]]:
    """Reduce gear_pool to top-K items per slot using naive + marginal ranking union."""
    if not isinstance(gear_pool, dict):
        return {}

    slot_stats: dict[str, np.ndarray] = {}
    for slot in GEAR_SLOTS:
        items = list(gear_pool.get(slot, []) or [])
        if not items:
            return {name: list(gear_pool.get(name, []) or []) for name in gear_pool.keys()}
        slot_stats[slot] = np.asarray([_item_stats6(item, p_color=p_color, s_color=s_color) for item in items], dtype=np.int32)

    scorer = _ProxyScorer(calc_song, ref_arrays)
    naive_rankings = _naive_rank_per_slot(slot_stats, scorer=scorer)
    marginal_rankings = _marginal_rank_per_slot(
        slot_stats,
        scorer=scorer,
        naive_rankings=naive_rankings,
        iterations=int(iterations),
    )
    selected_idx_by_slot = _union_topk_per_slot(naive_rankings, marginal_rankings, top_k=int(k))

    reduced_pool = {slot: list(gear_pool.get(slot, []) or []) for slot in gear_pool.keys()}
    for slot in GEAR_SLOTS:
        items = list(gear_pool.get(slot, []) or [])
        selected_idx = selected_idx_by_slot.get(slot) or []
        if not selected_idx:
            reduced_pool[slot] = items
            continue
        reduced_pool[slot] = [items[int(idx)] for idx in selected_idx if 0 <= int(idx) < len(items)]
    return reduced_pool


__all__ = [
    "prune_gear_pool_marginal",
    "read_marginal_prune_settings",
]
