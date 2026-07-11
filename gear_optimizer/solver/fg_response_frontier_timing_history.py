from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import platform
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

logger = logging.getLogger(__name__)

_SCHEMA_VERSION = 1
_MAX_RECORDS = 2048


@dataclass(frozen=True, slots=True)
class FgPrebuildChart:
    path: str
    digest: str
    note_count: int
    long_notes: int
    duration_sec: float


@dataclass(frozen=True, slots=True)
class FgPrebuildTimingContext:
    algorithm_version: str
    cpu_identity: str
    reducer_threads: int
    ref_signature: str
    stat_signature: str
    frontier_cpus: int
    max_workers: int


@dataclass(frozen=True, slots=True)
class FgPrebuildTimingPrediction:
    duration_ms: float
    source: str


@dataclass(frozen=True, slots=True)
class FgPrebuildScheduledChart:
    chart: FgPrebuildChart
    reducer_threads: int
    context: FgPrebuildTimingContext
    prediction: FgPrebuildTimingPrediction


def fg_prebuild_chart_digest(song_cache_key: tuple) -> str:
    return hashlib.blake2b(repr(song_cache_key).encode("utf-8"), digest_size=16).hexdigest()


def fg_prebuild_cpu_identity() -> str:
    fields = {
        "machine": platform.machine(),
        "processor": platform.processor(),
        "processor_identifier": os.environ.get("PROCESSOR_IDENTIFIER", ""),
        "system": platform.system(),
        "logical_cpus": int(os.cpu_count() or 1),
    }
    return json.dumps(fields, sort_keys=True, separators=(",", ":"))


def load_fg_prebuild_timing_history(path: Path) -> list[dict[str, Any]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        logger.warning("[FGResponseCache] Ignoring unreadable timing history %s: %s", path, exc)
        return []
    if not isinstance(raw, dict) or raw.get("schema_version") != _SCHEMA_VERSION:
        logger.warning("[FGResponseCache] Ignoring incompatible timing history %s", path)
        return []
    records = raw.get("records")
    if not isinstance(records, list):
        logger.warning("[FGResponseCache] Ignoring malformed timing history %s", path)
        return []
    return [dict(record) for record in records if isinstance(record, dict)]


def _record_matches_context(record: dict[str, Any], context: FgPrebuildTimingContext) -> bool:
    return all(record.get(key) == value for key, value in asdict(context).items())


def _finite_positive(value: object) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) and numeric > 0.0 else None


def _structural_prediction_ms(
    chart: FgPrebuildChart,
    compatible: list[dict[str, Any]],
) -> float | None:
    candidates: list[tuple[float, float]] = []
    current_notes = max(1, int(chart.note_count))
    current_long_ratio = float(chart.long_notes) / float(current_notes)
    current_duration = max(0.001, float(chart.duration_sec))
    for record in compatible:
        duration_ms = _finite_positive(record.get("duration_ms"))
        note_count = int(record.get("note_count", 0) or 0)
        long_notes = int(record.get("long_notes", 0) or 0)
        chart_duration = _finite_positive(record.get("chart_duration_sec"))
        if duration_ms is None or note_count <= 0 or chart_duration is None:
            continue
        long_ratio = float(long_notes) / float(note_count)
        distance = (
            abs(math.log(float(current_notes) / float(note_count)))
            + abs(current_long_ratio - long_ratio)
            + 0.25 * abs(math.log(current_duration / float(chart_duration)))
        )
        scaled_ms = float(duration_ms) * float(current_notes) / float(note_count)
        candidates.append((float(distance), float(scaled_ms)))
    if len(candidates) < 3:
        return None
    nearest = sorted(candidates)[: min(5, len(candidates))]
    weighted_sum = 0.0
    total_weight = 0.0
    for distance, scaled_ms in nearest:
        weight = 1.0 / max(0.05, float(distance))
        weighted_sum += float(scaled_ms) * weight
        total_weight += weight
    return float(weighted_sum / total_weight)


def predict_fg_prebuild_duration(
    chart: FgPrebuildChart,
    context: FgPrebuildTimingContext,
    records: Iterable[dict[str, Any]],
) -> FgPrebuildTimingPrediction:
    compatible = [record for record in records if _record_matches_context(record, context)]
    exact = [
        record
        for record in compatible
        if str(record.get("chart_digest", "")) == str(chart.digest)
        and _finite_positive(record.get("duration_ms")) is not None
    ]
    if exact:
        newest = max(exact, key=lambda record: float(record.get("completed_at", 0.0) or 0.0))
        return FgPrebuildTimingPrediction(float(newest["duration_ms"]), "history")
    structural_ms = _structural_prediction_ms(chart, compatible)
    if structural_ms is not None:
        return FgPrebuildTimingPrediction(float(structural_ms), "structure")
    return FgPrebuildTimingPrediction(float(max(0, int(chart.note_count))), "notes")


def update_fg_prebuild_timing_history(
    path: Path,
    records: Iterable[dict[str, Any]],
    *,
    chart: FgPrebuildChart,
    context: FgPrebuildTimingContext,
    duration_ms: float,
) -> list[dict[str, Any]]:
    measured_ms = _finite_positive(duration_ms)
    if measured_ms is None:
        raise ValueError("FG prebuild timing history requires a positive completed-build duration")
    replacement = {
        **asdict(context),
        "chart_digest": str(chart.digest),
        "note_count": int(chart.note_count),
        "long_notes": int(chart.long_notes),
        "chart_duration_sec": float(chart.duration_sec),
        "duration_ms": float(measured_ms),
        "completed_at": float(time.time()),
    }
    kept = [
        dict(record)
        for record in records
        if not (
            str(record.get("chart_digest", "")) == str(chart.digest)
            and _record_matches_context(record, context)
        )
    ]
    kept.append(replacement)
    kept.sort(key=lambda record: float(record.get("completed_at", 0.0) or 0.0), reverse=True)
    updated = kept[:_MAX_RECORDS]
    payload = {"schema_version": _SCHEMA_VERSION, "records": updated}
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
    return updated
