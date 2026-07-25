"""
Repo guardrails.

These tests exist to prevent removed GPU paths from quietly reappearing and to keep
production scoring code importing through the intended public GPU modules.

Rationale:
- Removed GPU APIs (old batch gem solver) were expensive (host transfers + VRAM) and
  easy to accidentally re-wire back into production.
- Scoring orchestration should not import `taichi_gem` internals directly; it should
  go through `gear_optimizer.solver.taichi_gem.api` and/or the GPU executor.
"""

from __future__ import annotations

import ast
import importlib.util
import re
import sys
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[1]
_GITHUB_MATH_TEXT_UNDERSCORE = re.compile(r"\\text\{[^}]*_[^}]*\}")
_SENSITIVE_PLAYER_EXPORT_KEY = re.compile(
    r'"(?:localPlayerId|playerId|playerName)"\s*:'
)


def test_github_math_text_labels_do_not_use_underscores() -> None:
    offenders: list[str] = []
    for path in sorted(_REPO_ROOT.rglob("*.md")):
        if any(part in {".git", ".venv", "bin", "node_modules", "venv"} for part in path.parts):
            continue
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            if _GITHUB_MATH_TEXT_UNDERSCORE.search(line):
                rel = path.relative_to(_REPO_ROOT)
                offenders.append(f"{rel}:{line_number}")

    assert not offenders, (
        "GitHub strips Markdown underscore escapes inside LaTeX "
        r"\text{...} labels; use spaces in displayed labels instead:"
        "\n" + "\n".join(offenders)
    )


def test_repository_does_not_contain_player_identity_exports() -> None:
    offenders: list[str] = []
    for path in sorted(_REPO_ROOT.rglob("*.json")):
        if any(part in {".git", ".venv", "bin", "node_modules", "venv"} for part in path.parts):
            continue
        if _SENSITIVE_PLAYER_EXPORT_KEY.search(
            path.read_text(encoding="utf-8", errors="ignore")
        ):
            offenders.append(str(path.relative_to(_REPO_ROOT)))

    assert not offenders, (
        "Player-identity exports must stay outside the repository:\n"
        + "\n".join(offenders)
    )


def _load_policy_offense_scan():
    script = _REPO_ROOT / "tools" / "dev" / "policy_offense_scan.py"
    spec = importlib.util.spec_from_file_location("policy_offense_scan", script)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _iter_python_files(root: Path, rel_dirs: list[str]):
    skip_parts = {
        ".git",
        ".pytest_cache",
        "__pycache__",
        "Data",
        "bin",
        "artifacts",
        ".venv",
        "venv",
    }

    for rel in rel_dirs:
        base = root / rel
        if not base.exists():
            continue
        for p in base.rglob("*.py"):
            if any(part in skip_parts for part in p.parts):
                continue
            yield p


def test_no_removed_gpu_symbols_present() -> None:
    # Keep this list scoped to the removed batch gem solver surface.
    forbidden = (
        "optimize_gems_gpu",
        "optimize_gems_batch_gpu",
        "OPTIMIZE_GEMS_BATCH",
        "solve_batch_kernel",
        "copy_fever_masks_from_ndarray_kernel",
    )

    offenders: list[str] = []
    for path in _iter_python_files(
        _REPO_ROOT,
        rel_dirs=[
            "gear_optimizer",
            "general_meta",
            "tools",
        ],
    ):
        txt = path.read_text(encoding="utf-8", errors="ignore")
        hits = [tok for tok in forbidden if tok in txt]
        if hits:
            rel = path.relative_to(_REPO_ROOT)
            offenders.append(f"{rel}: {', '.join(hits)}")

    assert not offenders, "Removed GPU symbols were reintroduced:\n" + "\n".join(offenders)


