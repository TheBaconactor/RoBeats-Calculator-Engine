from __future__ import annotations


def verify_and_repair_stats(*args, **kwargs):
    _ = args, kwargs
    raise RuntimeError("Stats verifier was removed from the optimizer main path")


def print_verification_warning(stats_dict: dict[str, int]) -> None:
    _ = stats_dict
