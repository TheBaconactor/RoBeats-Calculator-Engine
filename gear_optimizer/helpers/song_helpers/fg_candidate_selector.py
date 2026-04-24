from __future__ import annotations

import heapq
import os
from dataclasses import dataclass

from ...core.constants import LOADOUTS_PER_SONG_LIMIT
from .ga_entry_utils import candidate_loadout_hash
from .item_utils import _item_name


def _split_gear_minis(candidate: dict) -> tuple[list[dict], list[dict]]:
    """
    Robustly extract (gear, minis) from historical candidate shapes.

    Supported shapes:
    - {"Gear": [...], "Minis": [...]}
    - {"Genome": [...]} where first 6 are gear and next 3 are minis.
    """
    genome = candidate.get("Genome")
    if isinstance(genome, list) and genome:
        gear = list(genome[:6])
        minis = list(genome[6:9])
        return gear, minis
    gear = list(candidate.get("Gear") or [])[:6]
    minis = list(candidate.get("Minis") or [])[:3]
    return gear, minis


def _center_key(candidate: dict) -> tuple[int, int]:
    data = candidate.get("Data")
    if not isinstance(data, dict):
        data = candidate.get("data")
        if not isinstance(data, dict):
            data = {}
    ft = 0
    ff = 0
    try:
        ft = data.get("FT", candidate.get("FT", 0) or 0) or 0
        ff = data.get("FF", candidate.get("FF", 0) or 0) or 0
    except Exception:
        ft = candidate.get("FT", 0) or 0
        ff = candidate.get("FF", 0) or 0
    try:
        return int(ft), int(ff)
    except Exception:
        return 0, 0


def _base_score(candidate: dict) -> int:
    v = candidate.get("BaseScore")
    if v is None:
        v = candidate.get("Score", 0)
    try:
        return int(v or 0)
    except Exception:
        return 0


def _fg_proxy_from_items(items: list[dict], *, primary_color: str, secondary_color: str) -> int:
    """FG proxy variant that reuses already split gear+mini item lists."""

    def _i(item: dict, key: str) -> int:
        try:
            return int((item or {}).get(key, 0) or 0)
        except Exception:
            return 0

    score = 0
    for it in items:
        if not isinstance(it, dict) or not it:
            continue
        score += _i(it, "Fever Multiplier") * 4
        score += _i(it, "Fever Fill Rate") * 4
        score += _i(it, "Fever Time") * 3
        score += _i(it, "Combo Multiplier") * 2
        score += _i(it, "Perfect Points")
        if primary_color:
            score += _i(it, primary_color) * 2
        if secondary_color and secondary_color != primary_color:
            score += _i(it, secondary_color)
    return int(score)


def select_effective_unique_ga_candidates(
    candidates: list[dict],
    *,
    limit: int,
    registry: object = None,
    minis_by_name: dict[str, dict] | None = None,
    primary_color: str = "",
    secondary_color: str = "",
    selected_color: str = "",
) -> list[dict]:
    """
    Keep one best-base candidate per persisted loadout hash.

    GPU GA dedupes selected rows by exact gear/mini IDs, but DB persistence dedupes
    by song-context effective mini signatures. This selector bridges that contract
    before persistence so 51 raw candidates do not collapse to a tiny DB frontier.
    """
    if not candidates:
        return []
    try:
        limit_i = int(limit)
    except Exception:
        limit_i = 0
    if limit_i <= 0:
        return []

    best_by_hash: dict[str, dict] = {}
    best_rank_by_hash: dict[str, tuple[int, int, int]] = {}
    for order, cand in enumerate(candidates):
        if not isinstance(cand, dict):
            continue
        loadout_hash = candidate_loadout_hash(
            cand,
            registry=registry,
            minis_by_name=minis_by_name,
            primary_color=primary_color,
            secondary_color=secondary_color,
            selected_color=selected_color,
            mutate=True,
        )
        if not loadout_hash:
            continue
        try:
            fg_priority = int(cand.get("_fg_priority", 0) or 0)
        except Exception:
            fg_priority = 0
        # Higher base/priority wins; earlier rows win exact ties to preserve GPU ordering.
        rank = (_base_score(cand), fg_priority, -int(order))
        prev_rank = best_rank_by_hash.get(loadout_hash)
        if prev_rank is None or rank > prev_rank:
            best_by_hash[loadout_hash] = cand
            best_rank_by_hash[loadout_hash] = rank

    unique = list(best_by_hash.values())
    if len(unique) <= limit_i:
        unique.sort(key=_base_score, reverse=True)
        return unique

    return select_fg_candidates(
        unique,
        limit=limit_i,
        primary_color=primary_color,
        secondary_color=secondary_color,
    )


