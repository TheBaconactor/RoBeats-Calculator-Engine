from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import unquote

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from gear_optimizer.core.config import get_config_path, load_config
from gear_optimizer.data.database import get_db_connection_readonly, get_evolution_db_path
from tools.cli import discover_scripts, repo_root as tools_repo_root
from tools.profile.analyze_run import analyze_summary

try:
    from gear_optimizer.core.team_buff import resolve_baseline_team_buff_from_cfg
except ModuleNotFoundError:  # pragma: no cover - compatibility for older branches
    resolve_baseline_team_buff_from_cfg = None


REPO_ROOT = tools_repo_root()
DOCS_DIR = REPO_ROOT / "docs"
IMPLEMENTATION_RECORDS_DIR = DOCS_DIR / "Implementation Records"
WORKLOG_PATH = DOCS_DIR / "CODEX_WORKLOG.md"
CHARTER_PATH = DOCS_DIR / "MCP_HARNESS_CHARTER.md"
MANIFEST_PATH = REPO_ROOT / "tools" / "_mcp_harness" / "coverage_manifest.json"
ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "mcp_harness"
PROFILE_ROOT = REPO_ROOT / "artifacts" / "profile"
REPO_MCP_SERVER_NAME = "gear-optimizer-engineering-harness"

STATIC_MODULE_MAP = [
    {
        "id": "optimizer",
        "entrypoint": "main.py",
        "owner_path": "gear_optimizer/app.py",
        "summary": "End-to-end optimizer orchestration.",
    },
    {
        "id": "general-meta",
        "entrypoint": "general_meta_main.py",
        "owner_path": "general_meta/",
        "summary": "Cross-song and meta analysis.",
    },
    {
        "id": "inventory-optimizer",
        "entrypoint": "inventory_meta_coverage_main.py",
        "owner_path": "inventory_optimizer/",
        "summary": "Inventory meta coverage loop.",
    },
    {
        "id": "core-package",
        "entrypoint": "gear_optimizer/",
        "owner_path": "gear_optimizer/",
        "summary": "Scoring, solver, pipeline, config, and persistence ownership.",
    },
]

VERIFY_MATRIX = {
    "docs-only": {
        "category": "docs-only",
        "required": [],
        "optional": [],
        "why": "Documentation-only changes do not require code validation unless they document changed behavior.",
    },
    "mcp-harness": {
        "category": "mcp-harness",
        "required": [
            "python -m pytest -q tests/test_mcp_harness.py tests/test_mcp_harness_stdio.py --tb=short",
            "python -m ruff check tools/mcp_server.py tools/_mcp_harness tests/test_mcp_harness.py tests/test_mcp_harness_stdio.py",
        ],
        "optional": [
            "powershell -ExecutionPolicy Bypass -File tools/dev/quality_check.ps1 -CI",
        ],
        "why": "Harness changes should prove stdio startup, compact tool surfaces, and metadata-safe structured outputs.",
    },
    "database": {
        "category": "database",
        "required": [
            "python -m pytest -q tests/test_db_manager.py --tb=short",
        ],
        "optional": [
            "powershell -ExecutionPolicy Bypass -File tools/dev/quality_check.ps1 -CI",
        ],
        "why": "DB changes need schema/leaderboard correctness checks.",
    },
    "gpu-core": {
        "category": "gpu-core",
        "required": [
            "python -m pytest -m gpu tests/test_parity_smoke.py -q --tb=short",
        ],
        "optional": [
            "powershell -ExecutionPolicy Bypass -File tools/dev/quality_check.ps1",
        ],
        "why": "Solver or GPU-path changes must preserve parity and integrated production behavior.",
    },
    "repo-tools": {
        "category": "repo-tools",
        "required": [
            "powershell -ExecutionPolicy Bypass -File tools/dev/quality_check.ps1 -CI",
        ],
        "optional": [
            "python -m tools audit",
        ],
        "why": "Shared tooling changes should stay aligned with the standard harness.",
    },
}

SAFE_REPO_TOOL_PREFIXES = (
    "tools:bench/",
    "tools:db/",
    "tools:profile/",
    "tools:verify/",
    "tools:dev/",
)

DENIED_REPO_TOOL_IDS = {
    "tools:dev/cleanup_test_data",
}

DB_AUDIT_TOOL_MAP = {
    "summary": "tools:db/check_db",
    "fg-summary": "tools:db/check_db_fg",
    "force": "tools:db/check_force",
    "scores-vs-gpu": "tools:db/verify_db_scores_vs_gpu",
    "recover-song-base-deficit": "tools:db/recover_song_base_deficit",
    "smoke-run-and-audit": "tools:db/smoke_run_and_audit",
}

PROFILE_SUMMARY_KEYS = (
    "run_id",
    "elapsed_sec",
    "exit_code",
    "effective_settings",
    "gpu_phase_summary",
    "gpu_request_type_summary",
    "inflight_stage_profile",
    "profile_events_summary",
    "summary_v2",
)

CURATED_ENV_KEYS = (
    "METAFINDER_CONFIG_PATH",
    "EVOLUTION_DB_PATH",
    "GA_SEED",
    "SONG_REPEATS",
    "FG_SEARCH_RADIUS",
    "SONG_QUEUE_LIMIT",
    "GPU_EXECUTOR_PROFILE",
    "GPU_PROFILER",
    "PERF_TIMING",
    "GPU_SYNC_FOR_TIMING",
    "GPU_FORCE_SYNC",
)

GUARDRAILS = {
    "gpu_policy": "GPU-only production. CPU paths are reference-only and must not be reintroduced as production fallbacks.",
    "docs_policy": "Behavior, policy, or engineering-guidance changes require docs/CODEX_WORKLOG.md and implementation-record updates.",
    "generated_artifacts": [
        "Data/",
        "bin/",
        "artifacts/",
        "evolution.db",
        "*.pstats",
        "*.prof",
        "*.csv"
    ],
    "benchmark_policy": "Accept throughput wins only when FG debt/coverage does not regress under controlled reproducible settings.",
    "skill_policy": "Do not add repo-local custom Codex skills for this harness; use the repo-local MCP server and official OpenAI/Codex capabilities.",
    "maintenance_policy": "When new stable repeated engineering surfaces appear, update the MCP harness automatically if the change materially improves speed, safety, or token efficiency.",
}


def _utc_now() -> str:
    return datetime.now(tz=UTC).isoformat(timespec="seconds")


def _normalize_relpath(path: str | Path) -> str:
    text = str(path).replace("\\", "/").strip()
    if text.startswith("./"):
        text = text[2:]
    return text


def _path_mtime(path: Path) -> int:
    try:
        return int(path.stat().st_mtime_ns)
    except OSError:
        return -1


