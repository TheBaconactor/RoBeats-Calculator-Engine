"""
A/B quality harness for FG_CandidateLimit (non-randomized, reproducible).

Motivation:
- End-to-end GPU runs have noise unless RNG sources are pinned.
- With GA_SEED + per-song deterministic GA seeds (app.py),
  we can quantify whether FG_CandidateLimit changes cause a real quality regression
  vs run-to-run noise.

This tool:
1) Runs `python main.py` in subprocesses for two variants (A/B) across N reps.
2) Each run uses an isolated DB path (EVOLUTION_DB_PATH) so results don't leak.
3) Reads `songs.best_score` and `songs.best_fg_score` from that DB.
4) Produces a stable JSON report plus a small CLI summary.
"""

from __future__ import annotations

import argparse
import configparser
import json
import os
import sqlite3
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from statistics import median


@dataclass(frozen=True)
class Variant:
    name: str
    fg_candidate_limit: int


def _truthy(v: str) -> bool:
    return str(v or "").strip().lower() in {"1", "true", "yes", "on"}


def _rm_if_exists(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
    except Exception:
        pass


def _write_variant_config(
    *,
    base_config_path: Path,
    out_config_path: Path,
    fg_candidate_limit: int,
    song_repeats: int | None,
    inflight_songs: int | None,
) -> None:
    cfg = configparser.ConfigParser()
    cfg.read(str(base_config_path), encoding="utf-8-sig")

    if not cfg.has_section("IterationEngine"):
        cfg.add_section("IterationEngine")
    cfg.set("IterationEngine", "FG_CandidateLimit", str(int(fg_candidate_limit)))
    cfg.set("IterationEngine", "LoopForever", "false")
    cfg.set("IterationEngine", "IgnoreResumeQueue", "true")
    if song_repeats is not None:
        cfg.set("IterationEngine", "SongRepeats", str(int(song_repeats)))
    if inflight_songs is not None:
        cfg.set("IterationEngine", "InFlightSongs", str(int(inflight_songs)))

    out_config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_config_path, "w", encoding="utf-8") as fh:
        cfg.write(fh)


def _read_scores(db_path: Path) -> dict[str, dict[str, int]]:
    if not db_path.exists():
        return {}
    conn = sqlite3.connect(str(db_path))
    try:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT name, best_score, best_fg_score FROM songs").fetchall()
        out: dict[str, dict[str, int]] = {}
        for r in rows:
            out[str(r["name"])] = {
                "best_score": int(r["best_score"] or 0),
                "best_fg_score": int(r["best_fg_score"] or 0),
            }
        return out
    finally:
        conn.close()


def _fg_gain(scores: dict[str, int]) -> int:
    # best_fg_score and best_score are separate leaderboards; gain is a useful proxy.
    try:
        return max(0, int(scores.get("best_fg_score", 0)) - int(scores.get("best_score", 0)))
    except Exception:
        return 0


