"""tools/verify/gate.py: a silent compare would pass every change, so its verdicts are tested on records it reads."""

from __future__ import annotations

import json

import numpy as np
import pytest

from tools.verify import gate


def _record(root, label, outputs, *, instructions=100.0, versions=("timeline-1", "fg-1")):
    run = root / "runs" / label
    run.mkdir(parents=True)
    stages = ("prepare", "ga", "fg", "finish", "store")
    (run / "record.json").write_text(json.dumps({
        "commit": label,
        "cache_versions": list(versions),
        "cli_s": 1.0,
        "peak_mb": 1.0,
        "costs": {stage: [1.0, 1.0, instructions] for stage in stages},
        "outputs": outputs,
    }))


def test_identical_outputs_pass(tmp_path, capsys):
    _record(tmp_path, "base", {"rows/a": "1"})
    _record(tmp_path, "new", {"rows/a": "1"})

    assert gate.compare("base", "new", tmp_path) == 0
    assert "outputs IDENTICAL: 1" in capsys.readouterr().out


@pytest.mark.parametrize("outputs", [{"rows/a": "2"}, {}, {"rows/a": "1", "rows/b": "3"}])
def test_a_changed_missing_or_new_output_fails_and_is_named(tmp_path, capsys, outputs):
    _record(tmp_path, "base", {"rows/a": "1"})
    _record(tmp_path, "new", outputs)

    assert gate.compare("base", "new", tmp_path) == 1
    assert "outputs DIFFER: 1 (rows 1)" in capsys.readouterr().out


def test_more_solve_instructions_than_the_noise_fails(tmp_path, capsys):
    _record(tmp_path, "base", {})
    _record(tmp_path, "noise", {}, instructions=100.4)
    _record(tmp_path, "slower", {}, instructions=101.0)

    assert gate.compare("base", "noise", tmp_path) == 0
    assert gate.compare("base", "slower", tmp_path) == 1
    assert "SLOWER" in capsys.readouterr().out


def test_rounds_must_agree_and_their_median_prices_a_label(tmp_path, capsys):
    _record(tmp_path, "base-1", {"rows/a": "1"}, instructions=100.0)
    _record(tmp_path, "base-2", {"rows/a": "2"}, instructions=300.0)
    _record(tmp_path, "new", {"rows/a": "1"}, instructions=200.0)

    assert gate.compare("base", "new", tmp_path) == 1
    out = capsys.readouterr().out
    assert "base is not deterministic" in out
    assert "(+0.00%)" in out


def test_changed_cache_versions_are_called_out_without_failing(tmp_path, capsys):
    _record(tmp_path, "base", {})
    _record(tmp_path, "new", {}, versions=("timeline-1", "fg-2"))

    assert gate.compare("base", "new", tmp_path) == 0
    assert "cache versions CHANGED" in capsys.readouterr().out


def test_digest_reads_values_not_their_order_or_container():
    assert gate.digest({"a": 1, "b": [2]}) == gate.digest({"b": [2], "a": 1})
    assert gate.digest({"a": np.arange(3)}) == gate.digest({"a": np.arange(3)})
    assert gate.digest({"a": np.arange(3)}) != gate.digest({"a": np.arange(3).astype(np.float64)})
    assert gate.digest({"a": 1}) != gate.digest({"a": 2})
