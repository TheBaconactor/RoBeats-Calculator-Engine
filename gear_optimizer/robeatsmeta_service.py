from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

from gear_optimizer.core.parsing import env_int, env_str
from gear_optimizer.data.database import get_best_loadouts
from gear_optimizer.data.song_io import scan_song_header

# Stateless HTTP front-end over the canonical optimizer pipeline.
#
# The website owns identity, credits, TTL, sharing and persistence; this service only solves.
#   GET  /songs     -> the official chart list (from Data/ headers) the website picker chooses from
#   POST /optimize  -> solve one chart (official `targetSongId` OR custom `chartText`) and return
#                      its top T5 loadout, in the exact shape `get_best_loadouts` yields for the
#                      catalog, so the website serializes it through its normal SongBuild path.
#
# Every solve runs in a throwaway per-request dir with the song source, run state and output DB
# redirected via the ROBEATSMETA_OPTIMIZER_* path overrides, so requests never touch the catalog
# bin/ queues, the Data/ catalog, or evolution.db.

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = REPO_ROOT / "Data"
GEAR_DIR = DATA_ROOT / "Gear"
DIFFICULTIES = ("Easy", "Normal", "Hard")


class RequestError(ValueError):
    """A bad request from the caller -> HTTP 400 (an internal failure -> 500)."""


# --- official chart catalog --------------------------------------------------

def list_official_songs() -> list[dict[str, str]]:
    """The official chart list for the website picker, read from the catalog Data/ headers."""
    songs: list[dict[str, str]] = []
    for difficulty in DIFFICULTIES:
        diff_dir = DATA_ROOT / difficulty
        if not diff_dir.is_dir():
            continue
        for chart in sorted(diff_dir.glob("*.txt")):
            header = scan_song_header(str(chart)) or {}
            name = str(header.get("Song Name") or "").strip()
            if not name:
                continue
            songs.append(
                {
                    "songId": name,
                    "difficulty": difficulty,
                    "primaryElement": str(header.get("Primary Color") or "").strip(),
                    "secondaryElement": str(header.get("Secondary Color") or "").strip(),
                }
            )
    return songs


def find_official_chart(song_id: str) -> Path:
    """Return the official chart file whose `Song Name` header equals `song_id` exactly.

    The website picks from `list_official_songs()` and echoes back the exact `songId`, so an exact
    match is the contract -- no fuzzy/substring matching.
    """
    target = str(song_id or "").strip()
    if not target:
        raise RequestError("missing targetSongId")
    for difficulty in DIFFICULTIES:
        diff_dir = DATA_ROOT / difficulty
        if not diff_dir.is_dir():
            continue
        for chart in sorted(diff_dir.glob("*.txt")):
            header = scan_song_header(str(chart)) or {}
            if str(header.get("Song Name") or "").strip() == target:
                return chart
    raise RequestError(f"no official chart matches {target!r}")


# --- solve -------------------------------------------------------------------

def _job_slug(value: Any) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value or "").strip()).strip("_")
    return slug or "job"


def _normalize_chart(chart_text: str, name: str) -> str:
    """Force Song Name (the unique job slug, so the output is keyed by it) and Difficulty (the
    isolated Hard bucket the per-request workspace uses) so the header matches the run config."""
    out: list[str] = []
    have_name = have_diff = False
    for line in chart_text.splitlines():
        if line.startswith("Song Name\t") and not have_name:
            out.append(f"Song Name\t{name}")
            have_name = True
        elif line.startswith("Difficulty\t") and not have_diff:
            out.append("Difficulty\tHard")
            have_diff = True
        else:
            out.append(line)
    prefix: list[str] = []
    if not have_name:
        prefix.append(f"Song Name\t{name}")
    if not have_diff:
        prefix.append("Difficulty\tHard")
    return "\n".join(prefix + out) + "\n"


def chart_text_for_request(request: dict[str, Any]) -> str:
    """The chart to solve: custom `chartText` when present, else the official `targetSongId`."""
    chart_text = str(request.get("chartText") or "").strip()
    if chart_text:
        return chart_text + "\n"
    song_id = str(request.get("targetSongId") or "").strip()
    if song_id:
        return find_official_chart(song_id).read_text(encoding="utf-8")
    raise RequestError("request must include targetSongId or chartText")


def _service_run_root() -> Path:
    override = env_str("ROBEATSMETA_OPTIMIZER_SERVICE_RUN_DIR", "").strip()
    return Path(override) if override else (REPO_ROOT / "bin" / "robeatsmeta_api_runs")


