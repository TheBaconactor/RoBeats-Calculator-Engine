"""S1: the engine's modules import one way. Function-level imports count: they only defer a cycle to call time.

Each remaining cycle is listed with the stage that removes it; a new cycle, or a listed one that grew, fails.
"""

from __future__ import annotations

import ast
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

KNOWN_CYCLES = {
    # R5 (FG frontier builder + scoring): these modules are FG cache fingerprint sources.
    frozenset({
        "gear_optimizer.solver.taichi_gem.force_greats.response_cache",
        "gear_optimizer.solver.taichi_gem.force_greats.response_cache_keys",
        "gear_optimizer.solver.taichi_gem.force_greats.response_cache_serde",
        "gear_optimizer.solver.taichi_gem.force_greats.response_cache_store",
    }),
    # R1e deletes the in-flight pipeline.
    frozenset({
        "gear_optimizer.solver.native_inflight_lifecycle",
        "gear_optimizer.solver.native_inflight_lifecycle_prepare",
        "gear_optimizer.solver.native_inflight_pipeline",
        "gear_optimizer.solver.native_inflight_pipeline_fg",
    }),
    frozenset({
        "gear_optimizer.solver.native_inflight_config",
        "gear_optimizer.solver.native_inflight_scheduler_policy",
    }),
}


def _modules() -> dict[str, Path]:
    found = {}
    for path in (ROOT / "gear_optimizer").rglob("*.py"):
        parts = list(path.relative_to(ROOT).with_suffix("").parts)
        if parts[-1] == "__init__":
            parts.pop()
        found[".".join(parts)] = path
    return found


def _imports(modules: dict[str, Path]) -> dict[str, set[str]]:
    def resolve(name: str) -> str | None:
        while name and name not in modules:
            name = name.rpartition(".")[0]
        return name or None

    def statements(node: ast.AST):
        """Every node under `node` except typing-only imports (`if TYPE_CHECKING:` bodies)."""
        for child in ast.iter_child_nodes(node):
            test = getattr(child, "test", None) if isinstance(child, ast.If) else None
            if getattr(test, "id", getattr(test, "attr", None)) == "TYPE_CHECKING":
                yield from (n for orelse in child.orelse for n in [orelse, *statements(orelse)])
                continue
            yield child
            yield from statements(child)

    graph: dict[str, set[str]] = defaultdict(set)
    for module, path in modules.items():
        package = module if path.name == "__init__.py" else module.rpartition(".")[0]
        for node in statements(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                targets = [a.name for a in node.names if a.name.startswith("gear_optimizer")]
            elif isinstance(node, ast.ImportFrom) and (node.level or (node.module or "").startswith("gear_optimizer")):
                base = node.module or ""
                if node.level:
                    parts = package.split(".")
                    parts = parts[: len(parts) - (node.level - 1)]
                    base = ".".join(parts + ([node.module] if node.module else []))
                targets = [f"{base}.{a.name}" if f"{base}.{a.name}" in modules else base for a in node.names]
            else:
                continue
            graph[module].update(t for t in map(resolve, targets) if t and t != module)
    return graph


def _cycles(graph: dict[str, set[str]], nodes) -> list[frozenset[str]]:
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    found: list[frozenset[str]] = []
    sys.setrecursionlimit(max(10_000, sys.getrecursionlimit()))

    def visit(v: str) -> None:
        index[v] = low[v] = len(index)
        stack.append(v)
        on_stack.add(v)
        for w in graph.get(v, ()):
            if w not in index:
                visit(w)
                low[v] = min(low[v], low[w])
            elif w in on_stack:
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            component = set()
            while True:
                w = stack.pop()
                on_stack.discard(w)
                component.add(w)
                if w == v:
                    break
            if len(component) > 1:
                found.append(frozenset(component))

    for v in nodes:
        if v not in index:
            visit(v)
    return found


def test_the_engine_has_no_import_cycles_beyond_the_listed_ones():
    modules = _modules()
    cycles = set(_cycles(_imports(modules), modules))
    assert cycles - KNOWN_CYCLES == set(), "new or grown import cycles"
    assert KNOWN_CYCLES - cycles == set(), "a listed cycle is gone: remove it from KNOWN_CYCLES"