def test_non_skyline_compatibility_shims_stay_deleted() -> None:
    forbidden = [
        "gear_optimizer/core/cfg_window_decode.py",
        "gear_optimizer/helpers/song_helpers/stats_gateway.py",
        "gear_optimizer/helpers/song_helpers/persistence.py",
        "gear_optimizer/solver/scoring/force_greats.py",
        "gear_optimizer/solver/candidate_solver_cache.py",
        "gear_optimizer/solver/gpu_executor_profile.py",
        "gear_optimizer/solver/gpu_profiler.py",
        "gear_optimizer/solver/item_pools.py",
        "gear_optimizer/solver/taichi_gem/ftff_combos.py",
        "gear_optimizer/solver/taichi_gem/api/gpu_prefetch.py",
        "gear_optimizer/solver/taichi_gem/force_greats/response_build_gpu.py",
        "gear_optimizer/solver/taichi_gem/force_greats/response_inner.py",
        "gear_optimizer/solver/taichi_gem/force_greats/api.py",
        "gear_optimizer/helpers/song_helpers/force_greats/response_frontier_adapter.py",
        "scripts/profile/profile_ga_gpu.py",
        "scripts/profile/profile_main_hot.py",
        "scripts/regression/ga_gpu_integration.py",
        "scripts/regression/gpu_stats_regression.py",
        "scripts/regression/regression_baseline.py",
        "scripts/regression/regression_ga.py",
        "tests/test_ga_evaluate_population_fusion.py",
        "tests/test_ga_population_upload_kernel.py",
        "tests/test_ga_run_payload_packed.py",
        "tests/test_gpu_elites_regression.py",
        "tests/test_gpu_ga_cold_eval_determinism.py",
        "tests/test_gpu_ga_eval_race_free.py",
        "tests/test_gpu_ga_global_best_consistency.py",
        "tests/test_gpu_ga_ops.py",
        "tests/test_gpu_native_ga_plateau_prune_regression.py",
        "tools/bench/bench_gpu_native_ga_eval.py",
        "tools/profile/tests/profile_ga.py",
    ]

    present = [rel for rel in forbidden if (_REPO_ROOT / rel).exists()]

    assert not present, "Non-Skyline compatibility shims were reintroduced:\n" + "\n".join(present)


def test_taichi_api_package_imports_fail_loudly() -> None:
    api_init = (_REPO_ROOT / "gear_optimizer" / "solver" / "taichi_gem" / "api" / "__init__.py").read_text(
        encoding="utf-8"
    )

    assert "except ImportError" not in api_init


def test_scoring_package_does_not_reexport_old_fever_solver_surface() -> None:
    scoring_init = (_REPO_ROOT / "gear_optimizer" / "solver" / "scoring" / "__init__.py").read_text(
        encoding="utf-8"
    )

    assert "solve_best_fever_combination" not in scoring_init
    assert "batch_evaluate_genomes" not in scoring_init


def test_legacy_ftff_solver_api_stays_deleted() -> None:
    parallel_solvers = (
        _REPO_ROOT / "gear_optimizer" / "solver" / "taichi_gem" / "api" / "parallel_solvers.py"
    ).read_text(encoding="utf-8")
    api_init = (_REPO_ROOT / "gear_optimizer" / "solver" / "taichi_gem" / "api" / "__init__.py").read_text(
        encoding="utf-8"
    )

    assert "def solve_genomes_with_ftff(" not in parallel_solvers
    assert '"solve_genomes_with_ftff"' not in api_init


def _is_disallowed_taichi_gem_import(module: str) -> bool:
    # The public GPU API surface is the `taichi_gem.api` package (INCLUDING its
    # submodules, e.g. `taichi_gem.api.timeline`), plus `taichi_gem.runtime`.
    # Scoring may import from those. Everything DEEPER -- kernels, fields,
    # force_greats internals, the bare taichi_gem package -- remains forbidden.
    allowed_prefixes = (
        "gear_optimizer.solver.taichi_gem.api",
        "gear_optimizer.solver.taichi_gem.runtime",
        "taichi_gem.api",
        "taichi_gem.runtime",
    )
    for prefix in allowed_prefixes:
        if module == prefix or module.startswith(prefix + "."):
            return False
    if module == "gear_optimizer.solver.taichi_gem" or module.startswith("gear_optimizer.solver.taichi_gem."):
        return True
    if module == "taichi_gem" or module.startswith("taichi_gem."):
        return True
    return False


