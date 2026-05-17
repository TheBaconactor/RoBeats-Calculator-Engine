def test_ga_evolution_settings_do_not_expose_legacy_cache_hit_search_mode():
    """
    Cache-hit driven generation extension/mutation boosts were a hidden second
    GA mode. The invariant is that the parsed GA evolution policy has no field
    that can select that alternate behavior.
    """
    from dataclasses import fields

    from gear_optimizer.data.models import GAEvolutionSettings

    assert [field.name for field in fields(GAEvolutionSettings)] == [
        "memetic_elites",
        "memetic_steps",
        "memetic_top_gear",
        "memetic_top_minis",
        "multi_start",
    ]


def test_ga_kernel_decorators_attach_only_to_kernel_defs():
    """
    Deleting obsolete Taichi kernels must not leave an orphan @ti.kernel
    decorator stacked onto the next function.
    """
    from pathlib import Path

    path = Path("gear_optimizer/solver/taichi_gem/kernels/kernels_ga.py")
    lines = path.read_text(encoding="utf-8").splitlines()

    offenders = []
    for idx, line in enumerate(lines):
        if line.strip() != "@ti.kernel":
            continue
        next_nonblank = ""
        for next_line in lines[idx + 1 :]:
            if next_line.strip():
                next_nonblank = next_line.strip()
                break
        if not next_nonblank.startswith("def "):
            offenders.append((idx + 1, next_nonblank))

    assert offenders == []
