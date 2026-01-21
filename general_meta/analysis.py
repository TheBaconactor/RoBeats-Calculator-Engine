from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from gear_optimizer.data.loadout_equivalence import decode_minis_json, representative_mini_names

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

    - For (Primary, Secondary) combo categories, this will be {Primary, Secondary}.
    - For Primary/All categories (where secondary varies), this will be {Primary} U {all secondaries present}.
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


def _decode_db_minis(minis_json_blob: Optional[str]) -> tuple[tuple[str, ...], tuple[tuple[str, ...], ...]]:
    """
    Decode DB minis_json into:
    - representative mini names (sorted; multiplicity preserved)
    - a canonical "variant key" that preserves per-mini variant groups

    Supports both:
    - legacy `["MiniA","MiniB"]`
    - new `[[\"MiniA\",\"MiniA2\"],[\"MiniB\"]]`
    """
    groups = decode_minis_json(minis_json_blob)
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

    for song_name in song_names:
        loadouts = (loadouts_by_song or {}).get(song_name, [])
        if not loadouts:
            continue

        best = max(loadouts, key=_effective_score)
        try:
            gears = json.loads(best.get("gear_json") or "[]")
        except Exception:
            gears = []

        rep_names, variant_key = _decode_db_minis(best.get("minis_json"))
        sig = _mini_set_effect_signature(rep_names, minis_by_name, relevant_elements)

        loadout_key = (tuple(sorted(gears)), sig)
        wins[loadout_key] += 1
        loadout_rows.setdefault(loadout_key, []).append(best)
        mini_variants.setdefault(loadout_key, Counter())[variant_key] += 1

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
        peak_in_songs = sorted({str(r.get("song_name") or "") for r in rows if (r.get("song_name") or "").strip()})

        # Representative mini variant (preserves per-mini group variants).
        variants = mini_variants.get(key) or Counter()
        chosen_variant = _pick_representative_variant(variants)

        avg_gems = {"PP": 0, "CM": 0, "FM": 0, "FT": 0, "FF": 0, "Element": 0}
        avg_score = 0
        for row in rows:
            avg_score += int(_effective_score(row))
            try:
                details = json.loads(row.get("details_json") or "{}")
            except Exception:
                details = {}
            gems = details.get("GemCounts") or {}
            avg_gems["PP"] += int(gems.get("Perfect Points", 0) or 0)
            avg_gems["CM"] += int(gems.get("Combo Multiplier", 0) or 0)
            avg_gems["FM"] += int(gems.get("Fever Multiplier", 0) or 0)
            avg_gems["FT"] += int(details.get("FT", 0) or 0)
            avg_gems["FF"] += int(details.get("FF", 0) or 0)
            avg_gems["Element"] += int(gems.get("Element", 0) or 0)

        denom = max(1, len(rows))
        avg_score = int(avg_score / denom)
        for k in list(avg_gems.keys()):
            avg_gems[k] = int(round(avg_gems[k] / denom))

        results.append(
            {
                "rank": idx + 1,
                "loadout_key": loadout_key,
                "gear_names": list(gears),
                "minis_json": _groups_from_variant_key(tuple(chosen_variant) if chosen_variant else ()),
                "peak_in_songs": peak_in_songs,
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
