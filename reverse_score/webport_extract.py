"""Extract stat tables from the decompiled [REDACTED PRIVATE REPOSITORY] Lua sources.

Pulls the data dimensions the optimizer does not model:
- pet (mini) base/color stat modifier objects + rarity tier, per PetInfo file;
- gear upgrade definitions (EquipmentUpgradesSet1), taking the
  ``ColorGearStatsEnabled == true`` branch (live value).

Extraction is strict: a file that matches the shape but fails to parse is an
error listing the file, never a silent skip. The WebPort checkout is an
external boundary; missing directories fail loudly with the attempted path.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .game_model import GAME_TYPE_TO_KEY

_STAT_ENTRY_RE = re.compile(r"\[\s*\w+\.Type\.(\w+)\s*\]\s*=\s*(-?\d+)")
_RARITY_RE = re.compile(r"return\s+\w+\.Rarity\.Tier(\d)")
_PET_NAME_RE = re.compile(r'function\s+v1\.get_name.*?return\s+"((?:[^"\\]|\\.)*)"', re.S)
_UPGRADE_BLOCK_RE = re.compile(r"add_equipment_upgrade\((\d+)\s*,", re.S)
_COND_TABLE_RE = re.compile(
    r"ColorGearStatsEnabled\s*==\s*true\s+and\s+\{(.*?)\}\s+or\s+\{(.*?)\}", re.S
)


class WebPortExtractError(RuntimeError):
    pass


@dataclass(frozen=True)
class PetDef:
    name: str
    base_mods: dict[str, int]
    color_mods: dict[str, int]
    rarity: int
    source_file: str


@dataclass(frozen=True)
class UpgradeDef:
    upgrade_id: int
    stats: dict[str, int]


def _map_stats(entries: list[tuple[str, str]], source: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for game_type, value in entries:
        key = GAME_TYPE_TO_KEY.get(game_type)
        if key is None:
            raise WebPortExtractError(f"{source}: unknown GearStats type {game_type!r}")
        out[key] = out.get(key, 0) + int(value)
    return out


def _first_balanced_table(window: str, source: str) -> str:
    start = window.find("{")
    if start < 0:
        raise WebPortExtractError(f"{source}: no table literal found")
    depth = 0
    for j in range(start, len(window)):
        ch = window[j]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return window[start + 1 : j]
    raise WebPortExtractError(f"{source}: unterminated table literal")


def _stat_table_after(text: str, idx: int, source: str) -> str:
    """Return the stat-table body following position ``idx``: the
    ``ColorGearStatsEnabled == true`` branch when the conditional form is
    used, else the first balanced ``{...}`` literal. Functions in the
    decompiled sources appear at arbitrary indentation, so termination is by
    brace balance, not line anchors."""
    ret = text.find("return", idx)
    if ret < 0:
        raise WebPortExtractError(f"{source}: no return statement after marker")
    window = text[ret : ret + 4000]
    cond = _COND_TABLE_RE.search(window)
    first_brace = window.find("{")
    if cond is not None and (first_brace < 0 or cond.start() < first_brace):
        return cond.group(1)
    return _first_balanced_table(window, source)


def _extract_fn_table(text: str, fn_name: str, source: str) -> dict[str, int] | None:
    """Return the stat table inside ``function v1.<fn_name>`` (or None if the
    function is absent). Honors the ColorGearStatsEnabled conditional by
    taking the ``true`` branch."""
    marker = f".{fn_name}("
    idx = text.find(marker)
    if idx < 0:
        return None
    body = _stat_table_after(text, idx, f"{source}:{fn_name}")
    entries = _STAT_ENTRY_RE.findall(body)
    if not entries and body.strip():
        raise WebPortExtractError(
            f"{source}: {fn_name} present but no stat entries parsed"
        )
    return _map_stats(entries, source)


def extract_pets(webport_root: Path) -> dict[str, PetDef]:
    pet_dir = Path(webport_root) / "src" / "ReplicatedStorage" / "Pets" / "PetInfo"
    if not pet_dir.is_dir():
        raise WebPortExtractError(f"PetInfo directory not found: {pet_dir}")
    pets: dict[str, PetDef] = {}
    failures: list[str] = []
    for lua in sorted(pet_dir.glob("*.lua")):
        text = lua.read_text(encoding="utf-8", errors="replace")
        try:
            name_m = _PET_NAME_RE.search(text)
            if name_m is None:
                raise WebPortExtractError(f"{lua.name}: get_name not found")
            name = name_m.group(1).replace("\\'", "'").replace('\\"', '"')
            base = _extract_fn_table(text, "get_base_statmodifierobj", lua.name)
            color = _extract_fn_table(text, "get_color_statmodifierobj", lua.name)
            rarity_m = _RARITY_RE.search(text)
            if base is None or color is None or rarity_m is None:
                raise WebPortExtractError(
                    f"{lua.name}: missing base/color statmodifier or rarity"
                )
            if name in pets:
                raise WebPortExtractError(f"duplicate pet name {name!r} ({lua.name})")
            pets[name] = PetDef(
                name=name,
                base_mods=base,
                color_mods=color,
                rarity=int(rarity_m.group(1)),
                source_file=lua.name,
            )
        except WebPortExtractError as exc:
            failures.append(str(exc))
    if failures:
        raise WebPortExtractError(
            "pet extraction failed for %d file(s):\n%s" % (len(failures), "\n".join(failures))
        )
    if not pets:
        raise WebPortExtractError(f"no pets extracted from {pet_dir}")
    return pets


def extract_upgrades(webport_root: Path) -> list[UpgradeDef]:
    path = (
        Path(webport_root)
        / "src"
        / "ReplicatedStorage"
        / "Avatar"
        / "EquipmentUpgradesSet1.lua"
    )
    if not path.is_file():
        raise WebPortExtractError(f"EquipmentUpgradesSet1.lua not found: {path}")
    text = path.read_text(encoding="utf-8", errors="replace")
    blocks = list(_UPGRADE_BLOCK_RE.finditer(text))
    if not blocks:
        raise WebPortExtractError(f"{path.name}: no add_equipment_upgrade blocks found")
    upgrades: list[UpgradeDef] = []
    for i, match in enumerate(blocks):
        start = match.end()
        end = blocks[i + 1].start() if i + 1 < len(blocks) else len(text)
        body = text[start:end]
        stats = _extract_upgrade_stats(body, f"{path.name}#upgrade{match.group(1)}")
        upgrades.append(UpgradeDef(upgrade_id=int(match.group(1)), stats=stats))
    ids = [u.upgrade_id for u in upgrades]
    if len(set(ids)) != len(ids):
        raise WebPortExtractError(f"{path.name}: duplicate upgrade ids {ids}")
    return upgrades


def _extract_upgrade_stats(body: str, source: str) -> dict[str, int]:
    marker = ".get_gear_statmodifierobj("
    idx = body.find(marker)
    if idx < 0:
        raise WebPortExtractError(f"{source}: get_gear_statmodifierobj not found")
    fn_body = _stat_table_after(body, idx, source)
    entries = _STAT_ENTRY_RE.findall(fn_body)
    if not entries:
        raise WebPortExtractError(f"{source}: no stat entries parsed")
    return _map_stats(entries, source)


# Per-piece upgrade capacity (EquipmentUpgradeDatabase.upgrade_count_can_upgrade).
UPGRADES_PER_PIECE_MAX = 15
