from __future__ import annotations

from .export import export_inventory_meta_json


def run_inventory_meta_coverage(*args, **kwargs):
    # Lazy import to avoid importing Taichi/GPU modules at `inventory_optimizer` import time.
    from .coverage import run_inventory_meta_coverage as _run_inventory_meta_coverage

    return _run_inventory_meta_coverage(*args, **kwargs)


__all__ = ["export_inventory_meta_json", "run_inventory_meta_coverage"]
