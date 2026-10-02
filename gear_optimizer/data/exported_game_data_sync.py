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
from typing import Any, Iterator

from gear_optimizer.settings import paths
from gear_optimizer.core.utils import safe_int as _safe_int
from gear_optimizer.chart import read_header

logger = logging.getLogger(__name__)

_RUNTIME_UP_TO_DATE_FINGERPRINT: tuple[int, int] | None = None
_SYNC_SCHEMA_VERSION = 2

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
# Gears.csv stat columns after Type and Gear Name (Chill..Vibe, PPoint, CMult, FMult, Time, Fill, PTime).
_GEAR_STAT_KEYS = (
    *_ELEMENT_FROM_STATS.values(),
    "PerfectPoints", "ComboMultiplier", "FeverMultiplier", "FeverTime", "FeverFillRate", "PerfectTime",
)
# A mini's fever stats (CbMlt, FvMlt, FvTim, FvFil); Minis.csv lists them at base (x4) and at level 1.
_MINI_FEVER_KEYS = ("ComboMultiplier", "FeverMultiplier", "FeverTime", "FeverFillRate")
_SONG_DATA_DIRS = ("Easy", "Normal", "Hard")

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
    "Song Target",
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
    engine_paths = paths()
    return ExportedGameDataPaths(
        exported_json=engine_paths.data_dir / "exported_game_data.json",
        gears_csv=engine_paths.gears_csv,
        minis_csv=engine_paths.minis_csv,
        sync_state=engine_paths.bin_path("exported_game_data_sync_state.json"),
    )


def _blank_if_zero(value: int) -> str:
    return "" if value == 0 else str(value)


def _infer_mini_type(l1_elements: dict[str, int]) -> str:
    best_type = "Mini"
    best_value = -1
    for element in _ELEMENT_KEYS:
        value = l1_elements[element]
        if value > best_value:
            best_value = value
            best_type = element
    return best_type


def _song_name_from_export_song(song: dict[str, Any], *, song_id: int) -> str:
    display_name = str(song.get("displayname", "") or "")
    artist = str(song.get("artist", "") or "")
    if not display_name.strip() or not artist.strip():
        raise ValueError(f"Song {song_id} is missing displayname/artist for Song Target linking")
    return f"{display_name} by {artist}".strip()


def _export_items(source: dict[str, Any], key: str) -> Iterator[dict[str, Any]]:
    """The item objects of one export section ({source id: {key: [item, ...]}}); anything else is skipped."""
    for entry in source.values():
        items = entry.get(key, []) if isinstance(entry, dict) else []
        if isinstance(items, list):
            yield from (item for item in items if isinstance(item, dict))


def _song_names_by_id(payload: dict[str, Any]) -> dict[int, str]:
    source = payload.get("songs")
    if source is None:
        return {}
    if not isinstance(source, dict):
        raise ValueError("payload['songs'] must be an object")

    song_names: dict[int, str] = {}
    seen_names: dict[str, int] = {}
    for song in _export_items(source, "songs"):
        song_id = _safe_int(song.get("songid"), -1)
        if song_id <= 0:
            raise ValueError(f"Encountered exported song with invalid songid: {song.get('songid')!r}")
        if song_id in song_names:
            raise ValueError(f"Duplicate exported songid detected: {song_id}")
        song_name = _song_name_from_export_song(song, song_id=song_id)
        previous_id = seen_names.get(song_name)
        if previous_id is not None:
            raise ValueError(f"Duplicate exported Song Name detected: {song_name!r} ({previous_id}, {song_id})")
        seen_names[song_name] = song_id
        song_names[song_id] = song_name
    return song_names


def exported_song_names(payload: dict[str, Any]) -> set[str]:
    """Every Song Name the export describes -- the same names Mini Song Targets link to."""
    return set(_song_names_by_id(payload).values())


