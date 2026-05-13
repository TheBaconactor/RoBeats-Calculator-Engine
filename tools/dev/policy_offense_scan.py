"""Fail the quality gate when new fallback-style production code is introduced."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import PurePosixPath


ACTIVE_PREFIXES = (
    "gear_optimizer/",
    "general_meta/",
    "inventory_optimizer/",
    "scripts/",
    "tools/",
)
ACTIVE_ROOT_FILES = {
    "main.py",
    "general_meta_main.py",
    "inventory_cli.py",
}
CODE_SUFFIXES = {
    ".py",
    ".ps1",
    ".sh",
}
EXCLUDED_PREFIXES = (
    "tests/",
    "docs/",
    "bin/",
    "Data/",
    "artifacts/",
)
EXCLUDED_PATH_PARTS = {
    "archive",
    "branch-archives",
    "__pycache__",
}
EXCLUDED_FILES = {
    "tools/dev/policy_offense_scan.py",
}


FORBIDDEN_PATTERNS = (
    re.compile(r"fallback", re.IGNORECASE),
    re.compile(r"\bfall\s+back\b", re.IGNORECASE),
    re.compile(r"\bfalling\s+back\b", re.IGNORECASE),
    re.compile(r"\bdegraded\s+mode\b", re.IGNORECASE),
    re.compile(r"\bbest[- ]effort\b", re.IGNORECASE),
    re.compile(r"\bcompatibility\s+(?:shim|branch|path)\b", re.IGNORECASE),
    re.compile(r"\bsilent(?:ly)?\s+(?:catch|ignore|recover)", re.IGNORECASE),
)


@dataclass(frozen=True)
class Offense:
    path: str
    line: int
    text: str
    pattern: str


def is_active_code_path(path: str) -> bool:
    posix = path.replace("\\", "/")
    if posix in EXCLUDED_FILES:
        return False
    if posix.startswith(EXCLUDED_PREFIXES):
        return False
    parts = set(PurePosixPath(posix).parts)
    if parts & EXCLUDED_PATH_PARTS:
        return False
    if posix in ACTIVE_ROOT_FILES:
        return True
    if not posix.endswith(tuple(CODE_SUFFIXES)):
        return False
    return posix.startswith(ACTIVE_PREFIXES)


def scan_added_lines(diff_text: str) -> list[Offense]:
    offenses: list[Offense] = []
    path: str | None = None
    new_line: int | None = None

    for raw in diff_text.splitlines():
        if raw.startswith("diff --git "):
            path = None
            new_line = None
            continue

        if raw.startswith("+++ "):
            target = raw[4:].strip()
            path = target[2:] if target.startswith("b/") else target
            if path == "/dev/null":
                path = None
            continue

        if raw.startswith("@@ "):
            match = re.search(r"\+(\d+)(?:,(\d+))?", raw)
            new_line = int(match.group(1)) if match else None
            continue

        if path is None or new_line is None:
            continue

        if raw.startswith("+") and not raw.startswith("+++"):
            text = raw[1:]
            if is_active_code_path(path):
                for pattern in FORBIDDEN_PATTERNS:
                    if pattern.search(text):
                        offenses.append(Offense(path=path, line=new_line, text=text.strip(), pattern=pattern.pattern))
                        break
            new_line += 1
            continue

        if raw.startswith("-") and not raw.startswith("---"):
            continue

        if raw.startswith(" "):
            new_line += 1

    return offenses


def _run_git_diff(args: list[str]) -> str:
    proc = subprocess.run(
        ["git", *args],
        check=False,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode not in (0, 1):
        raise RuntimeError(proc.stderr.strip() or "git diff failed")
    return proc.stdout


def read_default_diff() -> str:
    staged = _run_git_diff(["diff", "--cached", "--unified=0", "--"])
    if staged.strip():
        return staged
    return _run_git_diff(["diff", "HEAD", "--unified=0", "--"])


def read_diff(args: argparse.Namespace) -> str:
    if args.staged:
        return _run_git_diff(["diff", "--cached", "--unified=0", "--"])
    if args.worktree:
        return _run_git_diff(["diff", "HEAD", "--unified=0", "--"])
    if args.range:
        return _run_git_diff(["diff", "--unified=0", args.range, "--"])
    return read_default_diff()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--staged", action="store_true", help="scan staged changes")
    mode.add_argument("--worktree", action="store_true", help="scan changes against HEAD")
    mode.add_argument("--range", metavar="REV_RANGE", help="scan a git revision range")
    args = parser.parse_args(argv)

    offenses = scan_added_lines(read_diff(args))
    if not offenses:
        return 0

    print("Policy offense scan failed: prohibited production recovery code was added.", file=sys.stderr)
    print("Internal invariants should fail loudly; delete the recovery path and fix the owner layer.", file=sys.stderr)
    print("", file=sys.stderr)
    for offense in offenses:
        print(f"{offense.path}:{offense.line}: {offense.text}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