def solve(request: dict[str, Any]) -> dict[str, Any]:
    """Solve one chart in an isolated per-request workspace and return its top T5 loadout entry."""
    job = _job_slug(request.get("jobId") or request.get("resultKey"))
    chart_text = chart_text_for_request(request)
    repeats = max(1, env_int("ROBEATSMETA_OPTIMIZER_SERVICE_REPEATS", 1))

    work = _service_run_root() / job
    shutil.rmtree(work, ignore_errors=True)
    data_dir = work / "Data"
    (data_dir / "Hard").mkdir(parents=True, exist_ok=True)
    shutil.copytree(GEAR_DIR, data_dir / "Gear")  # real files; discovery does not follow symlinks
    (data_dir / "Hard" / f"{job}.txt").write_text(_normalize_chart(chart_text, job), encoding="utf-8")
    # The isolated Data dir holds exactly this one chart, so "process discovered charts once"
    # (empty Song_Name + LoopForever off) solves it; a fresh bin means no resume/candidate queue.
    (work / "config.ini").write_text(
        "[CalculateSong]\n"
        "LoopForever = false\n\n"
        "[IterationEngine]\n"
        "IgnoreResumeQueue = true\n"
        f"SongRepeats = {repeats}\n"
        "SongQueueLimit = 1\n",
        encoding="utf-8",
    )
    db_path = work / "result.db"
    env = {
        **os.environ,
        "EVOLUTION_DB_PATH": str(db_path),
        "METAFINDER_CONFIG_PATH": str(work / "config.ini"),
        "ROBEATSMETA_OPTIMIZER_DATA_DIR": str(data_dir),
        "ROBEATSMETA_OPTIMIZER_BIN_DIR": str(work / "bin"),
    }
    try:
        proc = subprocess.run(
            [sys.executable, str(REPO_ROOT / "main.py"), "run"],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            tail = " | ".join((proc.stderr or proc.stdout or "").strip().splitlines()[-20:])
            raise RuntimeError(f"optimizer exited {proc.returncode}: {tail}")
        entries = get_best_loadouts(job, limit=1, team_buff="T5", db_path=str(db_path))
        if not entries:
            raise RuntimeError("optimizer produced no T5 loadout")
        return entries[0]
    finally:
        shutil.rmtree(work, ignore_errors=True)


# --- HTTP --------------------------------------------------------------------

class RoBeatsMetaServiceHandler(BaseHTTPRequestHandler):
    server_version = "RoBeatsMetaOptimizer/2.0"

    def _authorized(self) -> bool:
        token = env_str("ROBEATSMETA_OPTIMIZER_API_TOKEN", "").strip()
        return not token or self.headers.get("Authorization") == f"Bearer {token}"

    def do_GET(self) -> None:
        if self.path.rstrip("/") != "/songs":
            self._send(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        if not self._authorized():
            self._send(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
            return
        try:
            self._send(HTTPStatus.OK, {"songs": list_official_songs()})
        except Exception as exc:  # noqa: BLE001 - HTTP boundary: surface as 500
            self._send(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

    def do_POST(self) -> None:
        if self.path.rstrip("/") != "/optimize":
            self._send(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        if not self._authorized():
            self._send(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
            return
        try:
            request = self._read_json()
            loadout = solve(request)
            self._send(HTTPStatus.OK, {"jobId": request.get("jobId"), "loadout": loadout})
        except RequestError as exc:
            self._send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except Exception as exc:  # noqa: BLE001 - HTTP boundary: optimizer failure -> 500
            self._send(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

    def _read_json(self) -> dict[str, Any]:
        length = self.headers.get("Content-Length")
        if not length or not length.isdigit():
            raise RequestError("missing Content-Length")
        try:
            request = json.loads(self.rfile.read(int(length)).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RequestError(f"invalid JSON body: {exc}") from exc
        if not isinstance(request, dict):
            raise RequestError("request body must be a JSON object")
        return request

    def _send(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(int(status))
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("[robeatsmeta-service] " + (fmt % args) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="RoBeatsMeta optimizer service")
    parser.add_argument("--host", default=env_str("ROBEATSMETA_OPTIMIZER_API_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=env_int("ROBEATSMETA_OPTIMIZER_API_PORT", 8765))
    args = parser.parse_args(argv)
    server = HTTPServer((args.host, int(args.port)), RoBeatsMetaServiceHandler)
    print(f"[robeatsmeta-service] listening on http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
