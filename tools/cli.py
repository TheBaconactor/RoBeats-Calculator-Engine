from __future__ import annotations

import argparse
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence


@dataclass(frozen=True)
class ScriptEntry:
    source: str
    category: str
    name: str
    relative_path: str
    tool_id: str
    qualified_id: str
    private: bool


EXCLUDED_TOOL_FILES = {"__init__.py", "__main__.py", "cli.py"}
EXCLUDED_PARTS = {"__pycache__"}


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _is_private(parts: Sequence[str], script_name: str) -> bool:
    lowered = script_name.lower()
    parent_parts = parts[:-1]
    if script_name.startswith("_"):
        return True
    if lowered.startswith("test_"):
        return True
    if "tmp" in lowered:
        return True
    if any(part.startswith("_") for part in parent_parts):
        return True
    if "tests" in parent_parts:
        return True
    return False


def discover_scripts(
    root: Path,
    *,
    sources: Iterable[str] = ("tools", "scripts"),
    include_private: bool = True,
) -> List[ScriptEntry]:
    entries: List[ScriptEntry] = []
    for source in sources:
        base_dir = root / source
        if not base_dir.exists():
            continue

        for script_path in sorted(base_dir.rglob("*.py")):
            rel_from_source = script_path.relative_to(base_dir)
            parts = rel_from_source.parts
            if any(part in EXCLUDED_PARTS for part in parts):
                continue
            if source == "tools" and script_path.name in EXCLUDED_TOOL_FILES:
                continue

            name = script_path.stem
            category = "/".join(parts[:-1]) if len(parts) > 1 else "(root)"
            tool_id = f"{category}/{name}" if category != "(root)" else name
            qualified_id = f"{source}:{tool_id}"
            private = _is_private(parts, script_path.name)
            if private and not include_private:
                continue

            entries.append(
                ScriptEntry(
                    source=source,
                    category=category,
                    name=name,
                    relative_path=str(script_path.relative_to(root)).replace("\\", "/"),
                    tool_id=tool_id,
                    qualified_id=qualified_id,
                    private=private,
                )
            )
    return entries


def _print_grouped(entries: Sequence[ScriptEntry], show_paths: bool) -> None:
    grouped: dict[tuple[str, str], List[ScriptEntry]] = defaultdict(list)
    for entry in entries:
        grouped[(entry.source, entry.category)].append(entry)

    for group_key in sorted(grouped):
        source, category = group_key
        print(f"[{source}] {category}")
        for entry in sorted(grouped[group_key], key=lambda item: item.name):
            marker = " (private)" if entry.private else ""
            if show_paths:
                print(f"  {entry.qualified_id}{marker} -> {entry.relative_path}")
            else:
                print(f"  {entry.qualified_id}{marker}")


def _cmd_list(args: argparse.Namespace) -> int:
    source_filter = ("tools", "scripts") if args.source == "all" else (args.source,)
    entries = discover_scripts(repo_root(), sources=source_filter, include_private=args.all)

    if not entries:
        print("No scripts matched the provided filters.")
        return 0

    visible_count = len(entries)
    _print_grouped(entries, show_paths=args.paths)
    print(f"\nTotal scripts listed: {visible_count}")
    return 0


def _print_counts(title: str, counter: Counter[str]) -> None:
    print(title)
    for key, value in sorted(counter.items()):
        print(f"  {key}: {value}")


def _cmd_audit(args: argparse.Namespace) -> int:
    entries = discover_scripts(repo_root(), include_private=True)
    if not entries:
        print("No scripts found.")
        return 0

    total = len(entries)
    private_total = sum(1 for item in entries if item.private)
    public_total = total - private_total
    print(f"Scripts discovered: {total}")
    print(f"Public scripts: {public_total}")
    print(f"Private/scratch scripts: {private_total}")

    by_source = Counter(item.source for item in entries)
    _print_counts("\nBy source:", by_source)

    by_category = Counter(f"{item.source}:{item.category}" for item in entries)
    _print_counts("\nBy category:", by_category)

    private_by_category = Counter(f"{item.source}:{item.category}" for item in entries if item.private)
    if private_by_category:
        _print_counts("\nPrivate/scratch by category:", private_by_category)

    ambiguous_names = defaultdict(list)
    for item in entries:
        ambiguous_names[item.name].append(item.qualified_id)
    conflicts = {name: targets for name, targets in ambiguous_names.items() if len(targets) > 1}
    if conflicts:
        print("\nAmbiguous short names (use qualified id):")
        for name in sorted(conflicts):
            joined = ", ".join(sorted(conflicts[name]))
            print(f"  {name}: {joined}")
    else:
        print("\nNo ambiguous short names detected.")

    if args.show_private:
        private_entries = sorted(
            (item for item in entries if item.private),
            key=lambda item: (item.source, item.category, item.name),
        )
        if private_entries:
            print("\nPrivate/scratch scripts:")
            for item in private_entries:
                print(f"  {item.qualified_id} -> {item.relative_path}")

    return 0


