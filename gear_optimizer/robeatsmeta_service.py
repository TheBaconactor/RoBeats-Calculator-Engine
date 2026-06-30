from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

from gear_optimizer.data.database import get_best_loadouts
from gear_optimizer.data.loadout_equivalence import representative_mini_names
from gear_optimizer.data.song_io import scan_song_header

REPO_ROOT = Path(__file__).resolve().parents[1]
DIFFICULTIES = ("Easy", "Normal", "Hard")


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _clean_piece_names(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    out: list[str] = []
    for value in values:
        if isinstance(value, str):
            name = value.strip()
        elif isinstance(value, dict):
            name = str(value.get("Name") or value.get("name") or "").strip()
        else:
            name = ""
        if name:
            out.append(name)
    return out


def _stats_payload(details: dict[str, Any]) -> dict[str, int]:
    stats = details.get("Stats") if isinstance(details.get("Stats"), dict) else details
    return {
        "perfectPoints": _safe_int(stats.get("Perfect Points")),
        "comboMultiplier": _safe_int(stats.get("Combo Multiplier")),
        "feverMultiplier": _safe_int(stats.get("Fever Multiplier")),
        "feverFill": _safe_int(stats.get("Fever Fill Rate")),
        "feverTime": _safe_int(stats.get("Fever Time")),
    }


def _affinity_payload(details: dict[str, Any]) -> dict[str, int]:
    stats = details.get("Stats") if isinstance(details.get("Stats"), dict) else details
    return {
        "Chill": _safe_int(stats.get("Chill")),
        "Vibe": _safe_int(stats.get("Vibe")),
        "Beat": _safe_int(stats.get("Beat")),
        "Flow": _safe_int(stats.get("Flow")),
        "Rush": _safe_int(stats.get("Rush")),
    }


def _gem_counts(details: dict[str, Any]) -> dict[str, int]:
    raw = details.get("GemCounts") or details.get("gc") or []
    if not isinstance(raw, list):
        raw = []
    values = [_safe_int(v) for v in list(raw)[:6]]
    while len(values) < 6:
        values.append(0)
    return {
        "Perfect Points": values[0],
        "Combo Multiplier": values[1],
        "Fever Multiplier": values[2],
        "Elemental": values[3],
        "Fever Time": values[4],
        "Fever Fill": values[5],
    }


def _selected_element(details: dict[str, Any]) -> str:
    return str(
        details.get("Selected Element")
        or details.get("selected_element")
        or details.get("se")
        or details.get("Primary Color")
        or details.get("pc")
        or "General"
    ).strip() or "General"


def _primary_element(details: dict[str, Any]) -> str | None:
    value = str(details.get("Primary Color") or details.get("pc") or "").strip()
    return value or None


def _secondary_element(details: dict[str, Any]) -> str | None:
    value = str(details.get("Secondary Color") or details.get("sc") or "").strip()
    return value or None


def build_payload_from_entry(entry: dict[str, Any]) -> dict[str, Any]:
    details = entry.get("details") if isinstance(entry.get("details"), dict) else {}
    mini_groups = entry.get("mini_groups")
    if isinstance(mini_groups, list):
        minis = representative_mini_names(mini_groups)
    else:
        minis = _clean_piece_names(entry.get("minis"))
    return {
        "score": _safe_int(entry.get("score")),
        "loadoutHash": str(entry.get("loadout_hash") or "").strip() or None,
        "gear": _clean_piece_names(entry.get("gear")),
        "minis": minis,
        "element": _selected_element(details),
        "primaryElement": _primary_element(details),
        "secondaryElement": _secondary_element(details),
        "teamBuffTier": "T5",
        "forceGreats": False,
        "forceGreatsConfig": None,
        "stats": _stats_payload(details),
        "affinity": _affinity_payload(details),
        "gemCounts": _gem_counts(details),
        "metaTags": [],
    }


def resolve_official_song(song_id: str) -> tuple[str, str]:
    cleaned = str(song_id or "").strip()
    if not cleaned:
        raise ValueError("missing targetSongId")
    preferred: list[str] = []
    match = re.search(r"\((Easy|Normal|Hard)\)", cleaned, flags=re.IGNORECASE)
    if match:
        preferred.append(match.group(1).title())
    preferred.extend(diff for diff in DIFFICULTIES if diff not in preferred)
    for difficulty in preferred:
        diff_dir = REPO_ROOT / "Data" / difficulty
        if not diff_dir.is_dir():
            continue
        matches: list[str] = []
        for fp in sorted(diff_dir.glob("*.txt")):
            meta = scan_song_header(str(fp)) or {}
            name = str(meta.get("Song Name") or "").strip()
            if name and (name == cleaned or cleaned.lower() in name.lower()):
                matches.append(name)
        if len(matches) == 1:
            return matches[0], difficulty
        if len(matches) > 1:
            raise ValueError(f"targetSongId matched multiple {difficulty} charts")
    raise ValueError("targetSongId did not match an official chart")


def run_official_solve(song_name: str, difficulty: str, db_path: Path, repeats: int) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path = db_path.parent / f"{db_path.stem}.ini"
    log_path = db_path.parent / f"{db_path.stem}.log"
    cfg_path.write_text(
        "[CalculateSong]\n"
        f"Song_Name = {song_name}\n"
        f"Difficulty = {difficulty}\n"
        "TargetPrimary = All\n"
        "TargetSecondary = All\n"
        "LoopForever = false\n\n"
        "[IterationEngine]\n"
        f"SongRepeats = {max(1, int(repeats))}\n"
        "SongQueueLimit = 1\n",
        encoding="utf-8",
    )
    env = dict(os.environ)
    env["EVOLUTION_DB_PATH"] = str(db_path)
    env["METAFINDER_CONFIG_PATH"] = str(cfg_path)
    try:
        with log_path.open("w", encoding="utf-8") as log:
            proc = subprocess.run(
                [sys.executable, str(REPO_ROOT / "main.py")],
                cwd=str(REPO_ROOT),
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
        if proc.returncode != 0:
            tail = "\n".join(log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-25:])
            raise RuntimeError(f"optimizer exited {proc.returncode}: {tail}")
    finally:
        cfg_path.unlink(missing_ok=True)


def solve_official_request(request: dict[str, Any]) -> dict[str, Any]:
    song_name, difficulty = resolve_official_song(str(request.get("targetSongId") or ""))
    job_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(request.get("jobId") or "job").strip()) or "job"
    run_dir = Path(os.environ.get("ROBEATSMETA_OPTIMIZER_SERVICE_RUN_DIR") or (REPO_ROOT / "bin" / "robeatsmeta_api_runs"))
    db_path = run_dir / f"{job_id}.db"
    for suffix in ("", "-wal", "-shm"):
        Path(str(db_path) + suffix).unlink(missing_ok=True)
    repeats = _safe_int(os.environ.get("ROBEATSMETA_OPTIMIZER_SERVICE_REPEATS"), 1)
    run_official_solve(song_name, difficulty, db_path, repeats)
    entries = get_best_loadouts(song_name, limit=1, team_buff="T5", db_path=str(db_path))
    if not entries:
        raise RuntimeError("optimizer completed without a T5 build")
    return build_payload_from_entry(entries[0])


