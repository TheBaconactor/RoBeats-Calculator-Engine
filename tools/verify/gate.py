"""The engine's proof gate: a fixed set of official charts through every surface a player or the website sees, each
output compared with a base tree's, and the solve's stages priced side by side.

  python tools/verify/gate.py record LABEL               this tree's outputs and costs, in <root>/runs/LABEL
  python tools/verify/gate.py compare BASE LABEL         what differs, what got slower; exit 1 on either
  python tools/verify/gate.py ab BASE_TREE [--rounds N]  records alternating between BASE_TREE and this tree, then compare

Surfaces: `main.py run` and the service's solve loop (the result rows), both frontier caches, the service's solve()
(warm, custom pool, uploaded chart), and what the website reads: loadout entries, TeamBuff tier replays, note graphs,
exact scores, the General Meta. A lossless change leaves every output identical, which needs no game oracle run; an
intended change fails here and goes through the game oracles and the owner's yes instead.

Trees share one frozen copy of the inputs and one frontier cache per cache version (the first run of a version builds
it, and a complete one must stay untouched), all under <root> (--root, default ~/engine-gate). A record runs the tree's
own copy of this file, so a commit that moves engine code moves the imports here with it. Nothing reads or writes
production: every process gets its own HOME, database and bin.

Speed: one solve pass in a fresh process, priced in wall time, CPU seconds of all its threads and instructions retired
(macOS). Instructions barely move with machine load, so they carry the speed verdict; GPU time shows only in the GA
stage's wall time, so run `ab` for that.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import shutil
import sqlite3
import statistics
import subprocess
import sys
import time
from collections import Counter
from contextlib import contextmanager
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

import numpy as np

TREE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(TREE))

CHARTS = (
    "Easy/Back Out (Easy) by RiraN.txt",
    "Easy/LOVERS' OASIS (Easy) by dark cat.txt",  # one color, fewer notes than the combo ramp
    "Easy/Thorns (Easy) by Kawai Sprite.txt",
    "Easy/Yameen Yasar (Easy) by DJ Absi [Just Dance].txt",
    "Normal/BRODYAGA FUNK by Eternxlkz.txt",
    "Normal/Fairy Dance by UNDEAD CORPORATION.txt",
    "Normal/FREEDOM DiVE (Classic Map) [EXTENDED CUT] by xi (xi_com_giko_31).txt",
    "Normal/Welcome to Monday Night (DebugFill 1) by debug.txt",  # 9 notes
    "Hard/#include signalh (Hard) by Kurokotei.txt",
    "Hard/00 (Hard) by garlagan.txt",
    "Hard/Asteroid's Dream (Hard) by brz1128.txt",
    "Hard/Awaken (Hard) by Creo.txt",
    "Hard/Brilliant & Shining! (Hard) by Halv.txt",
    "Hard/Calamity Fortune (Hard) by LeaF (7eaF).txt",  # COMPLEXITY.md's reference chart
    "Hard/FREEDOM DiVE[METAL DIMENSIONS] (Hard) by xi (xi_com_giko_31) remixed by cosMo@bousouP.txt",
    "Hard/Sanctuary (Hard) by t+pazolite.txt",  # a mini's Song Target
)
_CONFIG = "[CalculateSong]\nLoopForever = false\n\n[IterationEngine]\nSongRepeats = 1\nWorkers = 1\n"
_TIER = "T5"
_SEED = "1234"
# Rewritten by every solve: not outputs.
_TIME_COLUMNS = {"last_updated", "meta_updated", "fg_updated"}
_SOLVE_STAGES = ("prepare", "ga", "fg", "finish", "store")
# Solve-stage instructions may rise this much before a change counts as slower: records of one tree differ by up to 0.4%.
_INSTRUCTION_NOISE = 0.005


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=_plain).encode()).hexdigest()[:24]


def _plain(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return [value.dtype.str, value.shape, hashlib.sha256(value.tobytes()).hexdigest()]
    if isinstance(value, np.generic):
        return value.item()
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, (set, frozenset)):
        return sorted(value)
    if isinstance(value, bytes):
        return hashlib.sha256(value).hexdigest()
    raise TypeError(f"no gate form for {type(value).__name__}")


_LIBSYSTEM = ctypes.CDLL(None) if sys.platform == "darwin" else None


def _process_counters() -> tuple[int, int]:
    """This process's instructions retired and peak memory footprint (rusage_info_v4; zeros off macOS)."""
    if _LIBSYSTEM is None:
        return 0, 0
    info = (ctypes.c_uint64 * 64)()
    if _LIBSYSTEM.proc_pid_rusage(os.getpid(), 4, info):
        raise OSError(ctypes.get_errno(), "proc_pid_rusage")
    return info[31], info[30]