def test_scoring_does_not_import_taichi_gem_internals() -> None:
    scoring_root = _REPO_ROOT / "gear_optimizer" / "solver" / "scoring"
    assert scoring_root.exists(), f"Expected scoring root at {scoring_root}"

    offenders: list[str] = []
    for path in scoring_root.rglob("*.py"):
        txt = path.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(txt, filename=str(path))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if _is_disallowed_taichi_gem_import(alias.name):
                        rel = path.relative_to(_REPO_ROOT)
                        offenders.append(f"{rel}:{node.lineno} import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module is None:
                    continue
                if _is_disallowed_taichi_gem_import(node.module):
                    rel = path.relative_to(_REPO_ROOT)
                    offenders.append(f"{rel}:{node.lineno} from {node.module} import ...")

    assert not offenders, (
        "Scoring code must import GPU functionality via taichi_gem.api/gpu_executor, "
        "not taichi_gem internals:\n" + "\n".join(offenders)
    )


def _expr_contains_fallback_text(node: ast.AST) -> bool:
    fallback_tokens = ("fallback", "fall back", "falling back")
    text_parts: list[str] = []

    def _visit(expr: ast.AST) -> None:
        if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
            text_parts.append(expr.value)
            return
        if isinstance(expr, ast.JoinedStr):
            for value in expr.values:
                _visit(value)
            return
        if isinstance(expr, ast.FormattedValue):
            _visit(expr.value)
            return

    _visit(node)
    blob = " ".join(text_parts).lower()
    return any(tok in blob for tok in fallback_tokens)


def test_no_raw_runtime_fallback_prints() -> None:
    offenders: list[str] = []
    for path in _iter_python_files(
        _REPO_ROOT,
        rel_dirs=[
            "gear_optimizer",
            "general_meta",
            "tools",
        ],
    ):
        txt = path.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(txt, filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Name) or node.func.id != "print":
                continue
            if any(_expr_contains_fallback_text(arg) for arg in node.args):
                rel = path.relative_to(_REPO_ROOT)
                offenders.append(f"{rel}:{node.lineno}")

    assert not offenders, (
        "Fallback paths must go through warn_fallback instead of raw print diagnostics:\n" + "\n".join(offenders)
    )


def test_policy_offense_scan_flags_new_active_code_fallbacks() -> None:
    scanner = _load_policy_offense_scan()
    diff = """diff --git a/gear_optimizer/app.py b/gear_optimizer/app.py
--- a/gear_optimizer/app.py
+++ b/gear_optimizer/app.py
@@ -10,0 +11,2 @@
+def broken():
+    return run_fallback_path()
"""

    offenses = scanner.scan_added_lines(diff)

    assert len(offenses) == 1
    assert offenses[0].path == "gear_optimizer/app.py"
    assert offenses[0].line == 12


def test_policy_offense_scan_ignores_docs_tests_and_itself() -> None:
    scanner = _load_policy_offense_scan()
    diff = """diff --git a/docs/example.md b/docs/example.md
--- a/docs/example.md
+++ b/docs/example.md
@@ -1,0 +2 @@
+fallback is discussed in policy docs
diff --git a/tests/example_test.py b/tests/example_test.py
--- a/tests/example_test.py
+++ b/tests/example_test.py
@@ -1,0 +2 @@
+assert "fallback" in message
diff --git a/tools/dev/policy_offense_scan.py b/tools/dev/policy_offense_scan.py
--- a/tools/dev/policy_offense_scan.py
+++ b/tools/dev/policy_offense_scan.py
@@ -1,0 +2 @@
+FORBIDDEN = "fallback"
"""

    assert scanner.scan_added_lines(diff) == []
