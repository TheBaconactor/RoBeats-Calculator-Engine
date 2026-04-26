"""Repeat the FG implicit-config benchmark for external GPU-util sampling."""

from __future__ import annotations

import argparse
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tools.bench.bench_fg_implicit_configs import main as bench_main


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=20)
    args = parser.parse_args()

    repeats = max(1, int(args.repeats))
    for _ in range(repeats):
        rc = int(bench_main())
        if rc != 0:
            return rc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
