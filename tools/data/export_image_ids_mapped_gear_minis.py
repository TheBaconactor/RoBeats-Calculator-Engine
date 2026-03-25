#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


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


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _blank_if_zero(value: int) -> str:
    return "" if int(value) == 0 else str(int(value))


def _infer_mini_type(l1_elements: dict[str, int]) -> str:
    # Note: RoBeatsMeta mini payloads do not include a dedicated element/type field.
    # Infer a stable "Type" from the max color stat (ties resolved by fixed element order).
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
    for _image_id, entry in source.items():
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
    for _image_id, entry in source.items():
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

            # Minis.csv (optimizer format) includes "base" stats and "L1 stats"; base is consistently
            # derived from L1 values (x5 colors, x4 multipliers/time/fill) in the checked-in dataset.
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
                    "",  # unused/blank column (matches existing optimizer Minis.csv)
                    _blank_if_zero(base_cbmlt),
                    _blank_if_zero(base_fvmlt),
                    _blank_if_zero(base_fvtim),
                    _blank_if_zero(base_fvfil),
                    "",  # "L1 Stats" separator column (always blank in existing file)
                    _blank_if_zero(l1_elements["Chill"]),
                    _blank_if_zero(l1_elements["Flow"]),
                    _blank_if_zero(l1_elements["Rush"]),
                    _blank_if_zero(l1_elements["Beat"]),
                    _blank_if_zero(l1_elements["Vibe"]),
                    "",  # unused/blank column (matches existing optimizer Minis.csv)
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


def _write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Export RoBeatsMeta image_ids_mapped.json to optimizer CSV formats.")
    parser.add_argument(
        "--input",
        default="Data/image_ids_mapped.json",
        help="Path to image_ids_mapped.json (default: Data/image_ids_mapped.json)",
    )
    parser.add_argument(
        "--gears-out",
        default="artifacts/robeatsmeta_export/Gears.csv",
        help="Output path for optimizer-formatted Gears.csv",
    )
    parser.add_argument(
        "--minis-out",
        default="artifacts/robeatsmeta_export/Minis.csv",
        help="Output path for optimizer-formatted Minis.csv",
    )
    args = parser.parse_args()

    payload = _load_payload(Path(args.input))
    gear_rows = _export_gears(payload)
    mini_rows = _export_minis(payload)

    _write_csv(
        Path(args.gears_out),
        [
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
        ],
        gear_rows,
    )
    _write_csv(
        Path(args.minis_out),
        [
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
        ],
        mini_rows,
    )

    print(f"Wrote {len(gear_rows)} gears -> {args.gears_out}")
    print(f"Wrote {len(mini_rows)} minis -> {args.minis_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

