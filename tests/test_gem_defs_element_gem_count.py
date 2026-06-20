from __future__ import annotations

from gear_optimizer.core.gem_defs import GemKey, build_gem_counts, element_gem_count


def test_element_gem_count_reads_canonical_key():
    assert element_gem_count(build_gem_counts(1, 2, 3, 7)) == 7
    assert element_gem_count({GemKey.ELEMENT.value: 4}) == 4


def test_element_gem_count_defaults_and_guards():
    assert element_gem_count({}) == 0
    assert element_gem_count(None) == 0
    # A gem dict without the Element key reads 0, not a KeyError.
    assert element_gem_count({"Perfect Points": 5}) == 0


def test_element_gem_count_ignores_legacy_aliases_internally():
    # Issue #56 Category A: the canonical INTERNAL reader does not tolerate legacy
    # spellings. Aliases ("Overflow"/"OV"/"Element Overflow"/...) must be normalized to
    # GemKey.ELEMENT.value at the explicit external DB-decode boundary, never here.
    assert element_gem_count({"Overflow": 9}) == 0
    assert element_gem_count({"OV": 9}) == 0
    assert element_gem_count({"Element Overflow": 9}) == 0
