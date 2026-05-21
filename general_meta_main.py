#!/usr/bin/env python3

from __future__ import annotations

import sys

from gear_optimizer.cli import meta as _cli_meta


def main() -> int:
    return _cli_meta()


if __name__ == "__main__":
    sys.exit(main())
