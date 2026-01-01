import argparse
import configparser
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


POST_FG_RE = re.compile(
    r"^\[POST\]\[FG\]\s+Saved\s+(?P<n>[0-9]+)\s+FG\s+variant\(s\)\s+for\s+(?P<song>.+?)\s+\(best_fg=(?P<best_fg>[0-9]+)\)\s*$"
)


def _to_ini(cfg: configparser.ConfigParser) -> str:
    from io import StringIO

    buf = StringIO()
    cfg.write(buf)
    return buf.getvalue()


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


def _read_best_scores(db_path: Path, *, song_prefix: str) -> dict[str, dict[str, int]]:
    if not db_path.exists():
        return {}

    conn = sqlite3.connect(str(db_path))
    try:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT name, best_score, best_fg_score FROM songs WHERE name LIKE ? ORDER BY name",
            (f"{song_prefix}%",),
        ).fetchall()
        out: dict[str, dict[str, int]] = {}
        for r in rows:
            name = str(r["name"] or "")
            out[name] = {
                "best_score": int(r["best_score"] or 0),
                "best_fg_score": int(r["best_fg_score"] or 0),
            }
        return out
    finally:
        conn.close()


def _apply_best_fg_from_log(scores: dict[str, dict[str, int]], *, log_path: Path, song_prefix: str) -> None:
    try:
        text = log_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return

    for line in (text or "").splitlines():
        m = POST_FG_RE.match(line.strip())
        if not m:
            continue
        song = str(m.group("song") or "").strip()
        if not song or not song.startswith(song_prefix):
            continue
        try:
            best_fg = int(m.group("best_fg") or 0)
        except Exception:
            best_fg = 0
        scores.setdefault(song, {"best_score": 0, "best_fg_score": 0})
        scores[song]["best_fg_score"] = max(int(scores[song].get("best_fg_score", 0) or 0), int(best_fg))


def _truthy(v: object) -> bool:
    return str(v or "").strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Mode:
    name: str
    neighbor_sweep: bool
    combo_booster: bool
    beam_booster: bool
    combo_booster_mode: str
    candidate_selector_mode: str


DEFAULT_MODES: dict[str, Mode] = {
    "baseline": Mode(
        name="baseline",
        neighbor_sweep=False,
        combo_booster=False,
        beam_booster=False,
        combo_booster_mode="classic",
        candidate_selector_mode="default",
    ),
    "neighbor_sweep": Mode(
        name="neighbor_sweep",
        neighbor_sweep=True,
        combo_booster=False,
        beam_booster=False,
        combo_booster_mode="classic",
        candidate_selector_mode="default",
    ),
    "combo_booster": Mode(
        name="combo_booster",
        neighbor_sweep=False,
        combo_booster=True,
        beam_booster=False,
        combo_booster_mode="classic",
        candidate_selector_mode="default",
    ),
    "combo_booster_multi_axis": Mode(
        name="combo_booster_multi_axis",
        neighbor_sweep=False,
        combo_booster=True,
        beam_booster=False,
        combo_booster_mode="multi_axis",
        candidate_selector_mode="default",
    ),
    "combo_booster_slot_diverse": Mode(
        name="combo_booster_slot_diverse",
        neighbor_sweep=False,
        combo_booster=True,
        beam_booster=False,
        combo_booster_mode="classic",
        candidate_selector_mode="slot_diverse_archive",
    ),
    "combo_booster_multi_axis_slot_diverse": Mode(
        name="combo_booster_multi_axis_slot_diverse",
        neighbor_sweep=False,
        combo_booster=True,
        beam_booster=False,
        combo_booster_mode="multi_axis",
        candidate_selector_mode="slot_diverse_archive",
    ),
    "beam_booster": Mode(
        name="beam_booster",
        neighbor_sweep=False,
        combo_booster=False,
        beam_booster=True,
        combo_booster_mode="classic",
        candidate_selector_mode="default",
    ),
    "promising_archive": Mode(
        name="promising_archive",
        neighbor_sweep=False,
        combo_booster=False,
        beam_booster=False,
        combo_booster_mode="classic",
        candidate_selector_mode="promising_archive",
    ),
}


