"""
Loadout equivalence + mini variant grouping.

This module centralizes logic for:
- Computing a song-context "effective" mini signature (ignores irrelevant element stats)
- Computing a song-context loadout hash from gear names + effective mini signatures
- Merging mini variant groups across equivalent loadouts (union variant names per effective mini)
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from typing import Any, List

from ..core.utils import safe_int
from ..gamedata import Mini, SongMini

# (primary, secondary, selected) -> (the song-mini map it was built from, signature -> names). The entry keeps
# that map alive, so the identity check can never match a different, later map.
_MINI_SIG_TO_NAMES_CACHE: dict[tuple[str, str, str], tuple[Mapping[str, Mini | SongMini], dict[tuple[Any, ...], list[str]]]] = {}


def representative_mini_names(groups: list[list[str]]) -> list[str]:
    """
    Pick a deterministic representative name per group.

    When the same mini-variant group appears multiple times (e.g., two equipped minis
    that are song-context equivalent), prefer picking distinct names across slots
    when possible so downstream displays don't show duplicate minis.
    """
    reps: list[str] = []
    used: set[str] = set()
    group_counts: dict[tuple[str, ...], int] = {}
    for g0 in groups or []:
        g = [str(x).strip() for x in (g0 or []) if x is not None]
        g = [n for n in g if n]
        if not g:
            continue

        key = tuple(g)
        seen = int(group_counts.get(key, 0) or 0)
        group_counts[key] = seen + 1

        preferred = g[seen % len(g)]
        if preferred not in used:
            choice = preferred
        else:
            choice = next((n for n in g if n not in used), preferred)

        reps.append(choice)
        used.add(choice)
    return reps


def rotate_mini_groups_for_slot_display(groups: list[list[str]]) -> list[list[str]]:
    """
    Rotate mini variant groups so the representative for each slot becomes the first element.

    Legacy DB behavior:
    - Minis are persisted as "variant groups" per equipped slot, e.g. [["A","B"], ["A","B"], ["C"]].
    - Many consumers historically treated `group[0]` as the displayed/representative mini name.
    - When a variant group repeats across slots, rotate representatives so the first elements are
      distinct when possible (A/B, A/B, C -> A/B, B/A, C).

    This preserves determinism while keeping the full variant set in each slot group.
    """

    if not groups:
        return []

    # Normalize shape: drop empties, strip strings, and keep per-group sorted unique names.
    normalized: list[list[str]] = []
    for g0 in groups:
        if not g0:
            continue
        g = [str(x).strip() for x in g0 if x is not None]
        g = [n for n in g if n]
        if not g:
            continue
        normalized.append(sorted(set(g)))

    if not normalized:
        return []

    reps = representative_mini_names(normalized)
    rotated: list[list[str]] = []
    for g, rep in zip(normalized, reps):
        if rep and rep in g and len(g) > 1:
            rotated.append([rep, *[n for n in g if n != rep]])
        else:
            rotated.append(g)

    return rotated


def effective_mini_signature(
    mini_stats: Mapping[str, int],
    primary_color: str,
    secondary_color: str,
    selected_color: str,
) -> tuple[Any, ...]:
    """
    Song-context effective signature for a single mini.

    Includes:
    - Core scoring stats: PP/CM/FM/FT/FF
    - Only elemental stats that can matter for this song context:
      primary, secondary, selected (duplicates allowed; caller may canonicalize)
    """
    pp = safe_int((mini_stats or {}).get("Perfect Points", 0), 0)
    cm = safe_int((mini_stats or {}).get("Combo Multiplier", 0), 0)
    fm = safe_int((mini_stats or {}).get("Fever Multiplier", 0), 0)
    ft = safe_int((mini_stats or {}).get("Fever Time", 0), 0)
    ff = safe_int((mini_stats or {}).get("Fever Fill Rate", 0), 0)

    p_val = safe_int((mini_stats or {}).get(primary_color, 0), 0) if primary_color else 0
    s_val = safe_int((mini_stats or {}).get(secondary_color, 0), 0) if secondary_color else 0
    sel_val = safe_int((mini_stats or {}).get(selected_color, 0), 0) if selected_color else 0

    return (pp, cm, fm, ft, ff, p_val, s_val, sel_val)


def effective_mini_signature_for_name(
    mini_name: str,
    minis_by_name: Mapping[str, Mini | SongMini],
    primary_color: str,
    secondary_color: str,
    selected_color: str,
) -> tuple[Any, ...]:
    if not mini_name:
        return ("name", "")
    mini = minis_by_name.get(mini_name)
    if mini is None:
        # Unknown mini: do not over-merge.
        return ("name", mini_name)
    return effective_mini_signature(mini.stats, primary_color, secondary_color, selected_color)


def minis_signature_to_names_map(
    minis_by_name: Mapping[str, Mini | SongMini],
    primary_color: str,
    secondary_color: str,
    selected_color: str,
) -> dict[tuple[Any, ...], list[str]]:
    """
    Build (and cache) a signature->all-names map for a given song-context.

    This lets persistence populate mini variant groups deterministically from Minis.csv
    (instead of relying on the GA to have explored both names).
    """
    key = (str(primary_color), str(secondary_color), str(selected_color))
    cached = _MINI_SIG_TO_NAMES_CACHE.get(key)
    if cached is not None and cached[0] is minis_by_name:
        return cached[1]

    sig_to_names: dict[tuple[Any, ...], list[str]] = {}
    for name, mini in minis_by_name.items():
        sig = effective_mini_signature(mini.stats, primary_color, secondary_color, selected_color)
        sig_to_names.setdefault(sig, []).append(name)

    for sig, names in list(sig_to_names.items()):
        sig_to_names[sig] = sorted(set(names))

    if len(_MINI_SIG_TO_NAMES_CACHE) >= 8:
        _MINI_SIG_TO_NAMES_CACHE.clear()
    _MINI_SIG_TO_NAMES_CACHE[key] = (minis_by_name, sig_to_names)
    return sig_to_names


def canonical_minis_groups_from_names(
    mini_names: List[str],
    minis_by_name: Mapping[str, Mini | SongMini],
    primary_color: str,
    secondary_color: str,
    selected_color: str,
    mini_sigs: List[tuple[Any, ...]] | None = None,
) -> list[list[str]]:
    """
    Deterministically expand minis into variant groups based on Minis.csv equivalence.

    For each selected mini name, we compute its effective signature under the song context,
    then expand it to all minis that share that signature in the provided Minis.csv map.
    Callers that already computed those signatures for hashing can pass `mini_sigs`.

    Multiplicity is preserved (e.g., if duplicates ever appear).
    """
    names = [str(name or "").strip() for name in mini_names or []]
    names = [name for name in names if name]
    if mini_sigs is None:
        mini_sigs = [
            effective_mini_signature_for_name(
                name,
                minis_by_name,
                primary_color,
                secondary_color,
                selected_color,
            )
            for name in names
        ]
    elif len(mini_sigs) != len(names):
        raise ValueError("mini_sigs length must match non-empty mini_names length")

    sig_counts: Counter = Counter()
    sig_rep: dict[tuple[Any, ...], str] = {}

    for n, sig in zip(names, mini_sigs):
        sig_counts[sig] += 1
        sig_rep.setdefault(sig, n)

    if not sig_counts:
        return []

    sig_to_all = minis_signature_to_names_map(minis_by_name, primary_color, secondary_color, selected_color)

    def _sig_sort_key(sig: tuple[Any, ...]) -> str:
        return "|".join(str(x) for x in sig)

    out: list[list[str]] = []
    for sig in sorted(sig_counts.keys(), key=_sig_sort_key):
        # Unknown mini names use a signature tagged with ("name", <name>); don't over-expand.
        if len(sig) >= 2 and sig[0] == "name":
            group = [str(sig[1])]
        else:
            group = sig_to_all.get(sig)
            if not group:
                group = [sig_rep.get(sig, "")]
        group = [n for n in group if n]
        if not group:
            continue
        for _ in range(int(sig_counts[sig] or 0)):
            out.append(group)
    return out


def effective_loadout_hash_from_names(
    gear_names: List[str],
    mini_sigs: List[tuple[Any, ...]],
) -> str:
    from ..helpers.song_helpers.loadout_hashing import (
        effective_loadout_hash_from_names as _impl,
    )

    return _impl(gear_names, mini_sigs)
