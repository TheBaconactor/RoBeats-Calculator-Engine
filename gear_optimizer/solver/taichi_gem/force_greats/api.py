"""Minimal ForceGreats API stubs for response-frontier production FG."""
from __future__ import annotations

from . import fields


def reset_force_greats_api_state() -> None:
    fields.reset_fields_state()
