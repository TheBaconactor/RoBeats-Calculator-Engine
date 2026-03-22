"""
Mutation-style regression guard verifier.

Purpose:
- Prove that our key regression tests actually fail when the historical bug patterns are reintroduced.
- Keep this as an *optional* developer tool (it intentionally makes the worktree dirty temporarily).

What it does:
1) Runs a small baseline set of GPU regression tests (expected PASS).
2) "Bug injection" scenario A (no file edits): disables winner refinement and asserts the refinement test FAILS.
3) "Bug injection" scenario B (temporary file edit): reintroduces in-place hint inheritance and asserts the hint test FAILS.
4) "Bug injection" scenario C (temporary file edit): breaks warmstart best-key reduction and asserts parity test FAILS.

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


def _mutate_ga_inherit_hints_in_place(path: Path) -> str:
    original = path.read_text(encoding="utf-8")

    old_a = "kernels_helpers.genome_hint_allocation_next[g][i] = kernels_helpers.genome_hint_allocation[parent_a][i]"
    new_a = "kernels_helpers.genome_hint_allocation[g][i] = kernels_helpers.genome_hint_allocation[parent_a][i]"

    old_b = "kernels_helpers.genome_hint_allocation_next[g][i] = 0"
    new_b = "kernels_helpers.genome_hint_allocation[g][i] = 0"

    # Only mutate the specific kernel we are guarding (avoid rewriting other helper kernels).
    start = original.find("def ga_inherit_hints_kernel")
    if start < 0:
        raise RuntimeError("Failed to locate ga_inherit_hints_kernel() in kernels_ga.py")
    # Find the next kernel decorator (end of this kernel's body).
    end = original.find("@ti.kernel", start)
    if end < 0:
        end = len(original)

    block = original[start:end]
    mutated_block = block.replace(old_a, new_a).replace(old_b, new_b)
    if mutated_block == block:
        raise RuntimeError("Failed to apply hint-inheritance mutation (expected patterns not found in kernel).")
    if old_a in mutated_block or old_b in mutated_block:
        raise RuntimeError("Hint-inheritance mutation did not fully apply inside ga_inherit_hints_kernel().")

    mutated = original[:start] + mutated_block + original[end:]

    _write_text_lf(path, mutated)
    return original


def _mutate_warmstart_no_best_key_write(path: Path) -> str:
    original = path.read_text(encoding="utf-8")

    old = "ti.atomic_max(kernels_helpers.chunk_best_key[genome_idx], local_best_key)"
    new = "ti.atomic_max(kernels_helpers.chunk_best_key[genome_idx], ti.u64(0))"

    # Only mutate the warmstart kernel (avoid accidental edits if the pattern is reused).
    start = original.find("def ga_find_best_combo_warmstart_kernel")
    if start < 0:
        raise RuntimeError("Failed to locate ga_find_best_combo_warmstart_kernel() in warmstart.py")
    end = original.find("@ti.kernel", start + 1)
    if end < 0:
        end = len(original)

    block = original[start:end]
    if old not in block:
        raise RuntimeError("Failed to locate warmstart best-key atomic_max line for mutation.")

    mutated_block = block.replace(old, new)
    if mutated_block == block:
        raise RuntimeError("Failed to apply warmstart mutation.")
    if old in mutated_block:
        raise RuntimeError("Warmstart mutation did not fully apply inside ga_find_best_combo_warmstart_kernel().")

    mutated = original[:start] + mutated_block + original[end:]
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
        "tests/test_solve_genomes_from_registry_score_parity.py::test_solve_genomes_from_registry_matches_parallel_scores_with_user_gems_and_static_overflow",
        "tests/test_gpu_ga_hint_inheritance_race_free.py::test_ga_inherit_hints_uses_next_buffer_and_does_not_mutate_parents_in_place",
        "tests/test_gpu_ga_winner_refinement_enforced.py::test_gpu_native_ga_winner_refinement_is_enforced",
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

    print("[mutation-guards] Injection A: disable GA winner refinement; expect FAIL")
    rc = _pytest(
        [
            "-q",
            "tests/test_gpu_ga_winner_refinement_enforced.py::test_gpu_native_ga_winner_refinement_is_enforced",
        ],
        extra_env={"GPU_GA_WINNER_REFINEMENT": "0"},
    )
    if rc == 0:
        print("[mutation-guards] ERROR: refinement-disabled run unexpectedly PASSED (guard is too weak).")
        return 2

    print("[mutation-guards] Injection B: reintroduce in-place hint inheritance; expect FAIL")
    kernels_path = PROJECT_ROOT / "gear_optimizer/solver/taichi_gem/kernels/kernels_ga.py"
    original = _mutate_ga_inherit_hints_in_place(kernels_path)
    try:
        rc = _pytest(
            [
                "-q",
                "tests/test_gpu_ga_hint_inheritance_race_free.py::test_ga_inherit_hints_uses_next_buffer_and_does_not_mutate_parents_in_place",
            ]
        )
        if rc == 0:
            print("[mutation-guards] ERROR: mutated hint inheritance unexpectedly PASSED (guard is too weak).")
            return 3
    finally:
        _write_text_lf(kernels_path, original)

    print("[mutation-guards] Injection C: break warmstart best-key reduction; expect FAIL")
    warmstart_path = PROJECT_ROOT / "gear_optimizer/solver/taichi_gem/kernels/ga_eval/warmstart.py"
    warmstart_original = _mutate_warmstart_no_best_key_write(warmstart_path)
    try:
        rc = _pytest(
            [
                "-q",
                "tests/test_solve_genomes_from_registry_score_parity.py::test_solve_genomes_from_registry_matches_parallel_scores_with_user_gems_and_static_overflow",
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
