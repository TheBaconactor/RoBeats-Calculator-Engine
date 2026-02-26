from __future__ import annotations

import os
import threading
import time
import weakref
import zlib
from collections import OrderedDict
from dataclasses import dataclass
from typing import Optional, Iterable

from ...core.constants import (
    GEM_SCALE_FEVER,
    SKIP_ITEM_KEYS,
    TOTAL_GEM_BUDGET,
)
from ...core.utils import get_selected_element
from ...solver.gpu_executor import is_gpu_worker_mode, submit_gpu_solve_genomes
from ...solver.scoring.genome_evaluation import prepare_gpu_batch_eval_plan, finalize_gpu_batch_eval_plan
from ...solver.base_stats import build_base_fixed_stats_list
from ...solver.scoring.stats_ops import apply_gems_to_base_stats
from .item_utils import _item_name


FG_COMBO_BOOSTER_MAX_EVALS = 4096
FG_COMBO_BOOSTER_TOP_K = 8
FG_COMBO_BOOSTER_POSITIONS_PER_SEED = 2
# Default to full evaluation to avoid sacrificing FG coverage/accuracy.
# Users can override via `FG_COMBO_BOOSTER_GPU_EVALS` if they explicitly want speed.
FG_COMBO_BOOSTER_DEFAULT_GPU_EVALS = FG_COMBO_BOOSTER_MAX_EVALS
_SLOT_ITEMS_CACHE_LOCK = threading.Lock()
_SLOT_ITEMS_CACHE: "weakref.WeakKeyDictionary[object, OrderedDict[tuple, dict[int, list[dict]]]]" = (
    weakref.WeakKeyDictionary()
)


def _genome_key(genome: list[dict]) -> tuple[str, ...]:
    gear_names = tuple(_item_name(it) for it in (genome or [])[:6])
    mini_names = tuple(sorted(_item_name(it) for it in (genome or [])[6:9]))
    return gear_names + mini_names


def _as_genome(candidate: dict) -> list[dict]:
    genome = candidate.get("Genome")
    if isinstance(genome, list) and genome:
        out = list(genome[:9])
        while len(out) < 9:
            out.append({})
        return out
    gear = list(candidate.get("Gear") or [])[:6]
    minis = list(candidate.get("Minis") or [])[:3]
    while len(gear) < 6:
        gear.append({})
    while len(minis) < 3:
        minis.append({})
    return gear + minis


def _int(v: object, default: int = 0) -> int:
    try:
        return int(v or 0)
    except Exception:
        return int(default)


def _env_int(name: str, default: int) -> int:
    v = os.environ.get(name)
    if v is None:
        return int(default)
    s = str(v).strip()
    if not s:
        return int(default)
    try:
        return int(s)
    except Exception:
        return int(default)


def _env_bool(name: str, default: str = "1") -> bool:
    return str(os.environ.get(name, default) or "").strip().lower() in {"1", "true", "yes", "on"}


def _slot_items_cache_max() -> int:
    return max(0, _env_int("FG_COMBO_BOOSTER_SLOT_CACHE_MAX", 32))


def _slot_items_cache_get(registry, key: tuple) -> dict[int, list[dict]] | None:
    if not _env_bool("FG_COMBO_BOOSTER_SLOT_CACHE", "1"):
        return None
    try:
        with _SLOT_ITEMS_CACHE_LOCK:
            reg_cache = _SLOT_ITEMS_CACHE.get(registry)
            if reg_cache is None:
                return None
            cached = reg_cache.get(key)
            if cached is None:
                return None
            reg_cache.move_to_end(key)
            return cached
    except Exception:
        return None


def _slot_items_cache_put(registry, key: tuple, value: dict[int, list[dict]]) -> None:
    if not _env_bool("FG_COMBO_BOOSTER_SLOT_CACHE", "1"):
        return
    try:
        with _SLOT_ITEMS_CACHE_LOCK:
            reg_cache = _SLOT_ITEMS_CACHE.get(registry)
            if reg_cache is None:
                reg_cache = OrderedDict()
                _SLOT_ITEMS_CACHE[registry] = reg_cache
            reg_cache[key] = value
            reg_cache.move_to_end(key)
            max_n = int(_slot_items_cache_max())
            if max_n <= 0:
                reg_cache.clear()
                return
            while len(reg_cache) > max_n:
                reg_cache.popitem(last=False)
    except Exception:
        return


def _cached_interesting_items_by_slot(
    registry,
    *,
    primary_color: str,
    secondary_color: str,
    top_k: int,
) -> dict[int, list[dict]]:
    key = ("classic", str(primary_color or ""), str(secondary_color or ""), int(top_k))
    cached = _slot_items_cache_get(registry, key)
    if cached is not None:
        return cached
    out = _build_interesting_items_by_slot(
        registry,
        primary_color=str(primary_color or ""),
        secondary_color=str(secondary_color or ""),
        top_k=int(top_k),
    )
    _slot_items_cache_put(registry, key, out)
    return out


def _cached_interesting_items_by_slot_multi_axis(
    registry,
    *,
    primary_color: str,
    secondary_color: str,
    top_k: int,
    items_per_slot: int,
) -> dict[int, list[dict]]:
    key = ("multi_axis", str(primary_color or ""), str(secondary_color or ""), int(top_k), int(items_per_slot))
    cached = _slot_items_cache_get(registry, key)
    if cached is not None:
        return cached
    out = _build_interesting_items_by_slot_multi_axis(
        registry,
        primary_color=str(primary_color or ""),
        secondary_color=str(secondary_color or ""),
        top_k=int(top_k),
        items_per_slot=int(items_per_slot),
    )
    _slot_items_cache_put(registry, key, out)
    return out


def _clear_fg_combo_booster_slot_cache_for_tests() -> None:
    try:
        with _SLOT_ITEMS_CACHE_LOCK:
            _SLOT_ITEMS_CACHE.clear()
    except Exception:
        return


def _base_score(candidate: dict) -> int:
    return _int(candidate.get("BaseScore", candidate.get("Score", 0) or 0), 0)


def _fg_item_score(item: dict, *, primary_color: str, secondary_color: str) -> int:
    if not isinstance(item, dict) or not item:
        return 0

    def _i(key: str) -> int:
        return _int(item.get(key, 0), 0)

    score = 0
    score += _i("Fever Multiplier") * 4
    score += _i("Fever Fill Rate") * 4
    score += _i("Fever Time") * 3
    score += _i("Combo Multiplier") * 2
    score += _i("Perfect Points")
    if primary_color:
        score += _i(primary_color) * 2
    if secondary_color and secondary_color != primary_color:
        score += _i(secondary_color)
    return int(score)


