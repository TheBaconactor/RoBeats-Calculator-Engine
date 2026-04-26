"""
Run repeatable GA/FG kernel-shape sweeps using the maintained microbenches.

This harness always launches each case in a fresh subprocess so Taichi/kernel env
overrides that are cached at import time are measured correctly.
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.bench._bench_reporting import BENCH_JSON_PREFIX


def parse_csv_ints(value: str) -> list[int]:
    out: list[int] = []
    for part in str(value or "").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.append(int(part))
        except Exception as exc:
            raise ValueError(f"Invalid integer list value: {part!r}") from exc
    if not out:
        raise ValueError("Expected at least one integer value.")
    return out


def parse_csv_strings(value: str) -> list[str]:
    out: list[str] = []
    for part in str(value or "").split(","):
        normalized = str(part or "").strip().lower()
        if normalized:
            out.append(normalized)
    if not out:
        raise ValueError("Expected at least one string value.")
    return out


def build_ga_sweep_cases(
    *,
    taichi_block_dims: list[int],
    reduce_block_dims: list[int],
    batch_runs: list[int],
    materialize_modes: list[str],
) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for taichi_block_dim, reduce_block_dim, batch_run, materialize_mode in itertools.product(
        taichi_block_dims, reduce_block_dims, batch_runs, materialize_modes
    ):
        env = {
            "TAICHI_BLOCK_DIM": int(taichi_block_dim),
            "GA_FTFF_REDUCE_BLOCK_DIM": int(reduce_block_dim),
            "GPU_NATIVE_GA_BATCH_RUNS": int(batch_run),
        }
        mode_label = str(materialize_mode).replace("-", "_")
        label = (
            f"taichi{int(taichi_block_dim)}_reduce{int(reduce_block_dim)}_batch{int(batch_run)}_mode_{mode_label}"
        )
        cases.append({"label": label, "env": env, "materialize_mode": str(materialize_mode)})
    return cases


def build_fg_sweep_cases(
    *,
    stage1_block_dims: list[int],
    target_threads: list[int],
) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for stage1_block_dim, target_thread_budget in itertools.product(stage1_block_dims, target_threads):
        env = {
            "FG_STAGE1_BLOCK_DIM": int(stage1_block_dim),
            "FG_TARGET_THREADS_PER_KERNEL": int(target_thread_budget),
        }
        label = f"stage1_{int(stage1_block_dim)}_threads_{int(target_thread_budget)}"
        cases.append({"label": label, "env": env})
    return cases


def rank_ga_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(results, key=lambda item: float(item.get("iters_per_sec", 0.0)), reverse=True)


def rank_fg_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(results, key=lambda item: float(item.get("steady_iters_per_sec", 0.0)), reverse=True)


def _default_out_path() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return REPO_ROOT / "artifacts" / "bench" / f"gpu_occupancy_matrix_{stamp}.json"


def _extract_bench_json(stdout: str) -> dict[str, Any]:
    for line in reversed(str(stdout or "").splitlines()):
        if not line.startswith(BENCH_JSON_PREFIX):
            continue
        return json.loads(line[len(BENCH_JSON_PREFIX) :])
    raise ValueError("Bench JSON payload was not found in subprocess stdout.")


def _tail_lines(text: str, *, limit: int = 20) -> list[str]:
    lines = [line.rstrip() for line in str(text or "").splitlines()]
    if len(lines) <= int(limit):
        return lines
    return lines[-int(limit) :]


def _run_case(
    *,
    script_relative_path: str,
    script_args: list[str],
    env_overrides: dict[str, int],
    verbose: bool,
) -> dict[str, Any]:
    script_path = REPO_ROOT / Path(script_relative_path)
    cmd = [sys.executable, str(script_path), *script_args, "--json"]
    env = os.environ.copy()
    for key, value in env_overrides.items():
        env[str(key)] = str(value)
    completed = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if verbose and completed.stdout:
        print(completed.stdout, end="" if completed.stdout.endswith("\n") else "\n")
    if completed.returncode != 0:
        stderr_tail = "\n".join(_tail_lines(completed.stderr, limit=40))
        raise RuntimeError(
            f"Bench subprocess failed (returncode={completed.returncode}): {' '.join(cmd)}\n{stderr_tail}"
        )
    payload = _extract_bench_json(completed.stdout)
    payload["command"] = cmd
    payload["env_overrides"] = {str(key): int(value) for key, value in env_overrides.items()}
    payload["stdout_tail"] = _tail_lines(completed.stdout)
    payload["stderr_tail"] = _tail_lines(completed.stderr)
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("ga", "fg", "both"), default="both")
    ap.add_argument("--out", type=str, default="", help="Write sweep results JSON to this path.")
    ap.add_argument("--top", type=int, default=5, help="How many top cases to print per sweep.")
    ap.add_argument("--dry-run", action="store_true", help="Print the planned cases without executing them.")
    ap.add_argument("--verbose", action="store_true", help="Print full subprocess stdout while running.")

    ap.add_argument("--ga-taichi-block-dims", default="128,256")
    ap.add_argument("--ga-reduce-block-dims", default="128,256")
    ap.add_argument("--ga-batch-runs", default="0,1")
    ap.add_argument("--ga-materialize-modes", default="none")
    ap.add_argument("--ga-genomes", type=int, default=705)
    ap.add_argument("--ga-budget", type=int, default=90)
    ap.add_argument("--ga-iters", type=int, default=6)
    ap.add_argument("--ga-warmup", type=int, default=2)
    ap.add_argument("--ga-seed", type=int, default=1337)
    ap.add_argument("--ga-prune-plateaus", type=int, default=1)
    ap.add_argument("--ga-kernel-profiler", action="store_true")

    ap.add_argument("--fg-stage1-block-dims", default="64,128")
    ap.add_argument("--fg-target-threads", default="2000000,4000000,6000000")
    ap.add_argument("--fg-mode", choices=("executor", "direct"), default="direct")
    ap.add_argument("--fg-genomes", type=int, default=1024)
    ap.add_argument("--fg-sections", type=int, default=3)
    ap.add_argument("--fg-max-fp", default="5,5,5")
    ap.add_argument("--fg-tasks", type=int, default=16)
    ap.add_argument("--fg-ftff", type=int, default=128)
    ap.add_argument("--fg-iters", type=int, default=4)
    ap.add_argument("--fg-warmup", type=int, default=1)
    ap.add_argument("--fg-seed", type=int, default=1337)
    ap.add_argument("--fg-reuse-genome-stats", action="store_true")
    ap.add_argument("--fg-no-profiler", action="store_true")
    ap.add_argument("--fg-kernel-profiler", action="store_true")
    args = ap.parse_args()

    payload: dict[str, Any] = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": str(args.mode),
        "ga": None,
        "fg": None,
    }
    out_path = Path(str(args.out)).resolve() if str(args.out).strip() else _default_out_path()

    if args.mode in {"ga", "both"}:
        ga_cases = build_ga_sweep_cases(
            taichi_block_dims=parse_csv_ints(str(args.ga_taichi_block_dims)),
            reduce_block_dims=parse_csv_ints(str(args.ga_reduce_block_dims)),
            batch_runs=parse_csv_ints(str(args.ga_batch_runs)),
            materialize_modes=parse_csv_strings(str(args.ga_materialize_modes)),
        )
        print(f"[ga] planned cases: {len(ga_cases)}")
        if args.dry_run:
            for case in ga_cases:
                print(f"  - {case['label']}: {case['env']}")
        else:
            ga_results: list[dict[str, Any]] = []
            for idx, case in enumerate(ga_cases, start=1):
                print(f"[ga] case {idx}/{len(ga_cases)} {case['label']}")
                script_args = [
                    "--genomes",
                    str(int(args.ga_genomes)),
                    "--budget",
                    str(int(args.ga_budget)),
                    "--iters",
                    str(int(args.ga_iters)),
                    "--warmup",
                    str(int(args.ga_warmup)),
                    "--seed",
                    str(int(args.ga_seed)),
                    "--prune-plateaus",
                    str(int(args.ga_prune_plateaus)),
                    "--materialize-mode",
                    str(case["materialize_mode"]),
                ]
                if args.ga_kernel_profiler:
                    script_args.append("--kernel-profiler")
                result = _run_case(
                    script_relative_path="tools/bench/bench_gpu_native_ga_eval.py",
                    script_args=script_args,
                    env_overrides=case["env"],
                    verbose=bool(args.verbose),
                )
                result["label"] = case["label"]
                ga_results.append(result)
                kernel_pct = result.get("kernel_profiler_wall_pct")
                kernel_suffix = (
                    f" kernel%={float(kernel_pct):.2f}" if isinstance(kernel_pct, (float, int)) else ""
                )
                print(
                    f"  -> per_iter={float(result.get('per_iter_sec', 0.0)):.6f}s "
                    f"iters/sec={float(result.get('iters_per_sec', 0.0)):.3f}{kernel_suffix}"
                )
            ranked = rank_ga_results(ga_results)
            payload["ga"] = {
                "cases": ga_results,
                "best": ranked[0] if ranked else None,
                "top": ranked[: max(1, int(args.top))],
            }

    if args.mode in {"fg", "both"}:
        fg_cases = build_fg_sweep_cases(
            stage1_block_dims=parse_csv_ints(str(args.fg_stage1_block_dims)),
            target_threads=parse_csv_ints(str(args.fg_target_threads)),
        )
        print(f"[fg] planned cases: {len(fg_cases)}")
        if args.dry_run:
            for case in fg_cases:
                print(f"  - {case['label']}: {case['env']}")
        else:
            fg_results: list[dict[str, Any]] = []
            for idx, case in enumerate(fg_cases, start=1):
                print(f"[fg] case {idx}/{len(fg_cases)} {case['label']}")
                script_args = [
                    "--mode",
                    str(args.fg_mode),
                    "--genomes",
                    str(int(args.fg_genomes)),
                    "--sections",
                    str(int(args.fg_sections)),
                    "--max-fp",
                    str(args.fg_max_fp),
                    "--tasks",
                    str(int(args.fg_tasks)),
                    "--ftff",
                    str(int(args.fg_ftff)),
                    "--iters",
                    str(int(args.fg_iters)),
                    "--warmup",
                    str(int(args.fg_warmup)),
                    "--seed",
                    str(int(args.fg_seed)),
                ]
                if args.fg_reuse_genome_stats:
                    script_args.append("--reuse-genome-stats")
                if args.fg_no_profiler:
                    script_args.append("--no-profiler")
                if args.fg_kernel_profiler:
                    script_args.append("--kernel-profiler")
                result = _run_case(
                    script_relative_path="tools/bench/bench_fg_batch_throughput.py",
                    script_args=script_args,
                    env_overrides=case["env"],
                    verbose=bool(args.verbose),
                )
                result["label"] = case["label"]
                fg_results.append(result)
                kernel_pct = result.get("kernel_profiler_wall_pct")
                kernel_suffix = (
                    f" kernel%={float(kernel_pct):.2f}" if isinstance(kernel_pct, (float, int)) else ""
                )
                print(
                    f"  -> steady_mean={float(result.get('steady_mean_wall_sec', 0.0)):.6f}s "
                    f"steady_iters/sec={float(result.get('steady_iters_per_sec', 0.0)):.3f}{kernel_suffix}"
                )
            ranked = rank_fg_results(fg_results)
            payload["fg"] = {
                "cases": fg_results,
                "best": ranked[0] if ranked else None,
                "top": ranked[: max(1, int(args.top))],
            }

    if not args.dry_run:
        _write_json(out_path, payload)
        print(f"[out] wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
