"""Upgrade lattice for the reverse score engine.

Owns the 22 upgrade types from decompiled ``EquipmentUpgradesSet1``, taking the
``ColorGearStatsEnabled == true`` stat branch (the live value). Each upgrade
carries a per-unit signed stat pattern (e.g. PerfectTime+ = +1 Perfect Time,
-1 Perfect Points, +1 Chill). Per-piece capacity is 15 (6 pieces x 15 slots =
joint budget 90).

The production forward optimizer does not model upgrades as a search dimension;
the reverse engine needs them because real leaderboard rows carry applied
upgrades that contribute to the observed statsdict.

Reference:
- Decompiled source: ``Avatar/EquipmentUpgradesSet1/EquipmentUpgradesSet1.lua``
  (single file containing 22 ``add_equipment_upgrade`` blocks).
- Per-piece capacity: ``Avatar/EquipmentUpgradeDatabase.upgrade_count_can_upgrade``.
- v1 reference parser: ``reverse_score/webport_extract.py:148-185``.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from gear_optimizer.core.utils import safe_int
from gear_optimizer.data.mini_scaling import (
    GAME_TYPE_TO_KEY,
    _COND_TABLE_RE,
    _STAT_ENTRY_RE,
    _first_balanced_table,
)

UPGRADES_PER_PIECE_MAX: int = 15
UPGRADE_TOTAL_MAX: int = 90  # 6 pieces x 15 slots


class UpgradeExtractError(RuntimeError):
    """Raised on any upgrade parse failure or data inconsistency."""


@dataclass(frozen=True, slots=True)
class UpgradeDef:
    """One upgrade type from ``EquipmentUpgradesSet1``.

    ``stat_pattern`` is the signed per-unit stat delta (the
    ``ColorGearStatsEnabled == true`` branch). ``gear_power`` is the per-unit
    gear-power cost (decompiled ``get_gear_power`` return value).
    """

    uid: int
    name: str
    stat_pattern: dict[str, int]
    gear_power: int = 0
    source_file: str = ""


# ``add_equipment_upgrade(<id>, (function() ... end)())``.
_UPGRADE_BLOCK_RE = re.compile(r"add_equipment_upgrade\((\d+)\s*,", re.S)
# ``return DebugConfig.ColorGearStatsEnabled == true and "Name" or "Alt"``.
_UPGRADE_NAME_COND_RE = re.compile(
    r'ColorGearStatsEnabled\s*==\s*true\s+and\s+"((?:[^"\\]|\\.)*)"\s+or\s+"((?:[^"\\]|\\.)*)"',
    re.S,
)
# Plain ``return "Name"`` (no conditional). Allow trailing content on the
# same line (the decompiled body continues with ``end`` on the next line).
_UPGRADE_NAME_PLAIN_RE = re.compile(r'return\s+"((?:[^"\\]|\\.)*)"')
# ``return <int>`` inside ``get_gear_power``.
_GEAR_POWER_RE = re.compile(r"return\s+(-?\d+)")
# Function declaration markers. The decompiler appends a per-block suffix
# (``get_name_7``, ``get_gear_statmodifierobj_3``, ...) to keep each closure
# unique, so match the prefix.
_GET_NAME_DECL_RE = re.compile(r"function\s+get_name\w*\s*\(")
_GET_STATMOD_DECL_RE = re.compile(r"function\s+get_gear_statmodifierobj\w*\s*\(")
_GET_GEAR_POWER_DECL_RE = re.compile(r"function\s+get_gear_power\w*\s*\(")


def _extract_upgrade_name(body: str, source: str) -> str:
    """Return the ``ColorGearStatsEnabled == true`` branch of ``get_name``."""
    # The decompiler appends a per-block suffix (``get_name_7`` etc.), so match
    # the prefix. Then find the next ``return`` inside the function body.
    m = _GET_NAME_DECL_RE.search(body)
    if m is None:
        raise UpgradeExtractError(f"{source}: get_name declaration not found")
    ret = body.find("return", m.end())
    if ret < 0:
        raise UpgradeExtractError(f"{source}: no return after get_name declaration")
    window = body[ret : ret + 600]
    cond = _UPGRADE_NAME_COND_RE.search(window)
    if cond is not None:
        return cond.group(1).replace("\\'", "'").replace('\\"', '"')
    plain = _UPGRADE_NAME_PLAIN_RE.search(window)
    if plain is not None:
        return plain.group(1).replace("\\'", "'").replace('\\"', '"')
    raise UpgradeExtractError(f"{source}: could not parse get_name return")


def _extract_upgrade_stat_pattern(body: str, source: str) -> dict[str, int]:
    """Return the ``ColorGearStatsEnabled == true`` stat branch."""
    m = _GET_STATMOD_DECL_RE.search(body)
    if m is None:
        raise UpgradeExtractError(f"{source}: get_gear_statmodifierobj declaration not found")
    ret = body.find("return", m.end())
    if ret < 0:
        raise UpgradeExtractError(f"{source}: no return after get_gear_statmodifierobj")
    window = body[ret : ret + 4000]
    cond = _COND_TABLE_RE.search(window)
    first_brace = window.find("{")
    if cond is not None and (first_brace < 0 or cond.start() < first_brace):
        table_body = cond.group(1)
    else:
        table_body = _first_balanced_table(window, source)
    entries = _STAT_ENTRY_RE.findall(table_body)
    if not entries:
        raise UpgradeExtractError(f"{source}: no stat entries parsed")
    out: dict[str, int] = {}
    for game_type, value in entries:
        key = GAME_TYPE_TO_KEY.get(game_type)
        if key is None:
            raise UpgradeExtractError(f"{source}: unknown GearStats type {game_type!r}")
        out[key] = out.get(key, 0) + int(value)
    return out


def _extract_upgrade_gear_power(body: str, source: str) -> int:
    """Return the per-unit gear power cost (decompiled ``get_gear_power``)."""
    m = _GET_GEAR_POWER_DECL_RE.search(body)
    if m is None:
        return 0
    ret = body.find("return", m.end())
    if ret < 0:
        return 0
    window = body[ret : ret + 200]
    pw = _GEAR_POWER_RE.search(window)
    if pw is None:
        return 0
    return safe_int(pw.group(1), 0)


def _iter_upgrade_files(upgrades_root: Path) -> list[Path]:
    """Return every ``.lua`` file under ``upgrades_root``.

    The decompiled tree places a single ``EquipmentUpgradesSet1.lua`` inside
    the ``Avatar/EquipmentUpgradesSet1/`` directory, but iterate over all
    ``.lua`` files so a future split into multiple files is picked up
    automatically. Sort for deterministic ordering.
    """
    if not upgrades_root.is_dir():
        # Allow the legacy single-file layout (``EquipmentUpgradesSet1.lua``
        # directly under ``Avatar/``) as a fallback.
        return []
    return sorted(upgrades_root.glob("*.lua"))


def _parse_upgrade_file(path: Path) -> list[UpgradeDef]:
    text = path.read_text(encoding="utf-8", errors="replace")
    blocks = list(_UPGRADE_BLOCK_RE.finditer(text))
    if not blocks:
        raise UpgradeExtractError(f"{path.name}: no add_equipment_upgrade blocks found")
    upgrades: list[UpgradeDef] = []
    for i, match in enumerate(blocks):
        uid = int(match.group(1))
        start = match.end()
        end = blocks[i + 1].start() if i + 1 < len(blocks) else len(text)
        body = text[start:end]
        source = f"{path.name}#upgrade{uid}"
        name = _extract_upgrade_name(body, source)
        stats = _extract_upgrade_stat_pattern(body, source)
        gear_power = _extract_upgrade_gear_power(body, source)
        upgrades.append(
            UpgradeDef(
                uid=uid,
                name=name,
                stat_pattern=stats,
                gear_power=gear_power,
                source_file=path.name,
            )
        )
    return upgrades


def extract_upgrade_defs(webport_root: Path) -> list[UpgradeDef]:
    """Read every Lua file under ``Avatar/EquipmentUpgradesSet1/`` and parse
    the ``add_equipment_upgrade`` blocks, taking the
    ``ColorGearStatsEnabled == true`` stat branch.

    Fails loudly on any parse failure or duplicate upgrade id. Returns all
    upgrade types in source order (sorted by file then by uid).
    """
    upgrades_root = Path(webport_root) / "Avatar" / "EquipmentUpgradesSet1"
    files = _iter_upgrade_files(upgrades_root)
    if not files:
        # Legacy single-file layout fallback.
        legacy = Path(webport_root) / "Avatar" / "EquipmentUpgradesSet1.lua"
        if legacy.is_file():
            files = [legacy]
        else:
            raise UpgradeExtractError(
                f"EquipmentUpgradesSet1 not found under {upgrades_root} or {legacy}"
            )

    all_upgrades: list[UpgradeDef] = []
    failures: list[str] = []
    for lua in files:
        try:
            all_upgrades.extend(_parse_upgrade_file(lua))
        except UpgradeExtractError as exc:
            failures.append(str(exc))
    if failures:
        raise UpgradeExtractError(
            "upgrade extraction failed for %d file(s):\n%s"
            % (len(failures), "\n".join(failures))
        )
    if not all_upgrades:
        raise UpgradeExtractError("no upgrades extracted")
    ids = [u.uid for u in all_upgrades]
    if len(set(ids)) != len(ids):
        dupes = sorted({uid for uid in ids if ids.count(uid) > 1})
        raise UpgradeExtractError(f"duplicate upgrade ids: {dupes}")
    return all_upgrades


def load_upgrade_defs(webport_root: Path | None = None) -> dict[int, UpgradeDef]:
    """Return ``{uid: UpgradeDef}``. If ``webport_root`` is None, resolve the
    decompiled source via the ``ROBEATS_DECOMPILED_ROOT`` env var, else fail
    loudly (no silent fallback).
    """
    import os

    if webport_root is None:
        env_root = os.environ.get("ROBEATS_DECOMPILED_ROOT", "").strip()
        if not env_root:
            raise UpgradeExtractError(
                "load_upgrade_defs requires webport_root or ROBEATS_DECOMPILED_ROOT env var"
            )
        webport_root = Path(env_root)
    return {u.uid: u for u in extract_upgrade_defs(webport_root)}


@dataclass(frozen=True, slots=True)
class UpgradeLatticeReport:
    count: int
    names: list[str] = field(default_factory=list)
    negative_stat_upgrades: list[str] = field(default_factory=list)
    per_piece_cap: int = UPGRADES_PER_PIECE_MAX
    total_cap: int = UPGRADE_TOTAL_MAX


def summarize_upgrade_lattice(upgrades: list[UpgradeDef]) -> UpgradeLatticeReport:
    """Return a compact summary of the extracted upgrade lattice."""
    names = [u.name for u in upgrades]
    negative = [
        u.name
        for u in upgrades
        if any(v < 0 for v in u.stat_pattern.values())
    ]
    return UpgradeLatticeReport(
        count=len(upgrades),
        names=names,
        negative_stat_upgrades=negative,
        per_piece_cap=UPGRADES_PER_PIECE_MAX,
        total_cap=UPGRADE_TOTAL_MAX,
    )
