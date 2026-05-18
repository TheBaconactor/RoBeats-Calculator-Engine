from __future__ import annotations

import json
import logging
import os
import time

logger = logging.getLogger(__name__)


class PostCpuProfiler:
    def __init__(self, *, enabled: bool, out_path: str | None) -> None:
        self.enabled = bool(enabled)
        out_path = str(out_path or "").strip()
        self.out_path = out_path or None
        self._t0_wall = time.perf_counter()
        self._t0_cpu = time.process_time()
        self._stages: dict[str, dict[str, float | int]] = {}

    def record(self, stage: str, cpu_s: float) -> None:
        if not self.enabled:
            return
        try:
            cpu_s = float(cpu_s)
        except Exception as e:
            logger.warning(f"post_processor:record: {e}")
            return
        if cpu_s <= 0.0:
            return
        entry = self._stages.get(stage)
        if entry is None:
            entry = {"count": 0, "cpu_total_s": 0.0, "cpu_max_s": 0.0}
            self._stages[stage] = entry
        entry["count"] = int(entry.get("count", 0) or 0) + 1
        entry["cpu_total_s"] = float(entry.get("cpu_total_s", 0.0) or 0.0) + cpu_s
        entry["cpu_max_s"] = max(float(entry.get("cpu_max_s", 0.0) or 0.0), cpu_s)

    def emit(self) -> None:
        if not self.enabled:
            return
        total_cpu = max(0.0, time.process_time() - float(self._t0_cpu))
        total_wall = max(0.0, time.perf_counter() - float(self._t0_wall))
        ranked = sorted(self._stages.items(), key=lambda kv: float(kv[1].get("cpu_total_s", 0.0) or 0.0), reverse=True)
        print(f"[POST][CpuProfile] total_cpu_s={total_cpu:.3f} total_wall_s={total_wall:.3f}")
        for name, info in ranked[:10]:
            print(
                "[POST][CpuProfile] {:<22} cpu_total={:>8.3f}s max={:>6.3f}s n={}".format(
                    name,
                    float(info.get("cpu_total_s", 0.0) or 0.0),
                    float(info.get("cpu_max_s", 0.0) or 0.0),
                    int(info.get("count", 0) or 0),
                )
            )
        if self.out_path:
            try:
                os.makedirs(os.path.dirname(self.out_path), exist_ok=True)
            except Exception as e:
                logger.warning(f"post_processor:emit: {e}")
            try:
                payload = {"total_cpu_s": total_cpu, "total_wall_s": total_wall, "stages": self._stages}
                with open(self.out_path, "w", encoding="utf-8") as fh:
                    json.dump(payload, fh, indent=2, sort_keys=True)
            except Exception as e:
                logger.warning(f"post_processor:emit: {e}")
