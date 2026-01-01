import argparse
import configparser
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


POST_FG_RE = re.compile(
    r"^\[POST\]\[FG\]\s+Saved\s+(?P<n>[0-9]+)\s+FG\s+variant\(s\)\s+for\s+(?P<song>.+?)\s+\(best_fg=(?P<best_fg>[0-9]+)\)\s*$"
)
GPU_EXECUTOR_PROFILE_RE = re.compile(
    r"^\[GpuExecutor\]\[PROFILE\]\s+wait=(?P<wait>[0-9.]+)s\s+exec=(?P<exec>[0-9.]+)s\s+(?:busy|util)=(?P<util>[0-9.]+)%"
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


def _rm_if_exists(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
    except Exception:
        pass


def _parse_best_fg_from_log(log_path: Path) -> dict[str, int]:
    try:
        text = log_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return {}

    out: dict[str, int] = {}
    for line in (text or "").splitlines():
        m = POST_FG_RE.match(line.strip())
        if not m:
            continue
        song = str(m.group("song") or "").strip()
        if not song:
            continue
        try:
            best_fg = int(m.group("best_fg") or 0)
        except Exception:
            best_fg = 0
        prev = out.get(song, 0)
        if best_fg > prev:
            out[song] = best_fg
    return out


def _parse_gpu_executor_profile(log_path: Path) -> dict | None:
    try:
        text = log_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None

    prof = None
    for line in (text or "").splitlines():
        m = GPU_EXECUTOR_PROFILE_RE.match(line.strip())
        if not m:
            continue
        try:
            prof = {
                "wait_sec": float(m.group("wait")),
                "exec_sec": float(m.group("exec")),
                "util_pct": float(m.group("util")),
            }
        except Exception:
            prof = None
    return prof


@dataclass(frozen=True)
class Mode:
    name: str
    neighbor_sweep: bool
    combo_booster: bool
    beam_booster: bool
    candidate_selector_mode: str


DEFAULT_MODES: dict[str, Mode] = {
    "baseline": Mode(
        name="baseline",
        neighbor_sweep=False,
        combo_booster=False,
        beam_booster=False,
        candidate_selector_mode="default",
    ),
    "neighbor_sweep": Mode(
        name="neighbor_sweep",
        neighbor_sweep=True,
        combo_booster=False,
        beam_booster=False,
        candidate_selector_mode="default",
    ),
    "combo_booster": Mode(
        name="combo_booster",
        neighbor_sweep=False,
        combo_booster=True,
        beam_booster=False,
        candidate_selector_mode="default",
    ),
    "combo_booster_slot_diverse": Mode(
        name="combo_booster_slot_diverse",
        neighbor_sweep=False,
        combo_booster=True,
        beam_booster=False,
        candidate_selector_mode="slot_diverse_archive",
    ),
    "beam_booster": Mode(
        name="beam_booster",
        neighbor_sweep=False,
        combo_booster=False,
        beam_booster=True,
        candidate_selector_mode="default",
    ),
    "promising_archive": Mode(
        name="promising_archive",
        neighbor_sweep=False,
        combo_booster=False,
        beam_booster=False,
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
    env["GPU_EXECUTOR_PROFILE"] = "1"

    env["FG_COMBO_BOOSTER_ENABLED"] = "1" if mode.combo_booster else "0"
    env["FG_BEAM_BOOSTER_ENABLED"] = "1" if mode.beam_booster else "0"

    if mode.candidate_selector_mode and mode.candidate_selector_mode != "default":
        env["FG_CANDIDATE_SELECTOR_MODE"] = str(mode.candidate_selector_mode)
    else:
        env.pop("FG_CANDIDATE_SELECTOR_MODE", None)

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


def _compute_success_counts(runs: list[dict]) -> dict:
    songs: set[str] = set()
    for r in runs:
        scores = r.get("best_fg") or {}
        for name in scores.keys():
            songs.add(str(name))
    song_names = sorted(songs)

    global_best: dict[str, int] = {s: 0 for s in song_names}
    for r in runs:
        scores = r.get("best_fg") or {}
        for s in song_names:
            try:
                v = int(scores.get(s, 0) or 0)
            except Exception:
                v = 0
            if v > global_best.get(s, 0):
                global_best[s] = v

    by_mode: dict[str, dict] = {}
    for r in runs:
        mode = str(r.get("mode") or "")
        if not mode:
            continue
        scores = r.get("best_fg") or {}
        state = by_mode.setdefault(
            mode,
            {
                "__runs__": 0,
                "__all__": 0,
                "__mean_song_hit_rate__": 0.0,
                "__songs_where_mode_reached_global_best__": 0,
                "__mode_best_fg__": {},
                "__song_hits__": {s: 0 for s in song_names},
                "__songs_matched_per_run__": [],
            },
        )
        state["__runs__"] += 1

        matched = 0
        all_ok = True
        for s in song_names:
            try:
                v = int(scores.get(s, 0) or 0)
            except Exception:
                v = 0
            ok = v == global_best.get(s, 0)
            if ok:
                state["__song_hits__"][s] = int(state["__song_hits__"].get(s, 0) or 0) + 1
                matched += 1
            all_ok = all_ok and ok
            # Mode best (across runs)
            prev = int(state["__mode_best_fg__"].get(s, 0) or 0)
            if v > prev:
                state["__mode_best_fg__"][s] = v

        state["__songs_matched_per_run__"].append(int(matched))
        if all_ok:
            state["__all__"] += 1

    for mode, state in by_mode.items():
        n = int(state.get("__runs__", 0) or 0)
        if n <= 0:
            continue
        hit_rates = []
        for s, c in (state.get("__song_hits__") or {}).items():
            try:
                hit_rates.append(float(c) / float(n))
            except Exception:
                pass
        state["__mean_song_hit_rate__"] = float(sum(hit_rates) / len(hit_rates)) if hit_rates else 0.0

        # How many songs did this mode ever reach the global best for?
        reached = 0
        mode_best = state.get("__mode_best_fg__") or {}
        for s in song_names:
            if int(mode_best.get(s, 0) or 0) == int(global_best.get(s, 0) or 0):
                reached += 1
        state["__songs_where_mode_reached_global_best__"] = int(reached)

    return {
        "song_names": song_names,
        "global_best_fg": global_best,
        "by_mode": by_mode,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-config", default=str(Path("configs") / "profile" / "config_profile_inflight_queue24_fast.ini"))
    ap.add_argument("--runs", type=int, default=10)
    ap.add_argument("--seed-base", type=int, default=1000)
    ap.add_argument(
        "--modes",
        default="baseline,neighbor_sweep,combo_booster,combo_booster_slot_diverse,beam_booster,promising_archive",
    )
    ap.add_argument("--outdir", default=str(Path("artifacts") / "bench" / "queue24_boosters"))
    ap.add_argument("--fg-promising-band-pct", type=float, default=0.1)
    ap.add_argument("--fg-promising-max-pool", type=int, default=20000)
    ap.add_argument("--fg-promising-per-mini", type=int, default=6)
    ap.add_argument("--fg-promising-per-center", type=int, default=6)
    ap.add_argument("--fg-promising-center-bin", type=int, default=2)
    ap.add_argument("--fg-slot-band-pct", type=float, default=1.0)
    ap.add_argument("--fg-slot-max-pool", type=int, default=20000)
    ap.add_argument("--fg-slot-per-slot", type=int, default=10)
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

    env_overrides = {
        "FG_PROMISING_BAND_PCT": str(float(args.fg_promising_band_pct)),
        "FG_PROMISING_MAX_POOL": str(int(args.fg_promising_max_pool)),
        "FG_PROMISING_PER_MINI": str(int(args.fg_promising_per_mini)),
        "FG_PROMISING_PER_CENTER": str(int(args.fg_promising_per_center)),
        "FG_PROMISING_CENTER_BIN": str(int(args.fg_promising_center_bin)),
        "FG_SLOT_DIVERSE_BAND_PCT": str(float(args.fg_slot_band_pct)),
        "FG_SLOT_DIVERSE_MAX_POOL": str(int(args.fg_slot_max_pool)),
        "FG_SLOT_DIVERSE_PER_SLOT": str(int(args.fg_slot_per_slot)),
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

            for suffix in ("", "-wal", "-shm"):
                _rm_if_exists(Path(str(db_out) + suffix))

            overrides = {
                "IterationEngine": {
                    "LoopForever": "false",
                    "IgnoreResumeQueue": "true",
                    "FG_NeighborSweep": "true" if mode.neighbor_sweep else "false",
                }
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

            best_fg = _parse_best_fg_from_log(log_out)
            prof = _parse_gpu_executor_profile(log_out)
            run = {
                "mode": mode.name,
                "run": i,
                "seed": seed,
                "run_dir": str(run_dir),
                **meta,
                "best_fg": best_fg,
                "gpu_executor_profile": prof,
            }
            runs.append(run)

            util = (prof or {}).get("util_pct")
            util_str = f"{util:.1f}%" if isinstance(util, (int, float)) else "n/a"
            print(
                f"[{run_idx}/{total_runs}] mode={mode.name} run={i} seed={seed} "
                f"exit={run['exit_code']} time={run['elapsed_sec']:.1f}s gpu_busy={util_str}"
            )

    success = _compute_success_counts(runs)
    summary = {
        "base_config": str(base_cfg_path),
        "runs_per_mode": int(args.runs),
        "modes": [m.name for m in modes],
        "env_overrides": env_overrides,
        "runs": runs,
        "success": success,
    }
    summary_path = outdir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Saved: {summary_path}")

    # Print compact summary.
    song_names = success.get("song_names") or []
    by_mode = success.get("by_mode") or {}
    print(f"\nSongs tracked: {len(song_names)}")
    for mode_name, st in by_mode.items():
        n = int(st.get("__runs__", 0) or 0)
        all_hits = int(st.get("__all__", 0) or 0)
        mean_rate = float(st.get("__mean_song_hit_rate__", 0.0) or 0.0)
        reached = int(st.get("__songs_where_mode_reached_global_best__", 0) or 0)
        print(
            f"  {mode_name}: all_songs={all_hits}/{n} mean_song_hit_rate={mean_rate:.3f} "
            f"reached_global_best_songs={reached}/{len(song_names)}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
