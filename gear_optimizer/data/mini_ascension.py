from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence
import math

from gear_optimizer.core.gem_defs import ELEMENT_STAT_KEYS, GemKey
from gear_optimizer.core.utils import safe_int

MINI_ASCENSION_MAX_LEVEL = 10
MINI_ASCENSION_BASE_PP_PER_LEVEL = 2
# Universal-pool per-level scale (Component 1). The additive positional match extra (Component 2)
# uses max(quality - 0.5, 0) -> 0.5 same-position / 0.25 cross / 0 no-match. See issue #127/#117.
MINI_ASCENSION_ELEMENTAL_SCALE_PER_LEVEL = 0.5
MINI_ASCENSION_CACHE_VERSION = "mini-ascension-v4"
MINI_ASCENSION_DISABLED_CACHE_KEY = ("mini-ascension-disabled",)
MINI_ASCENSION_BASE_STAT_PREFIX = "Mini Ascension Base "

MINI_ASCENSION_METADATA_KEYS = frozenset(
    {
        "Song Target",
        "Mini Ascension Enabled",
        "Mini Ascension Level",
        "Mini Ascension Source Version",
        "Mini Ascension Song Target Applied",
        "Mini Ascension Elemental Bonus",
        "Mini Ascension Match Qualities",
        "Mini Ascension Materialized",
        "Mini Ascension Materialized Song",
        "Mini Ascension Materialized Primary Color",
        "Mini Ascension Materialized Secondary Color",
        "Mini Ascension Base Chill",
        "Mini Ascension Base Flow",
        "Mini Ascension Base Rush",
        "Mini Ascension Base Beat",
        "Mini Ascension Base Vibe",
    }
)

_RANKED_COLOR_ORDER: tuple[str, ...] = ("Chill", "Vibe", "Beat", "Flow", "Rush")
_ELEMENT_STAT_SET = frozenset(ELEMENT_STAT_KEYS)


@dataclass(frozen=True, slots=True)
class MiniAscensionSongContext:
    enabled: bool
    song_name: str
    primary_color: str
    secondary_color: str
    applied_mini_names: tuple[str, ...]
    cache_key: tuple[Any, ...]


def mini_ascension_base_perfect_points(ascension_level: int = MINI_ASCENSION_MAX_LEVEL) -> int:
    level = max(0, min(MINI_ASCENSION_MAX_LEVEL, safe_int(ascension_level, MINI_ASCENSION_MAX_LEVEL)))
    return int(MINI_ASCENSION_BASE_PP_PER_LEVEL * level)


def mini_ascension_base_perfect_points_for_mini(mini: Mapping[str, Any]) -> int:
    """Return the unconditional ascension PP contribution for one raw mini row.

    Materialized rows already contain this contribution in ``Perfect Points`` and are
    rejected so callers cannot add it twice.
    """
    if bool((mini or {}).get("Mini Ascension Materialized")):
        raise ValueError("Mini ascension base PP must be derived from an unmaterialized mini row")
    if not mini_ascension_enabled(mini):
        return 0
    return mini_ascension_base_perfect_points(
        safe_int((mini or {}).get("Mini Ascension Level"), MINI_ASCENSION_MAX_LEVEL)
    )


def normalize_song_secondary(primary_color: object, secondary_color: object) -> str:
    primary = str(primary_color or "").strip()
    secondary = str(secondary_color or "").strip()
    if not secondary or secondary == primary:
        return ""
    return secondary


def mini_ascension_match_quality(
    pet_color: str,
    *,
    is_pet_primary: bool,
    song_primary_color: str,
    song_secondary_color: str,
) -> float:
    pet = str(pet_color or "").strip()
    primary = str(song_primary_color or "").strip()
    secondary = normalize_song_secondary(primary, song_secondary_color)
    if pet == primary:
        return 1.0 if bool(is_pet_primary) else 0.75
    if secondary and pet == secondary:
        return 0.75 if bool(is_pet_primary) else 1.0
    return 0.5


def mini_ascension_enabled(mini: Mapping[str, Any]) -> bool:
    return bool((mini or {}).get("Mini Ascension Enabled"))