def _json_load(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _first_heading(text: str, fallback: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or fallback
    return fallback


def _compact_text(text: str, max_chars: int = 1200) -> str:
    text = str(text or "").strip()
    if len(text) <= max_chars:
        return text
    return text[: max(0, max_chars - 3)].rstrip() + "..."


def _cfg_get(cfg: Any, section: str, option: str, default: Any = "") -> Any:
    try:
        return cfg.get(section, option, fallback=default)
    except Exception:
        return default


def _cfg_get_bool(cfg: Any, section: str, option: str, default: bool = False) -> bool:
    try:
        return bool(cfg.getboolean(section, option, fallback=default))
    except Exception:
        return bool(default)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        try:
            return int(str(value).strip())
        except Exception:
            return int(default)


def _interesting_env_overrides() -> dict[str, str]:
    overrides: dict[str, str] = {}
    for key in CURATED_ENV_KEYS:
        raw = os.environ.get(key)
        if raw is None:
            continue
        value = str(raw).strip()
        if value:
            overrides[key] = value
    return overrides


def _git_output(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
        stdin=subprocess.DEVNULL,
    )
    if completed.returncode != 0:
        return ""
    return str(completed.stdout or "").strip()


def _git_status_entries() -> list[dict[str, Any]]:
    completed = subprocess.run(
        ["git", "-c", "core.quotepath=false", "status", "--porcelain=v1", "-z", "--untracked-files=normal"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        check=False,
        stdin=subprocess.DEVNULL,
    )
    if completed.returncode != 0:
        return []
    raw = completed.stdout or b""
    entries: list[dict[str, Any]] = []
    parts = raw.split(b"\x00")
    index = 0
    while index < len(parts):
        chunk = parts[index]
        index += 1
        if not chunk.strip():
            continue
        text = chunk.decode("utf-8", errors="replace")
        status = text[:2]
        raw_path = text[3:].strip()
        if "R" in status or "C" in status:
            index += 1
        entries.append(
            {
                "status": status,
                "path": _normalize_relpath(raw_path),
                "tracked": not status.startswith("??"),
            }
        )
    return entries


def _repo_provenance() -> dict[str, Any]:
    return {
        "branch": _git_output("branch", "--show-current"),
        "head": _git_output("rev-parse", "--short", "HEAD"),
        "config_path": str(get_config_path()),
        "db_path": str(get_evolution_db_path()),
        "env_overrides": _interesting_env_overrides(),
        "timestamp_utc": _utc_now(),
    }


def _result(
    *,
    summary: str,
    facts: Mapping[str, Any] | None = None,
    warnings: Sequence[str] | None = None,
    paths: Sequence[str] | None = None,
    suggested_next_tools: Sequence[str] | None = None,
    status: str = "ok",
) -> dict[str, Any]:
    return {
        "status": status,
        "summary": str(summary).strip(),
        "facts": dict(facts or {}),
        "warnings": [str(item) for item in (warnings or []) if str(item).strip()],
        "paths": [_normalize_relpath(item) for item in (paths or []) if str(item).strip()],
        "provenance": _repo_provenance(),
        "suggested_next_tools": [str(item) for item in (suggested_next_tools or []) if str(item).strip()],
    }


def _markdown_linked_records() -> list[Path]:
    return [
        path
        for path in sorted(IMPLEMENTATION_RECORDS_DIR.glob("*.md"))
        if path.name.upper() != "README.MD"
    ]


@lru_cache(maxsize=1)
def _load_manifest_cached(signature: int) -> dict[str, Any]:
    del signature
    return _json_load(MANIFEST_PATH, {})


def _load_manifest() -> dict[str, Any]:
    return _load_manifest_cached(_path_mtime(MANIFEST_PATH))


@lru_cache(maxsize=1)
def _load_record_docs_cached(signature: tuple[tuple[str, int], ...]) -> list[dict[str, Any]]:
    del signature
    documents: list[dict[str, Any]] = []
    for path in _markdown_linked_records():
        text = path.read_text(encoding="utf-8")
        documents.append(
            {
                "slug": path.stem,
                "title": _first_heading(text, path.stem.replace("_", " ")),
                "path": _normalize_relpath(path.relative_to(REPO_ROOT)),
                "text": text,
                "text_lower": text.lower(),
            }
        )
    return documents


def _load_record_docs() -> list[dict[str, Any]]:
    signature = tuple((path.name, _path_mtime(path)) for path in _markdown_linked_records())
    return _load_record_docs_cached(signature)


@lru_cache(maxsize=1)
def _load_worklog_blocks_cached(signature: int) -> list[dict[str, Any]]:
    del signature
    text = WORKLOG_PATH.read_text(encoding="utf-8")
    lines = text.splitlines()
    blocks: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    heading_re = re.compile(r"^(#{2,4})\s+(.*\S)\s*$")
    for line_no, line in enumerate(lines, start=1):
        match = heading_re.match(line)
        if match:
            heading = str(match.group(2)).strip()
            if current is not None:
                current["text"] = "\n".join(current["lines"]).strip()
                blocks.append(current)
            current = {
                "heading": heading,
                "line_start": line_no,
                "lines": [line],
            }
            continue
        if current is not None:
            current["lines"].append(line)
    if current is not None:
        current["text"] = "\n".join(current["lines"]).strip()
        blocks.append(current)
    return blocks


def _load_worklog_blocks() -> list[dict[str, Any]]:
    return _load_worklog_blocks_cached(_path_mtime(WORKLOG_PATH))


def _score_tokens(query: str, text: str) -> int:
    tokens = [token for token in re.split(r"[^A-Za-z0-9]+", query.lower()) if token]
    haystack = text.lower()
    score = 0
    for token in tokens:
        score += haystack.count(token)
    return score


def _resolve_public_scripts(*, source: str = "all", include_private: bool = False) -> list[dict[str, Any]]:
    source_filter = ("tools", "scripts") if source == "all" else (source,)
    entries = discover_scripts(REPO_ROOT, sources=source_filter, include_private=include_private)
    return [
        {
            "source": entry.source,
            "category": entry.category,
            "name": entry.name,
            "tool_id": entry.tool_id,
            "qualified_id": entry.qualified_id,
            "relative_path": entry.relative_path,
            "private": bool(entry.private),
        }
        for entry in entries
    ]


def _resolve_profile_runs() -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    if not PROFILE_ROOT.exists():
        return runs
    for path in sorted(PROFILE_ROOT.glob("run_*"), key=lambda item: _path_mtime(item), reverse=True):
        summary_path = path / "summary.json"
        runs.append(
            {
                "run_id": path.name,
                "path": _normalize_relpath(path.relative_to(REPO_ROOT)),
                "summary_path": _normalize_relpath(summary_path.relative_to(REPO_ROOT)) if summary_path.exists() else "",
                "mtime_ns": _path_mtime(path),
            }
        )
    return runs


def _resolve_profile_summary(run_id: str) -> tuple[Path | None, dict[str, Any] | None]:
    run_key = str(run_id or "").strip()
    runs = _resolve_profile_runs()
    if not runs:
        return (None, None)
    chosen: dict[str, Any] | None = None
    if not run_key or run_key.lower() == "latest":
        chosen = runs[0]
    else:
        for entry in runs:
            if entry["run_id"] == run_key or entry["path"].endswith(run_key):
                chosen = entry
                break
    if not chosen:
        return (None, None)
    summary_path = REPO_ROOT / chosen["summary_path"]
    return (summary_path if summary_path.exists() else None, chosen)


def _resolve_default_team_buff(cfg: Any) -> str:
    if callable(resolve_baseline_team_buff_from_cfg):
        try:
            return resolve_baseline_team_buff_from_cfg(cfg, default="T5")
        except Exception:
            pass

    fallback = str(_cfg_get(cfg, "TeamContributionBuffConstant", "TeamBuff", "T5")).strip().upper()
    return fallback or "T5"


def _effective_settings(workflow: str = "optimizer") -> dict[str, Any]:
    cfg = load_config()
    workflow_key = str(workflow or "optimizer").strip().lower()
    team_buff = _resolve_default_team_buff(cfg)
    optimizer = {
        "meta_finder": _cfg_get_bool(cfg, "IterationEngine", "MetaFinder", False),
        "gpu_mode": _cfg_get_bool(cfg, "IterationEngine", "GPU_Mode", True),
        "gpu_native_ga": _cfg_get_bool(cfg, "IterationEngine", "GPU_Native_GA", True),
        "use_evolution_db": _cfg_get_bool(cfg, "IterationEngine", "UseEvolutionDB", True),
        "ga_search_depth": _safe_int(_cfg_get(cfg, "IterationEngine", "GA_SearchDepth", 0), 0),
        "ga_multi_start": _safe_int(_cfg_get(cfg, "IterationEngine", "GA_MultiStart", 0), 0),
        "ga_db_seed_probability": _cfg_get(cfg, "IterationEngine", "GA_DBSeedProbability", 0),
        "song_repeats": _safe_int(_cfg_get(cfg, "IterationEngine", "SongRepeats", 1), 1),
        "inflight_songs": _safe_int(_cfg_get(cfg, "IterationEngine", "InFlightSongs", 0), 0),
        "fg_candidate_limit": _safe_int(_cfg_get(cfg, "IterationEngine", "FG_CandidateLimit", 0), 0),
        "fg_search_radius": _safe_int(_cfg_get(cfg, "IterationEngine", "FG_SearchRadius", 0), 0),
        "team_buff": team_buff,
        "outer_search_engine": _cfg_get(cfg, "IterationEngine", "OuterSearchEngine", ""),
        "fg_solver_mode": _cfg_get(cfg, "IterationEngine", "FG_SolverMode", ""),
    }
    common = {
        "workflow": workflow_key,
        "config_path": str(get_config_path()),
        "db_path": str(get_evolution_db_path()),
        "env_overrides": _interesting_env_overrides(),
        "optimizer": optimizer,
    }
    if workflow_key == "general-meta":
        common["workflow_settings"] = {
            "db_path": str(get_evolution_db_path()),
            "entrypoint": "general_meta_main.py",
            "team_buff": team_buff,
        }
    elif workflow_key in {"benchmark", "profile", "verification"}:
        common["workflow_settings"] = {
            "team_buff": team_buff,
            "ga_seed": os.environ.get("GA_SEED", ""),
            "song_repeats": optimizer["song_repeats"],
            "fg_search_radius": optimizer["fg_search_radius"],
        }
    else:
        common["workflow_settings"] = optimizer
    return common


def _tool_catalog_summary(*, include_private: bool = False, source: str = "all") -> dict[str, Any]:
    entries = _resolve_public_scripts(source=source, include_private=include_private)
    by_source = Counter(entry["source"] for entry in entries)
    by_category = Counter(f'{entry["source"]}:{entry["category"]}' for entry in entries)
    ambiguous = defaultdict(list)
    for entry in entries:
        ambiguous[entry["name"]].append(entry["qualified_id"])
    conflicts = {name: sorted(values) for name, values in ambiguous.items() if len(values) > 1}
    return {
        "entries": entries,
        "by_source": dict(sorted(by_source.items())),
        "by_category": dict(sorted(by_category.items())),
        "ambiguous_names": conflicts,
    }


def _public_tool_catalog(*, include_private: bool = False, source: str = "all", category: str = "") -> dict[str, Any]:
    data = _tool_catalog_summary(include_private=include_private, source=source)
    entries = list(data["entries"])
    if category:
        entries = [
            entry
            for entry in entries
            if str(entry["category"]).startswith(str(category).strip())
        ]
    return {
        "entries": entries,
        "by_source": data["by_source"],
        "by_category": data["by_category"],
        "ambiguous_names": data["ambiguous_names"],
    }


def _recent_record_matches(query: str, limit: int) -> list[dict[str, Any]]:
    query_text = str(query or "").strip()
    docs = _load_record_docs()
    scored: list[tuple[int, dict[str, Any]]] = []
    for doc in docs:
        score = _score_tokens(query_text, f'{doc["slug"]} {doc["title"]} {doc["text"]}')
        if score <= 0 and query_text:
            continue
        scored.append((score, doc))
    scored.sort(key=lambda item: (-item[0], item[1]["slug"]))
    results: list[dict[str, Any]] = []
    for score, doc in scored[: max(1, int(limit))]:
        results.append(
            {
                "slug": doc["slug"],
                "title": doc["title"],
                "path": doc["path"],
                "score": int(score),
                "snippet": _compact_text(doc["text"], max_chars=380),
            }
        )
    return results


def _search_worklog_lines(query: str, limit: int) -> list[dict[str, Any]]:
    text = WORKLOG_PATH.read_text(encoding="utf-8")
    lines = text.splitlines()
    tokens = [token for token in re.split(r"[^A-Za-z0-9]+", query.lower()) if token]
    matches: list[dict[str, Any]] = []
    for line_no, line in enumerate(lines, start=1):
        lowered = line.lower()
        if tokens and not all(token in lowered for token in tokens):
            continue
        start = max(0, line_no - 2)
        end = min(len(lines), line_no + 1)
        snippet = "\n".join(lines[start:end]).strip()
        matches.append(
            {
                "line": line_no,
                "path": _normalize_relpath(WORKLOG_PATH.relative_to(REPO_ROOT)),
                "snippet": _compact_text(snippet, max_chars=420),
            }
        )
        if len(matches) >= max(1, int(limit)):
            break
    return matches


def _recent_handoff_block() -> dict[str, Any]:
    blocks = _load_worklog_blocks()
    if not blocks:
        return {}
    latest = blocks[-1]
    text = str(latest.get("text", "") or "")
    branch_match = re.search(r"Branch:\s*`([^`]+)`", text)
    head_match = re.search(r"HEAD[^`]*`([^`]+)`", text)
    next_match = re.search(r"(?im)^- Next:\s*(.+)$", text)
    status_match = re.search(r"(?im)^- Current status:\s*(.+)$", text)
    return {
        "heading": latest.get("heading", ""),
        "line_start": latest.get("line_start", 0),
        "path": _normalize_relpath(WORKLOG_PATH.relative_to(REPO_ROOT)),
        "branch": branch_match.group(1) if branch_match else "",
        "head": head_match.group(1) if head_match else "",
        "status": status_match.group(1).strip() if status_match else "",
        "next_step": next_match.group(1).strip() if next_match else "",
        "snippet": _compact_text(text, max_chars=900),
    }


def _record_by_slug(slug: str) -> dict[str, Any] | None:
    target = str(slug or "").strip()
    for doc in _load_record_docs():
        if doc["slug"].lower() == target.lower():
            return doc
    return None


def _db_connect(db_path: str | None = None) -> sqlite3.Connection | None:
    chosen = str(db_path or get_evolution_db_path())
    try:
        return get_db_connection_readonly(chosen)
    except Exception:
        return None


def _table_row_count(conn: sqlite3.Connection, table: str) -> int:
    try:
        row = conn.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()
    except sqlite3.Error:
        return 0
    if row is None:
        return 0
    if isinstance(row, sqlite3.Row):
        return int(row["count"] or 0)
    return int(row[0] or 0)


def _db_summary(db_path: str | None = None) -> dict[str, Any]:
    chosen_path = str(db_path or get_evolution_db_path())
    db_file = Path(chosen_path)
    if not db_file.exists():
        return {
            "db_path": chosen_path,
            "exists": False,
            "tables": {},
            "file_size_bytes": 0,
        }
    conn = _db_connect(chosen_path)
    if conn is None:
        return {
            "db_path": chosen_path,
            "exists": True,
            "tables": {},
            "file_size_bytes": int(db_file.stat().st_size),
            "warning": "failed_to_open_readonly",
        }
    try:
        tables = {}
        for table in ("songs", "team_buff_loadouts", "team_buff_fg_loadouts"):
            tables[table] = _table_row_count(conn, table)
        return {
            "db_path": chosen_path,
            "exists": True,
            "tables": tables,
            "file_size_bytes": int(db_file.stat().st_size),
            "mtime_utc": datetime.fromtimestamp(db_file.stat().st_mtime, tz=UTC).isoformat(timespec="seconds"),
        }
    finally:
        conn.close()


def _song_query(song_name: str, *, team_buff: str | None = None, limit: int = 5, db_path: str | None = None) -> dict[str, Any]:
    chosen_path = str(db_path or get_evolution_db_path())
    conn = _db_connect(chosen_path)
    if conn is None:
        return {
            "song_name": song_name,
            "team_buff": team_buff or "T5",
            "db_path": chosen_path,
            "found": False,
            "warning": "failed_to_open_db",
        }
    cfg = load_config()
    resolved_team_buff = str(team_buff or _resolve_default_team_buff(cfg)).strip().upper() or "T5"
    out: dict[str, Any] = {
        "song_name": str(song_name),
        "team_buff": resolved_team_buff,
        "db_path": chosen_path,
        "found": False,
        "song_row": {},
        "base_top": [],
        "fg_top": [],
    }
    try:
        try:
            song_row = conn.execute(
                """
                SELECT name, best_score, best_fg_score, last_updated, attempt_lifetime, attempts_first
                FROM songs
                WHERE name = ?
                """,
                (song_name,),
            ).fetchone()
        except sqlite3.Error:
            song_row = None
        if song_row is not None:
            out["song_row"] = dict(song_row)
            out["found"] = True
        for table, order_col, key in (
            ("team_buff_loadouts", "score", "base_top"),
            ("team_buff_fg_loadouts", "fg_score", "fg_top"),
        ):
            try:
                rows = conn.execute(
                    f"""
                    SELECT song_name, team_buff, score, fg_score, timestamp, details_json
                    FROM {table}
                    WHERE song_name = ? AND team_buff = ?
                    ORDER BY {order_col} DESC, score DESC
                    LIMIT ?
                    """,
                    (song_name, resolved_team_buff, max(1, int(limit))),
                ).fetchall()
            except sqlite3.Error:
                rows = []
            packed_rows = []
            for row in rows:
                entry = {
                    "score": int(row["score"] or 0),
                    "fg_score": int(row["fg_score"] or 0),
                    "timestamp": row["timestamp"],
                }
                details_json = row["details_json"] if "details_json" in row.keys() else None
                if details_json:
                    try:
                        details = json.loads(details_json)
                        entry["ft"] = details.get("FT")
                        entry["ff"] = details.get("FF")
                    except Exception:
                        pass
                packed_rows.append(entry)
            out[key] = packed_rows
            if packed_rows:
                out["found"] = True
    finally:
        conn.close()
    return out


def _run_artifact_dir(kind: str) -> Path:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", str(kind or "run")).strip("-") or "run"
    path = ARTIFACT_ROOT / f"{datetime.now(tz=UTC).strftime('%Y%m%d_%H%M%S')}_{slug}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _run_command(
    *,
    slug: str,
    command: Sequence[str],
    timeout_sec: int,
    env_overrides: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    env = os.environ.copy()
    if env_overrides:
        env.update({str(key): str(value) for key, value in env_overrides.items()})
    artifact_dir = _run_artifact_dir(slug)
    stdout_path = artifact_dir / "stdout.log"
    stderr_path = artifact_dir / "stderr.log"
    started_at = time.perf_counter()
    completed = subprocess.run(
        list(command),
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=max(1, int(timeout_sec)),
        check=False,
        env=env,
        stdin=subprocess.DEVNULL,
    )
    duration_sec = time.perf_counter() - started_at
    stdout_path.write_text(str(completed.stdout or ""), encoding="utf-8")
    stderr_path.write_text(str(completed.stderr or ""), encoding="utf-8")
    return {
        "command": list(command),
        "return_code": int(completed.returncode),
        "duration_sec": round(float(duration_sec), 3),
        "stdout_path": _normalize_relpath(stdout_path.relative_to(REPO_ROOT)),
        "stderr_path": _normalize_relpath(stderr_path.relative_to(REPO_ROOT)),
        "stdout_excerpt": _compact_text(completed.stdout or "", max_chars=800),
        "stderr_excerpt": _compact_text(completed.stderr or "", max_chars=800),
        "artifacts": [
            _normalize_relpath(artifact_dir.relative_to(REPO_ROOT)),
            _normalize_relpath(stdout_path.relative_to(REPO_ROOT)),
            _normalize_relpath(stderr_path.relative_to(REPO_ROOT)),
        ],
    }


def _classify_paths(changed_paths: Sequence[str]) -> str:
    normalized = [_normalize_relpath(path) for path in changed_paths if str(path).strip()]
    if normalized and all(path.startswith("docs/") or path in {"README.md", "CONTRIBUTING.md"} for path in normalized):
        return "docs-only"
    if any(path.startswith("tools/_mcp_harness/") or path == "tools/mcp_server.py" or path == ".codex/config.toml" for path in normalized):
        return "mcp-harness"
    if any(path.startswith("gear_optimizer/data/") or path.startswith("tools/db/") for path in normalized):
        return "database"
    if any(path.startswith("gear_optimizer/solver/") or "gpu" in path.lower() or "taichi" in path.lower() for path in normalized):
        return "gpu-core"
    if any(path.startswith("tools/") for path in normalized):
        return "repo-tools"
    return "repo-tools"


def _changed_paths(include_git_status: bool = True) -> list[str]:
    entries = _git_status_entries() if include_git_status else []
    manifest = _load_manifest()
    ignore_prefixes = tuple(manifest.get("ignore_path_prefixes") or [])
    changed: list[str] = []
    for entry in entries:
        path = str(entry["path"])
        if any(path.startswith(prefix) for prefix in ignore_prefixes):
            continue
        changed.append(path)
    return changed


def _public_python_script(path: str) -> bool:
    normalized = _normalize_relpath(path)
    parts = normalized.split("/")
    if not normalized.endswith(".py"):
        return False
    if any(part.startswith("_") for part in parts[:-1]):
        return False
    if parts[-1].startswith("_") or parts[-1] in {"__init__.py", "__main__.py", "cli.py"}:
        return False
    return True


def _find_harness_gaps(changed_paths: Sequence[str] | None = None, *, include_git_status: bool = True, max_results: int = 10) -> list[dict[str, Any]]:
    manifest = _load_manifest()
    subsystems = list(manifest.get("subsystems") or [])
    review_triggers = list(manifest.get("review_triggers") or [])
    paths = [_normalize_relpath(path) for path in (changed_paths or _changed_paths(include_git_status=include_git_status))]
    results: list[dict[str, Any]] = []
    seen_titles: set[str] = set()
    for path in paths:
        matched = [
            subsystem
            for subsystem in subsystems
            if any(path.startswith(prefix) for prefix in subsystem.get("path_prefixes", []))
        ]
        if not matched:
            title = f"Unmapped changed area: {path}"
            if title not in seen_titles:
                seen_titles.add(title)
                results.append(
                    {
                        "title": title,
                        "path": path,
                        "reason": "This changed path is not covered by the harness manifest and should be reviewed for first-class MCP coverage.",
                        "priority": "high",
                        "score": 100,
                        "suggested_capability": "Add manifest coverage and, if the surface is repeated/high-value, add a compact MCP tool or resource.",
                    }
                )
        if _public_python_script(path) and (
            path.startswith("tools/bench/")
            or path.startswith("tools/db/")
            or path.startswith("tools/profile/")
            or path.startswith("tools/verify/")
            or path.startswith("scripts/query/")
            or path.startswith("scripts/regression/")
        ):
            title = f"Review script for MCP promotion: {path}"
            if title not in seen_titles:
                seen_titles.add(title)
                results.append(
                    {
                        "title": title,
                        "path": path,
                        "reason": "Changed public engineering scripts are common repeated surfaces; promote them when they answer recurring questions or save multi-file context reads.",
                        "priority": "medium",
                        "score": 80,
                        "suggested_capability": "Consider a first-class MCP wrapper or a richer structured result in an existing namespace.",
                    }
                )
        for trigger in review_triggers:
            if any(path.startswith(prefix) for prefix in trigger.get("path_prefixes", [])):
                title = f'{trigger.get("name", "Harness review trigger")}: {path}'
                if title not in seen_titles:
                    seen_titles.add(title)
                    results.append(
                        {
                            "title": title,
                            "path": path,
                            "reason": str(trigger.get("reason", "")).strip(),
                            "priority": "medium",
                            "score": 70,
                            "suggested_capability": "Review whether the changed surface keeps common repo questions answerable in 1-2 MCP calls.",
                        }
                    )
    results.sort(key=lambda item: (-int(item.get("score", 0)), str(item.get("path", ""))))
    return results[: max(1, int(max_results))]


def _tool_allowed(tool_id: str) -> bool:
    target = str(tool_id or "").strip()
    if target in DENIED_REPO_TOOL_IDS:
        return False
    return any(target.startswith(prefix) for prefix in SAFE_REPO_TOOL_PREFIXES)


def _resolve_target_tool(tool_id: str) -> dict[str, Any] | None:
    for entry in _resolve_public_scripts(source="tools", include_private=False):
        if entry["qualified_id"] == tool_id or entry["tool_id"] == tool_id or entry["name"] == tool_id:
            return entry
    return None


def _protocol_summary() -> dict[str, Any]:
    settings = _effective_settings("benchmark")
    rules = [
        "Freeze workload knobs for comparisons: SongRepeats, queue limits, search radius, and seed strategy.",
        "Report both throughput and FG debt/coverage; throughput-only wins are rejected when FG debt regresses.",
        "Prefer explicit GA_SEED / SONG_REPEATS / FG_SEARCH_RADIUS overrides in the protocol run provenance.",
    ]
    blocking_warnings = []
    return {
        "rules": rules,
        "effective_settings": settings["workflow_settings"],
        "blocking_warnings": blocking_warnings,
    }


HARNESS = FastMCP(
    name=REPO_MCP_SERVER_NAME,
    instructions=(
        "Use this repo-local engineering harness when you need compact, repo-specific answers in 1-2 calls. "
        "Prefer it over manual file spelunking for effective settings, history, DB state, profile analysis, "
        "verification planning, and reproducible benchmark context."
    ),
)


READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
GATED_EXEC = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False)


@HARNESS.resource(
    "repo://context",
    name="repo-context",
    description="Compact repository context: branch, dirty state, entrypoints, and next MCP calls.",
    mime_type="application/json",
)
def repo_context_resource() -> dict[str, Any]:
    return repo_get_context()["facts"]


@HARNESS.resource(
    "repo://guardrails",
    name="repo-guardrails",
    description="Current repo guardrails and engineering policy that the harness enforces.",
    mime_type="application/json",
)
def repo_guardrails_resource() -> dict[str, Any]:
    return repo_get_guardrails()["facts"]


@HARNESS.resource(
    "repo://modules",
    name="repo-modules",
    description="High-level module map for the repo entrypoints and ownership boundaries.",
    mime_type="application/json",
)
def repo_modules_resource() -> dict[str, Any]:
    return {"modules": STATIC_MODULE_MAP}


@HARNESS.resource(
    "tools://catalog",
    name="tools-catalog",
    description="Structured list of public repo tools and categories.",
    mime_type="application/json",
)
def tools_catalog_resource() -> dict[str, Any]:
    return _public_tool_catalog()


@HARNESS.resource(
    "verify://matrix",
    name="verify-matrix",
    description="Verification matrix used to turn changed paths into required and optional checks.",
    mime_type="application/json",
)
def verify_matrix_resource() -> dict[str, Any]:
    return VERIFY_MATRIX


@HARNESS.resource(
    "config://effective/{workflow}",
    name="effective-settings",
    description="Workflow-specific effective settings with config/env precedence already resolved.",
    mime_type="application/json",
)
def effective_settings_resource(workflow: str) -> dict[str, Any]:
    return _effective_settings(unquote(workflow))


@HARNESS.resource(
    "history://record/{slug}",
    name="implementation-record",
    description="One implementation record by slug in compact form.",
    mime_type="application/json",
)
def history_record_resource(slug: str) -> dict[str, Any]:
    record = _record_by_slug(unquote(slug))
    if not record:
        return {"status": "error", "summary": "Record not found", "slug": slug}
    return {
        "slug": record["slug"],
        "title": record["title"],
        "path": record["path"],
        "body": _compact_text(record["text"], max_chars=2000),
    }


@HARNESS.resource(
    "history://worklog/{query}",
    name="worklog-query",
    description="Compact worklog matches for a keyword or subsystem query.",
    mime_type="application/json",
)
def history_worklog_resource(query: str) -> dict[str, Any]:
    decoded = unquote(query)
    return {
        "query": decoded,
        "matches": _search_worklog_lines(decoded, limit=8),
    }


@HARNESS.resource(
    "profile://run/{run_id}",
    name="profile-run-summary",
    description="Compact summary for one profile run directory.",
    mime_type="application/json",
)
def profile_run_resource(run_id: str) -> dict[str, Any]:
    response = profile_get_run_summary(unquote(run_id))
    return response["facts"]


@HARNESS.resource(
    "db://song/{song_name}",
    name="db-song-summary",
    description="Compact DB summary for a specific song name.",
    mime_type="application/json",
)
def db_song_resource(song_name: str) -> dict[str, Any]:
    response = db_query_song(unquote(song_name))
    return response["facts"]


@HARNESS.tool(
    name="repo.get_context",
    description="Use this when you need the repo state, entrypoints, dirty summary, and the next best harness calls in one compact response.",
    annotations=READ_ONLY,
    structured_output=True,
)
def repo_get_context() -> dict[str, Any]:
    status_entries = _git_status_entries()
    tracked_dirty = [entry["path"] for entry in status_entries if entry["tracked"]]
    untracked = [entry["path"] for entry in status_entries if not entry["tracked"]]
    summary = (
        f'Repo context ready: branch `{_git_output("branch", "--show-current")}` at `{_git_output("rev-parse", "--short", "HEAD")}` '
        f'with {len(tracked_dirty)} tracked changes and {len(untracked)} untracked paths.'
    )
    facts = {
        "repo_root": str(REPO_ROOT),
        "branch": _git_output("branch", "--show-current"),
        "head": _git_output("rev-parse", "--short", "HEAD"),
        "entrypoints": STATIC_MODULE_MAP,
        "tracked_dirty_paths": tracked_dirty,
        "untracked_paths": untracked,
        "tool_count": len(_public_tool_catalog()["entries"]),
        "config_path": str(get_config_path()),
    }
    return _result(
        summary=summary,
        facts=facts,
        suggested_next_tools=[
            "repo.get_effective_settings",
            "history.get_recent_handoff",
            "verify.suggest_checks",
        ],
        paths=["docs/NAVIGATION.md", "docs/CODEX_WORKLOG.md"],
    )


@HARNESS.tool(
    name="repo.get_guardrails",
    description="Use this when you need the repo-specific engineering rules, GPU-only policy, docs obligations, and maintenance contract in one answer.",
    annotations=READ_ONLY,
    structured_output=True,
)
def repo_get_guardrails() -> dict[str, Any]:
    return _result(
        summary="Repo guardrails loaded: GPU-only production, durable docs/worklog discipline, and self-maintaining MCP-harness policy.",
        facts=GUARDRAILS,
        paths=["AGENTS.md", "docs/ENGINEERING_PRINCIPLES.md", "docs/MCP_HARNESS_CHARTER.md"],
        suggested_next_tools=["repo.get_effective_settings", "repo.get_harness_charter"],
    )


@HARNESS.tool(
    name="repo.get_effective_settings",
    description="Use this when you need the effective config plus env overrides for optimizer, benchmark, profile, verification, or general-meta workflows.",
    annotations=READ_ONLY,
    structured_output=True,
)
def repo_get_effective_settings(workflow: str = "optimizer") -> dict[str, Any]:
    settings = _effective_settings(workflow)
    warnings = []
    return _result(
        summary=f"Effective settings resolved for workflow `{workflow}` with config/env precedence already merged.",
        facts=settings,
        warnings=warnings,
        paths=[str(get_config_path()), "gear_optimizer/core/config.py", "gear_optimizer/core/env_config.py"],
        suggested_next_tools=["verify.suggest_checks", "bench.summarize_protocol"],
    )


@HARNESS.tool(
    name="repo.list_tools",
    description="Use this when you need the maintained tool/script catalog without reading the filesystem manually.",
    annotations=READ_ONLY,
    structured_output=True,
)
def repo_list_tools(source: str = "all", include_private: bool = False, category: str = "") -> dict[str, Any]:
    catalog = _public_tool_catalog(include_private=include_private, source=source, category=category)
    return _result(
        summary=f"Catalog ready: {len(catalog['entries'])} matching script entries.",
        facts=catalog,
        suggested_next_tools=["verify.run_repo_tool", "repo.audit_tools"],
        paths=["tools/cli.py"],
    )


@HARNESS.tool(
    name="repo.audit_tools",
    description="Use this when you want a compact structured audit of the repo tool inventory, ambiguity, and private-script counts.",
    annotations=READ_ONLY,
    structured_output=True,
)
def repo_audit_tools(source: str = "all", include_private: bool = True) -> dict[str, Any]:
    catalog = _tool_catalog_summary(include_private=include_private, source=source)
    facts = {
        "counts": {
            "entries": len(catalog["entries"]),
            "private_entries": sum(1 for entry in catalog["entries"] if entry["private"]),
            "public_entries": sum(1 for entry in catalog["entries"] if not entry["private"]),
        },
        "by_source": catalog["by_source"],
        "by_category": catalog["by_category"],
        "ambiguous_names": catalog["ambiguous_names"],
    }
    return _result(
        summary="Tool audit ready with source/category counts and ambiguous short-name warnings.",
        facts=facts,
        suggested_next_tools=["repo.list_tools", "repo.find_harness_gaps"],
        paths=["tools/cli.py"],
    )


@HARNESS.tool(
    name="repo.get_harness_charter",
    description="Use this when you need the MCP-harness charter, its goals, and the autonomous maintenance contract in one compact response.",
    annotations=READ_ONLY,
    structured_output=True,
)
def repo_get_harness_charter() -> dict[str, Any]:
    text = CHARTER_PATH.read_text(encoding="utf-8") if CHARTER_PATH.exists() else ""
    return _result(
        summary="Harness charter loaded.",
        facts={
            "path": _normalize_relpath(CHARTER_PATH.relative_to(REPO_ROOT)),
            "title": _first_heading(text, "MCP Harness Charter"),
            "body": _compact_text(text, max_chars=1800),
        },
        paths=[_normalize_relpath(CHARTER_PATH.relative_to(REPO_ROOT))],
        suggested_next_tools=["repo.get_harness_coverage", "repo.find_harness_gaps"],
    )


@HARNESS.tool(
    name="repo.get_harness_coverage",
    description="Use this when you need the current MCP-harness coverage map, principles, and subsystem ownership surface.",
    annotations=READ_ONLY,
    structured_output=True,
)
def repo_get_harness_coverage() -> dict[str, Any]:
    manifest = _load_manifest()
    return _result(
        summary=f"Harness coverage loaded for {len(manifest.get('subsystems', []))} subsystems.",
        facts=manifest,
        paths=[_normalize_relpath(MANIFEST_PATH.relative_to(REPO_ROOT))],
        suggested_next_tools=["repo.find_harness_gaps", "repo.get_harness_charter"],
    )


@HARNESS.tool(
    name="repo.find_harness_gaps",
    description="Use this when changed files may require MCP-harness maintenance; it ranks missing or review-worthy coverage candidates automatically.",
    annotations=READ_ONLY,
    structured_output=True,
)
def repo_find_harness_gaps(changed_paths: list[str] | None = None, include_git_status: bool = True, max_results: int = 10) -> dict[str, Any]:
    findings = _find_harness_gaps(changed_paths, include_git_status=include_git_status, max_results=max_results)
    summary = "No obvious harness gaps found." if not findings else f"Found {len(findings)} harness maintenance candidates."
    return _result(
        summary=summary,
        facts={
            "changed_paths": changed_paths or _changed_paths(include_git_status=include_git_status),
            "findings": findings,
        },
        paths=[_normalize_relpath(MANIFEST_PATH.relative_to(REPO_ROOT))],
        suggested_next_tools=["repo.get_harness_coverage", "repo.list_tools"],
        status="ok" if not findings else "warning",
    )


@HARNESS.tool(
    name="history.find_relevant_records",
    description="Use this when you need the most relevant implementation records for a subsystem, bug family, or engineering topic without manually reading the docs tree.",
    annotations=READ_ONLY,
    structured_output=True,
)
def history_find_relevant_records(query: str, limit: int = 5) -> dict[str, Any]:
    matches = _recent_record_matches(query, limit=limit)
    summary = "No matching implementation records found." if not matches else f"Found {len(matches)} relevant implementation records."
    return _result(
        summary=summary,
        facts={"query": query, "records": matches},
        paths=["docs/Implementation Records/README.md"],
        suggested_next_tools=["history.get_record", "history.search_worklog"],
        status="ok" if matches else "warning",
    )


@HARNESS.tool(
    name="history.get_recent_handoff",
    description="Use this when you need the latest worklog handoff state, next step, branch, and resumable context in one response.",
    annotations=READ_ONLY,
    structured_output=True,
)
def history_get_recent_handoff() -> dict[str, Any]:
    handoff = _recent_handoff_block()
    status = "ok" if handoff else "warning"
    summary = "Latest worklog handoff loaded." if handoff else "Worklog handoff block not found."
    return _result(
        summary=summary,
        facts=handoff,
        paths=["docs/CODEX_WORKLOG.md"],
        suggested_next_tools=["history.search_worklog", "history.find_relevant_records"],
        status=status,
    )


@HARNESS.tool(
    name="history.search_worklog",
    description="Use this when you need compact worklog matches by keyword, branch name, file path, or subsystem name.",
    annotations=READ_ONLY,
    structured_output=True,
)
def history_search_worklog(query: str, limit: int = 8) -> dict[str, Any]:
    matches = _search_worklog_lines(query, limit=limit)
    return _result(
        summary=f"Found {len(matches)} worklog matches for `{query}`." if matches else f"No worklog matches found for `{query}`.",
        facts={"query": query, "matches": matches},
        paths=["docs/CODEX_WORKLOG.md"],
        suggested_next_tools=["history.get_recent_handoff", "history.find_relevant_records"],
        status="ok" if matches else "warning",
    )


@HARNESS.tool(
    name="history.get_record",
    description="Use this when you know the implementation-record slug and want the compact body plus path immediately.",
    annotations=READ_ONLY,
    structured_output=True,
)
def history_get_record(slug: str) -> dict[str, Any]:
    record = _record_by_slug(slug)
    if record is None:
        return _result(
            summary=f"Implementation record `{slug}` was not found.",
            facts={"slug": slug},
            paths=["docs/Implementation Records/README.md"],
            suggested_next_tools=["history.find_relevant_records"],
            status="warning",
        )
    return _result(
        summary=f"Implementation record `{record['slug']}` loaded.",
        facts={
            "slug": record["slug"],
            "title": record["title"],
            "path": record["path"],
            "body": _compact_text(record["text"], max_chars=2200),
        },
        paths=[record["path"]],
        suggested_next_tools=["history.search_worklog", "history.find_relevant_records"],
    )


@HARNESS.tool(
    name="db.get_summary",
    description="Use this when you need the current DB path, table counts, size, and recency without opening SQLite manually.",
    annotations=READ_ONLY,
    structured_output=True,
)
def db_get_summary(db_path: str = "") -> dict[str, Any]:
    facts = _db_summary(db_path or None)
    return _result(
        summary=f"DB summary ready for `{facts['db_path']}`." if facts.get("exists") else f"DB file `{facts['db_path']}` does not exist.",
        facts=facts,
        suggested_next_tools=["db.query_song", "repo.get_effective_settings"],
        paths=[facts["db_path"]] if facts.get("db_path") else [],
        status="ok" if facts.get("exists") else "warning",
    )


@HARNESS.tool(
    name="db.query_song",
    description="Use this when you need the persisted base/FG leaderboard facts for one song in 1 call instead of manual SQL or script runs.",
    annotations=READ_ONLY,
    structured_output=True,
)
def db_query_song(song_name: str, team_buff: str = "", limit: int = 5, db_path: str = "") -> dict[str, Any]:
    facts = _song_query(song_name, team_buff=team_buff or None, limit=limit, db_path=db_path or None)
    warnings = []
    if not facts.get("found"):
        warnings.append("Song not found in songs or leaderboard tables for the requested team buff.")
    return _result(
        summary=f"DB song summary ready for `{song_name}`." if facts.get("found") else f"No DB entries found for `{song_name}`.",
        facts=facts,
        warnings=warnings,
        suggested_next_tools=["db.compare_song_to_db_top", "db.get_summary"],
        paths=[facts["db_path"]],
        status="ok" if facts.get("found") else "warning",
    )


@HARNESS.tool(
    name="db.compare_song_to_db_top",
    description="Use this when you have a candidate base/FG score and want a compact answer about whether it beats or trails the persisted DB top.",
    annotations=READ_ONLY,
    structured_output=True,
)
def db_compare_song_to_db_top(
    song_name: str,
    candidate_score: int,
    candidate_fg_score: int = 0,
    team_buff: str = "",
    db_path: str = "",
) -> dict[str, Any]:
    facts = _song_query(song_name, team_buff=team_buff or None, limit=1, db_path=db_path or None)
    song_row = facts.get("song_row") or {}
    best_score = _safe_int(song_row.get("best_score", 0), 0)
    best_fg = _safe_int(song_row.get("best_fg_score", 0), 0)
    comparison = {
        "candidate_score": int(candidate_score),
        "candidate_fg_score": int(candidate_fg_score),
        "db_best_score": best_score,
        "db_best_fg_score": best_fg,
        "beats_base": int(candidate_score) > best_score,
        "ties_base": int(candidate_score) == best_score,
        "beats_fg": int(candidate_fg_score) > best_fg,
        "ties_fg": int(candidate_fg_score) == best_fg,
    }
    return _result(
        summary=f"Compared candidate scores against persisted DB tops for `{song_name}`.",
        facts={
            "song_name": song_name,
            "team_buff": facts.get("team_buff"),
            "comparison": comparison,
            "song_row": song_row,
        },
        suggested_next_tools=["db.query_song", "verify.run_db_audit"],
        paths=[facts.get("db_path", "")],
    )


@HARNESS.tool(
    name="artifacts.list_recent",
    description="Use this when you need the most recent profile or harness artifacts without manually browsing artifacts or bin.",
    annotations=READ_ONLY,
    structured_output=True,
)
def artifacts_list_recent(category: str = "all", limit: int = 10) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    category_key = str(category or "all").strip().lower()
    roots = []
    if category_key in {"all", "profile"}:
        roots.append(PROFILE_ROOT)
    if category_key in {"all", "mcp"}:
        roots.append(ARTIFACT_ROOT)
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            items.append(
                {
                    "path": _normalize_relpath(path.relative_to(REPO_ROOT)),
                    "size_bytes": int(path.stat().st_size),
                    "mtime_utc": datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).isoformat(timespec="seconds"),
                }
            )
    items.sort(key=lambda item: item["mtime_utc"], reverse=True)
    items = items[: max(1, int(limit))]
    return _result(
        summary=f"Found {len(items)} recent artifact files for category `{category_key}`.",
        facts={"category": category_key, "items": items},
        suggested_next_tools=["profile.get_run_summary", "profile.analyze_run"],
        paths=[_normalize_relpath(PROFILE_ROOT.relative_to(REPO_ROOT)), _normalize_relpath(ARTIFACT_ROOT.relative_to(REPO_ROOT))],
    )


@HARNESS.tool(
    name="profile.get_run_summary",
    description="Use this when you need a compact structured summary for a profiling run directory instead of reading summary.json manually.",
    annotations=READ_ONLY,
    structured_output=True,
)
def profile_get_run_summary(run_id: str = "latest") -> dict[str, Any]:
    summary_path, chosen = _resolve_profile_summary(run_id)
    if summary_path is None or chosen is None:
        return _result(
            summary=f"Profile run `{run_id}` was not found.",
            facts={"run_id": run_id},
            suggested_next_tools=["artifacts.list_recent"],
            status="warning",
        )
    payload = _json_load(summary_path, {})
    facts = {key: payload.get(key) for key in PROFILE_SUMMARY_KEYS if key in payload}
    facts["run_id"] = chosen["run_id"]
    facts["path"] = chosen["path"]
    facts["summary_path"] = chosen["summary_path"]
    return _result(
        summary=f"Profile run summary ready for `{chosen['run_id']}`.",
        facts=facts,
        suggested_next_tools=["profile.analyze_run", "bench.compare_runs"],
        paths=[chosen["path"], chosen["summary_path"]],
    )


@HARNESS.tool(
    name="profile.analyze_run",
    description="Use this when you want the ranked bottlenecks and anomaly analysis for a profiling run in one compact call.",
    annotations=READ_ONLY,
    structured_output=True,
)
def profile_analyze_run(run_id: str = "latest") -> dict[str, Any]:
    summary_path, chosen = _resolve_profile_summary(run_id)
    if summary_path is None or chosen is None:
        return _result(
            summary=f"Profile run `{run_id}` was not found.",
            facts={"run_id": run_id},
            suggested_next_tools=["artifacts.list_recent"],
            status="warning",
        )
    payload = _json_load(summary_path, {})
    events_path_raw = str(((payload.get("paths") or {}).get("profile_events_jsonl") or "").strip())
    analysis = analyze_summary(payload, events_path=Path(events_path_raw) if events_path_raw else None)
    anomalies = list(analysis.get("anomalies") or [])
    return _result(
        summary=f"Profile analysis ready for `{chosen['run_id']}` with {len(anomalies)} anomalies.",
        facts={
            "run_id": chosen["run_id"],
            "summary_path": chosen["summary_path"],
            "analysis": analysis,
        },
        suggested_next_tools=["profile.get_run_summary", "bench.compare_runs"],
        paths=[chosen["summary_path"]],
    )


@HARNESS.tool(
    name="verify.get_matrix",
    description="Use this when you want the required and optional validation matrix for changed paths or a subsystem category.",
    annotations=READ_ONLY,
    structured_output=True,
)
def verify_get_matrix(changed_paths: list[str] | None = None) -> dict[str, Any]:
    paths = changed_paths or _changed_paths(include_git_status=True)
    matrix_key = _classify_paths(paths)
    facts = {
        "changed_paths": paths,
        "category": matrix_key,
        "matrix": VERIFY_MATRIX.get(matrix_key, VERIFY_MATRIX["repo-tools"]),
    }
    return _result(
        summary=f"Verification matrix resolved for category `{matrix_key}`.",
        facts=facts,
        suggested_next_tools=["verify.suggest_checks", "repo.find_harness_gaps"],
        paths=["tools/dev/quality_check.ps1", "pyproject.toml"],
    )


@HARNESS.tool(
    name="verify.suggest_checks",
    description="Use this when you need the exact next commands to validate the current change safely and with minimal unnecessary work.",
    annotations=READ_ONLY,
    structured_output=True,
)
def verify_suggest_checks(changed_paths: list[str] | None = None, goal: str = "") -> dict[str, Any]:
    matrix = verify_get_matrix(changed_paths)
    facts = dict(matrix["facts"])
    recommended = list((facts.get("matrix") or {}).get("required") or [])
    optional = list((facts.get("matrix") or {}).get("optional") or [])
    if goal and "benchmark" in str(goal).lower():
        optional.append("bench.summarize_protocol")
    return _result(
        summary=f"Recommended {len(recommended)} required checks for category `{facts.get('category', '')}`.",
        facts={
            "changed_paths": facts.get("changed_paths", []),
            "category": facts.get("category"),
            "required_commands": recommended,
            "optional_commands": optional,
            "why": (facts.get("matrix") or {}).get("why", ""),
        },
        suggested_next_tools=["verify.run_quality_check", "verify.run_pytest_slice", "verify.run_repo_tool"],
        paths=["tools/dev/quality_check.ps1"],
    )


@HARNESS.tool(
    name="verify.run_quality_check",
    description="Use this when you want the canonical repo quality harness executed locally instead of manually composing lint/test commands.",
    annotations=GATED_EXEC,
    structured_output=True,
)
def verify_run_quality_check(ci: bool = False, fix: bool = False, strict_format: bool = False, timeout_sec: int = 1800) -> dict[str, Any]:
    command = ["powershell", "-ExecutionPolicy", "Bypass", "-File", "tools/dev/quality_check.ps1"]
    if ci:
        command.append("-CI")
    if fix:
        command.append("-Fix")
    if strict_format:
        command.append("-StrictFormat")
    run = _run_command(slug="quality-check", command=command, timeout_sec=timeout_sec)
    return _result(
        summary=f"Quality harness completed with exit code {run['return_code']}.",
        facts=run,
        warnings=[run["stderr_excerpt"]] if run["stderr_excerpt"] else [],
        paths=run["artifacts"],
        suggested_next_tools=["verify.suggest_checks", "history.get_recent_handoff"],
        status="ok" if int(run["return_code"]) == 0 else "warning",
    )


@HARNESS.tool(
    name="verify.run_pytest_slice",
    description="Use this when you need a targeted pytest slice executed safely with explicit selectors and no arbitrary shell passthrough.",
    annotations=GATED_EXEC,
    structured_output=True,
)
def verify_run_pytest_slice(selectors: list[str], markers: str = "", timeout_sec: int = 1800) -> dict[str, Any]:
    if not selectors:
        return _result(
            summary="At least one pytest selector is required.",
            facts={"selectors": selectors},
            status="error",
        )
    command = [sys.executable, "-m", "pytest"]
    if str(markers or "").strip():
        command.extend(["-m", str(markers).strip()])
    command.extend(list(selectors))
    command.extend(["-q", "--tb=short"])
    run = _run_command(slug="pytest-slice", command=command, timeout_sec=timeout_sec)
    return _result(
        summary=f"Pytest slice completed with exit code {run['return_code']}.",
        facts=run,
        warnings=[run["stderr_excerpt"]] if run["stderr_excerpt"] else [],
        paths=run["artifacts"],
        suggested_next_tools=["verify.suggest_checks"],
        status="ok" if int(run["return_code"]) == 0 else "warning",
    )


@HARNESS.tool(
    name="verify.run_repo_tool",
    description="Use this when you want a maintained repo tool executed through an allowlisted, provenance-capturing wrapper rather than raw shell access.",
    annotations=GATED_EXEC,
    structured_output=True,
)
def verify_run_repo_tool(tool_id: str, script_args: list[str] | None = None, timeout_sec: int = 1800) -> dict[str, Any]:
    target = _resolve_target_tool(tool_id)
    if target is None or not _tool_allowed(target["qualified_id"]):
        return _result(
            summary=f"Repo tool `{tool_id}` is not allowlisted for MCP execution.",
            facts={"tool_id": tool_id},
            status="error",
        )
    args = list(script_args or [])
    command = [sys.executable, "-m", "tools", "run", target["qualified_id"], "--", *args]
    run = _run_command(slug=target["name"], command=command, timeout_sec=timeout_sec)
    return _result(
        summary=f"Repo tool `{target['qualified_id']}` completed with exit code {run['return_code']}.",
        facts={
            "tool": target,
            **run,
        },
        warnings=[run["stderr_excerpt"]] if run["stderr_excerpt"] else [],
        paths=run["artifacts"],
        suggested_next_tools=["repo.list_tools", "verify.suggest_checks"],
        status="ok" if int(run["return_code"]) == 0 else "warning",
    )


@HARNESS.tool(
    name="verify.run_db_audit",
    description="Use this when you need a safe, named DB audit or verifier run without remembering the exact script path.",
    annotations=GATED_EXEC,
    structured_output=True,
)
def verify_run_db_audit(audit: str, script_args: list[str] | None = None, timeout_sec: int = 1800) -> dict[str, Any]:
    tool_id = DB_AUDIT_TOOL_MAP.get(str(audit or "").strip().lower())
    if not tool_id:
        return _result(
            summary=f"Unknown DB audit `{audit}`.",
            facts={"known_audits": sorted(DB_AUDIT_TOOL_MAP)},
            status="error",
        )
    return verify_run_repo_tool(tool_id=tool_id, script_args=script_args or [], timeout_sec=timeout_sec)


@HARNESS.tool(
    name="bench.summarize_protocol",
    description="Use this when you need the repo benchmark rules, current effective settings, and blocking reproducibility warnings before running anything.",
    annotations=READ_ONLY,
    structured_output=True,
)
def bench_summarize_protocol() -> dict[str, Any]:
    protocol = _protocol_summary()
    return _result(
        summary="Benchmark protocol summary ready.",
        facts=protocol,
        warnings=protocol["blocking_warnings"],
        suggested_next_tools=["bench.run_protocol", "repo.get_effective_settings"],
        paths=["config.ini", "docs/INFLIGHT_GA_FG_THROUGHPUT.md"],
        status="ok" if not protocol["blocking_warnings"] else "warning",
    )


@HARNESS.tool(
    name="bench.run_protocol",
    description="Use this when you want an allowlisted benchmark or profiling tool run with reproducibility validation and explicit provenance.",
    annotations=GATED_EXEC,
    structured_output=True,
)
def bench_run_protocol(
    tool_id: str,
    script_args: list[str] | None = None,
    ga_seed: int = 0,
    song_repeats: int = 0,
    fg_search_radius: int = 0,
    db_path: str = "",
    timeout_sec: int = 3600,
    dry_run: bool = False,
) -> dict[str, Any]:
    target = _resolve_target_tool(tool_id)
    if target is None or not str(target["qualified_id"]).startswith("tools:bench/"):
        return _result(
            summary=f"Benchmark tool `{tool_id}` is not allowlisted.",
            facts={"tool_id": tool_id},
            status="error",
        )
    protocol = _protocol_summary()
    blocking = list(protocol["blocking_warnings"])
    if blocking:
        return _result(
            summary="Benchmark protocol blocked due to reproducibility warnings.",
            facts={"protocol": protocol, "tool": target},
            warnings=blocking,
            suggested_next_tools=["bench.summarize_protocol", "repo.get_effective_settings"],
            status="warning",
        )
    env_overrides = {}
    if ga_seed:
        env_overrides["GA_SEED"] = str(int(ga_seed))
    if song_repeats:
        env_overrides["SONG_REPEATS"] = str(int(song_repeats))
    if fg_search_radius:
        env_overrides["FG_SEARCH_RADIUS"] = str(int(fg_search_radius))
    if str(db_path or "").strip():
        env_overrides["EVOLUTION_DB_PATH"] = str(db_path).strip()
    command = [sys.executable, "-m", "tools", "run", target["qualified_id"], "--", *(script_args or [])]
    if dry_run:
        return _result(
            summary="Benchmark protocol dry run prepared.",
            facts={
                "tool": target,
                "command": command,
                "env_overrides": env_overrides,
                "protocol": protocol,
            },
            warnings=blocking,
            suggested_next_tools=["bench.run_protocol", "bench.summarize_protocol"],
        )
    run = _run_command(slug=target["name"], command=command, timeout_sec=timeout_sec, env_overrides=env_overrides)
    return _result(
        summary=f"Benchmark protocol run for `{target['qualified_id']}` completed with exit code {run['return_code']}.",
        facts={
            "tool": target,
            "protocol": protocol,
            "env_overrides": env_overrides,
            **run,
        },
        warnings=blocking + ([run["stderr_excerpt"]] if run["stderr_excerpt"] else []),
        paths=run["artifacts"],
        suggested_next_tools=["bench.compare_runs", "profile.get_run_summary"],
        status="ok" if int(run["return_code"]) == 0 else "warning",
    )


@HARNESS.tool(
    name="bench.compare_runs",
    description="Use this when you need a compact A/B comparison of two profile run summaries with throughput, GPU, backlog, and settings differences.",
    annotations=READ_ONLY,
    structured_output=True,
)
def bench_compare_runs(run_a: str, run_b: str) -> dict[str, Any]:
    path_a, chosen_a = _resolve_profile_summary(run_a)
    path_b, chosen_b = _resolve_profile_summary(run_b)
    if path_a is None or chosen_a is None or path_b is None or chosen_b is None:
        return _result(
            summary="Both profile runs must exist to compare them.",
            facts={"run_a": run_a, "run_b": run_b},
            status="warning",
        )
    summary_a = _json_load(path_a, {})
    summary_b = _json_load(path_b, {})
    comp = {
        "run_a": chosen_a["run_id"],
        "run_b": chosen_b["run_id"],
        "elapsed_sec": {
            "run_a": summary_a.get("elapsed_sec"),
            "run_b": summary_b.get("elapsed_sec"),
        },
        "gpu_weighted_mean_util": {
            "run_a": ((summary_a.get("gpu_phase_summary") or {}).get("fg_weighted_mean")),
            "run_b": ((summary_b.get("gpu_phase_summary") or {}).get("fg_weighted_mean")),
        },
        "backlog_growth": {
            "run_a": (((summary_a.get("profile_events_summary") or {}).get("backlog") or {}).get("growth")),
            "run_b": (((summary_b.get("profile_events_summary") or {}).get("backlog") or {}).get("growth")),
        },
        "effective_settings_changed": summary_a.get("effective_settings") != summary_b.get("effective_settings"),
    }
    return _result(
        summary=f"Compared profile runs `{chosen_a['run_id']}` and `{chosen_b['run_id']}`.",
        facts=comp,
        suggested_next_tools=["profile.analyze_run", "bench.summarize_protocol"],
        paths=[chosen_a["summary_path"], chosen_b["summary_path"]],
    )


def main() -> int:
    HARNESS.run(transport="stdio")
    return 0
