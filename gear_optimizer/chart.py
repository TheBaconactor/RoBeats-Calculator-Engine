"""Charts: one song's header and notes.

A chart file is "key<TAB>value" header lines, a "Timing Points" section (not used for scoring) and a
"Song Data" section with one note per line: time in seconds, note index, lane, note type (1 normal,
2 hold head, 3 hold tail). The game's exporter lists a hold's tail right after its head, so notes are
put in time order here; notes at the same time keep their file order.
"""

from __future__ import annotations

import threading
from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
from cachetools import LRUCache

from .gamedata import ELEMENTS

NOTE_TYPES = (1, 2, 3)
_SECTIONS = ("Timing Points", "Song Data")


@dataclass(frozen=True, slots=True, eq=False)
class Chart:
    header: Mapping[str, str]
    timestamps: np.ndarray  # float32 seconds, non-decreasing
    note_types: np.ndarray  # int16
    lanes: np.ndarray  # int32
    last_note_time: float  # seconds; fever duration scales with it
    long_notes: int  # hold notes; they add no fever fill

    @property
    def name(self) -> str:
        return self.header["Song Name"]

    @property
    def difficulty(self) -> str:
        return self.header.get("Difficulty", "")

    @property
    def primary(self) -> str:
        return self.header["Primary Color"]

    @property
    def secondary(self) -> str:
        """A one-color song names its primary here too."""
        return self.header["Secondary Color"]

    @property
    def total_notes(self) -> int:
        return int(self.timestamps.shape[0])

    def with_colors(self, primary: str, secondary: str) -> Chart:
        """This chart scored as if its song had these element colors (an element-override request)."""
        return replace(self, header={**self.header, "Primary Color": primary, "Secondary Color": secondary})


def _header_number(header: Mapping[str, str], key: str, kind: type, source: str):
    raw = header.get(key, "")
    try:
        return kind(raw)
    except ValueError as exc:
        raise ValueError(f"{source}: {key} header must be a number, got {raw!r}") from exc


def _header_field(raw: str, *, source: str, number: int) -> tuple[str, str]:
    key, tab, value = raw.partition("\t")
    if not tab:
        raise ValueError(f"{source}:{number}: header line is not 'key<TAB>value': {raw!r}")
    return key.strip(), value.strip()


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
            key, value = _header_field(raw, source=source, number=number)
            header[key] = value
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
    for key in ("Primary Color", "Secondary Color"):
        if header.get(key) not in ELEMENTS:
            raise ValueError(f"{source}: {key} header must be one of {ELEMENTS}, got {header.get(key)!r}")
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
        last_note_time=_header_number(header, "Last Note Time", float, source),
        long_notes=_header_number(header, "Long Notes", int, source),
    )


def read_chart(path: Path) -> Chart:
    return parse_chart(Path(path).read_text(encoding="utf-8-sig"), source=str(path))


def read_header(path: str | Path) -> dict[str, str]:
    """The header fields of the chart at ``path``, read without its notes."""
    header: dict[str, str] = {}
    with open(path, encoding="utf-8-sig") as f:
        for number, raw in enumerate(f, 1):
            line = raw.strip()
            if line in _SECTIONS:
                break
            if line:
                key, value = _header_field(raw.rstrip("\r\n"), source=str(path), number=number)
                header[key] = value
    return header


_CHART_CACHE: LRUCache = LRUCache(maxsize=64)
_CHART_CACHE_LOCK = threading.Lock()


def load_chart(path: Path) -> Chart:
    """read_chart, cached per file until the file changes (charts are shared and immutable)."""
    resolved = Path(path).resolve()
    stat = resolved.stat()
    stamp = (stat.st_mtime_ns, stat.st_size)
    with _CHART_CACHE_LOCK:
        cached = _CHART_CACHE.get(resolved)
        if cached is not None and cached[0] == stamp:
            return cached[1]
    chart = read_chart(resolved)
    with _CHART_CACHE_LOCK:
        _CHART_CACHE[resolved] = (stamp, chart)
    return chart
