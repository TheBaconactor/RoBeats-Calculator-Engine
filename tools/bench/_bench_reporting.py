from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterable

BENCH_JSON_PREFIX = "BENCH_JSON:"
TRUTHY_ENV_VALUES = frozenset({"1", "true", "yes", "on"})


def env_flag(key: str, default: str = "0") -> bool:
    return str(os.environ.get(str(key), default) or "").strip().lower() in TRUTHY_ENV_VALUES


def clear_taichi_kernel_profiler(*, enabled: bool) -> None:
    if not bool(enabled):
        return
    try:
        import taichi as ti

        ti.profiler.clear_kernel_profiler_info()
    except Exception:
        return


def get_taichi_kernel_profiler_total_sec(*, enabled: bool) -> float | None:
    if not bool(enabled):
        return None
    try:
        import taichi as ti

        ti.sync()
        return float(ti.profiler.get_kernel_profiler_total_time())
    except Exception:
        return None


def add_kernel_profiler_metrics(result: dict[str, Any], *, enabled: bool, wall_sec: float) -> None:
    result["kernel_profiler_enabled"] = bool(enabled)
    total_sec = get_taichi_kernel_profiler_total_sec(enabled=bool(enabled))
    if total_sec is None:
        result["kernel_profiler_total_sec"] = None
        result["kernel_profiler_wall_pct"] = None
        result["non_kernel_overhead_sec"] = None
        return

    wall_sec = float(wall_sec)
    result["kernel_profiler_total_sec"] = float(total_sec)
    result["kernel_profiler_wall_pct"] = float((total_sec / wall_sec) * 100.0) if wall_sec > 0.0 else None
    result["non_kernel_overhead_sec"] = float(max(0.0, wall_sec - total_sec))


def normalize_kernel_names(kernel_names: Iterable[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for kernel_name in kernel_names:
        name = str(kernel_name or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        out.append(name)
    return out


def get_taichi_kernel_profiler_kernel_entries(
    kernel_names: Iterable[str],
    *,
    enabled: bool,
) -> list[dict[str, Any]]:
    if not bool(enabled):
        return []
    try:
        import taichi as ti

        ti.sync()
    except Exception:
        return []

    entries: list[dict[str, Any]] = []
    for kernel_name in normalize_kernel_names(kernel_names):
        try:
            query = ti.profiler.query_kernel_profiler_info(kernel_name)
        except Exception:
            continue
        counter = int(getattr(query, "counter", 0) or 0)
        if counter <= 0:
            continue
        avg_ms = float(getattr(query, "avg", 0.0) or 0.0)
        total_sec = float(counter) * avg_ms / 1000.0
        entries.append(
            {
                "name": kernel_name,
                "counter": counter,
                "min_ms": float(getattr(query, "min", 0.0) or 0.0),
                "avg_ms": avg_ms,
                "max_ms": float(getattr(query, "max", 0.0) or 0.0),
                "total_sec": total_sec,
            }
        )
    entries.sort(key=lambda item: float(item.get("total_sec", 0.0)), reverse=True)
    return entries


def add_kernel_profiler_kernel_entries(
    result: dict[str, Any],
    *,
    enabled: bool,
    kernel_names: Iterable[str],
) -> None:
    entries = get_taichi_kernel_profiler_kernel_entries(kernel_names, enabled=bool(enabled))
    result["kernel_profiler_kernels"] = entries
    accounted_total_sec = float(sum(float(item.get("total_sec", 0.0)) for item in entries))
    result["kernel_profiler_accounted_total_sec"] = accounted_total_sec if entries else None

    total_sec = result.get("kernel_profiler_total_sec", None)
    if total_sec is None:
        result["kernel_profiler_unaccounted_total_sec"] = None
        result["kernel_profiler_accounted_pct"] = None
        return

    total_sec = float(total_sec)
    result["kernel_profiler_unaccounted_total_sec"] = float(max(0.0, total_sec - accounted_total_sec))
    result["kernel_profiler_accounted_pct"] = float((accounted_total_sec / total_sec) * 100.0) if total_sec > 0.0 else None


def snapshot_env(keys: Iterable[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key in keys:
        value = os.environ.get(str(key), None)
        if value is None:
            continue
        out[str(key)] = str(value)
    return out


def emit_bench_result(
    result: dict[str, Any],
    *,
    json_stdout: bool = False,
    json_out: str | None = None,
) -> None:
    if json_out:
        out_path = Path(str(json_out))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if json_stdout:
        print(f"{BENCH_JSON_PREFIX}{json.dumps(result, sort_keys=True)}")
