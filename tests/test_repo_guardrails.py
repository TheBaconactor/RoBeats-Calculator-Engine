"""
Repo guardrails.

These tests exist to prevent removed GPU paths from quietly reappearing and to keep
production scoring code importing through the intended public GPU modules.

Rationale:
- Removed GPU APIs (old batch gem solver) were expensive (host transfers + VRAM) and
  easy to accidentally re-wire back into production.
- The CPU layers (frontiers, traces, scoring, the store) work without Taichi: only the GA's GPU path loads it.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote


_REPO_ROOT = Path(__file__).resolve().parents[1]
_GITHUB_MATH_TEXT_UNDERSCORE = re.compile(r"\\text\{[^}]*_[^}]*\}")
_SENSITIVE_PLAYER_EXPORT_KEY = re.compile(
    r'"(?:localPlayerId|playerId|playerName)"\s*:'
)
_MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
_REPOSITORY_PATH_LITERAL = re.compile(
    r"`((?:gear_optimizer|general_meta|tools|scripts|tests|docs)/[^`\s]+)`"
)
_MAINTAINED_DOCS = (
    "README.md",
    "Data/README.md",
    ".github/CONTRIBUTING.md",
    ".github/GOVERNANCE.md",
    ".github/SECURITY.md",
    ".github/SUPPORT.md",
    ".github/PULL_REQUEST_TEMPLATE.md",
    "docs/README.md",
    "docs/ARCHITECTURE.md",
    "docs/DATABASE_SCHEMA.md",
    "docs/ENGINEERING_PRINCIPLES.md",
    "docs/MAINTENANCE_PLAYBOOK.md",
    "docs/NAVIGATION.md",
    "docs/math/FEVER_TIMELINE_MATH.md",
    "docs/math/FORMULA_REFERENCE.md",
    "docs/math/ON_DEMAND_TEAM_BUFF_TIER_SCORING.md",
    "docs/math/TIMING_ENVELOPE_EXACT_FRONTIER.md",
    "tools/verify/reference_oracle/README.md",
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


def _github_heading_slug(heading: str) -> str:
    text = re.sub(r"<[^>]+>", "", heading)
    text = re.sub(r"[`*_~]", "", text).strip().lower()
    text = re.sub(r"[^a-z0-9 _-]", "", text)
    return re.sub(r"\s+", "-", text)


def _heading_slugs(path: Path) -> set[str]:
    slugs: set[str] = set()
    counts: dict[str, int] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", line)
        if not match:
            continue
        base = _github_heading_slug(match.group(1))
        occurrence = counts.get(base, 0)
        counts[base] = occurrence + 1
        slugs.add(base if occurrence == 0 else f"{base}-{occurrence}")
    return slugs


def test_repository_document_links_resolve() -> None:
    offenders: list[str] = []
    for relative_path in _MAINTAINED_DOCS:
        assert (_REPO_ROOT / relative_path).is_file(), (
            f"Maintained document is missing: {relative_path}"
        )

    for source in sorted(_REPO_ROOT.rglob("*.md")):
        if any(
            part in {".git", ".venv", "bin", "node_modules", "venv"}
            for part in source.parts
        ):
            continue
        relative_path = str(source.relative_to(_REPO_ROOT))
        text = source.read_text(encoding="utf-8")
        for match in _MARKDOWN_LINK.finditer(text):
            raw_target = match.group(1).strip().strip("<>")
            if not raw_target or raw_target.startswith(
                ("#", "http://", "https://", "mailto:")
            ):
                continue
            target_text, _, fragment = raw_target.partition("#")
            target = (source.parent / unquote(target_text)).resolve()
            try:
                target.relative_to(_REPO_ROOT)
            except ValueError:
                offenders.append(f"{relative_path}: link escapes repository: {raw_target}")
                continue
            if not target.exists():
                offenders.append(f"{relative_path}: missing target: {raw_target}")
                continue
            if fragment and target.is_file() and target.suffix.lower() == ".md":
                decoded_fragment = unquote(fragment).lower()
                if decoded_fragment not in _heading_slugs(target):
                    offenders.append(
                        f"{relative_path}: missing heading #{fragment} in "
                        f"{target.relative_to(_REPO_ROOT)}"
                    )

    assert not offenders, "Repository documentation has broken links:\n" + "\n".join(
        offenders
    )


def test_maintained_document_code_paths_resolve() -> None:
    offenders: list[str] = []
    for relative_path in _MAINTAINED_DOCS:
        text = (_REPO_ROOT / relative_path).read_text(encoding="utf-8")
        for match in _REPOSITORY_PATH_LITERAL.finditer(text):
            raw_target = match.group(1)
            target_text = raw_target.split("::", 1)[0].rstrip(".,;:)")
            if any(char in target_text for char in "*{}<>"):
                continue
            if not (_REPO_ROOT / target_text).exists():
                offenders.append(f"{relative_path}: missing code path: {raw_target}")

    assert not offenders, "Maintained documentation has stale code paths:\n" + "\n".join(
        offenders
    )


def test_maintained_documentation_does_not_reference_retired_surfaces() -> None:
    retired = (
        "gear_optimizer/solver/genetic.py",
        "gear_optimizer/data/database.py",
        "gear_optimizer.data.db_manager",
        "EvolutionDbManager",
        "native_inflight_stages.py",
        "gpu_profiler.py",
        "force_greats/bellman_fixed.py",
        "bench_gpu_native_ga_eval.py",
        "METAFINDER_EVOLUTION_DB",
        "FEVER_FIX_PLAN.md",
        "implementation records",
    )
    offenders: list[str] = []
    for relative_path in _MAINTAINED_DOCS:
        text = (_REPO_ROOT / relative_path).read_text(
            encoding="utf-8",
            errors="ignore",
        )
        hits = [token for token in retired if token in text]
        if hits:
            offenders.append(f"{relative_path}: {', '.join(hits)}")

    assert not offenders, (
        "Maintained documentation references retired code or policy surfaces:\n"
        + "\n".join(offenders)
    )


def test_the_section_kernels_name_the_producer_kernels_they_compile_in() -> None:
    """Numba's cache does not follow calls into another file: an edit to the producer has to change section_kernels.py,
    or the cached section kernels keep running the old producer code."""
    from gear_optimizer.trace import section_kernels

    source = (_REPO_ROOT / "gear_optimizer" / "frontier" / "producer_kernels.py").read_bytes().replace(b"\r\n", b"\n")
    assert section_kernels._PRODUCER_KERNELS_SHA256 == hashlib.sha256(source).hexdigest()


def test_the_cpu_layers_never_load_taichi() -> None:
    imports = "import gear_optimizer.trace.note_graph, gear_optimizer.frontier.timeline_cache, gear_optimizer.store.legacy"
    tiers = "import gear_optimizer.solver.team_buff_tiers, gear_optimizer.solver.scoring.exact_rescore"
    code = f"{imports}; {tiers}; import sys; assert 'taichi' not in sys.modules"
    subprocess.run([sys.executable, "-c", code], cwd=_REPO_ROOT, check=True)