def _run_one(
    *,
    run_dir: Path,
    config_path: Path,
    db_path: Path,
    seed_db_path: Path | None,
    song_limit: int,
    ga_seed: int,
    fg_download_topk: int | None,
) -> dict:
    run_dir.mkdir(parents=True, exist_ok=True)
    for suffix in ("", "-wal", "-shm"):
        _rm_if_exists(Path(str(db_path) + suffix))

    if seed_db_path is not None:
        if not seed_db_path.exists():
            raise SystemExit(f"--seed-db not found: {seed_db_path}")
        # Copy seed DB into the run-local DB path so the optimizer sees identical initial state.
        # (We intentionally don't try to reuse WAL/SHM sidecars.)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        import shutil

        shutil.copy2(str(seed_db_path), str(db_path))

    env = os.environ.copy()
    env["METAFINDER_CONFIG_PATH"] = str(config_path)
    env["EVOLUTION_DB_PATH"] = str(db_path)
    env["METAFINDER_IGNORE_RESUME_QUEUE"] = "1"
    env["METAFINDER_THROUGHPUT"] = "1"
    env["SONG_QUEUE_LIMIT"] = str(max(1, int(song_limit)))
    env["GA_SEED"] = str(int(ga_seed))
    env.setdefault("PYTHONHASHSEED", "0")

    # Avoid hidden quality artifacts from reduced downloads during audits unless explicitly requested.
    if fg_download_topk is not None:
        env["FG_DOWNLOAD_TOPK"] = str(int(fg_download_topk))

    t0 = time.perf_counter()
    proc = subprocess.run(
        [sys.executable, "main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
        cwd=str(Path.cwd()),
    )
    wall_s = time.perf_counter() - t0

    (run_dir / "stdout.log").write_text(proc.stdout or "", encoding="utf-8", errors="replace")

    scores = _read_scores(db_path)
    return {
        "exit_code": int(proc.returncode),
        "wall_s": float(wall_s),
        "db_path": str(db_path),
        "config_path": str(config_path),
        "scores": scores,
        "stdout_tail": (proc.stdout or "")[-8000:],
    }


def _median_int(xs: list[int]) -> int:
    if not xs:
        return 0
    try:
        return int(median([int(x) for x in xs]))
    except Exception:
        return 0


def _summarize(runs_by_rep: list[dict]) -> dict:
    # Merge per-song metrics across reps.
    songs = set()
    for r in runs_by_rep:
        songs.update((r.get("scores") or {}).keys())

    by_song = {}
    for s in sorted(songs):
        base_scores = []
        fg_scores = []
        gains = []
        for r in runs_by_rep:
            sc = (r.get("scores") or {}).get(s) or {}
            base_scores.append(int(sc.get("best_score", 0) or 0))
            fg_scores.append(int(sc.get("best_fg_score", 0) or 0))
            gains.append(_fg_gain(sc))
        by_song[s] = {
            "best_score_median": _median_int(base_scores),
            "best_fg_score_median": _median_int(fg_scores),
            "fg_gain_median": _median_int(gains),
            "best_score_all": base_scores,
            "best_fg_score_all": fg_scores,
            "fg_gain_all": gains,
        }

    exit_codes = [int(r.get("exit_code", 0) or 0) for r in runs_by_rep]
    wall_s = [float(r.get("wall_s", 0.0) or 0.0) for r in runs_by_rep]
    return {
        "reps": len(runs_by_rep),
        "exit_codes": exit_codes,
        "wall_s": wall_s,
        "songs": by_song,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.ini", help="Base config.ini to start from.")
    ap.add_argument("--song-limit", type=int, default=60)
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--ga-seed", type=int, default=1337)
    ap.add_argument("--song-repeats", type=int, default=1, help="Override SongRepeats in generated configs.")
    ap.add_argument("--seed-db", default="", help="Optional seed DB to copy into each run's EVOLUTION_DB_PATH.")
    ap.add_argument(
        "--inflight-songs",
        type=int,
        default=-1,
        help="Override InFlightSongs in generated config (-1=keep base config, 0=off).",
    )
    ap.add_argument("--fg-download-topk", type=int, default=0, help="Set FG_DOWNLOAD_TOPK (0 recommended for audits).")
    ap.add_argument("--a", type=int, default=200, help="Variant A FG_CandidateLimit.")
    ap.add_argument("--b", type=int, default=100, help="Variant B FG_CandidateLimit.")
    ap.add_argument("--outdir", default="", help="Output directory (default: artifacts/analysis/ab_fg_candidate_limit_<ts>).")
    args = ap.parse_args()

    base_config_path = Path(args.config)
    if not base_config_path.exists():
        raise SystemExit(f"Config not found: {base_config_path}")

    reps = max(1, int(args.reps))
    song_limit = max(1, int(args.song_limit))
    ga_seed = int(args.ga_seed)
    song_repeats = max(1, int(args.song_repeats)) if int(args.song_repeats) > 0 else None
    seed_db_path = None
    if str(args.seed_db or "").strip():
        seed_db_path = Path(str(args.seed_db).strip())

    inflight_songs = None
    if int(args.inflight_songs) >= 0:
        inflight_songs = int(args.inflight_songs)

    outdir = Path(args.outdir) if str(args.outdir or "").strip() else None
    if outdir is None:
        ts = time.strftime("%Y%m%d_%H%M%S")
        outdir = Path("artifacts") / "analysis" / f"ab_fg_candidate_limit_{ts}"
    outdir.mkdir(parents=True, exist_ok=True)

    variants = [
        Variant("A", int(args.a)),
        Variant("B", int(args.b)),
    ]

    all_runs: dict[str, list[dict]] = {v.name: [] for v in variants}
    for rep in range(1, reps + 1):
        for v in variants:
            run_dir = outdir / f"{v.name}_rep{rep}"
            cfg_path = run_dir / "config.ini"
            db_path = run_dir / "evolution.db"

            _write_variant_config(
                base_config_path=base_config_path,
                out_config_path=cfg_path,
                fg_candidate_limit=int(v.fg_candidate_limit),
                song_repeats=song_repeats,
                inflight_songs=inflight_songs,
            )

            print(f"[ab] rep={rep}/{reps} variant={v.name} FG_CandidateLimit={v.fg_candidate_limit}")
            run = _run_one(
                run_dir=run_dir,
                config_path=cfg_path,
                db_path=db_path,
                seed_db_path=seed_db_path,
                song_limit=song_limit,
                ga_seed=ga_seed,
                fg_download_topk=int(args.fg_download_topk),
            )
            all_runs[v.name].append(run)
            print(f"[ab] rep={rep} variant={v.name} exit={run['exit_code']} wall_s={run['wall_s']:.1f}s songs={len(run.get('scores') or {})}")

    summ = {k: _summarize(v) for k, v in all_runs.items()}

    # Compare medians song-by-song (A - B).
    songs = set(summ["A"]["songs"].keys()) | set(summ["B"]["songs"].keys())
    deltas = {}
    for s in sorted(songs):
        a = summ["A"]["songs"].get(s) or {}
        b = summ["B"]["songs"].get(s) or {}
        deltas[s] = {
            "delta_best_score_median": int(a.get("best_score_median", 0) or 0) - int(b.get("best_score_median", 0) or 0),
            "delta_best_fg_score_median": int(a.get("best_fg_score_median", 0) or 0)
            - int(b.get("best_fg_score_median", 0) or 0),
            "delta_fg_gain_median": int(a.get("fg_gain_median", 0) or 0) - int(b.get("fg_gain_median", 0) or 0),
            "A": {
                "best_score_median": int(a.get("best_score_median", 0) or 0),
                "best_fg_score_median": int(a.get("best_fg_score_median", 0) or 0),
                "fg_gain_median": int(a.get("fg_gain_median", 0) or 0),
            },
            "B": {
                "best_score_median": int(b.get("best_score_median", 0) or 0),
                "best_fg_score_median": int(b.get("best_fg_score_median", 0) or 0),
                "fg_gain_median": int(b.get("fg_gain_median", 0) or 0),
            },
        }

    # Quick headline metrics.
    drops = [s for s, d in deltas.items() if int(d.get("delta_best_fg_score_median", 0) or 0) > 0]  # A > B
    wins = [s for s, d in deltas.items() if int(d.get("delta_best_fg_score_median", 0) or 0) < 0]  # B > A
    ties = [s for s, d in deltas.items() if int(d.get("delta_best_fg_score_median", 0) or 0) == 0]

    def _count_zero_fg(summary: dict) -> int:
        c = 0
        for s, m in (summary.get("songs") or {}).items():
            if int(m.get("best_fg_score_median", 0) or 0) <= 0:
                c += 1
        return c

    def _count_unstable_fg(summary: dict) -> int:
        c = 0
        for _s, m in (summary.get("songs") or {}).items():
            vals = m.get("best_fg_score_all") or []
            uniq = set(int(v or 0) for v in vals)
            if len(uniq) > 1:
                c += 1
        return c

    report = {
        "meta": {
            "base_config": str(base_config_path),
            "song_limit": song_limit,
            "reps": reps,
            "ga_seed": ga_seed,
            "song_repeats_override": song_repeats,
            "seed_db": str(seed_db_path) if seed_db_path is not None else "",
            "inflight_songs_override": inflight_songs,
            "allow_sequential": bool(args.allow_sequential),
            "fg_download_topk": int(args.fg_download_topk),
            "variants": [{"name": v.name, "FG_CandidateLimit": int(v.fg_candidate_limit)} for v in variants],
        },
        "runs": all_runs,
        "summary": summ,
        "deltas": deltas,
        "headline": {
            "songs_compared": len(deltas),
            "A_better_fg_median_count": len(drops),
            "B_better_fg_median_count": len(wins),
            "ties_fg_median_count": len(ties),
            "A_zero_fg_median_count": _count_zero_fg(summ.get("A") or {}),
            "B_zero_fg_median_count": _count_zero_fg(summ.get("B") or {}),
            "A_unstable_fg_count": _count_unstable_fg(summ.get("A") or {}),
            "B_unstable_fg_count": _count_unstable_fg(summ.get("B") or {}),
        },
    }

    out_path = outdir / "analysis_report.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("")
    print(f"[ab] wrote {out_path}")
    print(f"[ab] songs compared: {len(deltas)}")
    print(
        "[ab] median best_fg_score: A better={} B better={} ties={}".format(
            len(drops),
            len(wins),
            len(ties),
        )
    )

    # Heuristic verdict: only call a "real drop" if it's consistent and not just a couple songs.
    if len(deltas) > 0:
        frac = len(wins) / max(1, len(deltas))
        if frac >= 0.30 and len(wins) >= 5:
            print("[ab][verdict] likely genuine quality drop from A->B (many songs worse).")
        elif len(wins) == 0:
            print("[ab][verdict] no observed quality drop from A->B on this workload.")
        else:
            print("[ab][verdict] mixed: some songs worse, some better; treat as inconclusive without more reps/workload.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
