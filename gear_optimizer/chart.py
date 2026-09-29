"""Charts: one song's header and notes.

A chart file is "key<TAB>value" header lines, a "Timing Points" section (not used for scoring) and a
"Song Data" section with one note per line: time in seconds, note index, lane, note type (1 normal,
2 hold head, 3 hold tail). The game's exporter lists a hold's tail right after its head, so notes are
put in time order here; notes at the same time keep their file order.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import numpy as np

NOTE_TYPES = (1, 2, 3)
_SECTIONS = ("Timing Points", "Song Data")


@dataclass(frozen=True, slots=True, eq=False)
class Chart:
    header: Mapping[str, str]
    timestamps: np.ndarray  # float32 seconds, non-decreasing
    note_types: np.ndarray  # int16
    lanes: np.ndarray  # int32

    @property
    def name(self) -> str:
        return self.header["Song Name"]

    @property
    def primary(self) -> str:
        return self.header.get("Primary Color", "")

    @property
    def secondary(self) -> str:
        return self.header.get("Secondary Color", "")


def parse_chart(text: str, *, source: str = "chart") -> Chart:
    header: dict[str, str] = {}
    section = ""
    rows: list[tuple[float, int, int]] = []
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        if line in _SECTIONS:
            section = line
            continue
        if not section:
            key, tab, value = raw.partition("\t")
            if not tab:
                raise ValueError(f"{source}:{number}: header line is not 'key<TAB>value': {raw!r}")
            header[key.strip()] = value.strip()
        elif section == "Song Data":
            parts = line.split()
            if len(parts) != 4:
                raise ValueError(f"{source}:{number}: a note needs 4 columns, got {raw!r}")
            try:
                rows.append((float(parts[0]), int(parts[2]), int(parts[3])))
            except ValueError as exc:
                raise ValueError(f"{source}:{number}: malformed note {raw!r}") from exc
    if not header.get("Song Name"):
        raise ValueError(f"{source}: no Song Name header")
    if not rows:
        raise ValueError(f"{source}: no notes (missing 'Song Data' section?)")

    timestamps = np.asarray([row[0] for row in rows], dtype=np.float32)
    lanes = np.asarray([row[1] for row in rows], dtype=np.int32)
    note_types = np.asarray([row[2] for row in rows], dtype=np.int16)
    if not np.isin(note_types, NOTE_TYPES).all():
        raise ValueError(f"{source}: note types must be one of {NOTE_TYPES}")
    order = np.argsort(timestamps, kind="stable")
    return Chart(
        header=header,
        timestamps=np.ascontiguousarray(timestamps[order]),
        note_types=np.ascontiguousarray(note_types[order]),
        lanes=np.ascontiguousarray(lanes[order]),
    )


def read_chart(path: Path) -> Chart:
    return parse_chart(Path(path).read_text(encoding="utf-8-sig"), source=str(path))


# The header keys the old calc_song metadata carried.
_CALC_SONG_KEYS = (
    "Song Name",
    "Difficulty",
    "Primary Color",
    "Secondary Color",
    "Last Note Time",
    "Total Notes",
    "Fever Fill",
    "Fever Time",
    "Long Notes",
    "Timing Mode",
)


def to_calc_song(chart: Chart) -> dict:
    """The calc_song dict the not-yet-rewritten engine layers consume (frontier builders, GPU search).

    Reproduces the old loader exactly, including its "0" for a header key present with an empty value,
    because the frontier cache keys hash these fields.
    """
    metadata = {key: (chart.header[key] or "0") if key in chart.header else "" for key in _CALC_SONG_KEYS}
    return {
        "metadata": metadata,
        "song_data": {
            "timestamps": chart.timestamps,
            "chart_timestamps": chart.timestamps,
            "note_types": chart.note_types,
            "lanes": chart.lanes,
        },
    }
