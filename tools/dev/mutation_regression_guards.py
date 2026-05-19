"""
Mutation-style regression guard verifier.

Purpose:
- Prove that our key regression tests actually fail when the historical bug patterns are reintroduced.
- Keep this as an *optional* developer tool (it intentionally makes the worktree dirty temporarily).

What it does:
1) Runs a small baseline set of GPU regression tests (expected PASS).
2) "Bug injection" scenario A (temporary file edit): disables CM lookahead and asserts the plateau guard FAILS.
3) "Bug injection" scenario B (temporary file edit): breaks warmstart best-key reduction and asserts parity test FAILS.

This is designed to catch the kind of multi-day debugging incidents caused by subtle GPU races and
"hidden top-1 misses" (suboptimal winners that look like regressions).
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _run(cmd: list[str], *, env: dict[str, str] | None = None) -> int:
    proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT), env=env)
    return int(proc.returncode)


def _write_text_lf(path: Path, data: str) -> None:
    # The repo enforces LF for *.py via .gitattributes. When running on Windows,
    # Path.write_text(newline=None) would translate to CRLF; keep outputs stable.
    path.write_text(data, encoding="utf-8", newline="\n")


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _pytest(args: list[str], *, extra_env: dict[str, str] | None = None) -> int:
    env = dict(os.environ)
    if extra_env:
        env.update({str(k): str(v) for k, v in extra_env.items()})
    return _run([sys.executable, "-m", "pytest", *args], env=env)


def _require_clean_worktree() -> None:
    proc = subprocess.run(["git", "status", "--porcelain"], cwd=str(PROJECT_ROOT), capture_output=True, text=True)
    if int(proc.returncode) != 0:
        raise RuntimeError("git status failed; is git installed and is this a git repo?")
    if (proc.stdout or "").strip():
        raise RuntimeError("Worktree must be clean (git status --porcelain not empty).")


def _mutate_warmstart_no_best_key_write(path: Path) -> str:
    original = path.read_text(encoding="utf-8")

    old_candidates = [
        "kernels_helpers.chunk_best_key[genome_idx] = block_best",
        "ti.atomic_max(kernels_helpers.chunk_best_key[genome_idx], local_best_key)",
    ]
    new_map = {
        old_candidates[0]: "kernels_helpers.chunk_best_key[genome_idx] = ti.u64(0)",
        old_candidates[1]: "ti.atomic_max(kernels_helpers.chunk_best_key[genome_idx], ti.u64(0))",
    }

    # Only mutate the warmstart kernel (avoid accidental edits if the pattern is reused).
    start = original.find("def ga_find_best_combo_warmstart_kernel")
    if start < 0:
        raise RuntimeError("Failed to locate ga_find_best_combo_warmstart_kernel() in warmstart.py")
    end = original.find("@ti.kernel", start + 1)
    if end < 0:
        end = len(original)

    block = original[start:end]
    matched = None
    for old in old_candidates:
        if old in block:
            matched = old
            break
    if matched is None:
        raise RuntimeError("Failed to locate warmstart best-key write for mutation.")

    mutated_block = block.replace(matched, new_map[matched])
    if mutated_block == block:
        raise RuntimeError("Failed to apply warmstart mutation.")
    if matched in mutated_block:
        raise RuntimeError("Warmstart mutation did not fully apply inside ga_find_best_combo_warmstart_kernel().")

    mutated = original[:start] + mutated_block + original[end:]
    _write_text_lf(path, mutated)
    return original


def _mutate_disable_cm_lookahead(path: Path) -> str:
    original = _read_text(path)
    old = "CM_LOOKAHEAD_MAX = 10"
    new = "CM_LOOKAHEAD_MAX = 0"
    if old not in original:
        raise RuntimeError("Failed to locate CM_LOOKAHEAD_MAX line for mutation.")
    mutated = original.replace(old, new, 1)
    if mutated == original or old in mutated:
        raise RuntimeError("Failed to apply CM lookahead mutation.")
    _write_text_lf(path, mutated)
    return original


def _mutate_disable_cm_jump(path: Path) -> str:
    original = _read_text(path)
    old = "CM_JUMP_MAX: ti.i32 = 10"
    new = "CM_JUMP_MAX: ti.i32 = 0"
    if old not in original:
        raise RuntimeError("Failed to locate CM_JUMP_MAX line for mutation.")
    mutated = original.replace(old, new, 1)
    if mutated == original or old in mutated:
        raise RuntimeError("Failed to apply CM jump mutation.")
    _write_text_lf(path, mutated)
    return original


def main() -> int:
    parser = argparse.ArgumentParser(description="Run regression-guard mutation checks.")
    parser.add_argument(
        "--baseline-only",
        action="store_true",
        help="Only run the baseline guard tests (skip bug-injection scenarios).",
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Allow running mutation scenarios even with a dirty worktree (the mutated file is restored in-process).",
    )
    args = parser.parse_args()

    baseline_tests = [
        "-q",
        "tests/test_gpu_exact_inner_registry_solve.py::test_registry_solve_exact_inner_matches_cpu_exact",
        "tests/test_gem_optimizer_cm_lookahead.py::test_optimize_core_jit_cm_lookahead_breaks_plateau_trap",
        "tests/test_gpu_local_search_cm_plateau.py::test_local_search_from_hint_cm_jump_breaks_plateau_trap",
    ]

    print("[mutation-guards] Baseline: expect PASS")
    rc = _pytest(baseline_tests)
    if rc != 0:
        print("[mutation-guards] Baseline FAILED (fix tests/environment before running mutations).")
        return rc

    if args.baseline_only:
        return 0

    # From here on we mutate env/files; enforce a clean tree so we can always restore safely.
    if not args.allow_dirty:
        _require_clean_worktree()

    print("[mutation-guards] Injection A: disable CM lookahead; expect FAIL")
    scoring_core_path = PROJECT_ROOT / "gear_optimizer/solver/scoring_core.py"
    scoring_core_original = _mutate_disable_cm_lookahead(scoring_core_path)
    try:
        rc = _pytest(
            [
                "-q",
                "tests/test_gem_optimizer_cm_lookahead.py::test_optimize_core_jit_cm_lookahead_breaks_plateau_trap",
            ]
        )
        if rc == 0:
            print("[mutation-guards] ERROR: mutated CM lookahead unexpectedly PASSED (guard is too weak).")
            return 2
    finally:
        _write_text_lf(scoring_core_path, scoring_core_original)

    print("[mutation-guards] Injection B: disable warmstart CM jump; expect FAIL")
    kernels_scoring_path = PROJECT_ROOT / "gear_optimizer/solver/taichi_gem/kernels/kernels_scoring.py"
    kernels_scoring_original = _mutate_disable_cm_jump(kernels_scoring_path)
    try:
        rc = _pytest(
            [
                "-q",
                "tests/test_gpu_local_search_cm_plateau.py::test_local_search_from_hint_cm_jump_breaks_plateau_trap",
            ]
        )
        if rc == 0:
            print("[mutation-guards] ERROR: mutated CM jump unexpectedly PASSED (guard is too weak).")
            return 3
    finally:
        _write_text_lf(kernels_scoring_path, kernels_scoring_original)

    print("[mutation-guards] Injection C: break warmstart best-key reduction; expect FAIL")
    warmstart_path = PROJECT_ROOT / "gear_optimizer/solver/taichi_gem/kernels/ga_eval/warmstart.py"
    warmstart_original = _mutate_warmstart_no_best_key_write(warmstart_path)
    try:
        rc = _pytest(
            [
                "-q",
                "tests/test_gpu_exact_inner_registry_solve.py::test_registry_solve_exact_inner_matches_cpu_exact",
            ]
        )
        if rc == 0:
            print("[mutation-guards] ERROR: mutated warmstart unexpectedly PASSED (guard is too weak).")
            return 4
    finally:
        _write_text_lf(warmstart_path, warmstart_original)

    print("[mutation-guards] OK: injected bugs were detected by tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