def _render_song_targets(
    mini: dict[str, Any],
    *,
    mini_name: str,
    song_names_by_id: dict[int, str],
) -> str:
    targets = mini.get("ascension_songs")
    if targets is None:
        return ""
    if not isinstance(targets, list):
        raise ValueError(f"Mini '{mini_name}' ascension_songs must be a list")
    if not targets:
        return ""
    if not song_names_by_id:
        raise ValueError(f"Mini '{mini_name}' has ascension_songs but payload['songs'] is missing or empty")

    rendered: list[str] = []
    seen_targets: set[str] = set()
    for index, target in enumerate(targets, start=1):
        if not isinstance(target, dict):
            raise ValueError(f"Mini '{mini_name}' ascension_songs[{index}] must be an object")
        song_id = _safe_int(target.get("song_id", target.get("songid")), -1)
        if song_id <= 0:
            raise ValueError(f"Mini '{mini_name}' ascension_songs[{index}] is missing song_id")
        song_name = song_names_by_id.get(song_id)
        if song_name is None:
            raise ValueError(f"Mini '{mini_name}' ascension_songs[{index}] references unknown song_id {song_id}")
        exported_label = str(target.get("label", "") or "").strip()
        if exported_label and exported_label != song_name:
            raise ValueError(
                f"Mini '{mini_name}' ascension_songs[{index}] label {exported_label!r} "
                f"does not match songs table Song Name {song_name!r}"
            )
        if song_name in seen_targets:
            raise ValueError(f"Mini '{mini_name}' has duplicate ascension Song Target {song_name!r}")
        seen_targets.add(song_name)
        rendered.append(song_name)

    return json.dumps(rendered, ensure_ascii=False, separators=(",", ":"))


def _local_chart_song_names(data_dir: Path) -> set[str] | None:
    song_dirs = [data_dir / dirname for dirname in _SONG_DATA_DIRS if (data_dir / dirname).is_dir()]
    if not song_dirs:
        return None

    names_by_header: dict[str, Path] = {}
    scanned_files = 0
    for song_dir in song_dirs:
        for song_path in sorted(song_dir.glob("*.txt")):
            scanned_files += 1
            song_name = read_header(song_path).get("Song Name", "")
            if not song_name:
                raise ValueError(f"Song data file is missing a non-empty Song Name header: {song_path}")
            previous_path = names_by_header.get(song_name)
            if previous_path is not None:
                raise ValueError(
                    f"Duplicate local Song Name header detected: {song_name!r} ({previous_path}, {song_path})"
                )
            names_by_header[song_name] = song_path

    if scanned_files == 0:
        joined_dirs = ", ".join(str(path) for path in song_dirs)
        raise ValueError(f"No local song data files found under: {joined_dirs}")
    return set(names_by_header)


def _validate_mini_song_targets_resolve_to_local_charts(mini_rows: list[list[str]], *, data_dir: Path) -> None:
    chart_song_names = _local_chart_song_names(data_dir)
    if chart_song_names is None:
        return

    mini_name_index = _MINI_CSV_HEADER.index("Mini Name")
    song_target_index = _MINI_CSV_HEADER.index("Song Target")
    unresolved: list[tuple[str, str]] = []
    for row in mini_rows:
        mini_name = row[mini_name_index]
        raw_targets = row[song_target_index].strip()
        if not raw_targets:
            continue
        try:
            targets = json.loads(raw_targets)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Generated Song Target for mini '{mini_name}' is not valid JSON") from exc
        if not isinstance(targets, list) or not all(isinstance(target, str) and target.strip() for target in targets):
            raise ValueError(f"Generated Song Target for mini '{mini_name}' must be a JSON string list")
        for missing_target in sorted(set(targets) - chart_song_names):
            unresolved.append((mini_name, missing_target))

    if unresolved:
        sample = "; ".join(f"{mini_name} -> {song_name!r}" for mini_name, song_name in unresolved[:8])
        extra = "" if len(unresolved) <= 8 else f"; +{len(unresolved) - 8} more"
        raise ValueError(
            f"Mini Song Target values do not resolve to local song data under {data_dir}: {sample}{extra}"
        )


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
    for gear in _export_items(source, "gears"):
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
        rows.append([gear_type, name, *(_blank_if_zero(_safe_int(stats.get(key))) for key in _GEAR_STAT_KEYS)])

    expected = sum(len(entry.get("gears", []) or []) for entry in source.values() if isinstance(entry, dict))
    if len(rows) != expected:
        raise ValueError(f"Gear export mismatch: expected {expected} rows, wrote {len(rows)}")
    return rows


