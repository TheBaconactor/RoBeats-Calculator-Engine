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
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[1]


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