def _run_main(
    *,
    config_path: Path,
    db_path: Path,
    out_log: Path,
    seed: int,
    mode: Mode,
    env_overrides: dict[str, str],
) -> dict:
    env = os.environ.copy()
    env["METAFINDER_CONFIG_PATH"] = str(config_path)
    env["EVOLUTION_DB_PATH"] = str(db_path)
    env["GA_SEED"] = str(int(seed))
    env["METAFINDER_IGNORE_RESUME_QUEUE"] = "1"

    # Toggle combo booster.
    env["FG_COMBO_BOOSTER_ENABLED"] = "1" if mode.combo_booster else "0"
    env["FG_BEAM_BOOSTER_ENABLED"] = "1" if mode.beam_booster else "0"
    if mode.combo_booster:
        env["FG_COMBO_BOOSTER_MODE"] = str(mode.combo_booster_mode or "classic")
    else:
        env.pop("FG_COMBO_BOOSTER_MODE", None)

    # Toggle candidate selector mode (env driven so all call sites pick it up).
    if mode.candidate_selector_mode and mode.candidate_selector_mode != "default":
        env["FG_CANDIDATE_SELECTOR_MODE"] = str(mode.candidate_selector_mode)
    else:
        env.pop("FG_CANDIDATE_SELECTOR_MODE", None)

    # Optional promising-archive knobs (only used when selector mode is active).
    env.update({k: str(v) for k, v in (env_overrides or {}).items() if v is not None})

    out_log.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    with out_log.open("wb") as fh:
        proc = subprocess.run(
            [sys.executable, "main.py"],
            stdout=fh,
            stderr=subprocess.STDOUT,
            env=env,
            cwd=str(Path.cwd()),
        )
    dt = time.perf_counter() - t0
    return {
        "exit_code": int(proc.returncode),
        "elapsed_sec": float(dt),
    }