class _Clock:
    """What the process spends per stage (wall seconds, CPU seconds, instructions), charged to the innermost open
    stage, so a nested stage is not part of its parent's cost."""

    def __init__(self) -> None:
        self.costs: dict[str, list[float]] = {}
        self._open: list[str] = []
        self._last = self._now()

    @staticmethod
    def _now() -> tuple[float, float, float]:
        return time.perf_counter(), time.process_time(), float(_process_counters()[0])

    def _charge(self) -> None:
        now = self._now()
        if self._open:
            cost = self.costs.setdefault(self._open[-1], [0.0, 0.0, 0.0])
            for index, (after, before) in enumerate(zip(now, self._last)):
                cost[index] += after - before
        self._last = now

    @contextmanager
    def __call__(self, stage: str):
        self._charge()
        self._open.append(stage)
        try:
            yield
        finally:
            self._charge()
            self._open.pop()

    def priced(self, module: Any, name: str, stage: str) -> None:
        """Charge every call of module.name to `stage`."""
        inner = getattr(module, name)

        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with self(stage):
                return inner(*args, **kwargs)

        setattr(module, name, wrapper)


def _save(run: Path, step: str, outputs: dict[str, str], clock: _Clock | None = None) -> None:
    costs = clock.costs if clock else {}
    (run / f"{step}.json").write_text(json.dumps({"outputs": outputs, "costs": costs, "peak_mb": _process_counters()[1] / 2**20}))


def versions(run: Path) -> None:
    """The tree's frontier cache versions."""
    from gear_optimizer.frontier.timeline_cache import TIMELINE_FRONTIER_CACHE
    from gear_optimizer.frontier.fg_cache_store import FG_RESPONSE_FRONTIER_CACHE

    (run / "versions.json").write_text(json.dumps([TIMELINE_FRONTIER_CACHE.version(), FG_RESPONSE_FRONTIER_CACHE.version()]))


def profile(run: Path) -> None:
    """The service worker's solve loop over the queue `main.py run` solves, in a fresh process, stage by stage."""
    clock = _Clock()
    with clock("startup"):
        from gear_optimizer import settings
        from gear_optimizer.domain.jobs import SharedRunContext
        from gear_optimizer.data.game_export import load_catalog
        from gear_optimizer.gamedata import stat_curves
        from gear_optimizer.pipeline import fg, prepare, solve
        from gear_optimizer.pipeline.queue import build_queue
        from gear_optimizer.pipeline.storing import store_solve
        from gear_optimizer.gpu.executor import start_gpu_executor
        from gear_optimizer.store import schema

        run_settings, paths = settings.read_run_settings(), settings.paths()
        catalog = load_catalog(paths.game_export)
        gears, minis = catalog.gears, catalog.minis
        schema.ensure(paths.database)
        tasks = build_queue(run_settings, SharedRunContext(multi_start=run_settings.multi_start, curves=stat_curves(),
                                                           gears=gears, minis=minis, ga_depth=run_settings.search_depth))
        executor = start_gpu_executor()
    with clock("warmup"):  # numba's and the kernels' first load belongs to no song
        solve.solve_song(tasks[0], executor)
    clock.priced(prepare, "prepare_native_song", "prepare")
    clock.priced(solve, "run_ga", "ga")
    clock.priced(fg, "fg_turn", "fg")
    clock.priced(solve, "finish_song", "finish")
    conn = schema.connect(paths.database, write=True)
    for task in tasks:
        solved = solve.solve_song(task, executor)
        with clock("store"):
            store_solve(conn, solved, gears, minis)
    conn.close()
    executor.stop()
    _save(run, "profile", {}, clock)


def _frontier_outputs(chart_path: Path, mode: str, curves: Any) -> dict[str, str]:
    """Every array of the chart's frontier files in `mode` (a Non-Precise song has no timeline file)."""
    from gear_optimizer.frontier.timeline_cache import TIMELINE_FRONTIER_CACHE
    from gear_optimizer.frontier.fg_cache_store import FG_RESPONSE_FRONTIER_CACHE

    outputs = {}
    for cache in (TIMELINE_FRONTIER_CACHE, FG_RESPONSE_FRONTIER_CACHE):
        path = cache.chart_file(str(chart_path), curves, mode)
        if path.exists():
            with np.load(path, allow_pickle=False) as arrays:
                for name in arrays.files:
                    if name != "version":
                        outputs[f"frontier/{cache.name}/{mode}/{chart_path.stem}/{name}"] = digest(arrays[name])
    return outputs