class RoBeatsMetaServiceHandler(BaseHTTPRequestHandler):
    server_version = "RoBeatsMetaOptimizer/1.0"

    def do_POST(self) -> None:
        if self.path.rstrip("/") != "/optimize":
            self._write_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        token = str(os.environ.get("ROBEATSMETA_OPTIMIZER_API_TOKEN") or "").strip()
        if token:
            expected = f"Bearer {token}"
            if self.headers.get("Authorization") != expected:
                self._write_json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
                return
        try:
            length = _safe_int(self.headers.get("Content-Length"), 0)
            body = self.rfile.read(length)
            request = json.loads(body.decode("utf-8"))
            if not isinstance(request, dict):
                raise ValueError("request body must be a JSON object")
            if request.get("chartText"):
                raise ValueError("custom chart optimization is not wired in Metafinder yet")
            build = solve_official_request(request)
            self._write_json(HTTPStatus.OK, {"jobId": request.get("jobId"), "build": build})
        except ValueError as exc:
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except Exception as exc:
            self._write_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("[robeatsmeta-service] " + (fmt % args) + "\n")

    def _write_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(int(status))
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="RoBeatsMeta optimizer API service")
    parser.add_argument("--host", default=os.environ.get("ROBEATSMETA_OPTIMIZER_API_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=_safe_int(os.environ.get("ROBEATSMETA_OPTIMIZER_API_PORT"), 8765))
    args = parser.parse_args(argv)
    server = HTTPServer((args.host, int(args.port)), RoBeatsMetaServiceHandler)
    print(f"[robeatsmeta-service] listening on http://{args.host}:{args.port}", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