def mini_song_target_active(mini: Mapping[str, Any], song_name: str) -> bool:
    target = (mini or {}).get("Song Target")
    if not target:
        return False
    song = str(song_name or "").strip()
    if not song:
        return False
    if isinstance(target, str):
        return target.strip() == song
    if not isinstance(target, Sequence):
        return False
    for item in target:
        if str(item or "").strip() == song:
            return True
    return False


def ranked_mini_colors(mini: Mapping[str, Any]) -> tuple[tuple[str, int], ...]:
    return _ranked_color_values(mini, use_ascension_base_stats=False)


def ranked_mini_ascension_colors(mini: Mapping[str, Any]) -> tuple[tuple[str, int], ...]:
    return _ranked_color_values(mini, use_ascension_base_stats=True)


def _ranked_color_values(
    mini: Mapping[str, Any],
    *,
    use_ascension_base_stats: bool,
) -> tuple[tuple[str, int], ...]:
    ranked: list[tuple[str, int, int]] = []
    for order, color in enumerate(_RANKED_COLOR_ORDER):
        if use_ascension_base_stats:
            base_key = f"{MINI_ASCENSION_BASE_STAT_PREFIX}{color}"
            raw_value = (mini or {}).get(base_key, (mini or {}).get(color, 0))
        else:
            raw_value = (mini or {}).get(color, 0)
        value = safe_int(raw_value, 0)
        if value > 0:
            ranked.append((color, value, order))
    ranked.sort(key=lambda item: (-int(item[1]), int(item[2])))
    return tuple((color, value) for color, value, _order in ranked)


def _provisional_export_distribution(
    *,
    budget: int,
    song_primary_color: str,
    song_secondary_color: str,
) -> dict[str, int]:
    """Return the current isolated export-audit interpretation for elemental insertion.

    The decompiled final insertion path accumulates a raw base-stat ascension budget, then inserts
    it into the song primary for one-color songs or splits it 2:1 across primary/secondary. Keep
    this distribution rule isolated because that final block is decompiler-noisy.
    """
    amount = max(0, int(budget))
    if amount <= 0:
        return {}
    primary = str(song_primary_color or "").strip()
    secondary = normalize_song_secondary(song_primary_color, song_secondary_color)
    if secondary:
        return {
            primary: int(math.floor((amount * 2) / 3)),
            secondary: int(math.floor(amount / 3)),
        }
    return {primary: amount}


