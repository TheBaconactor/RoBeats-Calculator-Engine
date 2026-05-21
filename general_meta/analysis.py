from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from gear_optimizer.core.gem_defs import extract_gem_totals
from gear_optimizer.data.loadout_equivalence import representative_mini_names
from gear_optimizer.core.utils import safe_int as _safe_int

_ELEMENT_ORDER: Tuple[str, ...] = ("Chill", "Flow", "Rush", "Beat", "Vibe")


def _effective_score(loadout: dict) -> int:
    """
    Return the score GeneralMeta should use for ranking.

    When ForceGreats is enabled, `fg_score` can exceed the base `score` for the
    same gear+mini set. GeneralMeta should treat the best achievable score as
    the max of these fields.
    """
    score = int(loadout.get("score") or 0)
    fg_score = int(loadout.get("fg_score") or 0)
    return max(score, fg_score)


def _loadout_key_fingerprint(gears: tuple[str, ...], mini_sig: tuple[Any, ...]) -> str:
    """
    Return a stable, category-aware fingerprint for a (gear set + mini effect signature).

    This is used to cheaply compare category winners across TeamBuff tiers without
    being sensitive to representative mini-name choice.
    """
    payload = json.dumps([list(gears), list(mini_sig)], separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def _relevant_elements_for_category(songs: List[dict]) -> Tuple[str, ...]:
    """
    Determine which element stats can affect scoring for this category.

    Returns the union of all primary/secondary elements present in the provided songs.
    """
    elements = set()
    for song in songs:
        primary = (song.get("primary") or "").strip()
        secondary = (song.get("secondary") or "").strip()
        if primary:
            elements.add(primary)
        if secondary:
            elements.add(secondary)

    order = {name: idx for idx, name in enumerate(_ELEMENT_ORDER)}
    return tuple(sorted(elements, key=lambda el: order.get(el, 999)))


def _mini_set_effect_signature(
    mini_names: Tuple[str, ...],
    minis_by_name: Dict[str, dict],
    relevant_elements: Tuple[str, ...],
) -> Tuple[Any, ...]:
    """
    Build a category-aware signature for a mini set.

    This allows GeneralMeta to merge mini variants that differ only in stats that
    cannot affect scoring for the current category (e.g., extra Rush in a Vibe/Vibe category).
    """
    if not mini_names:
        return ("stats", 0, 0, 0, 0, 0, *([0] * len(relevant_elements)))

    for name in mini_names:
        if name not in minis_by_name:
            return ("names", mini_names)

    pp = cm = fm = ft = ff = 0
    elem_totals = [0] * len(relevant_elements)

    for name in mini_names:
        m = minis_by_name.get(name) or {}
        pp += int(m.get("Perfect Points", 0) or 0)
        cm += int(m.get("Combo Multiplier", 0) or 0)
        fm += int(m.get("Fever Multiplier", 0) or 0)
        ft += int(m.get("Fever Time", 0) or 0)
        ff += int(m.get("Fever Fill Rate", 0) or 0)
        for idx, el in enumerate(relevant_elements):
            elem_totals[idx] += int(m.get(el, 0) or 0)

    return ("stats", pp, cm, fm, ft, ff, *elem_totals)


def _pick_representative_variant(variants: Counter) -> Tuple[Any, ...]:
    """
    Pick a deterministic representative from a Counter of name-tuples.

    - Prefer the most frequent variant.
    - Break ties lexicographically for determinism.
    """
    if not variants:
        return ()
    max_count = max(variants.values())
    tied = [variant for variant, count in variants.items() if count == max_count]
    return min(tied)

def _row_mode(row: dict) -> str:
    return "fg" if _safe_int(row.get("fg_score")) > _safe_int(row.get("score")) else "meta"


def _row_mode_score(row: dict, mode: str) -> int:
    return _safe_int(row.get("fg_score" if mode == "fg" else "score"))


def _rank_index_for_song_mode(rows: list[dict], target: dict, mode: str) -> int | None:
    ranked = [
        row
        for row in rows
        if _row_mode_score(row, mode) > 0
        and (mode != "fg" or _safe_int(row.get("fg_score")) > _safe_int(row.get("score")))
    ]
    ranked.sort(
        key=lambda row: (
            -_row_mode_score(row, mode),
            str(row.get("loadout_hash") or ""),
            tuple(str(v or "") for v in (row.get("gear") or [])),
            tuple(tuple(str(v or "") for v in group) for group in (row.get("mini_groups") or [])),
        )
    )

    target_hash = str(target.get("loadout_hash") or "").strip()
    for idx, row in enumerate(ranked):
        if target_hash and str(row.get("loadout_hash") or "").strip() == target_hash:
            return idx
        if row is target:
            return idx
    return None


def _song_win_entry(row: dict, *, mode: str, rank_index: int | None, team_buff: str | None = None) -> dict:
    song_name = str(row.get("song_name") or "").strip()
    loadout_hash = str(row.get("loadout_hash") or "").strip()
    score = _row_mode_score(row, mode)
    out = {
        "song_id": song_name,
        "song_name": song_name,
        "mode": mode,
        "score": score,
        "base_score": _safe_int(row.get("score")),
        "fg_score": _safe_int(row.get("fg_score")),
    }
    if team_buff:
        out["team_buff"] = str(team_buff)
    if loadout_hash:
        out["loadout_hash"] = loadout_hash
    if rank_index is not None:
        out["rank_index"] = int(rank_index)
        out["rank"] = int(rank_index) + 1
    return out


def _minis_keys_from_groups(mini_groups: object) -> tuple[tuple[str, ...], tuple[tuple[str, ...], ...]]:
    """
    Convert decoded mini variant groups into:
    - representative mini names (sorted; multiplicity preserved)
    - a canonical "variant key" that preserves per-slot variant groups
    """
    groups: list[list[str]] = []
    if isinstance(mini_groups, list):
        for g0 in mini_groups:
            if not isinstance(g0, list):
                continue
            names = [str(n).strip() for n in g0 if n]
            names = sorted(set([n for n in names if n]))
            if names:
                groups.append(names)

    reps = representative_mini_names(groups)
    rep_key = tuple(sorted([n for n in reps if n]))
    variant_key = tuple(sorted(tuple(g) for g in groups))
    return rep_key, variant_key


def _groups_from_variant_key(variant_key: tuple[tuple[str, ...], ...]) -> list[list[str]]:
    return [list(g) for g in (variant_key or ())]


def find_most_common_loadout(
    songs: List[dict],
    all_loadouts: List[dict],
    minis_by_name: Dict[str, dict],
    top_n: Optional[int] = 1,
    *,
    loadouts_by_song: Optional[Dict[str, list]] = None,
    gears_by_name: Optional[Dict[str, dict]] = None,
) -> List[dict]:
    """
    Find the most frequently appearing gear+mini SETs for songs in this category.
    Then look up existing DB entries that use each SET to get pre-optimized gems.
    """
    song_names = {s["song_name"] for s in songs}
    relevant_elements = _relevant_elements_for_category(songs)

    if loadouts_by_song is None:
        loadouts_by_song = {}
        for loadout in all_loadouts:
            name = loadout["song_name"]
            if name in song_names:
                loadouts_by_song.setdefault(name, []).append(loadout)

    wins: Counter = Counter()
    loadout_rows: Dict[Tuple[Any, ...], List[dict]] = {}
    mini_variants: Dict[Tuple[Any, ...], Counter] = {}
    song_win_rows: Dict[Tuple[Any, ...], List[dict]] = {}

    for song_name in song_names:
        loadouts = (loadouts_by_song or {}).get(song_name, [])
        if not loadouts:
            continue

        best = max(loadouts, key=_effective_score)
        mode = _row_mode(best)
        gears = list(best.get("gear") or [])
        rep_names, variant_key = _minis_keys_from_groups(best.get("mini_groups"))
        sig = _mini_set_effect_signature(rep_names, minis_by_name, relevant_elements)

        if gears_by_name:
            ordered_gears = sort_gears_by_slot(list(gears), gears_by_name)
        else:
            ordered_gears = sorted(gears)
        loadout_key = (tuple(ordered_gears), sig)
        wins[loadout_key] += 1
        loadout_rows.setdefault(loadout_key, []).append(best)
        mini_variants.setdefault(loadout_key, Counter())[variant_key] += 1
        song_win_rows.setdefault(loadout_key, []).append(
            _song_win_entry(
                best,
                mode=mode,
                rank_index=_rank_index_for_song_mode(loadouts, best, mode),
                team_buff=str(best.get("team_buff") or "").strip() or None,
            )
        )

    if not wins:
        return []

    ranked = sorted(wins.items(), key=lambda kv: (-kv[1], kv[0]))

    results: List[dict] = []
    for idx, (key, count) in enumerate(ranked):
        if top_n is not None and idx >= int(top_n):
            break
        gears, _sig = key
        loadout_key = _loadout_key_fingerprint(tuple(gears), tuple(_sig))
        rows = loadout_rows.get(key, [])
        peak_in_songs_meta = sorted(
            {
                str(r.get("song_name") or "")
                for r in rows
                if (r.get("song_name") or "").strip() and int(r.get("score") or 0) >= int(r.get("fg_score") or 0)
            }
        )
        peak_in_songs_fg = sorted(
            {
                str(r.get("song_name") or "")
                for r in rows
                if (r.get("song_name") or "").strip() and int(r.get("fg_score") or 0) > int(r.get("score") or 0)
            }
        )
        peak_in_songs = sorted(set(peak_in_songs_meta) | set(peak_in_songs_fg))
        song_wins = sorted(
            song_win_rows.get(key) or [],
            key=lambda item: (str(item.get("song_name") or ""), str(item.get("mode") or "")),
        )

        # Representative mini variant (preserves per-mini group variants).
        variants = mini_variants.get(key) or Counter()
        chosen_variant = _pick_representative_variant(variants)
        gem_sums = {"PP": 0, "CM": 0, "FM": 0, "FT": 0, "FF": 0, "Element": 0}
        avg_score = 0
        for row in rows:
            avg_score += int(_effective_score(row))
            try:
                details = json.loads(row.get("details_json") or "{}")
            except Exception:
                details = {}
            totals = extract_gem_totals(details)
            gem_sums["PP"] += int(totals.pp)
            gem_sums["CM"] += int(totals.cm)
            gem_sums["FM"] += int(totals.fm)
            gem_sums["FT"] += int(totals.ft)
            gem_sums["FF"] += int(totals.ff)
            gem_sums["Element"] += int(totals.element)

        denom = max(1, len(rows))
        avg_score = int(avg_score / denom)
        if sum(int(v) for v in gem_sums.values()) <= 0:
            avg_gems = {k: 0 for k in gem_sums}
        else:
            avg_gems = _round_mean_gems_to_total(gem_sums, denom, total=90)

        results.append(
            {
                "rank": idx + 1,
                "loadout_key": loadout_key,
                "gear_names": list(gears),
                "mini_groups": _groups_from_variant_key(tuple(chosen_variant) if chosen_variant else ()),
                "peak_in_songs": peak_in_songs,
                "peak_in_songs_meta": peak_in_songs_meta,
                "peak_in_songs_fg": peak_in_songs_fg,
                "song_wins": song_wins,
                "songs_with_set": len(rows),
                "win_frequency": count,
                "avg_score": avg_score,
                "avg_gems": avg_gems,
            }
        )

    return results


def sort_gears_by_slot(gear_names: List[str], gears_by_name: Dict[str, dict]) -> List[str]:
    slot_order = {
        "Hat": 0,
        "Neck": 1,
        "Face": 2,
        "Shirt": 3,
        "Back": 4,
        "Pants": 5,
        "Pant": 5,
    }

    def get_slot_index(gear_name: str) -> int:
        gear = gears_by_name.get(gear_name) or {}
        slot = str(gear.get("Slot") or "")
        for prefix, idx in slot_order.items():
            if slot.startswith(prefix):
                return idx
        return 99

    return sorted(gear_names, key=get_slot_index)


def _round_mean_gems_to_total(gem_sums: Dict[str, int], denom: int, *, total: int) -> Dict[str, int]:
    """
    Convert per-field gem sums into an integer mean allocation that always sums to `total`.

    This uses a largest-remainder style allocation so that:
    - the vector is as close as possible to the true mean,
    - the sum is exact (no 89/91 gem artifacts from independent rounding).
    """
    denom = max(1, int(denom))
    keys = ("PP", "CM", "FM", "FT", "FF", "Element")

    means: Dict[str, float] = {k: float(int(gem_sums.get(k, 0) or 0)) / denom for k in keys}
    floors: Dict[str, int] = {k: int(math.floor(means[k])) for k in keys}

    current_total = sum(floors.values())
    remaining = int(total) - current_total
    if remaining == 0:
        return floors

    def sort_key_for_add(k: str) -> tuple[float, float, int]:
        frac = means[k] - floors[k]
        return (frac, means[k], keys.index(k))

    def sort_key_for_sub(k: str) -> tuple[float, float, int]:
        frac = means[k] - floors[k]
        # Prefer subtracting from smallest fractional part / smallest mean, while staying >= 0.
        return (frac, means[k], keys.index(k))

    if remaining > 0:
        order = sorted(keys, key=sort_key_for_add, reverse=True)
        for k in order:
            if remaining <= 0:
                break
            floors[k] += 1
            remaining -= 1
    else:
        order = sorted(keys, key=sort_key_for_sub)
        for k in order:
            if remaining >= 0:
                break
            if floors[k] <= 0:
                continue
            floors[k] -= 1
            remaining += 1

    # If float error or weird inputs leave us off by a few, repair deterministically.
    if remaining != 0:
        repair_keys = list(keys)
        i = 0
        while remaining != 0 and i < 10_000:
            k = repair_keys[i % len(repair_keys)]
            if remaining > 0:
                floors[k] += 1
                remaining -= 1
            else:
                if floors[k] > 0:
                    floors[k] -= 1
                    remaining += 1
            i += 1

    return floors


def format_gem_counts(avg_gems: Dict[str, int]) -> Dict[str, int]:
    return {
        "Perfect Points": int(avg_gems.get("PP", 0) or 0),
        "Combo Multiplier": int(avg_gems.get("CM", 0) or 0),
        "Fever Multiplier": int(avg_gems.get("FM", 0) or 0),
        "Fever Time": int(avg_gems.get("FT", 0) or 0),
        "Fever Fill Rate": int(avg_gems.get("FF", 0) or 0),
        "Element": int(avg_gems.get("Element", 0) or 0),
    }


__all__ = [
    "find_most_common_loadout",
    "format_gem_counts",
    "sort_gears_by_slot",
]