@dataclass(frozen=True)
class _CandMeta:
    cand: dict
    key: tuple[str, ...]
    base: int
    fg_proxy: int
    mini_key: tuple[str, ...]
    center: tuple[int, int]
    fg_priority: int


def _meta_base_key(meta: _CandMeta) -> tuple[int, int, tuple[str, ...]]:
    return meta.base, meta.fg_proxy, meta.key


def _meta_fg_key(meta: _CandMeta) -> tuple[int, int, tuple[str, ...]]:
    return meta.fg_proxy, meta.base, meta.key


def select_fg_candidates(
    candidates: list[dict],
    *,
    limit: int,
    primary_color: str = "",
    secondary_color: str = "",
    mode: str = "default",
    promising_band_pct: float = 1.0,
    promising_max_pool: int = 20000,
    promising_per_mini: int = 6,
    promising_per_center: int = 6,
    promising_center_bin: int = 2,
) -> list[dict]:
    """
    Pick a bounded candidate funnel for ForceGreatsFinder.

    Goal: keep the best base-score candidates (DB stability) while also retaining
    candidates with high fever potential that may only become optimal once
    ForceGreats is applied.

    Environment overrides:
      - FG_CANDIDATE_SELECTOR_MODE: "default" (mixed budgets), "promising_archive", "slot_diverse_archive"
      - FG_PROMISING_* and FG_SLOT_DIVERSE_*: tune budgets for those modes
    """
    if not candidates:
        return []

    try:
        limit = int(limit)
    except Exception:
        limit = 0
    if limit <= 0:
        return []

    primary_color = str(primary_color or "")
    secondary_color = str(secondary_color or "")
    mode = str(mode or "default").strip().lower() or "default"

    # Optional environment overrides so benchmarks (and power users) can switch
    # candidate selection modes without touching config files.
    if mode == "default":
        env_mode = os.environ.get("FG_CANDIDATE_SELECTOR_MODE")
        if env_mode:
            mode = str(env_mode).strip().lower()

    env_band = os.environ.get("FG_PROMISING_BAND_PCT")
    if env_band is not None and str(env_band).strip():
        try:
            promising_band_pct = float(env_band)
        except Exception:
            pass

    env_max_pool = os.environ.get("FG_PROMISING_MAX_POOL")
    if env_max_pool is not None and str(env_max_pool).strip():
        try:
            promising_max_pool = int(env_max_pool)
        except Exception:
            pass

    env_per_mini = os.environ.get("FG_PROMISING_PER_MINI")
    if env_per_mini is not None and str(env_per_mini).strip():
        try:
            promising_per_mini = int(env_per_mini)
        except Exception:
            pass

    env_per_center = os.environ.get("FG_PROMISING_PER_CENTER")
    if env_per_center is not None and str(env_per_center).strip():
        try:
            promising_per_center = int(env_per_center)
        except Exception:
            pass

    env_center_bin = os.environ.get("FG_PROMISING_CENTER_BIN")
    if env_center_bin is not None and str(env_center_bin).strip():
        try:
            promising_center_bin = int(env_center_bin)
        except Exception:
            pass

    slot_band_pct = 1.0
    slot_max_pool = 20000
    slot_per_slot = 10

    env_slot_band = os.environ.get("FG_SLOT_DIVERSE_BAND_PCT")
    if env_slot_band is not None and str(env_slot_band).strip():
        try:
            slot_band_pct = float(env_slot_band)
        except Exception:
            pass

    env_slot_max_pool = os.environ.get("FG_SLOT_DIVERSE_MAX_POOL")
    if env_slot_max_pool is not None and str(env_slot_max_pool).strip():
        try:
            slot_max_pool = int(env_slot_max_pool)
        except Exception:
            pass

    env_slot_per_slot = os.environ.get("FG_SLOT_DIVERSE_PER_SLOT")
    if env_slot_per_slot is not None and str(env_slot_per_slot).strip():
        try:
            slot_per_slot = int(env_slot_per_slot)
        except Exception:
            pass

    def _select_promising_archive(metas: list[_CandMeta]) -> list[dict]:
        try:
            band_pct = float(promising_band_pct)
        except Exception:
            band_pct = 1.0
        if band_pct < 0:
            band_pct = 0.0

        try:
            max_pool = int(promising_max_pool)
        except Exception:
            max_pool = 0
        if max_pool <= 0:
            max_pool = 20000

        try:
            per_mini = int(promising_per_mini)
        except Exception:
            per_mini = 0
        if per_mini < 0:
            per_mini = 0

        try:
            per_center = int(promising_per_center)
        except Exception:
            per_center = 0
        if per_center < 0:
            per_center = 0

        try:
            center_bin = int(promising_center_bin)
        except Exception:
            center_bin = 2
        if center_bin <= 0:
            center_bin = 1

        # Avoid full-list sorts when metas is large: we only need the top slice.
        try:
            best_base = max((m.base for m in metas), default=0)
        except Exception:
            best_base = 0
        threshold = int(best_base * (1.0 - (band_pct / 100.0))) if best_base > 0 else 0

        # Base band: candidates within X% of the best base-score loadout.
        band = [m for m in metas if m.base >= threshold]
        if not band:
            band = list(metas)

        # Prevent pathological sizes when GA returns a very wide funnel.
        if len(band) > max_pool:
            band = heapq.nlargest(max_pool, band, key=_meta_base_key)

        band_by_fg = sorted(band, key=_meta_fg_key, reverse=True)

        selected: list[dict] = []
        seen_keys: set[tuple[str, ...]] = set()

        mini_counts: dict[tuple[str, ...], int] = {}
        center_counts: dict[tuple[int, int], int] = {}

        def _center_bucket(center: tuple[int, int]) -> tuple[int, int]:
            try:
                return int(center[0] // center_bin), int(center[1] // center_bin)
            except Exception:
                return 0, 0

        def _add(meta: _CandMeta) -> bool:
            if meta.key in seen_keys:
                return False
            seen_keys.add(meta.key)
            selected.append(meta.cand)
            return True

        # Hard guarantee: keep at least the top-N by base score (DB stability).
        top_base_keep = min(limit, int(LOADOUTS_PER_SONG_LIMIT))
        metas_by_base = heapq.nlargest(min(len(metas), max(limit, top_base_keep)), metas, key=_meta_base_key)
        for meta in metas_by_base:
            if len(selected) >= top_base_keep:
                break
            _add(meta)

        # Preserve a small slice of explicitly marked FG-priority candidates.
        priority_budget = max(0, min(limit - len(selected), max(5, limit // 10)))
        if priority_budget:
            priority = [m for m in band_by_fg if m.fg_priority]
            for meta in priority:
                if len(selected) >= (top_base_keep + priority_budget):
                    break
                _add(meta)

        # Promising archive fill:
        # 1) Keep a few top FG-proxy candidates per mini-team (prevents mini collapse).
        if per_mini > 0:
            for meta in band_by_fg:
                if len(selected) >= limit:
                    break
                k = meta.mini_key
                if mini_counts.get(k, 0) >= per_mini:
                    continue
                if _add(meta):
                    mini_counts[k] = mini_counts.get(k, 0) + 1

        # 2) Keep a few top FG-proxy candidates per (FT,FF) center bucket (prevents center collapse).
        if per_center > 0:
            for meta in band_by_fg:
                if len(selected) >= limit:
                    break
                b = _center_bucket(meta.center)
                if center_counts.get(b, 0) >= per_center:
                    continue
                if _add(meta):
                    center_counts[b] = center_counts.get(b, 0) + 1

        # 3) Fill remaining by FG proxy within the band, then by base score.
        for meta in band_by_fg:
            if len(selected) >= limit:
                break
            _add(meta)

        if len(selected) < limit:
            for meta in metas_by_base:
                if len(selected) >= limit:
                    break
                _add(meta)

        return selected[:limit]

    def _select_slot_diverse_archive(metas: list[_CandMeta]) -> list[dict]:
        try:
            band_pct = float(slot_band_pct)
        except Exception:
            band_pct = 1.0
        if band_pct < 0:
            band_pct = 0.0

        try:
            max_pool = int(slot_max_pool)
        except Exception:
            max_pool = 0
        if max_pool <= 0:
            max_pool = 20000

        try:
            per_slot = int(slot_per_slot)
        except Exception:
            per_slot = 10
        per_slot = max(1, min(50, int(per_slot)))

        # Only materialize top slices we can actually consume.
        base_pool_k = min(len(metas), max(limit, 20000))
        metas_by_base = heapq.nlargest(base_pool_k, metas, key=_meta_base_key)
        metas_by_fg = heapq.nlargest(base_pool_k, metas, key=_meta_fg_key)

        best_base = metas_by_base[0].base if metas_by_base else 0
        threshold = int(best_base * (1.0 - (band_pct / 100.0))) if best_base > 0 else 0
        slot_pool = [m for m in metas_by_base if m.base >= threshold]
        if not slot_pool:
            slot_pool = metas_by_base[:]
        if len(slot_pool) > max_pool:
            slot_pool = slot_pool[:max_pool]

        selected: list[dict] = []
        seen_keys: set[tuple[str, ...]] = set()
        seen_minis: set[tuple[str, ...]] = set()
        seen_centers: set[tuple[int, int]] = set()
        seen_items_by_slot: list[set[str]] = [set() for _ in range(6)]

        def _add(meta: _CandMeta) -> bool:
            if meta.key in seen_keys:
                return False
            seen_keys.add(meta.key)
            selected.append(meta.cand)
            seen_minis.add(meta.mini_key)
            seen_centers.add(meta.center)
            for slot_idx in range(6):
                try:
                    name = meta.key[slot_idx]
                except Exception:
                    name = ""
                if name:
                    seen_items_by_slot[slot_idx].add(name)
            return True

        # 1) Hard guarantee: keep at least the top-N by base score (DB stability).
        top_base_keep = min(limit, int(LOADOUTS_PER_SONG_LIMIT))
        for meta in metas_by_base:
            if len(selected) >= top_base_keep:
                break
            _add(meta)

        # 2) Preserve a small slice of explicitly marked FG-priority candidates.
        priority_budget = max(0, min(limit - len(selected), max(5, limit // 10)))
        if priority_budget:
            priority = [m for m in metas_by_fg if m.fg_priority]
            for meta in priority:
                if len(selected) >= (top_base_keep + priority_budget):
                    break
                _add(meta)

        # 3) Slot-diverse archive: keep candidates that introduce new items per gear slot,
        # within a high-base band (prevents "single-item collapse" that hides FG peaks).
        def _needs_slot_item(meta: _CandMeta) -> bool:
            for slot_idx in range(6):
                if len(seen_items_by_slot[slot_idx]) >= per_slot:
                    continue
                try:
                    name = meta.key[slot_idx]
                except Exception:
                    name = ""
                if name and name not in seen_items_by_slot[slot_idx]:
                    return True
            return False

        for meta in slot_pool:
            if len(selected) >= limit:
                break
            if not _needs_slot_item(meta):
                continue
            _add(meta)
            if all(len(s) >= per_slot for s in seen_items_by_slot):
                break

        # 4) Continue with the default mixed budgets (exploitation + FG-proxy + diversity).
        base_budget = min(limit, max(top_base_keep, int(limit * 0.55)))
        fg_budget_end = min(limit, base_budget + int(limit * 0.30))

        for meta in metas_by_base:
            if len(selected) >= base_budget:
                break
            _add(meta)

        for meta in metas_by_fg:
            if len(selected) >= fg_budget_end:
                break
            if meta.center in seen_centers:
                continue
            _add(meta)
        for meta in metas_by_fg:
            if len(selected) >= fg_budget_end:
                break
            _add(meta)

        for meta in metas_by_base:
            if len(selected) >= limit:
                break
            if meta.mini_key in seen_minis:
                continue
            _add(meta)

        for meta in metas_by_base:
            if len(selected) >= limit:
                break
            _add(meta)

        return selected[:limit]

    # 1) Deduplicate by (gear slots, mini set) key; keep the best base-score copy.
    best_by_key: dict[tuple[str, ...], dict] = {}
    best_score_by_key: dict[tuple[str, ...], int] = {}
    split_cache_by_key: dict[tuple[str, ...], tuple[list[dict], list[dict], tuple[str, ...]]] = {}
    for cand in candidates:
        if not isinstance(cand, dict):
            continue
        gear, minis = _split_gear_minis(cand)
        gear_names = tuple(_item_name(it) for it in gear)
        mini_key = tuple(sorted(_item_name(it) for it in minis))
        k = gear_names + mini_key
        score = _base_score(cand)
        prev_score = best_score_by_key.get(k)
        if prev_score is None or score > prev_score:
            best_by_key[k] = cand
            best_score_by_key[k] = score
            split_cache_by_key[k] = (gear, minis, mini_key)

    uniq_items = list(best_by_key.items())
    uniq = [cand for _k, cand in uniq_items]
    if len(uniq) <= limit:
        uniq.sort(key=_base_score, reverse=True)
        return uniq

    metas: list[_CandMeta] = []
    for key, cand in uniq_items:
        try:
            fg_priority = int(cand.get("_fg_priority", 0) or 0)
        except Exception:
            fg_priority = 0
        gear, minis, mini_key = split_cache_by_key.get(key, ([], [], tuple()))
        fg_proxy = _fg_proxy_from_items(
            list(gear) + list(minis), primary_color=primary_color, secondary_color=secondary_color
        )
        meta = _CandMeta(
            cand=cand,
            key=key,
            base=_base_score(cand),
            fg_proxy=fg_proxy,
            mini_key=mini_key,
            center=_center_key(cand),
            fg_priority=fg_priority,
        )
        metas.append(meta)

    if mode in {"promising_archive", "promising-archive", "promising"}:
        return _select_promising_archive(metas)
    if mode in {"slot_diverse_archive", "slot-diverse-archive", "slot_diverse", "slot-diverse"}:
        return _select_slot_diverse_archive(metas)

    # Deterministic ordering helpers
    # Avoid full sorts for very large funnels; keep deterministic tie-breakers via `m.key`.
    base_pool_k = min(len(metas), max(limit, 20000))
    metas_by_base = heapq.nlargest(base_pool_k, metas, key=_meta_base_key)
    metas_by_fg = heapq.nlargest(base_pool_k, metas, key=_meta_fg_key)

    selected: list[dict] = []
    seen_keys: set[tuple[str, ...]] = set()
    seen_minis: set[tuple[str, ...]] = set()
    seen_centers: set[tuple[int, int]] = set()

    def _add(meta: _CandMeta) -> bool:
        if meta.key in seen_keys:
            return False
        seen_keys.add(meta.key)
        selected.append(meta.cand)
        seen_minis.add(meta.mini_key)
        seen_centers.add(meta.center)
        return True

    # Hard guarantee: keep at least the top-N by base score (DB stability).
    top_base_keep = min(limit, int(LOADOUTS_PER_SONG_LIMIT))
    for meta in metas_by_base:
        if len(selected) >= top_base_keep:
            break
        _add(meta)

    # Preserve a small slice of explicitly marked FG-priority candidates.
    priority_budget = max(0, min(limit - len(selected), max(5, limit // 10)))
    if priority_budget:
        priority = [m for m in metas_by_fg if m.fg_priority]
        for meta in priority:
            if len(selected) >= (top_base_keep + priority_budget):
                break
            _add(meta)

    # Budgets: mix exploitation + FG-proxy + diversity.
    base_budget = min(limit, max(top_base_keep, int(limit * 0.55)))
    fg_budget_end = min(limit, base_budget + int(limit * 0.30))

    # 1) Fill by base score (stable exploitation).
    for meta in metas_by_base:
        if len(selected) >= base_budget:
            break
        _add(meta)

    # 2) Fill by FG proxy; prefer new FT/FF centers first.
    for meta in metas_by_fg:
        if len(selected) >= fg_budget_end:
            break
        if meta.center in seen_centers:
            continue
        _add(meta)
    for meta in metas_by_fg:
        if len(selected) >= fg_budget_end:
            break
        _add(meta)

    # 3) Mini-team diversity fill.
    for meta in metas_by_base:
        if len(selected) >= limit:
            break
        if meta.mini_key in seen_minis:
            continue
        _add(meta)

    # 4) Final fill by base score.
    for meta in metas_by_base:
        if len(selected) >= limit:
            break
        _add(meta)

    return selected[:limit]
