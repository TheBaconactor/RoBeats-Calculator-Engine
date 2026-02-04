import argparse
import configparser
import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path


def _parse_int_list(s: str) -> list[int]:
    out: list[int] = []
    for part in (s or "").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.append(int(part))
        except Exception:
            pass
    return out


def _read_fg_best(db_path: Path, *, song_substr: str) -> list[dict]:
    if not db_path.exists():
        return []

    conn = sqlite3.connect(str(db_path))
    try:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT name, best_score, best_fg_score FROM songs WHERE name LIKE ? ORDER BY name",
            (f"%{song_substr}%",),
        ).fetchall()
        out: list[dict] = []
        for r in rows:
            song_name = str(r["name"] or "")
            best_score = int(r["best_score"] or 0)
            best_fg_score = int(r["best_fg_score"] or 0)

            best_fg = conn.execute(
                "SELECT fg_score, gear_json, minis_json FROM team_buff_fg_loadouts WHERE song_name = ? ORDER BY fg_score DESC LIMIT 1",
                (song_name,),
            ).fetchone()
            gear = []
            minis = []
            if best_fg:
                try:
                    gear = json.loads(best_fg["gear_json"] or "[]")
                except Exception:
                    gear = []
                try:
                    minis = json.loads(best_fg["minis_json"] or "[]")
                except Exception:
                    minis = []
            out.append(
                {
                    "song": song_name,
                    "best_score": best_score,
                    "best_fg_score": best_fg_score,
                    "best_fg_gear": gear,
                    "best_fg_minis": minis,
                }
            )
        return out
    finally:
        conn.close()


def _write_cfg(base_cfg_path: Path, *, out_path: Path, overrides: dict[str, dict[str, str]]) -> None:
    cfg = configparser.ConfigParser()
    cfg.optionxform = str  # type: ignore[attr-defined]
    cfg.read(str(base_cfg_path), encoding="utf-8")
    for section, kv in (overrides or {}).items():
        if section not in cfg:
            cfg[section] = {}
        for k, v in (kv or {}).items():
            cfg[section][str(k)] = str(v)
    out_path.write_text(_to_ini(cfg), encoding="utf-8")


def _to_ini(cfg: configparser.ConfigParser) -> str:
    from io import StringIO

    buf = StringIO()
    cfg.write(buf)
    return buf.getvalue()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-config", default="config.ini")
    ap.add_argument("--song", default="Feeling Alright")
    ap.add_argument("--difficulty", default="All")
    ap.add_argument("--fg-radius", type=int, default=5)
    ap.add_argument("--depths", default="200,2000", help="Comma-separated GA_SearchDepth values.")
    ap.add_argument(
        "--inflight-songs",
        default="",
        help="Comma-separated InFlightSongs values. Empty => keep base config value.",
    )
    ap.add_argument("--seed", type=int, default=42, help="Sets GA_SEED for determinism.")
    ap.add_argument("--outdir", default=str(Path("artifacts") / "bench" / "fg_depth_quick"))
    args = ap.parse_args()

    base_cfg_path = Path(args.base_config)
    if not base_cfg_path.exists():
        print(f"Base config not found: {base_cfg_path}")
        return 2

    depths = _parse_int_list(args.depths)
    if not depths:
        print("No valid --depths provided")
        return 2

    inflights = _parse_int_list(args.inflight_songs)
    if not inflights:
        inflights = [None]  # Keep base config value.

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    runs: list[dict] = []
    for inflight in inflights:
        for depth in depths:
            tag = f"depth{int(depth)}"
            if inflight is not None:
                tag += f"_inflight{int(inflight)}"

            # IMPORTANT: Keep benchmarks independent (no cross-run DB reuse/seeding)
            # by isolating each (depth,inflight) run into its own directory.
            run_dir = outdir / tag
            run_dir.mkdir(parents=True, exist_ok=True)

            cfg_out = run_dir / "config.ini"
            db_out = run_dir / "evolution.db"
            log_out = run_dir / "run.log"

            if db_out.exists():
                backup = db_out.with_name(db_out.name + f".backup_{int(time.time())}")
                db_out.replace(backup)

            overrides = {
                "CalculateSong": {"Song_Name": str(args.song), "Difficulty": str(args.difficulty)},
                "IterationEngine": {
                    "GA_SearchDepth": str(int(depth)),
                    "ForceGreatsMode": "true",
                    "ForceGreatsFinder": "true",
                    "FG_SearchRadius": str(int(args.fg_radius)),
                    "LoopForever": "false",
                },
            }
            if inflight is not None:
                overrides["IterationEngine"]["InFlightSongs"] = str(int(inflight))

            _write_cfg(base_cfg_path, out_path=cfg_out, overrides=overrides)

            env = os.environ.copy()
            env["METAFINDER_CONFIG_PATH"] = str(cfg_out)
            env["EVOLUTION_DB_PATH"] = str(db_out)
            env["GA_SEED"] = str(int(args.seed))

            t0 = time.perf_counter()
            proc = subprocess.run(
                [sys.executable, "main.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
                cwd=str(Path.cwd()),
            )
            dt = time.perf_counter() - t0
            log_out.write_text(proc.stdout, encoding="utf-8", errors="replace")

            scores = _read_fg_best(db_out, song_substr=str(args.song))
            runs.append(
                {
                    "tag": tag,
                    "exit_code": int(proc.returncode),
                    "elapsed_sec": float(dt),
                    "db": str(db_out),
                    "run_dir": str(run_dir),
                    "scores": scores,
                }
            )

            best_fg = 0
            try:
                best_fg = max(int(s.get("best_fg_score", 0) or 0) for s in scores)
            except Exception:
                best_fg = 0
            print(f"[{tag}] exit={proc.returncode} time={dt:.1f}s best_fg={best_fg}")

    (outdir / "summary.json").write_text(json.dumps({"runs": runs}, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