def _graph_outputs(key: str, entry: dict, chart: Any, song: Any, curves: Any) -> dict[str, str]:
    """The entry's note graphs and exact scores, called as the website calls them."""
    from gear_optimizer.core.timing_modes import NON_PRECISE, PRECISE
    from gear_optimizer.store.fg_payload import require_response_surface
    from gear_optimizer.rules import MAX_STAT
    from gear_optimizer.solver.fever_timeline import calculate_fever_timeline_indices
    from gear_optimizer.trace.note_graph import (
        base_note_graph,
        force_greats_note_graph,
        timeline_frontier_note_graph,
    )
    from gear_optimizer.solver.scoring.exact_rescore import (
        score_force_greats_response_surface_exact,
        score_stats_exact,
        score_stats_fixed_timing_exact,
    )
    from gear_optimizer.solver.timing_envelope import fever_axes

    details, force, mode, hash_key = entry["details"], entry["force"], song.mode, f"{key}/{entry['loadout_hash']}"
    timestamps, n = chart.timestamps, chart.total_notes
    arrays = dict(total_notes=n, note_types=chart.note_types, lanes=chart.lanes, timing_mode=mode,
                  perfect_time=sum(gear.perfect_time for gear in entry["gear"]))
    outputs = {}
    if "BaseScore" not in details:  # a meta board entry
        trace = details.get("TimelineFrontier", {}).get("frontier_trace")
        if trace:
            graph = timeline_frontier_note_graph(frontier_trace=trace, timestamps=timestamps, **arrays)
        else:
            durations, thresholds = fever_axes(chart.total_notes, chart.long_notes, chart.last_note_time, curves)
            duration = float(durations[min(MAX_STAT, details["Stats"]["Fever Time"])])
            threshold = int(np.ceil(thresholds[min(MAX_STAT, details["Stats"]["Fever Fill Rate"])]))
            mask = np.zeros(n, dtype=bool)
            calculate_fever_timeline_indices(timestamps, n, threshold, duration, mask)
            graph = base_note_graph(total_notes=n, timestamps=timestamps, is_fever_mask=mask)
        score = score_stats_fixed_timing_exact if mode == NON_PRECISE else score_stats_exact
        outputs[f"graphs/base/{hash_key}"] = digest(graph)
        outputs[f"scores/base/{hash_key}"] = digest(int(score(details["Stats"], song, curves)))
    if force is not None:
        fg_timestamps = np.floor(np.asarray(timestamps, dtype=np.float64) * 1000.0 + 0.5) / 1000.0
        graph = force_greats_note_graph(frontier_trace=force["ForceGreats"]["frontier_trace"], **arrays,
                                        timestamps=fg_timestamps if mode == PRECISE else timestamps)
        surface = require_response_surface(force)
        outputs[f"graphs/fg/{hash_key}"] = digest(graph)
        outputs[f"scores/fg/{hash_key}"] = digest(
            score_force_greats_response_surface_exact(force["BaseStats"], song, curves, surface)
        )
    return outputs


