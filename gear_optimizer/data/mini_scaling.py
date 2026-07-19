"""PetUtils level/rank scaling law for the reverse score engine.

Owns the decompiled ``PetUtils.petid_level_rank_apply_statsdict`` math that turns
a mini's L1/rank-1 base + color stat modifier objects (from ``PetInfo/*.lua``)
into the statsdict contribution at an arbitrary ``(level, rank)`` state. The
production forward optimizer never needed this because it only ever sees maxed
minis; the reverse engine needs it because real leaderboard rows carry unmaxed
minis.

Reference: ``Pets/PetUtils.lua`` (decompiled). The law is
- rank multiplies base mods by ``rank``;
- level scales color mods by ``lerp(1.0 at level 1 -> 5.0 at level 50)``,
  floored per-entry (``PetRankUpEnabled == true`` -> floor());
- level is clamped to ``[PET_MIN_LEVEL, pet_rank_to_max_level(rank)]``.

This module is the level/rank scaling that runs BEFORE
``gear_optimizer.data.mini_ascension`` (which owns ascension 0..10 +
song-target materialization). It does NOT redefine any production constant:
``GEM_SCALE_*`` / ``ELEMENTAL_GEM_SCALE`` live in
``gear_optimizer.core.constants`` and team-buff math lives in
``gear_optimizer.core.team_buff``.

Decompiled ground truth:
- PetInfo root: ``ReplicatedStorage/Pets/PetInfo/`` (one folder per pet, each
  containing ``Pet<Name>.lua``).
- v1 reference parser: ``reverse_score/webport_extract.py:108-147``.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

from gear_optimizer.core.utils import safe_int

PET_MIN_LEVEL: int = 1
PET_MAX_LEVEL: int = 50
PET_MIN_RANK: int = 1
PET_MAX_RANK: int = 4
PET_RANK_TO_MAX_LEVEL: dict[int, int] = {1: 20, 2: 30, 3: 40, 4: 50}

# Decompiled GearStats type name -> optimizer canonical stat key. This is the
# game-model surface the forward optimizer does not model, so it is owned here
# rather than redefined from the private ``_ELEMENT_FROM_STATS`` in
# ``exported_game_data_sync``. Keep in sync with the decompiled
# ``Avatar/GearStats.lua`` ``Type`` enum.
GAME_TYPE_TO_KEY: dict[str, str] = {
    "ColorBlue": "Chill",
    "ColorGreen": "Vibe",
    "ColorPurple": "Flow",
    "ColorRed": "Rush",
    "ColorOrange": "Beat",
    "NoteSpeed": "Note Speed",
    "PerfectTime": "Perfect Time",
    "PerfectPoints": "Perfect Points",
    "GreatTime": "Great Time",
    "GreatPoints": "Great Points",
    "OkayTime": "Okay Time",
    "OkayPoints": "Okay Points",
    "ComboThreshold": "Combo Threshold",
    "ComboMultiplier": "Combo Multiplier",
    "ComboBreakMultiplier": "Combo Break Multiplier",
    "FeverFillRate": "Fever Fill Rate",
    "FeverMultiplier": "Fever Multiplier",
    "FeverTime": "Fever Time",
    "FeverDrainRate": "Fever Drain Rate",
}


@dataclass(frozen=True, slots=True)
class PetDef:
    """One pet's decompiled base/color stat modifier objects + rarity tier."""

    name: str
    base_mods: dict[str, int]
    color_mods: dict[str, int]
    rarity: int
    source_file: str = ""


# --- Decompilation parse helpers --------------------------------------------
# These patterns are ported from v1's ``webport_extract.py``. The decompiled
# Lua uses ``[GearStats.Type.<Name>] = <int>`` table entries; the regex captures
# the type name and signed integer value. Functions appear at arbitrary
# indentation, so termination is by brace balance, not line anchors.

_STAT_ENTRY_RE = re.compile(r"\[\s*\w+\.Type\.(\w+)\s*\]\s*=\s*(-?\d+)")
_RARITY_RE = re.compile(r"return\s+\w+\.Rarity\.Tier(\d)")
# Decompiled form is ``local function get_name(self) --[[ Line: N ]]`` followed
# by an optional upvalue comment block and ``return "Name"``. The v1 parser
# assumed ``function v1.get_name``; the SarHort dump uses the local form.
_PET_NAME_RE = re.compile(
    r'function\s+get_name\b.*?return\s+"((?:[^"\\]|\\.)*)"', re.S
)
_COND_TABLE_RE = re.compile(
    r"ColorGearStatsEnabled\s*==\s*true\s+and\s+\{(.*?)\}\s+or\s+\{(.*?)\}", re.S
)


