#!/usr/bin/env python3

import sys

from gear_optimizer.cli import inventory


if __name__ == "__main__":
    sys.exit(inventory(sys.argv[1:]))