def surfaces(run: Path) -> None:
    """What the website reads of the run's result database, and both frontier caches."""
    clock = _Clock()
    from gear_optimizer.chart import load_chart
    from gear_optimizer.core.timing_modes import PRECISE, TIMING_MODES
    from gear_optimizer.data.game_export import load_catalog
    from gear_optimizer.gamedata import stat_curves
    from gear_optimizer.solver.team_buff_tiers import build_team_buff_tier_db_batches
    from gear_optimizer.settings import paths
    from gear_optimizer.frontier.timeline_cache import build_or_load_timeline_frontier_payload
    from gear_optimizer.solver.timing_envelope import time_song
    from gear_optimizer.store import legacy
    from general_meta import run_general_meta

    database, curves = paths().database, stat_curves()
    catalog = load_catalog(paths().game_export)
    gears, minis = catalog.gears, catalog.minis
    outputs: dict[str, str] = {}
    with clock("general-meta"):
        outputs["general-meta"] = digest(run_general_meta(database)["results"])
    for relative in CHARTS:
        chart_path = paths().data_dir / relative
        chart = load_chart(chart_path)
        for mode in TIMING_MODES:
            key = f"{mode}/{chart.name}"
            with clock("frontiers"):
                outputs |= _frontier_outputs(chart_path, mode, curves)
            song = time_song(chart, mode)
            if mode == PRECISE:
                build_or_load_timeline_frontier_payload(song, curves)
            with clock("entries"):
                entries = legacy.read_best_loadouts(database, mode, chart.name, _TIER, gears=gears, minis=minis)
            outputs[f"entries/{key}"] = digest(entries)
            with clock("graphs"):
                for entry in entries:
                    outputs |= _graph_outputs(key, entry, chart, song, curves)
            for color in dict.fromkeys((chart.primary, chart.secondary)):
                with clock("tiers"):
                    batches = build_team_buff_tier_db_batches(
                        entries=entries, song=song, curves=curves, base_team_color_override=chart.primary,
                        target_team_color_override=color,
                    )
                outputs |= {f"tiers/{key}/{color}/{tier}": digest(rows) for tier, rows in batches.items()}
    _save(run, "surfaces", outputs, clock)


def _service_requests(data: Path, excluded_gear: str) -> dict[str, dict]:
    """One request down each of the service's solve paths."""
    from gear_optimizer.chart import load_chart
    from gear_optimizer.core.timing_modes import NON_PRECISE, PRECISE

    easy = data / CHARTS[0]
    song = load_chart(easy).name
    return {
        "official": {"targetSongId": song, "timingMode": PRECISE},
        "official-strong": {"targetSongId": song, "timingMode": NON_PRECISE, "reasoning": "strong"},
        "custom-pool": {
            "targetSongId": song,
            "timingMode": PRECISE,
            "customGear": [{"name": "Gate Hat", "type": "Hat", "rush": 140, "ppoint": 60}],
            "customMinis": [{"name": "Gate Mini", "type": "Rush", "rush": 90, "fvfil": 30}],
            "excludeGear": [excluded_gear],
        },
        "uploaded-chart": {"chartText": easy.read_text(encoding="utf-8"), "timingMode": NON_PRECISE},
    }


def service(run: Path) -> None:
    """The service's solve(): official charts on the warm worker, a custom pool, and an uploaded chart's cold run."""
    clock = _Clock()
    from gear_optimizer import robeatsmeta_service
    from gear_optimizer.data.game_export import load_catalog
    from gear_optimizer.settings import paths

    requests = _service_requests(paths().data_dir, min(load_catalog(paths().game_export).gears))
    outputs = {}
    for name, request in requests.items():
        with clock(f"service {name}"):
            outputs[f"service/{name}"] = digest(robeatsmeta_service.solve({"jobId": name, **request}))
    _save(run, "service", outputs, clock)


def _rows(database: Path, prefix: str) -> dict[str, str]:
    """Every row of a result database, keyed by its primary key, without the columns that hold write times."""
    conn = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    outputs = {}
    for table, key_columns in (("songs", 2), ("loadouts", 4)):
        cursor = conn.execute(f"SELECT * FROM {table}")
        columns = [column[0] for column in cursor.description]
        kept = [index for index, column in enumerate(columns) if column not in _TIME_COLUMNS]
        for row in cursor:
            outputs[f"{prefix}/{table}/" + "/".join(row[:key_columns])] = digest([row[index] for index in kept])
    conn.close()
    return outputs


def _frozen_inputs(root: Path) -> Path:
    """The inputs every record reads, copied once from the first tree that records."""
    inputs = root / "inputs"
    if inputs.exists():
        return inputs
    staging = root / "inputs.staging"
    shutil.rmtree(staging, ignore_errors=True)
    for relative in CHARTS:
        (staging / "Data" / relative).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(TREE / "Data" / relative, staging / "Data" / relative)
    shutil.copyfile(TREE / "Data" / "exported_game_data.json", staging / "Data" / "exported_game_data.json")
    (staging / "config.ini").write_text(_CONFIG, encoding="utf-8")
    staging.rename(inputs)
    return inputs