def _resolve_target(entries: Sequence[ScriptEntry], target: str) -> ScriptEntry:
    exact_qualified = [item for item in entries if item.qualified_id == target]
    if len(exact_qualified) == 1:
        return exact_qualified[0]

    exact_tool = [item for item in entries if item.tool_id == target]
    if len(exact_tool) == 1:
        return exact_tool[0]
    if len(exact_tool) > 1:
        options = ", ".join(sorted(item.qualified_id for item in exact_tool))
        raise ValueError(f"Ambiguous target '{target}'. Use one of: {options}")

    exact_name = [item for item in entries if item.name == target]
    if len(exact_name) == 1:
        return exact_name[0]
    if len(exact_name) > 1:
        options = ", ".join(sorted(item.qualified_id for item in exact_name))
        raise ValueError(f"Ambiguous target '{target}'. Use one of: {options}")

    exact_rel = [item for item in entries if item.relative_path == target.replace("\\", "/")]
    if len(exact_rel) == 1:
        return exact_rel[0]

    raise ValueError(f"Script target '{target}' was not found.")


def _cmd_run(args: argparse.Namespace) -> int:
    source_filter = ("tools", "scripts") if args.source == "all" else (args.source,)
    entries = discover_scripts(repo_root(), sources=source_filter, include_private=args.private)
    try:
        entry = _resolve_target(entries, args.target)
    except ValueError as exc:
        print(str(exc))
        print("Tip: run `python -m tools list --all --paths` to discover valid targets.")
        return 2

    script_args = list(args.script_args)
    if script_args and script_args[0] == "--":
        script_args = script_args[1:]

    script_path = repo_root() / Path(entry.relative_path)
    cmd = [sys.executable, str(script_path), *script_args]
    print(f"Running: {' '.join(cmd)}", flush=True)
    completed = subprocess.run(cmd, cwd=str(repo_root()), check=False)
    return completed.returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m tools",
        description="Unified runner for maintained tools and ad-hoc scripts.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List available scripts.")
    list_parser.add_argument(
        "--source",
        choices=("all", "tools", "scripts"),
        default="all",
        help="Filter list output by source directory.",
    )
    list_parser.add_argument(
        "--all",
        action="store_true",
        help="Include private/scratch scripts (underscore, tmp, test, nested tests).",
    )
    list_parser.add_argument("--paths", action="store_true", help="Show file paths in output.")
    list_parser.set_defaults(func=_cmd_list)

    audit_parser = subparsers.add_parser("audit", help="Show script inventory and clutter hotspots.")
    audit_parser.add_argument(
        "--show-private",
        action="store_true",
        help="Print every private/scratch script path.",
    )
    audit_parser.set_defaults(func=_cmd_audit)

    run_parser = subparsers.add_parser("run", help="Run a script by id, name, or path.")
    run_parser.add_argument("target", help="Script identifier (e.g. tools:db/check_db).")
    run_parser.add_argument(
        "--source",
        choices=("all", "tools", "scripts"),
        default="all",
        help="Limit lookup to one source directory.",
    )
    run_parser.add_argument(
        "--private",
        action="store_true",
        help="Allow private/scratch targets in resolution.",
    )
    run_parser.add_argument(
        "script_args",
        nargs=argparse.REMAINDER,
        help="Arguments forwarded to the target script; use `--` before script args.",
    )
    run_parser.set_defaults(func=_cmd_run)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
