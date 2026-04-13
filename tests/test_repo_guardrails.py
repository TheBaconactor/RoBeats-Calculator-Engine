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
import json
from pathlib import Path
import subprocess


_REPO_ROOT = Path(__file__).resolve().parents[1]
_HARNESS_MANIFEST = _REPO_ROOT / "tools" / "_mcp_harness" / "coverage_manifest.json"


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


def _git_status_paths() -> list[str]:
    completed = subprocess.run(
        ["git", "-c", "core.quotepath=false", "status", "--porcelain=v1", "-z", "--untracked-files=normal"],
        cwd=_REPO_ROOT,
        capture_output=True,
        check=False,
        stdin=subprocess.DEVNULL,
    )
    if completed.returncode != 0:
        return []

    paths: list[str] = []
    parts = (completed.stdout or b"").split(b"\x00")
    index = 0
    while index < len(parts):
        chunk = parts[index]
        index += 1
        if not chunk.strip():
            continue
        text = chunk.decode("utf-8", errors="replace")
        status = text[:2]
        path = text[3:].strip()
        if "R" in status or "C" in status:
            index += 1
        paths.append(path.replace("\\", "/"))
    return paths


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
            "inventory_optimizer",
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


def test_high_value_engineering_surfaces_require_harness_touchpoints() -> None:
    manifest = json.loads(_HARNESS_MANIFEST.read_text(encoding="utf-8"))
    ignore_prefixes = tuple(manifest.get("ignore_path_prefixes") or [])
    trigger_prefixes = tuple(
        prefix
        for trigger in manifest.get("review_triggers", [])
        for prefix in trigger.get("path_prefixes", [])
    )
    harness_touchpoints = (
        ".codex/config.toml",
        "AGENTS.md",
        "docs/ENGINEERING_PRINCIPLES.md",
        "docs/MCP_HARNESS_CHARTER.md",
        "docs/Implementation Records/OPENAI_CODEX_MCP_ENGINEERING_HARNESS_V2.md",
        "tests/test_mcp_harness.py",
        "tests/test_mcp_harness_stdio.py",
        "tools/AGENTS.md",
        "tools/_mcp_harness/",
        "tools/mcp_server.py",
    )

    changed_paths = [
        path
        for path in _git_status_paths()
        if not any(path.startswith(prefix) for prefix in ignore_prefixes)
    ]
    triggered = [
        path
        for path in changed_paths
        if any(path.startswith(prefix) for prefix in trigger_prefixes)
    ]

    if not triggered:
        return

    assert any(
        path.startswith(prefix) for path in changed_paths for prefix in harness_touchpoints
    ), (
        "High-value engineering surfaces changed without any MCP harness maintenance touchpoint.\n"
        "Update the harness/docs/tests so the new workflow stays answerable in 1-2 MCP calls.\n"
        f"Triggered paths: {triggered}"
    )


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
            "inventory_optimizer",
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