def mini_ascension_elemental_bonus(
    mini: Mapping[str, Any],
    *,
    song_primary_color: str,
    song_secondary_color: str,
    ascension_level: int = MINI_ASCENSION_MAX_LEVEL,
) -> tuple[dict[str, int], tuple[tuple[str, bool, float, str, int], ...]]:
    """Compute Mini Ascension elemental bonuses (canonical two-component model, issue #127/#117).

    The in-game helper ``pet_id_song_color_list_get_element_statsdict`` adds two components:
    (1) a universal song-element pool ``floor(A * rawStat * 0.5)`` per ranked L1 Mini color,
    distributed ``2/3 + 1/3`` (two-color) or fully to the primary (one-color); and (2) an additive
    positional match extra routed to the matched song element -- ``floor(A * rawStat * 0.5)`` for a
    same-position match, ``floor(A * rawStat * 0.25)`` for a cross-position match, ``0`` otherwise.
    Ranked colors use the base/L1 stats (the normal optimizer color stats are max-level values, so
    generated CSV rows also carry the base/L1 columns). Verified against the in-game readings
    (Zara/Canon +62 at A5, +125 at A10; Monstercat own Chill/Flow +131/+68 at A10).
    """
    primary = str(song_primary_color or "").strip()
    if primary not in _ELEMENT_STAT_SET:
        raise ValueError(f"Mini ascension song primary color must be one of {sorted(_ELEMENT_STAT_SET)}, got {primary!r}")
    secondary = normalize_song_secondary(primary, song_secondary_color)
    if secondary and secondary not in _ELEMENT_STAT_SET:
        raise ValueError(
            f"Mini ascension song secondary color must be one of {sorted(_ELEMENT_STAT_SET)}, got {secondary!r}"
        )

    level = max(0, min(MINI_ASCENSION_MAX_LEVEL, safe_int(ascension_level, MINI_ASCENSION_MAX_LEVEL)))
    if level <= 0:
        return {}, ()

    # Issue #127/#117 (canonical, owner ZIP re-audit): the in-game helper adds TWO components.
    #   1) Universal pool (quality-INDEPENDENT): floor(A * rawStat * 0.5) per Mini color, each
    #      floored then summed, then distributed to the song 2/3+1/3 (two-color) or all-to-primary.
    #   2) Additive positional match extra, routed to the SONG element the Mini color matched:
    #        same-position match -> floor(A * rawStat * 0.5)
    #        cross-position match -> floor(A * rawStat * 0.25)   (= max(quality - 0.5, 0) * A * rawStat)
    #        no match            -> 0
    # Final bonus = pooled destination + positional extras. Verified: Zara/Canon +62 (A5) / +125 (A10),
    # Monstercat own Chill/Flow +131/+68 (A10). Earlier builds pooled a quality-WEIGHTED budget and
    # omitted component 2 entirely -- both wrong.
    scale = float(level) * float(MINI_ASCENSION_ELEMENTAL_SCALE_PER_LEVEL)  # A * 0.5
    pool = 0
    match_extras: dict[str, int] = {}
    quality_rows: list[tuple[str, bool, float, int, int]] = []
    for index, (pet_color, pet_value) in enumerate(ranked_mini_ascension_colors(mini)[:2]):
        is_primary = index == 0
        # Component 1: universal pooled base contribution (floored per color, before summing).
        base = int(math.floor(float(pet_value) * scale))
        if base > 0:
            pool += base
        # Component 2: positional match extra, floored per color, routed to the matched song element.
        quality = mini_ascension_match_quality(
            pet_color,
            is_pet_primary=is_primary,
            song_primary_color=primary,
            song_secondary_color=secondary,
        )
        extra_mult = max(float(quality) - 0.5, 0.0)  # 0.5 same-position, 0.25 cross, 0 no-match
        extra = int(math.floor(float(pet_value) * float(level) * extra_mult)) if extra_mult > 0.0 else 0
        if extra > 0:
            if pet_color == primary:
                match_extras[primary] = match_extras.get(primary, 0) + extra
            elif secondary and pet_color == secondary:
                match_extras[secondary] = match_extras.get(secondary, 0) + extra
            else:
                extra = 0
        quality_rows.append((pet_color, bool(is_primary), float(quality), int(base), int(extra)))
    bonus = dict(
        _provisional_export_distribution(
            budget=pool,
            song_primary_color=primary,
            song_secondary_color=secondary,
        )
    )
    for element, extra in match_extras.items():
        if extra > 0:
            bonus[element] = int(bonus.get(element, 0)) + int(extra)
    return bonus, tuple(quality_rows)


def materialize_mini_for_song(
    mini: Mapping[str, Any],
    *,
    song_name: str,
    primary_color: str,
    secondary_color: str,
) -> dict[str, Any]:
    if not isinstance(mini, Mapping):
        raise TypeError("materialize_mini_for_song expects a mini stats mapping")
    if not mini_ascension_enabled(mini):
        return dict(mini)
    song = str(song_name or "").strip()
    primary = str(primary_color or "").strip()
    secondary = normalize_song_secondary(primary, secondary_color)
    if bool(mini.get("Mini Ascension Materialized")):
        existing_song = str(mini.get("Mini Ascension Materialized Song") or "").strip()
        existing_primary = str(mini.get("Mini Ascension Materialized Primary Color") or "").strip()
        existing_secondary = str(mini.get("Mini Ascension Materialized Secondary Color") or "").strip()
        if existing_song == song and existing_primary == primary and existing_secondary == secondary:
            return dict(mini)
        raise ValueError(
            "Mini ascension stats were already materialized for a different song context: "
            f"{existing_song!r}/{existing_primary!r}/{existing_secondary!r} -> "
            f"{song!r}/{primary!r}/{secondary!r}"
        )

    level = safe_int(mini.get("Mini Ascension Level"), MINI_ASCENSION_MAX_LEVEL)
    level = max(0, min(MINI_ASCENSION_MAX_LEVEL, level))
    out = dict(mini)
    out["Mini Ascension Materialized"] = True
    out["Mini Ascension Source Version"] = MINI_ASCENSION_CACHE_VERSION
    out["Mini Ascension Materialized Song"] = song
    out["Mini Ascension Materialized Primary Color"] = primary
    out["Mini Ascension Materialized Secondary Color"] = secondary
    out[GemKey.PP.value] = safe_int(out.get(GemKey.PP.value), 0) + mini_ascension_base_perfect_points_for_mini(mini)

    applies = mini_song_target_active(mini, song)
    out["Mini Ascension Song Target Applied"] = bool(applies)
    if not applies:
        return out

    bonus, qualities = mini_ascension_elemental_bonus(
        mini,
        song_primary_color=primary_color,
        song_secondary_color=secondary_color,
        ascension_level=level,
    )
    for key, value in bonus.items():
        out[key] = safe_int(out.get(key), 0) + int(value)
    out["Mini Ascension Elemental Bonus"] = dict(bonus)
    out["Mini Ascension Match Qualities"] = list(qualities)
    return out