class PetScalingError(RuntimeError):
    """Raised on any decompiled-source parse failure or data inconsistency."""


def _first_balanced_table(window: str, source: str) -> str:
    start = window.find("{")
    if start < 0:
        raise PetScalingError(f"{source}: no table literal found")
    depth = 0
    for j in range(start, len(window)):
        ch = window[j]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return window[start + 1 : j]
    raise PetScalingError(f"{source}: unterminated table literal")


def _stat_table_after(text: str, idx: int, source: str) -> str:
    """Return the stat-table body following position ``idx``.

    Takes the ``ColorGearStatsEnabled == true`` branch when the conditional
    form is used, else the first balanced ``{...}`` literal.
    """
    ret = text.find("return", idx)
    if ret < 0:
        raise PetScalingError(f"{source}: no return statement after marker")
    window = text[ret : ret + 4000]
    cond = _COND_TABLE_RE.search(window)
    first_brace = window.find("{")
    if cond is not None and (first_brace < 0 or cond.start() < first_brace):
        return cond.group(1)
    return _first_balanced_table(window, source)


def _map_stat_entries(entries: list[tuple[str, str]], source: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for game_type, value in entries:
        key = GAME_TYPE_TO_KEY.get(game_type)
        if key is None:
            raise PetScalingError(f"{source}: unknown GearStats type {game_type!r}")
        out[key] = out.get(key, 0) + int(value)
    return out


def _extract_fn_table(text: str, fn_name: str, source: str) -> dict[str, int]:
    """Return the stat table inside ``function <fn_name>``.

    The SarHort decompiler emits ``local function <fn_name>(self_N)``; the v1
    WebPort checkout used ``function v1.<fn_name>``. Match the local-form
    declaration so the next ``return`` is inside its body. Honors the
    ``ColorGearStatsEnabled`` conditional by taking the ``true`` branch.
    Raises if the function is absent or empty.
    """
    marker = f"function {fn_name}"
    idx = text.find(marker)
    if idx < 0:
        raise PetScalingError(f"{source}:{fn_name} not found")
    body = _stat_table_after(text, idx, f"{source}:{fn_name}")
    entries = _STAT_ENTRY_RE.findall(body)
    if not entries and body.strip():
        raise PetScalingError(f"{source}:{fn_name}: stat entries present but none parsed")
    if not entries:
        raise PetScalingError(f"{source}:{fn_name}: no stat entries parsed")
    return _map_stat_entries(entries, source)


# --- Scaling law (PetUtils.petid_level_rank_apply_statsdict) ----------------


def pet_rank_to_max_level(rank: int) -> int:
    """Rank -> max attainable level. Rank 1->20, 2->30, 3->40, 4->50."""
    rk = int(rank)
    if rk in PET_RANK_TO_MAX_LEVEL:
        return PET_RANK_TO_MAX_LEVEL[rk]
    if rk <= 0:
        return PET_RANK_TO_MAX_LEVEL[PET_MIN_RANK]
    return PET_RANK_TO_MAX_LEVEL[PET_MAX_RANK]


def _line_y(x1: float, y1: float, x2: float, y2: float, x: float) -> float:
    """CurveUtil.YForPointOf2PtLineP1P2X -- exact argument order preserved."""
    slope = (y1 - y2) / (x1 - x2)
    return slope * x + (y1 - slope * x1)


def pet_color_level_scale(level: int) -> float:
    """Linear 1.0 at level 1 -> 5.0 at level 50 (YForPointOf2PtLineP1P2X)."""
    return _line_y(1.0, 1.0, 50.0, 5.0, float(level))


def pet_stats_delta(
    base_mods: Mapping[str, int],
    color_mods: Mapping[str, int],
    level: int,
    rank: int,
) -> dict[str, int]:
    """petid_level_rank_apply_statsdict: rank multiplies base mods; level
    scales color mods by ``lerp(1..5 over level 1..50)``, floored per-entry
    (``PetRankUpEnabled == true``).

    Level is clamped to ``[PET_MIN_LEVEL, pet_rank_to_max_level(rank)]`` and
    rank to ``[PET_MIN_RANK, PET_MAX_RANK]``.
    """
    rk = min(max(int(rank), PET_MIN_RANK), PET_MAX_RANK)
    lv_cap = pet_rank_to_max_level(rk)
    lv = min(max(int(level), PET_MIN_LEVEL), lv_cap)

    out: dict[str, int] = {}
    for key, val in base_mods.items():
        out[key] = out.get(key, 0) + int(val) * rk
    scale = pet_color_level_scale(lv)
    for key, val in color_mods.items():
        out[key] = out.get(key, 0) + math.floor(int(val) * scale)
    return out


# --- PetInfo extractor -------------------------------------------------------


def _iter_pet_lua_files(pet_dir: Path) -> list[Path]:
    """Yield every ``Pet<Name>.lua`` under ``pet_dir``.

    The decompiled tree nests one folder per pet (``PetUSAO/PetUSAO.lua``).
    Sort for deterministic ordering so duplicate-name errors are reproducible.
    """
    files: list[Path] = []
    for sub in sorted(pet_dir.iterdir()):
        if not sub.is_dir():
            continue
        for lua in sorted(sub.glob("*.lua")):
            files.append(lua)
    return files


def _parse_one_pet(lua: Path) -> PetDef:
    text = lua.read_text(encoding="utf-8", errors="replace")
    source = lua.name
    name_m = _PET_NAME_RE.search(text)
    if name_m is None:
        raise PetScalingError(f"{source}: get_name not found")
    name = name_m.group(1).replace("\\'", "'").replace('\\"', '"')
    base = _extract_fn_table(text, "get_base_statmodifierobj", source)
    color = _extract_fn_table(text, "get_color_statmodifierobj", source)
    rarity_m = _RARITY_RE.search(text)
    if rarity_m is None:
        raise PetScalingError(f"{source}: rarity tier not found")
    return PetDef(
        name=name,
        base_mods=base,
        color_mods=color,
        rarity=int(rarity_m.group(1)),
        source_file=lua.name,
    )


def extract_pet_info(webport_root: Path) -> dict[str, PetDef]:
    """Read every ``PetInfo/Pet<Name>.lua`` and return ``{name: PetDef}``.

    Fails loudly on any parse failure or duplicate pet name. ``webport_root``
    is the decompiled ``ReplicatedStorage`` parent directory; the PetInfo tree
    is resolved as ``<webport_root>/Pets/PetInfo``.
    """
    pet_dir = Path(webport_root) / "Pets" / "PetInfo"
    if not pet_dir.is_dir():
        raise PetScalingError(f"PetInfo directory not found: {pet_dir}")

    pets: dict[str, PetDef] = {}
    failures: list[str] = []
    for lua in _iter_pet_lua_files(pet_dir):
        try:
            pet = _parse_one_pet(lua)
            if pet.name in pets:
                raise PetScalingError(
                    f"duplicate pet name {pet.name!r} ({lua.name} vs "
                    f"{pets[pet.name].source_file})"
                )
            pets[pet.name] = pet
        except PetScalingError as exc:
            failures.append(str(exc))
    if failures:
        raise PetScalingError(
            "pet extraction failed for %d file(s):\n%s"
            % (len(failures), "\n".join(failures))
        )
    if not pets:
        raise PetScalingError(f"no pets extracted from {pet_dir}")
    return pets


# --- Minis.csv parity check --------------------------------------------------

# Canonical stat key -> Minis.csv main-block column name (the maxed L50/rank-4
# values). Used to reconstruct L1 base mods: the main block stores base×4 and
# color×5, so L1_base = main_base / 4 (exact: all main non-color values are
# divisible by 4) and L1_color = Mini Ascension Base <Color>.
_MAIN_CSV_COLUMN_MAP: dict[str, str] = {
    "Combo Multiplier": "Combo Multiplier",
    "Fever Multiplier": "Fever Multiplier",
    "Fever Time": "Fever Time",
    "Fever Fill Rate": "Fever Fill Rate",
}
# Color stat keys -> the L1 base stat prefix used by ``parse_mini_rows``.
_L1_COLOR_BASE_KEY_PREFIX = "Mini Ascension Base "

# Rank-4 base multiplier and level-50 color multiplier in the CSV main block.
_CSV_MAIN_BASE_RANK_MULT = 4
_CSV_MAIN_COLOR_LEVEL_SCALE = 5


@dataclass(frozen=True, slots=True)
class PetParityReport:
    matched: int
    mismatched: list[tuple[str, dict[str, int], dict[str, int]]] = field(default_factory=list)
    missing_in_csv: list[str] = field(default_factory=list)
    missing_in_petinfo: list[str] = field(default_factory=list)


def _csv_l1_stats_from_parsed_row(row: Mapping[str, object]) -> dict[str, int]:
    """Reconstruct the L1/rank-1 stat dict from a ``parse_mini_rows`` row.

    The main block stores base×4 and color×5 (verified: every main non-color
    value is divisible by 4, every main color value by 5). The L1 color base
    values are also carried verbatim under ``Mini Ascension Base <Color>``;
    prefer those for colors (they are the authoritative L1 source).
    """
    out: dict[str, int] = {}
    # Non-color base mods: L1 = main / 4 (rank-4 multiplier).
    for stat_key, col in _MAIN_CSV_COLUMN_MAP.items():
        raw = row.get(col)
        if raw is None or not str(raw).strip():
            continue
        main_val = safe_int(raw, 0)
        if main_val <= 0:
            continue
        if main_val % _CSV_MAIN_BASE_RANK_MULT != 0:
            raise PetScalingError(
                f"CSV main {col}={main_val} not divisible by "
                f"{_CSV_MAIN_BASE_RANK_MULT} (expected base×4 at rank 4)"
            )
        out[stat_key] = main_val // _CSV_MAIN_BASE_RANK_MULT
    # Color mods: prefer the authoritative L1 base columns.
    for color in ("Chill", "Flow", "Rush", "Beat", "Vibe"):
        l1_key = f"{_L1_COLOR_BASE_KEY_PREFIX}{color}"
        l1_raw = row.get(l1_key)
        if l1_raw is not None and str(l1_raw).strip():
            out[color] = safe_int(l1_raw, 0)
            continue
        # Fallback: derive from main (main_color / 5). Some rows may not carry
        # the L1 base column when ascension is disabled; still verify.
        main_raw = row.get(color)
        if main_raw is not None and str(main_raw).strip():
            main_val = safe_int(main_raw, 0)
            if main_val > 0:
                if main_val % _CSV_MAIN_COLOR_LEVEL_SCALE != 0:
                    raise PetScalingError(
                        f"CSV main {color}={main_val} not divisible by "
                        f"{_CSV_MAIN_COLOR_LEVEL_SCALE} (expected color×5 at L50)"
                    )
                out[color] = main_val // _CSV_MAIN_COLOR_LEVEL_SCALE
    return out


def parity_check_against_minis_csv(
    pets: Mapping[str, PetDef],
    minis_rows: Mapping[str, Mapping[str, object]],
) -> PetParityReport:
    """Verify ``pet_stats_delta(base, color, 1, 1)`` equals the L1 base values
    in Minis.csv for every matching pet. Fails loudly on mismatch.

    ``minis_rows`` is a ``{mini_name: row_mapping}`` as produced by
    ``gear_optimizer.data.csv_parser.parse_mini_rows`` (main-block stats under
    canonical keys, L1 color base values under ``Mini Ascension Base <Color>``).
    """
    matched = 0
    mismatched: list[tuple[str, dict[str, int], dict[str, int]]] = []
    missing_in_csv: list[str] = []
    missing_in_petinfo: list[str] = []

    for name, pet in pets.items():
        if name not in minis_rows:
            missing_in_csv.append(name)
            continue
        row = minis_rows[name]
        csv_stats = _csv_l1_stats_from_parsed_row(row)
        # At L1/rank-1: base * 1 + floor(color * 1.0) == base + color.
        delta = pet_stats_delta(pet.base_mods, pet.color_mods, level=1, rank=1)
        if delta != csv_stats:
            mismatched.append((name, dict(delta), dict(csv_stats)))
        else:
            matched += 1

    for name in minis_rows:
        if name not in pets:
            missing_in_petinfo.append(name)

    return PetParityReport(
        matched=matched,
        mismatched=mismatched,
        missing_in_csv=missing_in_csv,
        missing_in_petinfo=missing_in_petinfo,
    )
