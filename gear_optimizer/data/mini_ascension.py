from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence
import math

from gear_optimizer.core.gem_defs import ELEMENT_STAT_KEYS, GemKey
from gear_optimizer.core.utils import safe_int

MINI_ASCENSION_MAX_LEVEL = 10
MINI_ASCENSION_BASE_PP_PER_LEVEL = 2
MINI_ASCENSION_ELEMENTAL_SCALE_PER_LEVEL = 0.5
MINI_ASCENSION_CACHE_VERSION = "mini-ascension-v2"
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
    """Compute Mini Ascension elemental bonuses.

    The decompiled PetUtils path scales each ranked base Mini color by ``ascension * 0.5``. The
    normal optimizer color stats are max-level values, so generated CSV rows also carry the base/L1
    color stats used by Mini Ascension. The final destination distribution is intentionally routed
    through ``_provisional_export_distribution`` because that insertion path remains
    decompiler-noisy pending stronger evidence.
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

    scale = float(level) * float(MINI_ASCENSION_ELEMENTAL_SCALE_PER_LEVEL)
    budget = 0
    quality_rows: list[tuple[str, bool, float, str, int]] = []
    for index, (pet_color, pet_value) in enumerate(ranked_mini_ascension_colors(mini)[:2]):
        is_primary = index == 0
        quality = mini_ascension_match_quality(
            pet_color,
            is_pet_primary=is_primary,
            song_primary_color=primary,
            song_secondary_color=secondary,
        )
        amount = int(math.floor(float(pet_value) * scale))
        if amount <= 0:
            continue
        budget += amount
        quality_rows.append((pet_color, bool(is_primary), float(quality), "Element Budget", amount))
    bonus = _provisional_export_distribution(
        budget=budget,
        song_primary_color=primary,
        song_secondary_color=secondary,
    )
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
    out[GemKey.PP.value] = safe_int(out.get(GemKey.PP.value), 0) + mini_ascension_base_perfect_points(level)

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
