from __future__ import annotations

from pathlib import Path
from typing import Iterable


def install_from_ga_source(module_globals: dict[str, object], ga_filename: str, replacements: Iterable[tuple[str, str]]) -> None:
    ga_path = Path(__file__).parents[1] / "ga_eval" / ga_filename
    source = ga_path.read_text(encoding="utf-8")
    source = source.replace("GA_FG", "SKYLINE_FG")
    source = source.replace("GPU_GA", "GPU_SKYLINE")
    source = source.replace("MAX_GA_RUNS", "MAX_SKYLINE_RUNS")
    source = source.replace("MAX_GA_RUN_GENOMES", "MAX_SKYLINE_RUN_GENOMES")
    source = source.replace("ga_", "skyline_")
    source = source.replace("GA ", "skyline ")
    source = source.replace("GA-", "skyline-")
    source = source.replace("GA.", "skyline.")
    source = source.replace("GA:", "skyline:")
    source = source.replace("GA`", "skyline`")
    for old, new in replacements:
        source = source.replace(old, new)
    exec(compile(source, str(ga_path), "exec", dont_inherit=True), module_globals)
