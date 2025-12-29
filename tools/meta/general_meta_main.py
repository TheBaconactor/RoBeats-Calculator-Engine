#!/usr/bin/env python3
"""
GeneralMeta wrapper.

This file exists for backwards compatibility after moving the entry point to the
repo root.

Usage:
    python tools/meta/general_meta_main.py
"""

from __future__ import annotations

import runpy
from pathlib import Path


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    runpy.run_path(str(repo_root / "general_meta_main.py"), run_name="__main__")


if __name__ == "__main__":
    main()