def _export_minis(payload: dict[str, Any]) -> list[list[str]]:
    source = payload.get("minis")
    if not isinstance(source, dict):
        raise ValueError("payload['minis'] must be an object")

    song_names_by_id = _song_names_by_id(payload)
    rows: list[list[str]] = []
    seen_names: set[str] = set()
    for mini in _export_items(source, "minis"):
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

        # Level-1 stats; base (max level) elements are x5 and fever stats x4.
        l1_elements = {element: _safe_int(stats.get(stat_key)) for element, stat_key in _ELEMENT_FROM_STATS.items()}
        l1_fever = [_safe_int(stats.get(key)) for key in _MINI_FEVER_KEYS]
        song_targets = _render_song_targets(mini, mini_name=name, song_names_by_id=song_names_by_id)
        rows.append(
            [
                _infer_mini_type(l1_elements),
                str(star),
                name,
                *(_blank_if_zero(value * 5) for value in l1_elements.values()),
                "",
                *(_blank_if_zero(value * 4) for value in l1_fever),
                "",
                *(_blank_if_zero(value) for value in l1_elements.values()),
                "",
                *(_blank_if_zero(value) for value in l1_fever),
                song_targets,
            ]
        )

    expected = sum(len(entry.get("minis", []) or []) for entry in source.values() if isinstance(entry, dict))
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
    return stat.st_size, stat.st_mtime_ns


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


def _write_sync_state(path: Path, *, source_sha256: str, source_stat: tuple[int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": _SYNC_SCHEMA_VERSION,
        "source_sha256": source_sha256,
        "source_size": source_stat[0],
        "source_mtime_ns": source_stat[1],
        "synced_at": time.time(),
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _remember_up_to_date(paths: ExportedGameDataPaths) -> None:
    global _RUNTIME_UP_TO_DATE_FINGERPRINT
    if paths == default_exported_game_data_paths() and paths.exported_json.is_file():
        _RUNTIME_UP_TO_DATE_FINGERPRINT = _source_stat(paths.exported_json)


def _sync_reason(paths: ExportedGameDataPaths, *, force: bool) -> tuple[bool, str, str]:
    """(whether the CSVs need regenerating, why, the export's SHA-256 when this check already hashed it)."""
    if force:
        return True, "forced", ""
    if not paths.exported_json.is_file():
        return False, "exported_game_data_missing", ""
    if not paths.gears_csv.is_file() or not paths.minis_csv.is_file():
        return True, "csv_missing", ""
    source_stat = _source_stat(paths.exported_json)
    state = _read_sync_state(paths.sync_state)
    if state is not None and state.get("schema_version") != _SYNC_SCHEMA_VERSION:
        return True, "schema_changed", ""
    if paths == default_exported_game_data_paths() and _RUNTIME_UP_TO_DATE_FINGERPRINT == source_stat:
        return False, "up_to_date", ""
    if state is None:
        return True, "state_missing", ""
    if (state.get("source_size"), state.get("source_mtime_ns")) == source_stat and state.get("source_sha256"):
        _remember_up_to_date(paths)
        return False, "up_to_date", ""
    current_sha = _sha256_file(paths.exported_json)
    if state.get("source_sha256") != current_sha:
        return True, "exported_game_data_changed", current_sha
    _remember_up_to_date(paths)
    return False, "up_to_date", ""


def sync_exported_game_data(
    *,
    paths: ExportedGameDataPaths | None = None,
    force: bool = False,
) -> SyncResult:
    resolved = paths or default_exported_game_data_paths()
    should_sync, reason, known_sha = _sync_reason(resolved, force=force)
    if not should_sync:
        return SyncResult(synced=False, reason=reason)

    if not resolved.exported_json.is_file():
        raise FileNotFoundError(f"Missing exported game data: {resolved.exported_json}")

    source_stat = _source_stat(resolved.exported_json)
    payload = _load_payload(resolved.exported_json)
    gear_rows = _export_gears(payload)
    mini_rows = _export_minis(payload)
    _validate_mini_song_targets_resolve_to_local_charts(mini_rows, data_dir=resolved.exported_json.parent)

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

    _write_sync_state(
        resolved.sync_state, source_sha256=known_sha or _sha256_file(resolved.exported_json), source_stat=source_stat
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
    result = sync_exported_game_data(paths=paths, force=args.force)
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
