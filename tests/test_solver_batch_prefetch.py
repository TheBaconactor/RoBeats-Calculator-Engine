from __future__ import annotations

from gear_optimizer.solver.solver_common import prefetch_one


def test_prefetch_one_preserves_order() -> None:
    assert list(prefetch_one(range(5), enabled=True)) == [0, 1, 2, 3, 4]


def test_prefetch_one_disabled_is_transparent() -> None:
    seen: list[int] = []

    def gen():
        for value in range(3):
            seen.append(value)
            yield value

    assert list(prefetch_one(gen(), enabled=False)) == [0, 1, 2]
    assert seen == [0, 1, 2]


def test_prefetch_one_propagates_generator_exceptions() -> None:
    def gen():
        yield 1
        raise RuntimeError("boom")

    it = prefetch_one(gen(), enabled=True)
    assert next(it) == 1
    try:
        next(it)
    except RuntimeError as exc:
        assert str(exc) == "boom"
    else:  # pragma: no cover
        raise AssertionError("expected RuntimeError")
