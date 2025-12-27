"""
Lightweight Result type for operations that can fail.

This is intentionally small (no external dependencies) and safe to use in hot paths.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Optional, TypeVar, Union, cast

T = TypeVar("T")
E = TypeVar("E", bound=BaseException)


@dataclass(frozen=True)
class Ok(Generic[T]):
    value: T


@dataclass(frozen=True)
class Err(Generic[E]):
    error: E


Result = Union[Ok[T], Err[E]]


def is_ok(result: Result[T, E]) -> bool:
    return isinstance(result, Ok)


def is_err(result: Result[T, E]) -> bool:
    return isinstance(result, Err)


def unwrap(result: Result[T, E]) -> T:
    if isinstance(result, Ok):
        return result.value
    raise cast(Err[E], result).error


def unwrap_err(result: Result[T, E]) -> E:
    if isinstance(result, Err):
        return result.error
    raise RuntimeError("Expected Err, got Ok")


def ok_or_none(result: Result[T, E]) -> Optional[T]:
    if isinstance(result, Ok):
        return result.value
    return None

