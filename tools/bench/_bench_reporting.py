from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterable

BENCH_JSON_PREFIX = "BENCH_JSON:"


def snapshot_env(keys: Iterable[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key in keys:
        value = os.environ.get(str(key), None)
        if value is None:
            continue
        out[str(key)] = str(value)
    return out


def emit_bench_result(
    result: dict[str, Any],
    *,
    json_stdout: bool = False,
    json_out: str | None = None,
) -> None:
    if json_out:
        out_path = Path(str(json_out))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if json_stdout:
        print(f"{BENCH_JSON_PREFIX}{json.dumps(result, sort_keys=True)}")
