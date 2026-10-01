"""The GA's device evaluation memo (fields.ga_eval_cache_*): its entries hold for one evaluation context (budget,
gem caps, colors, song slot) over the current inputs. Every upload that replaces an input (the batch, the reference
tables, a timeline slot) resets it."""

from __future__ import annotations

from .. import fields

_context: tuple | None = None


def reset_ga_evaluation_cache() -> None:
    """Discard results when a batch, reference table, or timeline is replaced."""
    global _context
    _context = None
    if fields.ga_eval_cache_key is not None:
        fields.ga_eval_cache_key.fill(0)


def use_ga_evaluation_context(context: tuple) -> None:
    """Keep the memo for `context`; any other context resets it."""
    global _context
    if context != _context:
        reset_ga_evaluation_cache()
        _context = context