def _environment(inputs: Path, run: Path) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith(("ROBEATSMETA_", "METAFINDER_"))}
    for directory in ("home", "bin"):
        (run / directory).mkdir()
    return env | {
        "HOME": str(run / "home"),
        "PYTHONPATH": str(TREE),
        "GA_SEED": _SEED,
        "EVOLUTION_DB_PATH": str(run / "result.db"),
        "METAFINDER_CONFIG_PATH": str(inputs / "config.ini"),
        "METAFINDER_PROGRESS": "0",
        "ROBEATSMETA_OPTIMIZER_DATA_DIR": str(inputs / "Data"),
        "ROBEATSMETA_OPTIMIZER_BIN_DIR": str(run / "bin"),
        "ROBEATSMETA_OPTIMIZER_SERVICE_MODE": "1",
        "ROBEATSMETA_OPTIMIZER_SERVICE_MIN_FREE_MB": "0",
        "ROBEATSMETA_OPTIMIZER_SERVICE_RUN_DIR": str(run / "service"),
    }


def _execute(run: Path, name: str, command: list[str], env: dict[str, str]) -> float:
    """Run one process of the record (its output in <run>/<name>.log); its wall seconds. Fails loud."""
    started = time.perf_counter()
    with open(run / f"{name}.log", "w") as log:
        code = subprocess.run(command, cwd=TREE, env=env, stdout=log, stderr=subprocess.STDOUT).returncode
    if code:
        raise SystemExit(f"{name} failed with exit code {code}: see {run / f'{name}.log'}")
    return time.perf_counter() - started


def _listing(directory: Path) -> dict[str, tuple[int, int]]:
    return {str(path.relative_to(directory)): (path.stat().st_size, path.stat().st_mtime_ns)
            for path in directory.rglob("*") if path.is_file() and path.name != "complete"}


def record(label: str, root: Path) -> None:
    inputs = _frozen_inputs(root)
    run = root / "runs" / label
    shutil.rmtree(run, ignore_errors=True)
    run.mkdir(parents=True)
    env = _environment(inputs, run)

    def step(name: str, **overrides: str) -> float:
        return _execute(run, name, [sys.executable, __file__, name, str(run)], env | overrides)

    step("versions")
    cache_versions = json.loads((run / "versions.json").read_text())
    frontiers = root / "frontiers" / "--".join(cache_versions)
    env |= {"TIMELINE_FRONTIER_CACHE_DIR": str(frontiers / "timeline"), "FG_RESPONSE_FRONTIER_CACHE_DIR": str(frontiers / "fg")}
    complete = frontiers / "complete"
    before = _listing(frontiers) if complete.exists() else None
    cli_s = _execute(run, "cli", [sys.executable, "main.py", "run"], env)
    complete.touch()
    step("profile", EVOLUTION_DB_PATH=str(run / "profile.db"))
    step("surfaces")
    step("service", EVOLUTION_DB_PATH=str(run / "service.db"))
    if before is not None and _listing(frontiers) != before:
        raise SystemExit(f"a run wrote into the complete frontier cache {frontiers}")

    rows = _rows(run / "result.db", "rows")
    if rows != _rows(run / "profile.db", "rows"):
        raise SystemExit("`main.py run` and the service's solve loop stored different rows")
    steps = {name: json.loads((run / f"{name}.json").read_text()) for name in ("profile", "surfaces", "service")}
    commit = subprocess.run(["git", "describe", "--always", "--dirty"], cwd=TREE, capture_output=True, text=True, check=True)
    (run / "record.json").write_text(json.dumps({
        "commit": commit.stdout.strip(),
        "cache_versions": cache_versions,
        "cli_s": cli_s,
        "peak_mb": steps["profile"]["peak_mb"],
        "costs": {stage: cost for result in steps.values() for stage, cost in result["costs"].items()},
        "outputs": {**rows, **steps["surfaces"]["outputs"], **steps["service"]["outputs"], **_rows(run / "service.db", "promoted")},
    }))
    print(f"{label}: {len(rows):,} rows, {cli_s:.0f} s `main.py run`, {commit.stdout.strip()}", flush=True)


def _records(root: Path, label: str) -> list[dict]:
    """The records named `label`, or `label-<round>` for each round of an `ab`."""
    runs = [root / "runs" / label] + sorted((root / "runs").glob(f"{label}-[0-9]*"))
    records = [json.loads((run / "record.json").read_text()) for run in runs if (run / "record.json").exists()]
    if not records:
        raise SystemExit(f"no record named {label} under {root / 'runs'}")
    return records


def _differing(a: dict[str, str], b: dict[str, str]) -> list[str]:
    return sorted(key for key in a.keys() | b.keys() if a.get(key) != b.get(key))


