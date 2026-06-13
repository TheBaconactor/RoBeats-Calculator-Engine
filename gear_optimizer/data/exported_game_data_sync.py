"""Sync optimizer gear/mini CSVs from Data/exported_game_data.json."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gear_optimizer.core.constants import PATHS
from gear_optimizer.core.utils import safe_int as _safe_int
from gear_optimizer.data.loadout_equivalence import clear_gear_mini_csv_caches

logger = logging.getLogger(__name__)

_RUNTIME_UP_TO_DATE_FINGERPRINT: tuple[int, int] | None = None

_SLOT_TO_GEAR_TYPE: dict[str, str] = {
    "1": "Shirt",
    "2": "Pants",
    "3": "Hat",
    "4": "Face",
    "5": "Neck",
    "6": "Back",
}

_ELEMENT_KEYS = ("Chill", "Flow", "Rush", "Beat", "Vibe")
_ELEMENT_FROM_STATS = {
    "Chill": "ColorBlue",
    "Flow": "ColorPurple",
    "Rush": "ColorRed",
    "Beat": "ColorOrange",
    "Vibe": "ColorGreen",
}

_GEAR_CSV_HEADER = [
    "Type",
    "Gear Name",
    "Chill",
    "Flow",
    "Rush",
    "Beat",
    "Vibe",
    "PPoint",
    "CMult",
    "FMult",
    "Time",
    "Fill",
    "PTime",
]

_MINI_CSV_HEADER = [
    "Type",
    "Star",
    "Mini Name",
    "Chill",
    "Flow",
    "Rush",
    "Beat",
    "Vibe",
    "",
    "CbMlt",
    "FvMlt",
    "FvTim",
    "FvFil",
    "L1 Stats",
    "Chill",
    "Flow",
    "Rush",
    "Beat",
    "Vibe",
    "",
    "CbMlt",
    "FvMlt",
    "FvTim",
    "FvFil",
]


@dataclass(frozen=True, slots=True)
class ExportedGameDataPaths:
    exported_json: Path
    gears_csv: Path
    minis_csv: Path
    sync_state: Path


@dataclass(frozen=True, slots=True)
class SyncResult:
    synced: bool
    reason: str
    gear_count: int = 0
    mini_count: int = 0


def default_exported_game_data_paths() -> ExportedGameDataPaths:
    data_dir = Path(PATHS.data_dir)
    return ExportedGameDataPaths(
        exported_json=data_dir / "exported_game_data.json",
        gears_csv=data_dir / "Gear" / "Gears.csv",
        minis_csv=data_dir / "Gear" / "Minis.csv",
        sync_state=Path(PATHS.bin_path("exported_game_data_sync_state.json")),
    )


def _blank_if_zero(value: int) -> str:
    return "" if int(value) == 0 else str(value)


def _infer_mini_type(l1_elements: dict[str, int]) -> str:
    best_type = "Mini"
    best_value = -1
    for element in _ELEMENT_KEYS:
        value = int(l1_elements.get(element, 0))
        if value > best_value:
            best_value = value
            best_type = element
    return best_type


def _load_payload(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Expected top-level JSON object")
    return payload


def _export_gears(payload: dict[str, Any]) -> list[list[str]]:
    source = payload.get("gears")
    if not isinstance(source, dict):
        raise ValueError("payload['gears'] must be an object")

    rows: list[list[str]] = []
    seen_names: set[str] = set()
    for _source_id, entry in source.items():
        if not isinstance(entry, dict):
            continue
        gears = entry.get("gears", [])
        if not isinstance(gears, list):
            continue
        for gear in gears:
            if not isinstance(gear, dict):
                continue
            name = str(gear.get("name", "") or "").strip()
            if not name:
                raise ValueError("Encountered gear with empty name")
            if name in seen_names:
                raise ValueError(f"Duplicate gear name detected: {name}")
            seen_names.add(name)

            slot = str(gear.get("slot", "") or "").strip()
            gear_type = _SLOT_TO_GEAR_TYPE.get(slot)
            if not gear_type:
                raise ValueError(f"Unknown gear slot '{slot}' for gear '{name}'")

            stats = gear.get("stats", {})
            if not isinstance(stats, dict):
                stats = {}

            chill = _safe_int(stats.get("ColorBlue"))
            flow = _safe_int(stats.get("ColorPurple"))
            rush = _safe_int(stats.get("ColorRed"))
            beat = _safe_int(stats.get("ColorOrange"))
            vibe = _safe_int(stats.get("ColorGreen"))

            ppoint = _safe_int(stats.get("PerfectPoints"))
            cmult = _safe_int(stats.get("ComboMultiplier"))
            fmult = _safe_int(stats.get("FeverMultiplier"))
            ftime = _safe_int(stats.get("FeverTime"))
            ffill = _safe_int(stats.get("FeverFillRate"))
            ptime = _safe_int(stats.get("PerfectTime"))

            rows.append(
                [
                    gear_type,
                    name,
                    _blank_if_zero(chill),
                    _blank_if_zero(flow),
                    _blank_if_zero(rush),
                    _blank_if_zero(beat),
                    _blank_if_zero(vibe),
                    _blank_if_zero(ppoint),
                    _blank_if_zero(cmult),
                    _blank_if_zero(fmult),
                    _blank_if_zero(ftime),
                    _blank_if_zero(ffill),
                    _blank_if_zero(ptime),
                ]
            )

    expected = sum(len((entry or {}).get("gears", []) or []) for entry in source.values() if isinstance(entry, dict))
    if len(rows) != expected:
        raise ValueError(f"Gear export mismatch: expected {expected} rows, wrote {len(rows)}")
    return rows


def _export_minis(payload: dict[str, Any]) -> list[list[str]]:
    source = payload.get("minis")
    if not isinstance(source, dict):
        raise ValueError("payload['minis'] must be an object")

    rows: list[list[str]] = []
    seen_names: set[str] = set()
    for _source_id, entry in source.items():
        if not isinstance(entry, dict):
            continue
        minis = entry.get("minis", [])
        if not isinstance(minis, list):
            continue
        for mini in minis:
            if not isinstance(mini, dict):
                continue
            name = str(mini.get("name", "") or "").strip()
            if not name:
                raise ValueError("Encountered mini with empty name")
            if name in seen_names:
                raise ValueError(f"Duplicate mini name detected: {name}")
            seen_names.add(name)

            star = _safe_int(mini.get("rarity"))
            if star <= 0:
                raise ValueError(f"Unexpected mini rarity/star '{mini.get('rarity')}' for mini '{name}'")

            stats = mini.get("stats", {})
            if not isinstance(stats, dict):
                stats = {}

            l1_elements = {element: _safe_int(stats.get(stat_key)) for element, stat_key in _ELEMENT_FROM_STATS.items()}
            mini_type = _infer_mini_type(l1_elements)

            l1_cbmlt = _safe_int(stats.get("ComboMultiplier"))
            l1_fvmlt = _safe_int(stats.get("FeverMultiplier"))
            l1_fvtim = _safe_int(stats.get("FeverTime"))
            l1_fvfil = _safe_int(stats.get("FeverFillRate"))

            base_elements = {k: int(v) * 5 for k, v in l1_elements.items()}
            base_cbmlt = l1_cbmlt * 4
            base_fvmlt = l1_fvmlt * 4
            base_fvtim = l1_fvtim * 4
            base_fvfil = l1_fvfil * 4

            rows.append(
                [
                    mini_type,
                    str(star),
                    name,
                    _blank_if_zero(base_elements["Chill"]),
                    _blank_if_zero(base_elements["Flow"]),
                    _blank_if_zero(base_elements["Rush"]),
                    _blank_if_zero(base_elements["Beat"]),
                    _blank_if_zero(base_elements["Vibe"]),
                    "",
                    _blank_if_zero(base_cbmlt),
                    _blank_if_zero(base_fvmlt),
                    _blank_if_zero(base_fvtim),
                    _blank_if_zero(base_fvfil),
                    "",
                    _blank_if_zero(l1_elements["Chill"]),
                    _blank_if_zero(l1_elements["Flow"]),
                    _blank_if_zero(l1_elements["Rush"]),
                    _blank_if_zero(l1_elements["Beat"]),
                    _blank_if_zero(l1_elements["Vibe"]),
                    "",
                    _blank_if_zero(l1_cbmlt),
                    _blank_if_zero(l1_fvmlt),
                    _blank_if_zero(l1_fvtim),
                    _blank_if_zero(l1_fvfil),
                ]
            )

    expected = sum(len((entry or {}).get("minis", []) or []) for entry in source.values() if isinstance(entry, dict))
    if len(rows) != expected:
        raise ValueError(f"Mini export mismatch: expected {expected} rows, wrote {len(rows)}")
    return rows


def _render_csv(header: list[str], rows: list[list[str]]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return buffer.getvalue()


def _source_stat(path: Path) -> tuple[int, int]:
    stat = path.stat()
    return int(stat.st_size), int(stat.st_mtime_ns)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_sync_state(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid exported-game-data sync state: {path}")
    return payload


def _write_sync_state(
    path: Path,
    *,
    source_sha256: str,
    source_size: int,
    source_mtime_ns: int,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source_sha256": str(source_sha256),
        "source_size": int(source_size),
        "source_mtime_ns": int(source_mtime_ns),
        "synced_at": float(time.time()),
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _remember_up_to_date(paths: ExportedGameDataPaths) -> None:
    global _RUNTIME_UP_TO_DATE_FINGERPRINT
    if paths == default_exported_game_data_paths() and paths.exported_json.is_file():
        _RUNTIME_UP_TO_DATE_FINGERPRINT = _source_stat(paths.exported_json)


def _sync_reason(
    paths: ExportedGameDataPaths,
    *,
    force: bool,
) -> tuple[bool, str, str, tuple[int, int]]:
    if force:
        return True, "forced", "", (0, 0)
    if not paths.exported_json.is_file():
        return False, "exported_game_data_missing", "", (0, 0)
    if not paths.gears_csv.is_file() or not paths.minis_csv.is_file():
        source_stat = _source_stat(paths.exported_json)
        return True, "csv_missing", "", source_stat

    source_stat = _source_stat(paths.exported_json)
    if paths == default_exported_game_data_paths() and _RUNTIME_UP_TO_DATE_FINGERPRINT == source_stat:
        return False, "up_to_date", "", source_stat

    state = _read_sync_state(paths.sync_state)
    if state is not None:
        if (
            int(state.get("source_size", -1)) == source_stat[0]
            and int(state.get("source_mtime_ns", -1)) == source_stat[1]
            and str(state.get("source_sha256") or "")
        ):
            _remember_up_to_date(paths)
            return False, "up_to_date", str(state["source_sha256"]), source_stat
    if state is None:
        return True, "state_missing", "", source_stat

    current_sha = _sha256_file(paths.exported_json)
    if str(state.get("source_sha256") or "") != current_sha:
        return True, "exported_game_data_changed", current_sha, source_stat

    _remember_up_to_date(paths)
    return False, "up_to_date", current_sha, source_stat


def sync_exported_game_data(
    *,
    paths: ExportedGameDataPaths | None = None,
    force: bool = False,
) -> SyncResult:
    resolved = paths or default_exported_game_data_paths()
    should_sync, reason, known_sha, source_stat = _sync_reason(resolved, force=force)
    if not should_sync:
        return SyncResult(synced=False, reason=reason)

    if not resolved.exported_json.is_file():
        raise FileNotFoundError(f"Missing exported game data: {resolved.exported_json}")

    payload = _load_payload(resolved.exported_json)
    gear_rows = _export_gears(payload)
    mini_rows = _export_minis(payload)
    source_sha = known_sha or _sha256_file(resolved.exported_json)
    if source_stat == (0, 0):
        source_stat = _source_stat(resolved.exported_json)

    gears_text = _render_csv(_GEAR_CSV_HEADER, gear_rows)
    minis_text = _render_csv(_MINI_CSV_HEADER, mini_rows)
    wrote_files = False
    if (
        not resolved.gears_csv.is_file()
        or resolved.gears_csv.read_text(encoding="utf-8") != gears_text
        or not resolved.minis_csv.is_file()
        or resolved.minis_csv.read_text(encoding="utf-8") != minis_text
    ):
        resolved.gears_csv.parent.mkdir(parents=True, exist_ok=True)
        resolved.gears_csv.write_text(gears_text, encoding="utf-8")
        resolved.minis_csv.write_text(minis_text, encoding="utf-8")
        wrote_files = True
        clear_gear_mini_csv_caches()

    _write_sync_state(
        resolved.sync_state,
        source_sha256=source_sha,
        source_size=source_stat[0],
        source_mtime_ns=source_stat[1],
    )
    _remember_up_to_date(resolved)
    if wrote_files:
        logger.info(
            "[Data] Synced gear/mini CSVs from exported_game_data.json "
            f"({len(gear_rows)} gears, {len(mini_rows)} minis, reason={reason})"
        )
    return SyncResult(synced=True, reason=reason, gear_count=len(gear_rows), mini_count=len(mini_rows))


def _paths_for_cli(
    *,
    input_path: str | None,
    gears_out: str | None,
    minis_out: str | None,
) -> ExportedGameDataPaths:
    defaults = default_exported_game_data_paths()
    exported_json = Path(input_path) if input_path else defaults.exported_json
    gears_csv = Path(gears_out) if gears_out else defaults.gears_csv
    minis_csv = Path(minis_out) if minis_out else defaults.minis_csv
    using_defaults = (
        exported_json == defaults.exported_json
        and gears_csv == defaults.gears_csv
        and minis_csv == defaults.minis_csv
    )
    sync_state = defaults.sync_state if using_defaults else exported_json.parent / "exported_game_data_sync_state.json"
    return ExportedGameDataPaths(
        exported_json=exported_json,
        gears_csv=gears_csv,
        minis_csv=minis_csv,
        sync_state=sync_state,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Regenerate optimizer Gears.csv and Minis.csv from exported_game_data.json."
    )
    parser.add_argument(
        "--input",
        help="Path to exported_game_data.json (default: Data/exported_game_data.json)",
    )
    parser.add_argument(
        "--gears-out",
        help="Output path for Gears.csv (default: Data/Gear/Gears.csv)",
    )
    parser.add_argument(
        "--minis-out",
        help="Output path for Minis.csv (default: Data/Gear/Minis.csv)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate CSVs even when exported_game_data.json is unchanged.",
    )
    args = parser.parse_args(argv)
    paths = _paths_for_cli(
        input_path=args.input,
        gears_out=args.gears_out,
        minis_out=args.minis_out,
    )
    result = sync_exported_game_data(paths=paths, force=bool(args.force))
    if result.synced:
        print(
            f"Wrote {result.gear_count} gears -> {paths.gears_csv} "
            f"and {result.mini_count} minis -> {paths.minis_csv} (reason={result.reason})"
        )
    else:
        print(f"No sync needed ({result.reason}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
