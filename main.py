#!/usr/bin/env python3

import sys

from gear_optimizer.cli import run
from gear_optimizer.core.cpu_affinity import pin_to_performance_cores


if __name__ == "__main__":
    # On a hybrid Intel CPU, force the fast P-cores before the worker pool spawns (workers inherit
    # affinity). Without this, Windows EcoQoS parks the cold FG build on the slow E-cores. No-op
    # off Windows / non-hybrid.
    pin_to_performance_cores()
    sys.exit(run())