def _compute_success_counts(
    runs: list[dict],
    *,
    song_prefix: str,
) -> dict:
    songs: set[str] = set()
    for r in runs:
        scores = r.get("scores") or {}
        for name in scores.keys():
            if str(name).startswith(song_prefix):
                songs.add(str(name))
    song_names = sorted(songs)

    global_best: dict[str, int] = {s: 0 for s in song_names}
    for r in runs:
        scores = r.get("scores") or {}
        for s in song_names:
            try:
                v = int((scores.get(s) or {}).get("best_fg_score", 0) or 0)
            except Exception:
                v = 0
            if v > global_best.get(s, 0):
                global_best[s] = v

    by_mode: dict[str, dict[str, int]] = {}
    for r in runs:
        mode = str(r.get("mode") or "")
        if not mode:
            continue
        scores = r.get("scores") or {}
        by_mode.setdefault(mode, {"__runs__": 0, "__all__": 0})
        by_mode[mode]["__runs__"] += 1

        all_ok = True
        for s in song_names:
            try:
                v = int((scores.get(s) or {}).get("best_fg_score", 0) or 0)
            except Exception:
                v = 0
            ok = v == global_best.get(s, 0)
            by_mode[mode][s] = by_mode[mode].get(s, 0) + (1 if ok else 0)
            all_ok = all_ok and ok
        by_mode[mode]["__all__"] += 1 if all_ok else 0

    return {
        "song_prefix": song_prefix,
        "song_names": song_names,
        "global_best_fg_score": global_best,
        "by_mode": by_mode,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-config", default="config.ini")
    ap.add_argument("--song", default="Aether")
    ap.add_argument("--difficulty", default="All")
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--seed-base", type=int, default=1000)
    ap.add_argument(
        "--modes",
        default="baseline,neighbor_sweep,combo_booster,combo_booster_multi_axis,combo_booster_multi_axis_slot_diverse,combo_booster_slot_diverse,beam_booster,promising_archive",
    )
    ap.add_argument("--outdir", default=str(Path("artifacts") / "bench" / "fg_boosters_aether"))
    ap.add_argument("--fg-promising-band-pct", type=float, default=0.1)
    ap.add_argument("--fg-promising-max-pool", type=int, default=20000)
    ap.add_argument("--fg-promising-per-mini", type=int, default=6)
    ap.add_argument("--fg-promising-per-center", type=int, default=6)
    ap.add_argument("--fg-promising-center-bin", type=int, default=2)
    args = ap.parse_args()

    base_cfg_path = Path(args.base_config)
    if not base_cfg_path.exists():
        print(f"Base config not found: {base_cfg_path}")
        return 2

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    mode_names = [m.strip() for m in str(args.modes or "").split(",") if m.strip()]
    modes: list[Mode] = []
    for name in mode_names:
        mode = DEFAULT_MODES.get(name)
        if mode is None:
            print(f"Unknown mode: {name}")
            return 2
        modes.append(mode)
    if not modes:
        print("No modes selected")
        return 2

    # These env knobs apply only to promising_archive runs, but harmless elsewhere.
    env_overrides = {
        "FG_PROMISING_BAND_PCT": str(float(args.fg_promising_band_pct)),
        "FG_PROMISING_MAX_POOL": str(int(args.fg_promising_max_pool)),
        "FG_PROMISING_PER_MINI": str(int(args.fg_promising_per_mini)),
        "FG_PROMISING_PER_CENTER": str(int(args.fg_promising_per_center)),
        "FG_PROMISING_CENTER_BIN": str(int(args.fg_promising_center_bin)),
    }

    runs: list[dict] = []
    total_runs = int(args.runs) * len(modes)
    run_idx = 0

    for mode in modes:
        for i in range(1, int(args.runs) + 1):
            run_idx += 1
            seed = int(args.seed_base) + i

            run_dir = outdir / mode.name / f"run_{i}"
            run_dir.mkdir(parents=True, exist_ok=True)
            cfg_out = run_dir / "config.ini"
            db_out = run_dir / "evolution.db"
            log_out = run_dir / "run.log"

            # Ensure no DB seeding influences between runs.
            for suffix in ("", "-wal", "-shm"):
                try:
                    p = Path(str(db_out) + suffix)
                    if p.exists():
                        p.unlink()
                except Exception:
                    pass

            overrides = {
                "CalculateSong": {
                    "Song_Name": str(args.song),
                    "Difficulty": str(args.difficulty),
                    "TargetPrimary": "All",
                    "TargetSecondary": "All",
                },
                "IterationEngine": {
                    "LoopForever": "false",
                    "IgnoreResumeQueue": "true",
                    "ForceGreatsMode": "true",
                    "ForceGreatsFinder": "true",
                    "UseEvolutionDB": "true",
                    # Booster toggles (neighbor sweep is config-driven).
                    "FG_NeighborSweep": "true" if mode.neighbor_sweep else "false",
                },
            }
            _write_cfg(base_cfg_path, out_path=cfg_out, overrides=overrides)

            meta = _run_main(
                config_path=cfg_out,
                db_path=db_out,
                out_log=log_out,
                seed=seed,
                mode=mode,
                env_overrides=env_overrides,
            )

            scores = _read_best_scores(db_out, song_prefix=str(args.song))
            _apply_best_fg_from_log(scores, log_path=log_out, song_prefix=str(args.song))
            run = {
                "mode": mode.name,
                "run": i,
                "seed": seed,
                "run_dir": str(run_dir),
                **meta,
                "scores": scores,
            }
            runs.append(run)

            # Print quick progress line (Hard is usually the most interesting).
            hard_fg = 0
            for name, info in (scores or {}).items():
                if str(name).lower().startswith(str(args.song).lower()) and "(hard)" in str(name).lower():
                    hard_fg = int(info.get("best_fg_score", 0) or 0)
                    break
            print(
                f"[{run_idx}/{total_runs}] mode={mode.name} run={i} seed={seed} "
                f"exit={run['exit_code']} time={run['elapsed_sec']:.1f}s hard_fg={hard_fg}"
            )

    summary = {
        "base_config": str(base_cfg_path),
        "song": str(args.song),
        "difficulty": str(args.difficulty),
        "runs_per_mode": int(args.runs),
        "modes": [m.name for m in modes],
        "env_overrides": env_overrides,
        "runs": runs,
        "success": _compute_success_counts(runs, song_prefix=str(args.song)),
    }

    summary_path = outdir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Saved: {summary_path}")

    # Print final success counts.
    success = summary["success"]
    song_names = success.get("song_names") or []
    global_best = success.get("global_best_fg_score") or {}
    by_mode = success.get("by_mode") or {}

    print("\nGlobal best FG scores:")
    for s in song_names:
        print(f"  {s}: {int(global_best.get(s, 0) or 0)}")

    print("\nSuccess counts (hits global best):")
    for mode_name, counts in by_mode.items():
        n = int(counts.get("__runs__", 0) or 0)
        all_hits = int(counts.get("__all__", 0) or 0)
        parts = [f"{mode_name}: all={all_hits}/{n}"]
        for s in song_names:
            parts.append(f"{s}={int(counts.get(s, 0) or 0)}/{n}")
        print("  " + " | ".join(parts))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
