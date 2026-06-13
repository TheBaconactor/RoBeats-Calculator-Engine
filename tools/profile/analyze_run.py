"""
High-level bottleneck analyzer for deep profiling runs.

Consumes `summary.json` (from `tools/profile/profile_system_run.py`) and optional
structured events JSONL, then emits ranked anomalies with deterministic rules.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from gear_optimizer.core.utils import safe_float as _safe_float, safe_int as _safe_int


DEFAULT_THRESHOLDS = {
    "fg_prep_cpu_share": 0.30,
    "gpu_underutilized_pct": 70.0,
    "backlog_active_min_sec": 10.0,
    "backlog_growth_min": 3.0,
}


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        obj = json.load(f)
    if not isinstance(obj, dict):
        raise ValueError(f"Expected object JSON: {path}")
    return obj


def _load_events_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = str(line or "").strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if isinstance(obj, dict):
                out.append(obj)
    return out


def _extract_backlog_points(events: list[dict[str, Any]]) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for obj in events:
        ts = _safe_float(obj.get("ts_wall", 0.0), 0.0)
        if ts <= 0:
            continue
        comp = str(obj.get("component", "") or "")
        metrics = obj.get("metrics")
        if comp not in {"inflight_orchestrator", "app"} or not isinstance(metrics, dict):
            continue

        pending_fg = _safe_int(metrics.get("pending_fg", -1), -1)
        fg_futures = max(0, _safe_int(metrics.get("fg_futures", 0), 0))
        pending_all = _safe_int(metrics.get("pending", -1), -1)

        if pending_fg >= 0:
            points.append((float(ts), float(pending_fg + fg_futures)))
        elif pending_all >= 0 and comp == "app":
            points.append((float(ts), float(pending_all)))
    points.sort(key=lambda t: t[0])
    return points


def _summarize_backlog(events: list[dict[str, Any]]) -> dict[str, Any]:
    points = _extract_backlog_points(events)
    if len(points) < 2:
        return {
            "count": int(len(points)),
            "growth": 0.0,
            "window_sec": 0.0,
            "active_sec": 0.0,
            "positive_delta_ratio": 0.0,
            "max": _safe_float(points[0][1], 0.0) if points else 0.0,
        }

    growth = float(points[-1][1] - points[0][1])
    window = max(0.0, float(points[-1][0] - points[0][0]))
    active = 0.0
    positive = 0
    deltas = 0
    max_backlog = 0.0
    for i in range(len(points) - 1):
        a_ts, a_v = points[i]
        b_ts, b_v = points[i + 1]
        dt = max(0.0, float(b_ts - a_ts))
        max_backlog = max(float(max_backlog), float(a_v), float(b_v))
        if float(a_v) > 0.0 or float(b_v) > 0.0:
            active += dt
        d = float(b_v - a_v)
        if d > 0.0:
            positive += 1
        deltas += 1
    return {
        "count": int(len(points)),
        "growth": float(growth),
        "window_sec": float(window),
        "active_sec": float(active),
        "positive_delta_ratio": float((positive / deltas) if deltas > 0 else 0.0),
        "max": float(max_backlog),
    }


def _collect_metrics(summary: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    stage = summary.get("inflight_stage_profile") or {}
    gpu_summary = summary.get("gpu_summary") or {}
    events_summary = summary.get("profile_events_summary") or {}

    stage_total_wall_s = _safe_float(stage.get("total_wall_s", 0.0), _safe_float(summary.get("elapsed_sec", 0.0), 0.0))
    underfed_total_s = _safe_float(((stage.get("stages") or {}).get("underfed_wait") or {}).get("total_s", 0.0), 0.0)
    fg_prep_cpu_s = _safe_float(((stage.get("stages") or {}).get("fg_prep") or {}).get("cpu_total_s", 0.0), 0.0)

    util_mean = _safe_float((gpu_summary.get("target_engine_util_pct_max") or {}).get("mean", 0.0), 0.0)

    backlog = _summarize_backlog(events)
    if backlog.get("count", 0) < 2 and isinstance(events_summary, dict):
        summary_backlog = events_summary.get("backlog") or {}
        backlog = {
            "count": _safe_int(summary_backlog.get("count", 0), 0),
            "growth": _safe_float(summary_backlog.get("growth", 0.0), 0.0),
            "window_sec": _safe_float(summary_backlog.get("window_sec", 0.0), 0.0),
            "active_sec": _safe_float(summary_backlog.get("active_sec", 0.0), 0.0),
            "positive_delta_ratio": _safe_float(summary_backlog.get("positive_delta_ratio", 0.0), 0.0),
            "max": _safe_float((summary_backlog.get("stats") or {}).get("max", 0.0), 0.0),
        }

    return {
        "underfed_wait_share": float((underfed_total_s / stage_total_wall_s) if stage_total_wall_s > 0 else 0.0),
        "fg_prep_cpu_share": float((fg_prep_cpu_s / stage_total_wall_s) if stage_total_wall_s > 0 else 0.0),
        "gpu_util_mean_pct": float(util_mean),
        "backlog": backlog,
    }


def _mk_anomaly(
    *,
    aid: str,
    severity: float,
    confidence: float,
    summary: str,
    evidence_path: str,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    return {
        "id": str(aid),
        "severity": _clamp01(float(severity)),
        "confidence": _clamp01(float(confidence)),
        "summary": str(summary),
        "evidence_path": str(evidence_path),
        "evidence": dict(evidence or {}),
    }


def detect_anomalies(summary: dict[str, Any], events: list[dict[str, Any]], thresholds: dict[str, float]) -> list[dict[str, Any]]:
    metrics = _collect_metrics(summary, events)
    t = dict(DEFAULT_THRESHOLDS)
    t.update({k: _safe_float(v, t.get(k, 0.0)) for k, v in (thresholds or {}).items()})

    out: list[dict[str, Any]] = []

    fg_prep_share = _safe_float(metrics.get("fg_prep_cpu_share", 0.0), 0.0)
    if fg_prep_share > t["fg_prep_cpu_share"]:
        sev = _clamp01((fg_prep_share - t["fg_prep_cpu_share"]) / max(1e-9, (1.0 - t["fg_prep_cpu_share"])))
        out.append(
            _mk_anomaly(
                aid="fg_prep_cpu_bound",
                severity=sev,
                confidence=0.75,
                summary="FG prep is CPU-bound relative to wall time.",
                evidence_path="inflight_stage_profile.stages.fg_prep.cpu_total_s",
                evidence={
                    "fg_prep_cpu_share": float(fg_prep_share),
                    "threshold": float(t["fg_prep_cpu_share"]),
                },
            )
        )

    backlog = metrics.get("backlog") or {}
    backlog_active = _safe_float(backlog.get("active_sec", 0.0), 0.0)
    backlog_growth = _safe_float(backlog.get("growth", 0.0), 0.0)
    backlog_positive_ratio = _safe_float(backlog.get("positive_delta_ratio", 0.0), 0.0)
    backlog_max = _safe_float(backlog.get("max", 0.0), 0.0)

    if (
        backlog_active >= t["backlog_active_min_sec"]
        and backlog_growth >= t["backlog_growth_min"]
        and backlog_positive_ratio >= 0.60
    ):
        sev = _clamp01(
            ((backlog_growth / max(1e-9, t["backlog_growth_min"])) - 1.0) * 0.7
            + ((backlog_positive_ratio - 0.60) / 0.40) * 0.3
        )
        out.append(
            _mk_anomaly(
                aid="fg_backlog_risk",
                severity=sev,
                confidence=0.80,
                summary="FG backlog risk: pending FG grows over sustained active backlog time.",
                evidence_path="profile_events_summary.backlog",
                evidence={
                    "active_sec": float(backlog_active),
                    "growth": float(backlog_growth),
                    "positive_delta_ratio": float(backlog_positive_ratio),
                },
            )
        )

    util_mean = _safe_float(metrics.get("gpu_util_mean_pct", 0.0), 0.0)
    if backlog_active >= t["backlog_active_min_sec"] and backlog_max > 0.0 and util_mean < t["gpu_underutilized_pct"]:
        sev = _clamp01((t["gpu_underutilized_pct"] - util_mean) / max(1e-9, t["gpu_underutilized_pct"]))
        out.append(
            _mk_anomaly(
                aid="gpu_underutilized_with_backlog",
                severity=sev,
                confidence=0.70,
                summary="GPU underutilized while backlog remains active.",
                evidence_path="gpu_summary.target_engine_util_pct_max.mean",
                evidence={
                    "gpu_util_mean_pct": float(util_mean),
                    "backlog_active_sec": float(backlog_active),
                    "backlog_max": float(backlog_max),
                },
            )
        )

    out.sort(key=lambda a: (-_safe_float(a.get("severity", 0.0), 0.0), -_safe_float(a.get("confidence", 0.0), 0.0), str(a.get("id", ""))))
    return out


def analyze_summary(
    summary: dict[str, Any],
    *,
    events_path: Path | None = None,
    thresholds: dict[str, float] | None = None,
) -> dict[str, Any]:
    if events_path is None:
        path_raw = ""
        try:
            path_raw = str(((summary.get("paths") or {}).get("profile_events_jsonl") or "").strip())
        except Exception:
            path_raw = ""
        events_path = Path(path_raw) if path_raw else None

    events = _load_events_jsonl(events_path) if events_path is not None else []
    merged_thresholds = dict(DEFAULT_THRESHOLDS)
    if thresholds:
        merged_thresholds.update({k: _safe_float(v, merged_thresholds.get(k, 0.0)) for k, v in thresholds.items()})
    anomalies = detect_anomalies(summary, events, merged_thresholds)
    return {
        "ok": True,
        "events_path": str(events_path) if events_path is not None else "",
        "events_count": int(len(events)),
        "thresholds": merged_thresholds,
        "metrics": _collect_metrics(summary, events),
        "anomalies": anomalies,
    }


def format_top_bottlenecks(anomalies: list[dict[str, Any]], *, top: int = 5) -> str:
    if not anomalies:
        return "No bottlenecks detected."
    lines = [
        "rank  id                             severity  confidence  evidence",
    ]
    for idx, item in enumerate(anomalies[: max(1, int(top))], start=1):
        aid = str(item.get("id", "unknown"))[:30]
        sev = _safe_float(item.get("severity", 0.0), 0.0)
        conf = _safe_float(item.get("confidence", 0.0), 0.0)
        evidence = str(item.get("evidence_path", "") or "")
        lines.append(f"{idx:>4}  {aid:<30}  {sev:>8.3f}  {conf:>10.3f}  {evidence}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analyze a deep profiling run summary and rank bottlenecks.")
    ap.add_argument("--summary", required=True, help="Path to summary.json from profile_system_run.py")
    ap.add_argument("--events", default="", help="Optional events JSONL path (defaults to summary.paths.profile_events_jsonl)")
    ap.add_argument("--top", type=int, default=5, help="How many bottlenecks to print")
    ap.add_argument("--json", action="store_true", help="Print full analyzer result JSON")
    ns = ap.parse_args(argv)

    summary_path = Path(ns.summary)
    if not summary_path.exists():
        print(f"Summary not found: {summary_path}")
        return 2

    try:
        summary = _load_json(summary_path)
    except Exception as exc:
        print(f"Failed to load summary: {type(exc).__name__}: {exc}")
        return 2

    events_path = Path(ns.events) if str(ns.events or "").strip() else None
    result = analyze_summary(summary, events_path=events_path)
    anomalies = list(result.get("anomalies") or [])
    print(format_top_bottlenecks(anomalies, top=int(ns.top)))
    if ns.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