def _print_differences(differing: list[str]) -> None:
    groups = Counter(key.split("/")[0] for key in differing)
    print(f"outputs DIFFER: {sum(groups.values()):,} ({', '.join(f'{name} {count:,}' for name, count in groups.most_common())})")
    for name in groups:
        for key in [key for key in differing if key.startswith(f"{name}/") or key == name][:3]:
            print(f"  {key}")


def _medians(records: list[dict]) -> dict[str, list[float]]:
    stages = {stage for record_ in records for stage in record_["costs"]}
    return {stage: [statistics.median(r["costs"][stage][i] for r in records if stage in r["costs"]) for i in range(3)]
                    for stage in stages}


def _print_costs(base: dict[str, list[float]], candidate: dict[str, list[float]]) -> None:
    print(f"{'stage':<26}{'wall s':>17}{'CPU s':>17}{'G instructions':>17}{'change':>9}")
    for stage in sorted(base.keys() | candidate.keys(), key=lambda s: (s not in _SOLVE_STAGES, _stage_rank(s), s)):
        a, b = base.get(stage, [0.0] * 3), candidate.get(stage, [0.0] * 3)
        change = f"{(b[2] / a[2] - 1) * 100:+.2f}%" if a[2] else ""
        print(f"{stage:<26}{a[0]:>8.2f}{b[0]:>9.2f}{a[1]:>8.2f}{b[1]:>9.2f}{a[2] / 1e9:>8.2f}{b[2] / 1e9:>9.2f}{change:>9}")


def _stage_rank(stage: str) -> int:
    return _SOLVE_STAGES.index(stage) if stage in _SOLVE_STAGES else 0


def compare(base_label: str, candidate_label: str, root: Path) -> int:
    base, candidate = _records(root, base_label), _records(root, candidate_label)
    failed = False
    for name, group in ((base_label, base), (candidate_label, candidate)):
        for later in group[1:]:
            if differing := _differing(group[0]["outputs"], later["outputs"]):
                print(f"{name} is not deterministic:")
                _print_differences(differing)
                failed = True
    differing = _differing(base[0]["outputs"], candidate[0]["outputs"])
    if differing:
        _print_differences(differing)
        failed = True
    else:
        print(f"outputs IDENTICAL: {len(base[0]['outputs']):,} ({base[0]['commit']} vs {candidate[0]['commit']})")
    if base[0]["cache_versions"] != candidate[0]["cache_versions"]:
        print("cache versions CHANGED: ratify the predecessors before pushing, or the service purges every bundle")
    a, b = _medians(base), _medians(candidate)
    _print_costs(a, b)
    before, after = (sum(costs[stage][2] for stage in _SOLVE_STAGES) for costs in (a, b))
    print(f"peak MB {statistics.median(r['peak_mb'] for r in base):,.0f} -> {statistics.median(r['peak_mb'] for r in candidate):,.0f}")
    if before:
        print(f"solve stages: {before / 1e9:.2f} -> {after / 1e9:.2f} G instructions ({(after / before - 1) * 100:+.2f}%)")
        if after > before * (1 + _INSTRUCTION_NOISE):
            print("SLOWER than the base")
            failed = True
    return 1 if failed else 0


def ab(base_tree: Path, rounds: int, root: Path) -> int:
    """Records alternating between `base_tree` and this tree, base first, then their compare."""
    for round_ in range(1, rounds + 1):
        subprocess.run([sys.executable, str(base_tree / "tools/verify/gate.py"), "record", f"ab-base-{round_}",
                        "--root", str(root)], check=True)
        record(f"ab-candidate-{round_}", root)
    return compare("ab-base", "ab-candidate", root)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    for name, arguments in (("record", ("label",)), ("compare", ("base", "label")), ("ab", ("base_tree",))):
        command = commands.add_parser(name)
        for argument in arguments:
            command.add_argument(argument)
        command.add_argument("--root", type=Path, default=Path.home() / "engine-gate")
        if name == "ab":
            command.add_argument("--rounds", type=int, default=3)
    steps = {step.__name__: step for step in (versions, profile, surfaces, service)}
    for name in steps:  # the processes of a record
        commands.add_parser(name).add_argument("run", type=Path)
    args = parser.parse_args()
    if args.command in steps:
        steps[args.command](args.run)
        return 0
    if args.command == "record":
        record(args.label, args.root)
        return 0
    if args.command == "compare":
        return compare(args.base, args.label, args.root)
    return ab(Path(args.base_tree).resolve(), args.rounds, args.root)


if __name__ == "__main__":
    raise SystemExit(main())
