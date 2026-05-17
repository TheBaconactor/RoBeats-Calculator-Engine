"""
Repo guardrails.

These tests exist to prevent removed GPU paths from quietly reappearing and to keep
production scoring code importing through the intended public GPU modules.

Rationale:
- Removed GPU APIs (old batch gem solver) were expensive (host transfers + VRAM) and
  easy to accidentally re-wire back into production.
- Scoring orchestration should not import `taichi_gem` internals directly; it should
  go through `gear_optimizer.solver.taichi_gem.api`, `gear_optimizer.solver.taichi_gem.force_greats.api`,
  and/or the GPU executor.
"""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[1]


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


def _is_disallowed_taichi_gem_import(module: str) -> bool:
    allowed = {
        "gear_optimizer.solver.taichi_gem.api",
        "gear_optimizer.solver.taichi_gem.force_greats.api",
        "gear_optimizer.solver.taichi_gem.runtime",
        "taichi_gem.api",
        "taichi_gem.force_greats.api",
        "taichi_gem.runtime",
    }
    if module in allowed:
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
        "Scoring code must import GPU functionality via taichi_gem.api/force_greats.api/gpu_executor, "
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


def test_harness_engineering_route_stays_discoverable() -> None:
    required_routes = {
        "AGENTS.md": [
            "docs/ENGINEERING_PRINCIPLES.md",
            "docs/CODEX_WORKLOG.md",
        ],
        "docs/README.md": [
            "HARNESS_ENGINEERING.md",
            "ENGINEERING_PRINCIPLES.md",
        ],
        "docs/ENGINEERING_PRINCIPLES.md": [
            "docs/HARNESS_ENGINEERING.md",
            "repository knowledge as the system of record",
        ],
        "docs/Implementation Records/README.md": [
            "AGENT_HARNESS_ENGINEERING_PRACTICES.md",
        ],
    }

    missing: list[str] = []
    for rel_path, needles in required_routes.items():
        text = (_REPO_ROOT / rel_path).read_text(encoding="utf-8")
        for needle in needles:
            if needle not in text:
                missing.append(f"{rel_path}: missing {needle!r}")

    assert not missing, (
        "Harness engineering guidance must remain reachable from the repo routing docs:\n" + "\n".join(missing)
    )


def test_package_agents_stay_thin_and_route_to_navigation() -> None:
    text = (_REPO_ROOT / "gear_optimizer" / "AGENTS.md").read_text(encoding="utf-8")

    required = [
        "docs/NAVIGATION.md",
        "docs/ENGINEERING_PRINCIPLES.md",
    ]
    forbidden = [
        "## Package navigation",
        "## Feature map",
        "| Area |",
        "| Feature |",
    ]

    missing = [needle for needle in required if needle not in text]
    blocked = [needle for needle in forbidden if needle in text]

    assert not missing, "gear_optimizer/AGENTS.md must point to the canonical navigation docs:\n" + "\n".join(missing)
    assert not blocked, "gear_optimizer/AGENTS.md must not duplicate navigation tables:\n" + "\n".join(blocked)


def test_agents_files_stay_concise() -> None:
    root_limit = 3200
    nested_limit = 1400
    offenders: list[str] = []

    for path in _REPO_ROOT.rglob("AGENTS.md"):
        if any(part in {".git", ".venv", "venv", "__pycache__"} for part in path.parts):
            continue
        limit = root_limit if path == _REPO_ROOT / "AGENTS.md" else nested_limit
        size = len(path.read_text(encoding="utf-8"))
        if size > limit:
            rel = path.relative_to(_REPO_ROOT)
            offenders.append(f"{rel}: {size} bytes > {limit}")

    assert not offenders, "AGENTS.md files must stay concise routers:\n" + "\n".join(offenders)


def test_removed_user_skills_are_not_routed_from_repo_docs() -> None:
    removed_skill_refs = [
        "$repo-bootstrap",
        "repo-bootstrap",
        "dead-code-finder",
        "docs-sync",
        "jupyter-notebook",
        "agents-md",
    ]
    checked_roots = [
        _REPO_ROOT / "AGENTS.md",
        _REPO_ROOT / "docs" / "AGENTS.md",
        _REPO_ROOT / "docs" / "HARNESS_ENGINEERING.md",
        _REPO_ROOT / "docs" / "ENGINEERING_PRINCIPLES.md",
        _REPO_ROOT / "docs" / "Implementation Records" / "CONTEXT_ROTTING_CONTROL.md",
    ]

    offenders: list[str] = []
    for path in checked_roots:
        text = path.read_text(encoding="utf-8")
        hits = [needle for needle in removed_skill_refs if needle in text]
        if hits:
            rel = path.relative_to(_REPO_ROOT)
            offenders.append(f"{rel}: {', '.join(hits)}")

    assert not offenders, "Repo routing docs must not point at removed user skills:\n" + "\n".join(offenders)


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