def _base_item_score(item: dict, *, primary_color: str, secondary_color: str) -> int:
    if not isinstance(item, dict) or not item:
        return 0

    def _i(key: str) -> int:
        return _int(item.get(key, 0), 0)

    pp = _i("Perfect Points")
    cm = _i("Combo Multiplier")
    fm = _i("Fever Multiplier")
    ft = _i("Fever Time")
    ff = _i("Fever Fill Rate")

    primary_val = _i(primary_color) if primary_color else 0
    secondary_val = _i(secondary_color) if (secondary_color and secondary_color != primary_color) else 0

    # Approximate "modern" heuristic score (similar shape to GA heuristics).
    base = (pp * 3) + (cm * 3) + (fm * 3) + (ft * 2) + (ff * 2)
    elem = (primary_val * 2) + (secondary_val * 1)
    return int(base + (elem // 2))


def _iter_slot_items(registry, slot_idx: int) -> Iterable[dict]:
    start = _int(getattr(registry, "slot_start", [0] * 9)[slot_idx], 0)
    count = _int(getattr(registry, "slot_count", [0] * 9)[slot_idx], 0)
    id_to_item = getattr(registry, "id_to_item", {}) or {}
    for item_id in range(start, start + count):
        it = id_to_item.get(int(item_id))
        if isinstance(it, dict) and it.get("Name"):
            yield it


def _build_interesting_items_by_slot(
    registry,
    *,
    primary_color: str,
    secondary_color: str,
    top_k: int,
) -> dict[int, list[dict]]:
    by_slot: dict[int, list[dict]] = {}

    try:
        top_k = int(top_k)
    except Exception:
        top_k = 0
    if top_k <= 0:
        return by_slot

    for slot_idx in range(9):
        items = list(_iter_slot_items(registry, slot_idx))
        if not items:
            by_slot[slot_idx] = []
            continue

        ranked = items[: min(len(items), top_k)]
        by_fg = sorted(
            items,
            key=lambda it: (
                _fg_item_score(it, primary_color=primary_color, secondary_color=secondary_color),
                it.get("Name", ""),
            ),
            reverse=True,
        )

        # Mix "GA-ranked" items with FG-heuristic items so we don't end up with
        # a pure base-score list for every slot (common regression shape at high depth).
        out: list[dict] = []
        seen: set[str] = set()
        i = 0
        while len(out) < top_k and (i < len(ranked) or i < len(by_fg)):
            if i < len(ranked):
                it = ranked[i]
                name = _item_name(it)
                if name and name not in seen:
                    seen.add(name)
                    out.append(it)
            if len(out) >= top_k:
                break
            if i < len(by_fg):
                it = by_fg[i]
                name = _item_name(it)
                if name and name not in seen:
                    seen.add(name)
                    out.append(it)
            i += 1

        if len(out) < top_k:
            for it in by_fg:
                if len(out) >= top_k:
                    break
                name = _item_name(it)
                if not name or name in seen:
                    continue
                seen.add(name)
                out.append(it)
        by_slot[slot_idx] = out

    return by_slot


def _build_interesting_items_by_slot_multi_axis(
    registry,
    *,
    primary_color: str,
    secondary_color: str,
    top_k: int,
    items_per_slot: int,
) -> dict[int, list[dict]]:
    by_slot: dict[int, list[dict]] = {}

    try:
        top_k = int(top_k)
    except Exception:
        top_k = 0
    if top_k <= 0:
        top_k = 8

    try:
        items_per_slot = int(items_per_slot)
    except Exception:
        items_per_slot = 0
    if items_per_slot <= 0:
        items_per_slot = max(12, top_k * 2)
    items_per_slot = max(8, min(64, int(items_per_slot)))

    primary_color = str(primary_color or "")
    secondary_color = str(secondary_color or "")

    stat_keys = [
        "Perfect Points",
        "Combo Multiplier",
        "Fever Multiplier",
        "Fever Time",
        "Fever Fill Rate",
    ]
    if primary_color:
        stat_keys.append(primary_color)
    if secondary_color and secondary_color != primary_color:
        stat_keys.append(secondary_color)

    top_per_stat = 2

    for slot_idx in range(9):
        items = list(_iter_slot_items(registry, slot_idx))
        if not items:
            by_slot[slot_idx] = []
            continue

        by_base = sorted(
            items,
            key=lambda it: (
                _base_item_score(it, primary_color=primary_color, secondary_color=secondary_color),
                it.get("Name", ""),
            ),
            reverse=True,
        )
        by_fg = sorted(
            items,
            key=lambda it: (
                _fg_item_score(it, primary_color=primary_color, secondary_color=secondary_color),
                it.get("Name", ""),
            ),
            reverse=True,
        )

        out: list[dict] = []
        seen: set[str] = set()

        def _add(it: dict) -> None:
            if not it:
                return
            name = _item_name(it)
            if not name or name in seen:
                return
            seen.add(name)
            out.append(it)

        # Mix top-by-base and top-by-FG-proxy so early truncations keep coverage.
        i = 0
        base_cap = max(1, min(len(by_base), top_k))
        fg_cap = max(1, min(len(by_fg), top_k))
        while len(out) < items_per_slot and (i < base_cap or i < fg_cap):
            if i < base_cap:
                _add(by_base[i])
            if len(out) >= items_per_slot:
                break
            if i < fg_cap:
                _add(by_fg[i])
            i += 1

        # Add stat extremes (helps when the best FG loadout requires a "counterintuitive" swap).
        for key in stat_keys:
            ranked = sorted(items, key=lambda it: _int((it or {}).get(key, 0), 0), reverse=True)
            for it in ranked[:top_per_stat]:
                if len(out) >= items_per_slot:
                    break
                _add(it)
            if len(out) >= items_per_slot:
                break

        # Fill remaining from base heuristic.
        for it in by_base:
            if len(out) >= items_per_slot:
                break
            _add(it)

        by_slot[slot_idx] = out[:items_per_slot]

    return by_slot


@dataclass(frozen=True)
class _Seed:
    genome: list[dict]
    base_score: int
    key: tuple[str, ...]


def _select_seeds(
    candidates: list[dict],
    *,
    primary_color: str,
    secondary_color: str,
    max_seeds: int,
) -> list[_Seed]:
    best_by_key: dict[tuple[str, ...], _Seed] = {}
    for cand in candidates or []:
        if not isinstance(cand, dict):
            continue
        genome = _as_genome(cand)
        k = _genome_key(genome)
        b = _base_score(cand)
        prev = best_by_key.get(k)
        if prev is None or b > prev.base_score:
            best_by_key[k] = _Seed(genome=genome, base_score=b, key=k)

    seeds = list(best_by_key.values())
    if not seeds:
        return []

    by_base = sorted(seeds, key=lambda s: (s.base_score, s.key), reverse=True)
    by_fg = sorted(
        seeds,
        key=lambda s: (
            sum(_fg_item_score(it, primary_color=primary_color, secondary_color=secondary_color) for it in s.genome),
            s.base_score,
            s.key,
        ),
        reverse=True,
    )

    try:
        max_seeds = int(max_seeds)
    except Exception:
        max_seeds = 0
    if max_seeds <= 0:
        max_seeds = 1

    # Prefer base-score seeds, but reserve a slice for fever-heavy seeds to avoid
    # collapsing into the same high-base-score basin at high GA depth.
    base_take = max(1, int(max_seeds * 0.65))
    if base_take > max_seeds:
        base_take = max_seeds

    out: list[_Seed] = []
    seen: set[tuple[str, ...]] = set()
    for s in by_base:
        if len(out) >= base_take:
            break
        if s.key in seen:
            continue
        seen.add(s.key)
        out.append(s)

    for s in by_fg:
        if len(out) >= max_seeds:
            break
        if s.key in seen:
            continue
        seen.add(s.key)
        out.append(s)

    return out


def _pick_promising_positions(
    seed: list[dict],
    *,
    items_by_slot: dict[int, list[dict]],
    primary_color: str,
    secondary_color: str,
    positions_per_seed: int,
) -> list[int]:
    def _score_slot(slot_idx: int) -> tuple[int, int, int]:
        cur = seed[slot_idx] if slot_idx < len(seed) else {}
        cur_score = _fg_item_score(cur, primary_color=primary_color, secondary_color=secondary_color)
        cand_items = items_by_slot.get(slot_idx) or []
        best_score = cur_score
        for it in cand_items:
            s = _fg_item_score(it, primary_color=primary_color, secondary_color=secondary_color)
            if s > best_score:
                best_score = s
        delta = best_score - cur_score
        return delta, best_score, slot_idx

    gear_scored = [_score_slot(i) for i in range(6)]
    mini_scored = [_score_slot(i) for i in range(6, 9)]

    # Prefer earlier slots on ties for determinism and to bias towards gear first
    # (the primary search axis), while still allowing minis as a secondary axis.
    gear_scored.sort(key=lambda t: (-t[0], -t[1], t[2]))
    mini_scored.sort(key=lambda t: (-t[0], -t[1], t[2]))

    out: list[int] = []
    for delta, _best, slot_idx in gear_scored:
        if len(out) >= positions_per_seed:
            break
        if delta <= 0:
            continue
        out.append(int(slot_idx))

    for delta, _best, slot_idx in mini_scored:
        if len(out) >= positions_per_seed:
            break
        if delta <= 0:
            continue
        out.append(int(slot_idx))

    if out:
        return out[:positions_per_seed]

    # Fallback: if nothing shows a positive delta, still branch once to avoid a no-op.
    best_overall = sorted(gear_scored + mini_scored, key=lambda t: (-t[1], t[2]))
    if best_overall:
        return [int(best_overall[0][2])]
    return []


def _stable_seed_u32(seed_key: tuple[str, ...]) -> int:
    try:
        payload = "|".join(seed_key).encode("utf-8", errors="ignore")
    except Exception:
        payload = b""
    return int(zlib.adler32(payload) & 0xFFFFFFFF)


def _axis_slots(items_by_slot: dict[int, list[dict]], *, primary_color: str, secondary_color: str) -> list[int]:
    def _range(items: list[dict], key: str) -> int:
        vals = []
        for it in items or []:
            try:
                vals.append(int((it or {}).get(key, 0) or 0))
            except Exception:
                vals.append(0)
        if not vals:
            return 0
        return int(max(vals) - min(vals))

    primary_color = str(primary_color or "")
    secondary_color = str(secondary_color or "")

    scored: list[tuple[int, int]] = []
    for slot_idx in range(6):
        items = items_by_slot.get(slot_idx) or []
        if not items:
            continue
        fever_span = _range(items, "Fever Time") + _range(items, "Fever Fill Rate") + _range(items, "Fever Multiplier")
        base_span = 0
        try:
            vals = [
                _base_item_score(it, primary_color=primary_color, secondary_color=secondary_color)
                for it in (items or [])
            ]
            base_span = int(max(vals) - min(vals)) if vals else 0
        except Exception:
            base_span = 0
        elem_span = 0
        if primary_color:
            elem_span += _range(items, primary_color)
        if secondary_color and secondary_color != primary_color:
            elem_span += _range(items, secondary_color)
        score = int((fever_span * 10) + base_span + (elem_span * 2))
        scored.append((score, slot_idx))

    scored.sort(key=lambda t: (t[0], -t[1]), reverse=True)
    out = [int(slot) for score, slot in scored if score > 0][:2]
    return out


def _options_for_position(seed: list[dict], pos: int, items_by_slot: dict[int, list[dict]]) -> list[dict]:
    cur = seed[pos] if pos < len(seed) else {}
    out: list[dict] = []
    seen: set[str] = set()

    cur_name = _item_name(cur)
    if cur_name:
        out.append(cur)
        seen.add(cur_name)

    for it in items_by_slot.get(pos) or []:
        name = _item_name(it)
        if not name or name in seen:
            continue
        seen.add(name)
        out.append(it)
    return out


def _minis_unique(genome: list[dict]) -> bool:
    minis = (genome or [])[6:9]
    names = [_item_name(m) for m in minis]
    if any(not n for n in names):
        return False
    return len(set(names)) == 3


@dataclass(frozen=True)
class _GenomeMeta:
    idx: int
    score: int
    key: tuple[str, ...]
    mini_key: tuple[str, ...]


def select_fg_combo_booster_genomes_for_eval(
    genomes: list[list[dict]],
    *,
    primary_color: str,
    secondary_color: str,
    max_evals: int,
) -> list[list[dict]]:
    """
    Select a smaller subset of generated genomes to GPU-evaluate.

    `solve_genomes_parallel` is expensive, and in-flight mode can become GPU-queue bound.
    We keep FG coverage by emphasizing fever-heavy combos while preserving mini-team
    diversity.
    """
    if not genomes:
        return []

    try:
        max_evals = int(max_evals)
    except Exception:
        max_evals = 0
    if max_evals <= 0 or max_evals >= len(genomes):
        return list(genomes)

    primary_color = str(primary_color or "")
    secondary_color = str(secondary_color or "")

    metas: list[_GenomeMeta] = []
    for idx, gen in enumerate(genomes):
        try:
            score = sum(
                _fg_item_score(it, primary_color=primary_color, secondary_color=secondary_color) for it in (gen or [])
            )
        except Exception:
            score = 0
        key = _genome_key(gen)
        metas.append(_GenomeMeta(idx=idx, score=int(score), key=key, mini_key=key[6:9]))

    # Deterministic ordering: best (proxy) score first, then genome key.
    metas.sort(key=lambda m: (m.score, m.key), reverse=True)

    # 1) Diversity first: take the best genome per mini team.
    best_by_mini: dict[tuple[str, ...], _GenomeMeta] = {}
    for m in metas:
        prev = best_by_mini.get(m.mini_key)
        if prev is None or (m.score, m.key) > (prev.score, prev.key):
            best_by_mini[m.mini_key] = m

    diverse = sorted(best_by_mini.values(), key=lambda m: (m.score, m.key), reverse=True)
    diverse_take = min(len(diverse), max(1, max_evals // 2))

    selected: list[list[dict]] = []
    chosen: set[int] = set()

    for m in diverse[:diverse_take]:
        chosen.add(m.idx)
        selected.append(genomes[m.idx])
        if len(selected) >= max_evals:
            return selected

    # 2) Fill remaining slots by proxy score.
    for m in metas:
        if len(selected) >= max_evals:
            break
        if m.idx in chosen:
            continue
        chosen.add(m.idx)
        selected.append(genomes[m.idx])

    return selected[:max_evals]


def generate_fg_combo_booster_genomes(
    *,
    existing_candidates: list[dict],
    registry,
    primary_color: str,
    secondary_color: str,
    max_new: int = FG_COMBO_BOOSTER_MAX_EVALS,
    top_k: int = FG_COMBO_BOOSTER_TOP_K,
    positions_per_seed: int = FG_COMBO_BOOSTER_POSITIONS_PER_SEED,
) -> list[list[dict]]:
    """
    Enumerate all combinations across 1–2 promising positions around GA seeds.

    This is FG-only coverage: the goal is to cheaply surface fever-heavy variants
    that a deeper base-score GA run can crowd out.
    """
    try:
        max_new = int(max_new)
    except Exception:
        max_new = FG_COMBO_BOOSTER_MAX_EVALS
    max_new = max(0, min(FG_COMBO_BOOSTER_MAX_EVALS, max_new))
    if max_new <= 0:
        return []

    try:
        positions_per_seed = int(positions_per_seed)
    except Exception:
        positions_per_seed = FG_COMBO_BOOSTER_POSITIONS_PER_SEED
    positions_per_seed = max(1, min(2, positions_per_seed))

    items_by_slot = _cached_interesting_items_by_slot(
        registry,
        primary_color=str(primary_color or ""),
        secondary_color=str(secondary_color or ""),
        top_k=int(top_k),
    )

    existing_keys = set()
    for cand in existing_candidates or []:
        if not isinstance(cand, dict):
            continue
        existing_keys.add(_genome_key(_as_genome(cand)))

    seeds = _select_seeds(
        list(existing_candidates or []),
        primary_color=str(primary_color or ""),
        secondary_color=str(secondary_color or ""),
        max_seeds=256,
    )
    if not seeds:
        return []

    out: list[list[dict]] = []
    seen = set(existing_keys)

    for seed in seeds:
        if len(out) >= max_new:
            break

        positions = _pick_promising_positions(
            seed.genome,
            items_by_slot=items_by_slot,
            primary_color=str(primary_color or ""),
            secondary_color=str(secondary_color or ""),
            positions_per_seed=positions_per_seed,
        )
        if not positions:
            continue

        if len(positions) == 1:
            pos = int(positions[0])
            options = _options_for_position(seed.genome, pos, items_by_slot)
            for it in options:
                genome = list(seed.genome)
                genome[pos] = it
                if not _minis_unique(genome):
                    continue
                k = _genome_key(genome)
                if k in seen:
                    continue
                seen.add(k)
                out.append(genome)
                if len(out) >= max_new:
                    break
            continue

        pos1, pos2 = int(positions[0]), int(positions[1])
        if pos1 == pos2:
            continue
        options1 = _options_for_position(seed.genome, pos1, items_by_slot)
        options2 = _options_for_position(seed.genome, pos2, items_by_slot)

        for it1 in options1:
            for it2 in options2:
                genome = list(seed.genome)
                genome[pos1] = it1
                genome[pos2] = it2
                if not _minis_unique(genome):
                    continue
                k = _genome_key(genome)
                if k in seen:
                    continue
                seen.add(k)
                out.append(genome)
                if len(out) >= max_new:
                    break
            if len(out) >= max_new:
                break

    return out


def generate_fg_combo_booster_genomes_multi_axis(
    *,
    existing_candidates: list[dict],
    registry,
    primary_color: str,
    secondary_color: str,
    max_new: int = FG_COMBO_BOOSTER_MAX_EVALS,
    top_k: int = FG_COMBO_BOOSTER_TOP_K,
) -> list[list[dict]]:
    """
    Multi-axis booster (v2): generate a wider, more diverse set of near-seed genomes.

    Key differences vs classic combo booster:
    - Uses a richer per-slot "interesting items" list (base-heuristic, FG-proxy, and stat extremes).
    - Explores more than 1-2 slots per seed (adds deterministic exploration slots).
    - Generates a mix of single swaps and a few targeted pairs per seed.
    """
    try:
        max_new = int(max_new)
    except Exception:
        max_new = FG_COMBO_BOOSTER_MAX_EVALS
    max_new = max(0, min(FG_COMBO_BOOSTER_MAX_EVALS, max_new))
    if max_new <= 0:
        return []

    try:
        top_k = int(top_k)
    except Exception:
        top_k = FG_COMBO_BOOSTER_TOP_K
    top_k = max(2, min(32, int(top_k)))

    items_per_slot = _env_int("FG_MULTI_AXIS_ITEMS_PER_SLOT", max(16, top_k * 2))
    items_by_slot = _cached_interesting_items_by_slot_multi_axis(
        registry,
        primary_color=str(primary_color or ""),
        secondary_color=str(secondary_color or ""),
        top_k=int(top_k),
        items_per_slot=int(items_per_slot),
    )

    existing_keys = set()
    for cand in existing_candidates or []:
        if not isinstance(cand, dict):
            continue
        existing_keys.add(_genome_key(_as_genome(cand)))

    seeds = _select_seeds(
        list(existing_candidates or []),
        primary_color=str(primary_color or ""),
        secondary_color=str(secondary_color or ""),
        max_seeds=_env_int("FG_MULTI_AXIS_SEEDS", 256),
    )
    if not seeds:
        return []

    axis_slots = _axis_slots(
        items_by_slot,
        primary_color=str(primary_color or ""),
        secondary_color=str(secondary_color or ""),
    )

    max_positions = _env_int("FG_MULTI_AXIS_MAX_POSITIONS", 4)
    max_positions = max(2, min(8, int(max_positions)))

    single_opts_gear = _env_int("FG_MULTI_AXIS_SINGLE_OPTS_GEAR", 8)
    single_opts_mini = _env_int("FG_MULTI_AXIS_SINGLE_OPTS_MINI", 4)
    single_opts_gear = max(1, min(32, int(single_opts_gear)))
    single_opts_mini = max(1, min(16, int(single_opts_mini)))

    pair_opts_gear = _env_int("FG_MULTI_AXIS_PAIR_OPTS_GEAR", 4)
    pair_opts_mini = _env_int("FG_MULTI_AXIS_PAIR_OPTS_MINI", 3)
    pair_opts_gear = max(1, min(16, int(pair_opts_gear)))
    pair_opts_mini = max(1, min(12, int(pair_opts_mini)))

    max_pairs = _env_int("FG_MULTI_AXIS_MAX_PAIRS", 3)
    max_pairs = max(1, min(8, int(max_pairs)))

    out: list[list[dict]] = []
    seen = set(existing_keys)

    for seed in seeds:
        if len(out) >= max_new:
            break

        seed_hash = _stable_seed_u32(seed.key)
        explore_gear = int(seed_hash % 6)
        explore_mini = int(6 + ((seed_hash // 6) % 3))

        fg_positions = _pick_promising_positions(
            seed.genome,
            items_by_slot=items_by_slot,
            primary_color=str(primary_color or ""),
            secondary_color=str(secondary_color or ""),
            positions_per_seed=2,
        )

        positions = []
        for p in list(fg_positions or []) + list(axis_slots or []) + [explore_gear, explore_mini]:
            try:
                pi = int(p)
            except Exception:
                continue
            if pi < 0 or pi >= 9:
                continue
            if pi in positions:
                continue
            positions.append(pi)
            if len(positions) >= max_positions:
                break

        if not positions:
            continue

        options_by_pos: dict[int, list[dict]] = {}
        for pos in positions:
            opts = _options_for_position(seed.genome, pos, items_by_slot)
            if pos < 6:
                cap = single_opts_gear
            else:
                cap = single_opts_mini
            options_by_pos[pos] = opts[: 1 + cap]

        # Single swaps: ensure every chosen position gets explored.
        for pos in positions:
            if len(out) >= max_new:
                break
            opts = options_by_pos.get(pos) or []
            for it in opts[1:]:
                genome = list(seed.genome)
                genome[pos] = it
                if not _minis_unique(genome):
                    continue
                k = _genome_key(genome)
                if k in seen:
                    continue
                seen.add(k)
                out.append(genome)
                if len(out) >= max_new:
                    break

        if len(out) >= max_new:
            break

        # Targeted pairs: use FG positions as anchor when available.
        anchor = None
        if fg_positions:
            anchor = int(fg_positions[0])
        elif positions:
            anchor = int(positions[0])

        pairs: list[tuple[int, int]] = []
        if fg_positions and len(fg_positions) >= 2:
            a, b = int(fg_positions[0]), int(fg_positions[1])
            if a != b:
                pairs.append((a, b))

        if anchor is not None:
            for p in positions:
                if len(pairs) >= max_pairs:
                    break
                if p == anchor:
                    continue
                pair = (int(anchor), int(p))
                if pair[0] == pair[1] or pair in pairs:
                    continue
                pairs.append(pair)

        for a, b in pairs:
            if len(out) >= max_new:
                break

            opts_a = options_by_pos.get(a) or _options_for_position(seed.genome, a, items_by_slot)
            opts_b = options_by_pos.get(b) or _options_for_position(seed.genome, b, items_by_slot)
            cap_a = pair_opts_gear if a < 6 else pair_opts_mini
            cap_b = pair_opts_gear if b < 6 else pair_opts_mini
            opts_a = opts_a[: 1 + cap_a]
            opts_b = opts_b[: 1 + cap_b]

            for it_a in opts_a:
                for it_b in opts_b:
                    if len(out) >= max_new:
                        break
                    genome = list(seed.genome)
                    genome[a] = it_a
                    genome[b] = it_b
                    if not _minis_unique(genome):
                        continue
                    k = _genome_key(genome)
                    if k in seen:
                        continue
                    seen.add(k)
                    out.append(genome)
                if len(out) >= max_new:
                    break

    return out


def _finalize_gpu_batch_eval_plan_light(plan, gpu_results: Optional[list]) -> list[dict]:
    """
    Lightweight alternative to `finalize_gpu_batch_eval_plan` for the FG combo booster.

    The combo booster evaluates up to 4096 genomes, but the downstream FG funnel keeps only a
    small subset. Constructing full `Data["Stats"]` dicts for the entire batch can create large
    CPU stalls (and visible GPU idle gaps) in in-flight mode, so this finalizer returns only the
    minimal per-genome result data needed for candidate selection.

    Callers MUST hydrate `Data` (incl. Stats) for the selected subset before invoking ForceGreats.
    """
    if plan is None or not getattr(plan, "population", None):
        return []

    if plan.unique_stats and (gpu_results is None or len(gpu_results) < len(plan.unique_stats)):
        return list(finalize_gpu_batch_eval_plan(plan, gpu_results))

    sel_color = str(getattr(plan, "sel_color", "") or "")

    try:
        n_uncached = int(len(getattr(plan, "uncached_genomes", None) or []))
    except Exception:
        n_uncached = 0
    if n_uncached <= 0:
        return []

    # Per-uncached genome result buffers (avoid dicts/tuples to reduce allocations/GC spikes).
    scores = [0] * n_uncached
    fts = [0] * n_uncached
    ffs = [0] * n_uncached
    gem_counts_list: list[Optional[dict]] = [None] * n_uncached
    sel_list = [sel_color] * n_uncached
    filled = [False] * n_uncached

    # Cache hits (from GEM_SOLVER_CACHE) already contain a full res dict.
    for idx, res in (getattr(plan, "sig_to_result", None) or {}).items():
        if not isinstance(res, dict):
            continue
        try:
            i = int(idx)
        except Exception:
            continue
        if i < 0 or i >= n_uncached:
            continue
        scores[i] = _int(res.get("Score", 0), 0)
        fts[i] = _int(res.get("FT", 0), 0)
        ffs[i] = _int(res.get("FF", 0), 0)
        gc = res.get("GemCounts", {}) or {}
        gem_counts_list[i] = gc if isinstance(gc, dict) else None
        sel_list[i] = str(res.get("Selected Element", sel_color) or sel_color)
        filled[i] = True

    # GPU results (one per unique signature), broadcast to group members.
    for unique_idx, members in enumerate(getattr(plan, "unique_members", None) or []):
        if gpu_results is None or unique_idx >= len(gpu_results):
            continue
        try:
            score, g_ft, g_ff, g_pp, g_cm, g_fm, g_ov = gpu_results[unique_idx]
        except Exception:
            continue
        score = _int(score, 0)
        g_ft = _int(g_ft, 0)
        g_ff = _int(g_ff, 0)
        g_pp = _int(g_pp, 0)
        g_cm = _int(g_cm, 0)
        g_fm = _int(g_fm, 0)
        g_ov = _int(g_ov, 0)

        gem_counts = {
            "Perfect Points": g_pp,
            "Combo Multiplier": g_cm,
            "Fever Multiplier": g_fm,
            "Element": g_ov,
        }
        for i in members or []:
            try:
                ii = int(i)
            except Exception:
                continue
            if ii < 0 or ii >= n_uncached or filled[ii]:
                continue
            scores[ii] = score
            fts[ii] = g_ft
            ffs[ii] = g_ff
            gem_counts_list[ii] = gem_counts
            sel_list[ii] = sel_color
            filled[ii] = True

    if not all(filled):
        return list(finalize_gpu_batch_eval_plan(plan, gpu_results))

    pop_len = int(len(getattr(plan, "population", None) or []))
    all_results: list[Optional[dict]] = [None] * pop_len

    cached_results = getattr(plan, "cached_results", None) or {}
    for i, res in cached_results.items():
        try:
            idx = int(i)
        except Exception:
            continue
        if 0 <= idx < pop_len and isinstance(res, dict):
            all_results[idx] = res

    uncached_indices = getattr(plan, "uncached_indices", None) or list(range(n_uncached))
    uncached_genomes = getattr(plan, "uncached_genomes", None) or []
    for i, genome in enumerate(uncached_genomes):
        if not genome:
            continue
        try:
            out_idx = int(uncached_indices[i])
        except Exception:
            out_idx = i
        if out_idx < 0 or out_idx >= pop_len:
            continue

        score = int(scores[i])
        result = {
            "Score": score,
            "BaseScore": score,
            "Gear": genome[:6],
            "Minis": genome[6:9],
            # Store these at the top level for selection; `Data` is hydrated later for the selected subset.
            "FT": int(fts[i]),
            "FF": int(ffs[i]),
            "GemCounts": gem_counts_list[i] or {},
            "Selected Element": sel_list[i],
        }
        all_results[out_idx] = result

    return [r if isinstance(r, dict) else {} for r in all_results]


def evaluate_fg_combo_booster_genomes(
    genomes: list[list[dict]],
    *,
    registry: Optional[object] = None,
    base_stats_fixed: dict,
    cfg_data: dict,
    calc_song: dict,
    ref_arrays: dict,
    song_slot: int = 0,
    gpu_client: Optional[object] = None,
) -> list[dict]:
    if not genomes:
        return []

    # Never do this in CPU-only mode; it defeats the purpose of "cheap FG coverage".
    if not bool(cfg_data.get("use_gpu", False)):
        return []

    perf = str(os.environ.get("PERF_TIMING", "0") or "").strip().lower() in {"1", "true", "yes", "on"}
    t0 = time.perf_counter()

    plan, results = prepare_gpu_batch_eval_plan(
        genomes,
        base_stats_fixed,
        cfg_data,
        calc_song,
        ref_arrays,
    )
    t_plan = time.perf_counter()
    if plan is None:
        evaluated = list(results or [])
    else:
        flags = dict(plan.flags or {})

        gpu_results = None
        t_gpu0 = time.perf_counter()
        try:
            # Fast path: evaluate via registry->indices on GPU to avoid building/uploading
            # the huge FT/FF worklist required by `solve_genomes_parallel`.
            solver_mode = str(os.environ.get("FG_COMBO_BOOSTER_GPU_SOLVER", "auto") or "").strip().lower()
            prefer_registry = solver_mode in {"auto", "registry", "from_registry"}
            use_registry = False
            if (
                prefer_registry
                and registry is not None
                and hasattr(registry, "encode_population")
                and hasattr(registry, "to_gpu_arrays")
            ):
                use_registry = True

            if use_registry:
                rep_genomes: list[list[dict]] = []
                for members in plan.unique_members or []:
                    if not members:
                        continue
                    idx0 = int(members[0])
                    if 0 <= idx0 < len(plan.uncached_genomes):
                        rep_genomes.append(plan.uncached_genomes[idx0])

                if rep_genomes:
                    pop_indices = registry.encode_population(rep_genomes)  # (n_unique, 9)
                    gpu_arrays = registry.to_gpu_arrays()

                    base_fixed_stats_np, _ = build_base_fixed_stats_list(base_stats_fixed, cfg_data)
                    if gpu_client is not None:
                        payload = {
                            "population_indices": pop_indices,
                            "item_stats": gpu_arrays.get("item_stats"),
                            "slot_start": gpu_arrays.get("slot_start"),
                            "slot_count": gpu_arrays.get("slot_count"),
                            "base_fixed_stats": base_fixed_stats_np,
                            "timeline_grid": calc_song,
                            "is_p_ft": int(flags.get("is_p_ft", 0)),
                            "is_s_ft": int(flags.get("is_s_ft", 0)),
                            "is_p_ff": int(flags.get("is_p_ff", 0)),
                            "is_s_ff": int(flags.get("is_s_ff", 0)),
                            "is_p_pp": int(flags.get("is_p_pp", 0)),
                            "is_s_pp": int(flags.get("is_s_pp", 0)),
                            "is_p_cm": int(flags.get("is_p_cm", 0)),
                            "is_s_cm": int(flags.get("is_s_cm", 0)),
                            "is_p_fm": int(flags.get("is_p_fm", 0)),
                            "is_s_fm": int(flags.get("is_s_fm", 0)),
                            "is_p_ov": int(flags.get("is_p_ov", 0)),
                            "is_s_ov": int(flags.get("is_s_ov", 0)),
                            "ref_arrays": ref_arrays,
                            "total_budget": int(TOTAL_GEM_BUDGET),
                            "gem_scale_fever": int(GEM_SCALE_FEVER),
                            "song_slot": int(song_slot),
                        }
                        gpu_results = gpu_client.submit_solve_genomes_from_registry(payload).future.result()
                    elif is_gpu_worker_mode():
                        from ...solver.gpu_executor import submit_gpu_solve_genomes_from_registry

                        gpu_results = submit_gpu_solve_genomes_from_registry(
                            pop_indices,
                            gpu_arrays.get("item_stats"),
                            gpu_arrays.get("slot_start"),
                            gpu_arrays.get("slot_count"),
                            base_fixed_stats_np,
                            calc_song,
                            int(flags.get("is_p_ft", 0)),
                            int(flags.get("is_s_ft", 0)),
                            int(flags.get("is_p_ff", 0)),
                            int(flags.get("is_s_ff", 0)),
                            int(flags.get("is_p_pp", 0)),
                            int(flags.get("is_s_pp", 0)),
                            int(flags.get("is_p_cm", 0)),
                            int(flags.get("is_s_cm", 0)),
                            int(flags.get("is_p_fm", 0)),
                            int(flags.get("is_s_fm", 0)),
                            int(flags.get("is_p_ov", 0)),
                            int(flags.get("is_s_ov", 0)),
                            ref_arrays,
                            total_budget=int(TOTAL_GEM_BUDGET),
                            gem_scale_fever=int(GEM_SCALE_FEVER),
                            song_slot=int(song_slot),
                        )
                    else:
                        from ...solver.scoring.gpu_solver import _GPU_LOCK
                        from ...solver.taichi_gem.api import (
                            ga_upload_base_fixed_stats as ga_upload_base_fixed_stats_ti,
                            ga_upload_item_stats as ga_upload_item_stats_ti,
                            solve_genomes_from_registry as solve_genomes_from_registry_ti,
                        )

                        with _GPU_LOCK:
                            ga_upload_item_stats_ti(
                                gpu_arrays.get("item_stats"),
                                gpu_arrays.get("slot_start"),
                                gpu_arrays.get("slot_count"),
                            )
                            ga_upload_base_fixed_stats_ti(base_fixed_stats_np)
                            gpu_results = solve_genomes_from_registry_ti(
                                pop_indices,
                                calc_song,
                                int(flags.get("is_p_ft", 0)),
                                int(flags.get("is_s_ft", 0)),
                                int(flags.get("is_p_ff", 0)),
                                int(flags.get("is_s_ff", 0)),
                                int(flags.get("is_p_pp", 0)),
                                int(flags.get("is_s_pp", 0)),
                                int(flags.get("is_p_cm", 0)),
                                int(flags.get("is_s_cm", 0)),
                                int(flags.get("is_p_fm", 0)),
                                int(flags.get("is_s_fm", 0)),
                                int(flags.get("is_p_ov", 0)),
                                int(flags.get("is_s_ov", 0)),
                                ref_arrays,
                                total_budget=int(TOTAL_GEM_BUDGET),
                                gem_scale_fever=int(GEM_SCALE_FEVER),
                                song_slot=int(song_slot),
                            )

            if gpu_results is None:
                if gpu_client is not None:
                    payload = {
                        "genome_stats_list": plan.genome_stats_list,
                        "timeline_grid": calc_song,
                        "is_p_ft": int(flags.get("is_p_ft", 0)),
                        "is_s_ft": int(flags.get("is_s_ft", 0)),
                        "is_p_ff": int(flags.get("is_p_ff", 0)),
                        "is_s_ff": int(flags.get("is_s_ff", 0)),
                        "is_p_pp": int(flags.get("is_p_pp", 0)),
                        "is_s_pp": int(flags.get("is_s_pp", 0)),
                        "is_p_cm": int(flags.get("is_p_cm", 0)),
                        "is_s_cm": int(flags.get("is_s_cm", 0)),
                        "is_p_fm": int(flags.get("is_p_fm", 0)),
                        "is_s_fm": int(flags.get("is_s_fm", 0)),
                        "is_p_ov": int(flags.get("is_p_ov", 0)),
                        "is_s_ov": int(flags.get("is_s_ov", 0)),
                        "ref_arrays": ref_arrays,
                        "total_budget": int(TOTAL_GEM_BUDGET),
                        "gem_scale_fever": int(GEM_SCALE_FEVER),
                        "song_slot": int(song_slot),
                    }
                    gpu_results = gpu_client.submit_solve_genomes(payload).future.result()
                elif is_gpu_worker_mode():
                    gpu_results = submit_gpu_solve_genomes(
                        plan.genome_stats_list,
                        calc_song,
                        int(flags.get("is_p_ft", 0)),
                        int(flags.get("is_s_ft", 0)),
                        int(flags.get("is_p_ff", 0)),
                        int(flags.get("is_s_ff", 0)),
                        int(flags.get("is_p_pp", 0)),
                        int(flags.get("is_s_pp", 0)),
                        int(flags.get("is_p_cm", 0)),
                        int(flags.get("is_s_cm", 0)),
                        int(flags.get("is_p_fm", 0)),
                        int(flags.get("is_s_fm", 0)),
                        int(flags.get("is_p_ov", 0)),
                        int(flags.get("is_s_ov", 0)),
                        ref_arrays,
                        total_budget=int(TOTAL_GEM_BUDGET),
                        gem_scale_fever=int(GEM_SCALE_FEVER),
                        song_slot=int(song_slot),
                    )
                else:
                    from ...solver.scoring.gpu_solver import _GPU_LOCK
                    from ...solver.taichi_gem.api import solve_genomes_parallel as solve_genomes_parallel_ti

                    with _GPU_LOCK:
                        gpu_results = solve_genomes_parallel_ti(
                            plan.genome_stats_list,
                            calc_song,
                            int(flags.get("is_p_ft", 0)),
                            int(flags.get("is_s_ft", 0)),
                            int(flags.get("is_p_ff", 0)),
                            int(flags.get("is_s_ff", 0)),
                            int(flags.get("is_p_pp", 0)),
                            int(flags.get("is_s_pp", 0)),
                            int(flags.get("is_p_cm", 0)),
                            int(flags.get("is_s_cm", 0)),
                            int(flags.get("is_p_fm", 0)),
                            int(flags.get("is_s_fm", 0)),
                            int(flags.get("is_p_ov", 0)),
                            int(flags.get("is_s_ov", 0)),
                            ref_arrays,
                            total_budget=int(TOTAL_GEM_BUDGET),
                            gem_scale_fever=int(GEM_SCALE_FEVER),
                            song_slot=int(song_slot),
                        )
        except Exception:
            gpu_results = None
        t_gpu1 = time.perf_counter()

        finalize_mode = str(os.environ.get("FG_COMBO_BOOSTER_FINALIZE_MODE", "light") or "").strip().lower()
        if finalize_mode in {"full", "stats", "heavy"}:
            evaluated = finalize_gpu_batch_eval_plan(plan, gpu_results)
        else:
            evaluated = _finalize_gpu_batch_eval_plan_light(plan, gpu_results)
        t_finalize = time.perf_counter()
        if perf:
            try:
                n_pop = int(len(plan.population or []))
            except Exception:
                n_pop = int(len(genomes))
            try:
                n_sig = int(len(plan.unique_stats or []))
            except Exception:
                n_sig = 0
            try:
                n_stats = int(len(plan.genome_stats_list or []))
            except Exception:
                n_stats = 0
            print(
                "[PERF][FGBoosterEval] "
                f"genomes={n_pop} unique_sig={n_sig} gpu_work={n_stats} "
                f"plan={(t_plan - t0) * 1000:.1f}ms gpu={(t_gpu1 - t_gpu0) * 1000:.1f}ms "
                f"finalize={(t_finalize - t_gpu1) * 1000:.1f}ms total={(t_finalize - t0) * 1000:.1f}ms"
            )

    out: list[dict] = []
    for cand in evaluated or []:
        if not isinstance(cand, dict):
            continue
        # Mark as high-priority for the FG candidate funnel.
        cand["_fg_priority"] = 1
        cand["_fg_source"] = "combo_booster"
        out.append(cand)
    return out


def hydrate_fg_candidate_stats(
    candidates: list[dict],
    *,
    base_stats_fixed: dict,
    selected_color: str,
    cfg_data: Optional[dict] = None,
) -> None:
    """
    Ensure candidates have `Data` with `Stats` for ForceGreats.

    The FG combo booster may return lightweight candidates (no `Data` / no `Stats`) to avoid
    per-genome stats dict construction for the full booster batch. Downstream ForceGreatsFinder
    requires `eval_data["Stats"]`, so hydrate only the selected subset before building loadouts.
    """
    if not candidates:
        return

    selected_color = str(selected_color or "")
    cfg_data = cfg_data if isinstance(cfg_data, dict) else {}

    # Match GPU kernels: start from base_fixed (user-fixed gems + static overflow removed).
    base_fixed_list, fallback_sel = build_base_fixed_stats_list(
        base_stats_fixed,
        cfg_data,
        fallback_selected_color=selected_color,
    )
    stat_names = [
        "Perfect Points",
        "Combo Multiplier",
        "Fever Multiplier",
        "Fever Time",
        "Fever Fill Rate",
        "Beat",
        "Vibe",
        "Rush",
        "Flow",
        "Chill",
    ]
    base_fixed = {stat_names[i]: int(base_fixed_list[i]) for i in range(min(len(stat_names), len(base_fixed_list)))}
    if fallback_sel and not selected_color:
        selected_color = str(fallback_sel)

    for cand in candidates:
        if not isinstance(cand, dict):
            continue

        data = cand.get("Data")
        if not isinstance(data, dict):
            data = {}

        stats_existing = data.get("Stats")
        if isinstance(stats_existing, dict) and stats_existing:
            continue

        ft = data.get("FT", cand.get("FT", 0) or 0) or 0
        ff = data.get("FF", cand.get("FF", 0) or 0) or 0
        try:
            ft = int(ft)
        except Exception:
            ft = 0
        try:
            ff = int(ff)
        except Exception:
            ff = 0

        gem_counts = cand.get("GemCounts") or data.get("GemCounts") or {}
        if not isinstance(gem_counts, dict):
            gem_counts = {}

        g_pp = _int(gem_counts.get("Perfect Points", 0), 0)
        g_cm = _int(gem_counts.get("Combo Multiplier", 0), 0)
        g_fm = _int(gem_counts.get("Fever Multiplier", 0), 0)
        g_ov = _int(gem_counts.get("Element", gem_counts.get("Element Overflow", 0)), 0)

        sel = get_selected_element(data, "") or get_selected_element(cand, "") or str(selected_color or "")

        genome = cand.get("Genome")
        if not isinstance(genome, list) or not genome:
            genome = _as_genome(cand)

        # Aggregate base stats from base_fixed + items.
        stats = dict(base_fixed)
        for item in genome[:9]:
            if not isinstance(item, dict) or not item:
                continue
            for k, v in item.items():
                if k in SKIP_ITEM_KEYS:
                    continue
                try:
                    stats[k] = stats.get(k, 0) + v
                except Exception:
                    continue

        stats = apply_gems_to_base_stats(
            stats,
            str(sel),
            int(ft),
            int(ff),
            int(g_pp),
            int(g_cm),
            int(g_fm),
            int(g_ov),
            add_missing_element_key=False,
        )

        base_score = _base_score(cand)
        data["Score"] = int(base_score)
        data["BaseScore"] = int(base_score)
        data["FT"] = int(ft)
        data["FF"] = int(ff)
        data["GemCounts"] = gem_counts
        data["Selected Element"] = sel
        data["Stats"] = stats
        cand["Data"] = data


def build_fg_combo_booster_candidates(
    *,
    existing_candidates: list[dict],
    registry,
    base_stats_fixed: dict,
    cfg_data: dict,
    calc_song: dict,
    ref_arrays: dict,
    primary_color: str,
    secondary_color: str,
    song_slot: int = 0,
    max_extra_evals: int = FG_COMBO_BOOSTER_MAX_EVALS,
    top_k: int = FG_COMBO_BOOSTER_TOP_K,
    positions_per_seed: int = FG_COMBO_BOOSTER_POSITIONS_PER_SEED,
    gpu_client: Optional[object] = None,
) -> list[dict]:
    perf = str(os.environ.get("PERF_TIMING", "0") or "").strip().lower() in {"1", "true", "yes", "on"}
    t0 = time.perf_counter()
    gpu_eval_cap = _env_int("FG_COMBO_BOOSTER_GPU_EVALS", FG_COMBO_BOOSTER_DEFAULT_GPU_EVALS)
    # Treat non-positive as "no cap" (evaluate everything up to max_extra_evals).
    if gpu_eval_cap <= 0:
        gpu_eval_cap = int(max_extra_evals)
    gpu_eval_cap = max(1, min(int(max_extra_evals), int(gpu_eval_cap)))

    # Default to the improved multi-axis generator; users can set `FG_COMBO_BOOSTER_MODE=classic`
    # if they want the reference behavior for comparisons.
    booster_mode = str(os.environ.get("FG_COMBO_BOOSTER_MODE", "multi_axis") or "").strip().lower()
    if booster_mode in {"multi_axis", "multi-axis", "v2", "diverse"}:
        genomes = generate_fg_combo_booster_genomes_multi_axis(
            existing_candidates=existing_candidates,
            registry=registry,
            primary_color=primary_color,
            secondary_color=secondary_color,
            max_new=int(max_extra_evals),
            top_k=int(top_k),
        )
    else:
        genomes = generate_fg_combo_booster_genomes(
            existing_candidates=existing_candidates,
            registry=registry,
            primary_color=primary_color,
            secondary_color=secondary_color,
            max_new=int(max_extra_evals),
            top_k=int(top_k),
            positions_per_seed=int(positions_per_seed),
        )
    if not genomes:
        return []
    t_gen = time.perf_counter()

    genomes_for_eval = select_fg_combo_booster_genomes_for_eval(
        genomes,
        primary_color=str(primary_color or ""),
        secondary_color=str(secondary_color or ""),
        max_evals=int(gpu_eval_cap),
    )
    out = evaluate_fg_combo_booster_genomes(
        genomes_for_eval,
        registry=registry,
        base_stats_fixed=base_stats_fixed,
        cfg_data=cfg_data,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        song_slot=int(song_slot),
        gpu_client=gpu_client,
    )
    if perf:
        dt_total = time.perf_counter() - t0
        dt_gen = t_gen - t0
        dt_eval = time.perf_counter() - t_gen
        try:
            p = int(len(out))
        except Exception:
            p = 0
        try:
            g = int(len(genomes))
        except Exception:
            g = 0
        try:
            g_sel = int(len(genomes_for_eval))
        except Exception:
            g_sel = 0
        try:
            uniq = int(len({_genome_key(gen) for gen in genomes}))
        except Exception:
            uniq = g
        print(
            "[PERF][FGBooster] "
            f"mode={booster_mode} generated={g} selected={g_sel} eval_cap={gpu_eval_cap} uniq={uniq} evaluated={p} "
            f"gen={dt_gen * 1000:.1f}ms eval={dt_eval * 1000:.1f}ms total={dt_total * 1000:.1f}ms"
        )
    return out


def prepare_fg_combo_booster_candidates_job(
    *,
    existing_candidates: list[dict],
    registry,
    base_stats_fixed: dict,
    cfg_data: dict,
    calc_song: dict,
    ref_arrays: dict,
    primary_color: str,
    secondary_color: str,
    song_slot: int = 0,
    max_extra_evals: int = FG_COMBO_BOOSTER_MAX_EVALS,
    top_k: int = FG_COMBO_BOOSTER_TOP_K,
    positions_per_seed: int = FG_COMBO_BOOSTER_POSITIONS_PER_SEED,
    gpu_client: Optional[object] = None,
) -> dict | None:
    """
    Prepare an async combo-booster job.

    This splits the combo booster into two phases:
    - prepare + GPU submission (this function)
    - finalize (see `finalize_fg_combo_booster_candidates_job`)

    The goal is to let native in-flight schedule the GPU work earlier so the
    executor queue stays non-empty across GA↔FG boundaries.
    """
    if not existing_candidates:
        return None

    if gpu_client is None:
        return None

    # Never do this in CPU-only mode; it defeats the purpose of "cheap FG coverage".
    if not bool(cfg_data.get("use_gpu", False)):
        return None

    booster_mode = str(os.environ.get("FG_COMBO_BOOSTER_MODE", "multi_axis") or "").strip().lower()
    if booster_mode in {"multi_axis", "multi-axis", "v2", "diverse"}:
        genomes = generate_fg_combo_booster_genomes_multi_axis(
            existing_candidates=existing_candidates,
            registry=registry,
            primary_color=primary_color,
            secondary_color=secondary_color,
            max_new=int(max_extra_evals),
            top_k=int(top_k),
        )
    else:
        genomes = generate_fg_combo_booster_genomes(
            existing_candidates=existing_candidates,
            registry=registry,
            primary_color=primary_color,
            secondary_color=secondary_color,
            max_new=int(max_extra_evals),
            top_k=int(top_k),
            positions_per_seed=int(positions_per_seed),
        )
    if not genomes:
        return None

    gpu_eval_cap = _env_int("FG_COMBO_BOOSTER_GPU_EVALS", FG_COMBO_BOOSTER_DEFAULT_GPU_EVALS)
    if gpu_eval_cap <= 0:
        gpu_eval_cap = int(max_extra_evals)
    gpu_eval_cap = max(1, min(int(max_extra_evals), int(gpu_eval_cap)))

    genomes_for_eval = select_fg_combo_booster_genomes_for_eval(
        genomes,
        primary_color=str(primary_color or ""),
        secondary_color=str(secondary_color or ""),
        max_evals=int(gpu_eval_cap),
    )
    if not genomes_for_eval:
        return None

    plan, results = prepare_gpu_batch_eval_plan(
        genomes_for_eval,
        base_stats_fixed,
        cfg_data,
        calc_song,
        ref_arrays,
    )
    if plan is None:
        evaluated = list(results or [])
        for cand in evaluated:
            if isinstance(cand, dict):
                cand["_fg_priority"] = 1
                cand["_fg_source"] = "combo_booster"
        return {"evaluated": evaluated}

    flags = dict(getattr(plan, "flags", None) or {})
    solver_mode = str(os.environ.get("FG_COMBO_BOOSTER_GPU_SOLVER", "auto") or "").strip().lower()
    prefer_registry = solver_mode in {"auto", "registry", "from_registry"}
    use_registry = bool(
        prefer_registry
        and registry is not None
        and hasattr(registry, "encode_population")
        and hasattr(registry, "to_gpu_arrays")
    )
    if not use_registry:
        return None

    rep_genomes: list[list[dict]] = []
    for members in getattr(plan, "unique_members", None) or []:
        if not members:
            continue
        idx0 = int(members[0])
        if 0 <= idx0 < len(plan.uncached_genomes):
            rep_genomes.append(plan.uncached_genomes[idx0])
    if not rep_genomes:
        return None

    pop_indices = registry.encode_population(rep_genomes)  # (n_unique, 9)
    gpu_arrays = registry.to_gpu_arrays()
    base_fixed_stats_np, _ = build_base_fixed_stats_list(base_stats_fixed, cfg_data)

    payload = {
        "population_indices": pop_indices,
        "item_stats": gpu_arrays.get("item_stats"),
        "slot_start": gpu_arrays.get("slot_start"),
        "slot_count": gpu_arrays.get("slot_count"),
        "base_fixed_stats": base_fixed_stats_np,
        "timeline_grid": calc_song,
        "is_p_ft": int(flags.get("is_p_ft", 0)),
        "is_s_ft": int(flags.get("is_s_ft", 0)),
        "is_p_ff": int(flags.get("is_p_ff", 0)),
        "is_s_ff": int(flags.get("is_s_ff", 0)),
        "is_p_pp": int(flags.get("is_p_pp", 0)),
        "is_s_pp": int(flags.get("is_s_pp", 0)),
        "is_p_cm": int(flags.get("is_p_cm", 0)),
        "is_s_cm": int(flags.get("is_s_cm", 0)),
        "is_p_fm": int(flags.get("is_p_fm", 0)),
        "is_s_fm": int(flags.get("is_s_fm", 0)),
        "is_p_ov": int(flags.get("is_p_ov", 0)),
        "is_s_ov": int(flags.get("is_s_ov", 0)),
        "ref_arrays": ref_arrays,
        "total_budget": int(TOTAL_GEM_BUDGET),
        "gem_scale_fever": int(GEM_SCALE_FEVER),
        "song_slot": int(song_slot),
    }

    handle = gpu_client.submit_solve_genomes_from_registry(payload)
    return {
        "plan": plan,
        "future": handle.future,
    }


def finalize_fg_combo_booster_candidates_job(job: dict | None) -> list[dict]:
    if not isinstance(job, dict) or not job:
        return []

    evaluated = job.get("evaluated")
    if isinstance(evaluated, list):
        return [c for c in evaluated if isinstance(c, dict)]

    plan = job.get("plan")
    fut = job.get("future")
    if plan is None or fut is None:
        return []

    try:
        gpu_results = fut.result()
    except Exception:
        return []

    finalize_mode = str(os.environ.get("FG_COMBO_BOOSTER_FINALIZE_MODE", "light") or "").strip().lower()
    if finalize_mode in {"full", "stats", "heavy"}:
        evaluated = finalize_gpu_batch_eval_plan(plan, gpu_results)
    else:
        evaluated = _finalize_gpu_batch_eval_plan_light(plan, gpu_results)

    out: list[dict] = []
    for cand in evaluated or []:
        if not isinstance(cand, dict):
            continue
        cand["_fg_priority"] = 1
        cand["_fg_source"] = "combo_booster"
        out.append(cand)
    return out
