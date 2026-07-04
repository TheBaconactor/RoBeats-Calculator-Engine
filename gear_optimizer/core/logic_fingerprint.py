"""Content-addressed fingerprint of a module's *logic*, for folding into disk-cache keys.

WHY
---
Several disk caches (the base timeline-frontier grid, the FG response-frontier bundles) key on the
raw song INPUTS plus a hand-typed version string. The version string is the ONLY thing that
represents the producing CODE: if the DP logic changes but nobody bumps the string, stale payloads
built by the old logic keep validating against the new code -- a silent correctness bug. That is
exactly what shipped the Bopeebo base under-report (a floor-aware DP change with no version bump left
v7 nominal grids in service). See ``timeline._FRONTIER_DISK_CACHE_VERSION`` /
``response_cache_types._FG_RESPONSE_CACHE_VERSION``.

WHAT
----
``module_logic_fingerprint`` derives a short, stable digest from the *compiled shape* of a set of
source modules -- their statements, literals, names and structure -- via ``ast`` (parse -> strip
docstrings -> ``ast.dump`` without positions -> hash). It is therefore:

  * INSENSITIVE to comments, whitespace, blank lines and docstrings (so a docs-only edit does NOT
    trigger an expensive cold rebuild), and
  * SENSITIVE to any real logic change: a changed operator, literal constant, branch, or name.

Folded into a cache version as ``f"{base_version}+logic-{fp}"``, it makes the common failure mode
(edit the DP body, forget to bump) auto-invalidate stale payloads. The hand-typed base version is
KEPT as a human backstop for changes the fingerprint cannot see (e.g. a dependency's behavior, a
changed constant imported from elsewhere) and to document the semantic history. Over-invalidation is
safe (you just rebuild); under-invalidation is the bug this removes.

Note: this fingerprints the listed modules only. Adding a NEW module that co-determines a cache's
output means adding it to that cache's source list -- but the coarse module list is far more stable
than the per-change version bump it hardens, and the base version remains the backstop.
"""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path
from typing import Iterable

_DOC_HOLDERS = (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


def _strip_docstrings(tree: ast.AST) -> None:
    """Drop the leading string-literal docstring from every module/function/class in-place, so a
    docstring edit does not change the fingerprint (comments never reach the AST at all)."""
    for node in ast.walk(tree):
        if not isinstance(node, _DOC_HOLDERS):
            continue
        body = getattr(node, "body", None)
        if not body:
            continue
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(getattr(first, "value", None), ast.Constant)
            and isinstance(first.value.value, str)
        ):
            node.body = body[1:] or [ast.Pass()]  # keep the body syntactically non-empty


_fingerprint_cache: dict[tuple[str, ...], str] = {}


def module_logic_fingerprint(source_files: Iterable[str | Path], *, length: int = 12) -> str:
    """Stable short hex digest of the logic of ``source_files`` (order-independent, docstring/
    comment/whitespace-insensitive). Fails loudly if a path is missing or unparseable -- these are
    imported production modules, so a bad path is a wiring error, not a soft-miss."""
    paths = tuple(sorted(str(Path(p).resolve()) for p in source_files))
    if not paths:
        raise ValueError("module_logic_fingerprint requires at least one source file")
    cached = _fingerprint_cache.get(paths)
    if cached is not None:
        return cached
    hasher = hashlib.blake2b(digest_size=max(4, (int(length) + 1) // 2))
    for path in paths:
        p = Path(path)
        if not p.is_file():
            raise FileNotFoundError(f"logic-fingerprint source module not found: {p}")
        source = p.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(p))
        _strip_docstrings(tree)
        # ast.dump without include_attributes omits line/column positions, so pure reformatting
        # (line breaks, indentation) does not move the digest -- only semantic structure does.
        hasher.update(ast.dump(tree).encode("utf-8"))
        hasher.update(b"\x1e")
    fp = hasher.hexdigest()[: int(length)]
    _fingerprint_cache[paths] = fp
    return fp