def materialize_minis_for_song(
    all_minis: Sequence[Mapping[str, Any]] | None = None,
    *,
    minis_by_name: Mapping[str, Mapping[str, Any]] | None = None,
    calc_song: Mapping[str, Any] | None = None,
    song_name: str | None = None,
    primary_color: str | None = None,
    secondary_color: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], MiniAscensionSongContext]:
    source_minis = list(all_minis or [])
    if not source_minis and minis_by_name:
        source_minis = list(minis_by_name.values())

    metadata = (calc_song or {}).get("metadata", {}) if isinstance(calc_song, Mapping) else {}
    if not isinstance(metadata, Mapping):
        metadata = {}
    song = str(song_name or metadata.get("Song Name") or metadata.get("Song") or "").strip()
    primary = str(primary_color if primary_color is not None else metadata.get("Primary Color", "") or "").strip()
    secondary = str(
        secondary_color if secondary_color is not None else metadata.get("Secondary Color", "") or ""
    ).strip()
    normalized_secondary = normalize_song_secondary(primary, secondary)

    enabled = any(mini_ascension_enabled(mini) for mini in source_minis if isinstance(mini, Mapping))
    if not enabled:
        out = [dict(mini) for mini in source_minis if isinstance(mini, Mapping)]
        by_name = {str(mini.get("Name") or ""): mini for mini in out if str(mini.get("Name") or "").strip()}
        context = MiniAscensionSongContext(
            enabled=False,
            song_name=song,
            primary_color=primary,
            secondary_color=normalized_secondary,
            applied_mini_names=(),
            cache_key=MINI_ASCENSION_DISABLED_CACHE_KEY,
        )
        return out, by_name, context

    if not song:
        raise ValueError("Mini ascension materialization requires a non-empty song name")

    active_targets = [
        str(mini.get("Name") or "").strip()
        for mini in source_minis
        if isinstance(mini, Mapping) and mini_ascension_enabled(mini) and mini_song_target_active(mini, song)
    ]
    if active_targets and primary not in _ELEMENT_STAT_SET:
        raise ValueError(
            f"Mini ascension target song {song!r} requires a valid primary color, got {primary!r}"
        )

    out: list[dict[str, Any]] = []
    applied: list[str] = []
    for mini in source_minis:
        if not isinstance(mini, Mapping):
            continue
        materialized = materialize_mini_for_song(
            mini,
            song_name=song,
            primary_color=primary,
            secondary_color=normalized_secondary,
        )
        if bool(materialized.get("Mini Ascension Song Target Applied")):
            name = str(materialized.get("Name") or "").strip()
            if name:
                applied.append(name)
        out.append(materialized)

    by_name = {str(mini.get("Name") or ""): mini for mini in out if str(mini.get("Name") or "").strip()}
    applied_tuple = tuple(sorted(set(applied)))
    context = MiniAscensionSongContext(
        enabled=True,
        song_name=song,
        primary_color=primary,
        secondary_color=normalized_secondary,
        applied_mini_names=applied_tuple,
        cache_key=(MINI_ASCENSION_CACHE_VERSION, applied_tuple),
    )
    return out, by_name, context
