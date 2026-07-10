from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from tools.bench import issue116_corpus_chart as corpus


_VERSION = "fg-response-frontier-visible-first-v29+logic-test"
_NOTE_COUNT = 4
_HELD_COUNT = 1


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(root: Path, *args: str) -> str:
    env = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    return result.stdout.strip()


class _FakeProcess:
    def __init__(self, case: _Case | None = None) -> None:
        self._case = case
        self._calls = 0

    def memory_info(self):
        self._calls += 1
        if self._case is not None:
            self._case.call_log.append("memory_info")
        return SimpleNamespace(
            rss=1_000,
            wset=900,
            private=800 + self._calls,
            peak_wset=1_200,
            peak_pagefile=1_100,
        )

    def cpu_affinity(self) -> list[int]:
        return [0, 1]


class _FakePsutil:
    __version__ = "test-psutil"

    @staticmethod
    def Process() -> _FakeProcess:
        return _FakeProcess()

    @staticmethod
    def virtual_memory():
        return SimpleNamespace(total=64_000_000_000, available=40_000_000_000)

    @staticmethod
    def swap_memory():
        return SimpleNamespace(total=32_000_000_000, used=1_000_000)


class _FakeSampler:
    def __init__(self) -> None:
        self.started = False
        self.stopped = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        assert self.started
        self.stopped = True

    def report(self) -> dict:
        assert self.stopped
        return {
            "interval_seconds": 5.0,
            "sample_count": 2,
            "max_process_bytes": {"rss": 1_000, "wset": 900, "private": 800},
            "max_system_commit_total_bytes": 20_000_000_000,
            "min_system_commit_available_bytes": 30_000_000_000,
            "min_system_physical_available_bytes": 30_000_000_000,
        }


def _capacity(*, available: int = 30_000_000_000) -> dict[str, int]:
    return {
        "page_size_bytes": 4096,
        "commit_total_bytes": 20_000_000_000,
        "commit_limit_bytes": 20_000_000_000 + int(available),
        "commit_peak_bytes": 21_000_000_000,
        "commit_available_bytes": int(available),
        "physical_total_bytes": 64_000_000_000,
        "physical_available_bytes": int(available),
    }


class _Case:
    def __init__(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self.base = tmp_path
        self.target = tmp_path / "target"
        self.run_root = tmp_path / "run"
        self.target.mkdir()
        (self.target / "Data" / "Gear").mkdir(parents=True)
        (self.target / "Data" / "Easy").mkdir(parents=True)
        (self.target / "tools" / "bench").mkdir(parents=True)
        self.chart = self.target / "Data" / "Easy" / "Chart.txt"
        self.stats = self.target / "Data" / "Gear" / "Stats.txt"
        self.config = self.target / "config.ini"
        self.runner_file = self.target / "tools" / "bench" / "issue116_corpus_chart.py"
        self.chart.write_text("tracked chart\n", encoding="utf-8")
        self.stats.write_text("tracked stats\n", encoding="utf-8")
        self.config.write_text("[General]\n", encoding="utf-8")
        self.runner_file.write_text("# tracked runner fixture\n", encoding="utf-8")
        _git(self.target, "init", "-q")
        _git(self.target, "config", "user.email", "tests@example.invalid")
        _git(self.target, "config", "user.name", "Issue 116 Tests")
        _git(self.target, "add", ".")
        _git(self.target, "commit", "-q", "-m", "fixture")
        self.head = _git(self.target, "rev-parse", "HEAD")

        self.fg_cache = self.run_root / "fg_response_frontier_cache"
        self.timeline_cache = self.run_root / "timeline_frontier_cache"
        self.optimizer_bin = self.run_root / "optimizer_bin"
        self.artifacts = self.run_root / "artifacts"
        for directory in (self.fg_cache, self.timeline_cache, self.optimizer_bin, self.artifacts):
            directory.mkdir(parents=True)
        self.database = self.run_root / "evolution.db"
        self.profile = self.run_root / "profile_events.jsonl"
        self.manifest = self.run_root / "preflight.json"
        self.production = self.target / "bin" / "fg_response_frontier_cache"
        self.production.mkdir(parents=True)
        self.environment = {
            "FG_RESPONSE_FRONTIER_CACHE_DIR": str(self.fg_cache.resolve()),
            "TIMELINE_FRONTIER_CACHE_DIR": str(self.timeline_cache.resolve()),
            "ROBEATSMETA_OPTIMIZER_BIN_DIR": str(self.optimizer_bin.resolve()),
            "EVOLUTION_DB_PATH": str(self.database.resolve()),
            "METAFINDER_PROFILE_EVENTS_PATH": str(self.profile.resolve()),
        }
        self.payload = {
            "git_head": self.head,
            "target_worktree": {"root": str(self.target.resolve()), "git_head": self.head},
            "preflight_tool": {"root": str(self.target.resolve()), "git_head": self.head},
            "paths": {
                "bench_root": str(self.base.resolve()),
                "worktree_root": str(self.target.resolve()),
                "preflight_tool_root": str(self.target.resolve()),
                "git_common_dir": str((self.target / ".git").resolve()),
                "primary_worktree_root": str(self.target.resolve()),
                "run_root": str(self.run_root.resolve()),
                "fg_response_cache_dir": str(self.fg_cache.resolve()),
                "timeline_cache_dir": str(self.timeline_cache.resolve()),
                "optimizer_bin_dir": str(self.optimizer_bin.resolve()),
                "database_path": str(self.database.resolve()),
                "profile_events_path": str(self.profile.resolve()),
                "artifacts_dir": str(self.artifacts.resolve()),
                "preflight_manifest_path": str(self.manifest.resolve()),
                "production_fg_cache_dir": str(self.production.resolve()),
            },
            "environment": dict(self.environment),
        }
        self.write_manifest()

        for key in (*corpus._EXPECTED_ENV_KEYS, "METAFINDER_CONFIG_PATH"):
            monkeypatch.delenv(key, raising=False)
        for key in tuple(os.environ):
            if key.upper().startswith("GIT_"):
                monkeypatch.delenv(key, raising=False)
        self.pycache = self.artifacts / "pycache"
        self.numba_cache = self.artifacts / "numba-cache"
        monkeypatch.setenv("PYTHONHASHSEED", "0")
        monkeypatch.setenv("PYTHONPYCACHEPREFIX", str(self.pycache))
        monkeypatch.setenv("NUMBA_CACHE_DIR", str(self.numba_cache))
        monkeypatch.setattr(sys, "pycache_prefix", str(self.pycache))
        monkeypatch.chdir(self.target)

        self.mode = "success"
        self.load_called = False
        self.build_called = False
        self.capacity_calls = 0
        self.call_log: list[str] = []
        self.args = [
            "--preflight",
            str(self.manifest),
            "--chart-relative",
            "Data/Easy/Chart.txt",
            "--expected-chart-sha256",
            _sha256(self.chart),
            "--expected-stats-sha256",
            _sha256(self.stats),
            "--expected-config-sha256",
            _sha256(self.config),
            "--expected-note-count",
            str(_NOTE_COUNT),
            "--expected-held-count",
            str(_HELD_COUNT),
            "--expected-cache-version",
            _VERSION,
        ]
        self.dependencies = self._dependencies()

    def write_manifest(self) -> None:
        self.manifest.write_text(json.dumps(self.payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def use_sibling_tool_worktree(self) -> None:
        tool = self.base / "tool"
        _git(self.target, "worktree", "add", "-q", "-b", "runner-fixture", str(tool))
        tool_head = _git(tool, "rev-parse", "HEAD")
        self.runner_file = tool / "tools" / "bench" / "issue116_corpus_chart.py"
        self.payload["preflight_tool"] = {"root": str(tool.resolve()), "git_head": tool_head}
        self.payload["paths"]["preflight_tool_root"] = str(tool.resolve())
        self.write_manifest()
        self.dependencies = self._dependencies()

    def _run_git(self, root: Path, args) -> str:
        self.call_log.append(f"git:{args[0]}")
        return corpus._run_git(root, args)

    def _read_capacity(self) -> dict[str, int]:
        self.call_log.append("capacity")
        self.capacity_calls += 1
        if self.mode == "capacity":
            return _capacity(available=12_999_999_999)
        if self.mode == "capacity_fall" and self.capacity_calls >= 2:
            return _capacity(available=12_999_999_999)
        return _capacity()

    def _build(self, chart_path: str, ref_arrays: dict, *, stat_keys) -> SimpleNamespace:
        self.build_called = True
        assert self.load_called
        assert os.environ["FG_RESPONSE_FRONTIER_CACHE_DIR"] == str(self.fg_cache.resolve())
        assert os.environ["METAFINDER_CONFIG_PATH"] == str(self.config.resolve())
        if self.mode == "builder_exception":
            raise RuntimeError("builder exploded")
        bundle = self.fg_cache / "bundle.npz"
        np.savez(
            bundle,
            version=np.asarray(_VERSION),
            stat_keys=np.asarray(stat_keys, dtype=np.int32),
            total_notes=np.asarray(_NOTE_COUNT, dtype=np.int32),
            long_notes=np.asarray(_HELD_COUNT, dtype=np.int32),
        )
        np.save(self.fg_cache / "bundle.surf_pool.npy", np.zeros((1, 11), dtype=np.uint32))
        np.save(self.fg_cache / "bundle.surf_coeffs.npy", np.zeros((1, 8), dtype=np.uint16))
        if self.mode == "extra_cache":
            (self.fg_cache / "unexpected").write_text("x", encoding="utf-8")
        events = []
        if self.mode != "profile_missing":
            events.append(
                {
                    "component": "fg_response_cache",
                    "event": "prebuild_song_done",
                    "song_key": self.chart.name,
                    "metrics": {
                        "source": "built" if self.mode != "profile_source" else "disk",
                        "note_count": _NOTE_COUNT,
                        "build_ms": 2.0,
                    },
                }
            )
        if self.mode == "profile_duplicate":
            events.append(dict(events[0]))
        if events:
            self.profile.write_text("".join(json.dumps(event) + "\n" for event in events), encoding="utf-8")
        if self.mode == "database":
            self.database.write_text("unexpected", encoding="utf-8")
        if self.mode == "timeline":
            (self.timeline_cache / "unexpected").write_text("x", encoding="utf-8")
        if self.mode == "post_mutation":
            self.chart.write_text("mutated after build\n", encoding="utf-8")
        self.call_log.append("builder_return")
        return SimpleNamespace(
            path=str(chart_path),
            source="disk" if self.mode == "source" else "built",
            build_ms=2.0,
            cache_file=str(bundle),
        )

    def _runtime(self) -> corpus._Runtime:
        self.load_called = True
        self.call_log.append("load_runtime")
        assert self.call_log[0] == "capacity"
        assert "git:hash-object" in self.call_log
        assert os.environ["FG_RESPONSE_FRONTIER_CACHE_DIR"] == str(self.fg_cache.resolve())
        assert os.environ["METAFINDER_CONFIG_PATH"] == str(self.config.resolve())
        names = (
            "Perfect Points",
            "Combo Multiplier",
            "Fever Multiplier",
            "Fever Fill Rate",
            "Fever Time",
        )
        reducer = SimpleNamespace(
            configure_force_greats_response_first_frontier_threads=lambda value: None,
            _resolve_first_only_reducer_threads=lambda work: 2,
        )
        config_path = self.config if self.mode != "config_resolution" else self.target / "wrong.ini"
        process = _FakeProcess(self)
        psutil = SimpleNamespace(
            __version__="test-psutil",
            Process=lambda: process,
            virtual_memory=_FakePsutil.virtual_memory,
            swap_memory=_FakePsutil.swap_memory,
        )
        return corpus._Runtime(
            np=np,
            numba=SimpleNamespace(__version__="test-numba"),
            psutil=psutil,
            read_table=lambda path: [[float(row + col) for col in range(5)] for row in range(161)],
            get_base_calc_song=lambda path, cfg: {
                "metadata": {"Total Notes": str(_NOTE_COUNT), "Long Notes": str(_HELD_COUNT)},
                "song_data": {
                    "timestamps": np.asarray([0.0, 1.0, 2.0, 3.0], dtype=np.float32),
                    "note_types": np.asarray([1, 2, 3, 1], dtype=np.int16),
                    "lanes": np.asarray([1, 2, 2, 3], dtype=np.int32),
                },
            },
            build_ref_arrays_from_stats=lambda table, dtype: {
                name: np.arange(161, dtype=dtype) for name in names
            },
            prebuild=SimpleNamespace(
                _FG_PREBUILD_PEAK_COMMIT_GB=7.0,
                _FG_PREBUILD_SYSTEM_RESERVE_GB=6.0,
                build_fg_response_frontier_cache_for_path=self._build,
            ),
            reducer=reducer,
            cache_types=SimpleNamespace(
                _FG_RESPONSE_CACHE_VERSION=_VERSION,
                all_response_stat_keys=lambda: tuple(
                    (ft, ff) for ft in range(161) for ff in range(161)
                ),
            ),
            constants=SimpleNamespace(TOTAL_ROWS=160),
            config=SimpleNamespace(get_config_path=lambda: str(config_path)),
        )

    def _load_runtime(self, target: Path) -> corpus._Runtime:
        assert target == self.target.resolve()
        return self._runtime()

    def _dependencies(self) -> corpus._Dependencies:
        perf_values = iter((1_000_000_000, 2_000_000_000))
        wall_values = iter((1_700_000_000_000_000_000, 1_700_000_001_000_000_000))
        return corpus._Dependencies(
            run_git=self._run_git,
            read_capacity=self._read_capacity,
            read_hardware=lambda: {"hardware": "fixture"},
            load_runtime=self._load_runtime,
            sampler_factory=lambda psutil, reader: _FakeSampler(),
            validate_bench_root=lambda value: self.base.resolve()
            if Path(value).resolve() == self.base.resolve()
            else (_ for _ in ()).throw(ValueError("wrong fixture bench root")),
            runner_path=self.runner_file,
            hash_randomization=0,
            perf_counter_ns=lambda: next(perf_values),
            time_ns=lambda: next(wall_values),
        )

    @property
    def completed(self) -> Path:
        return self.artifacts / "completed_build.json"

    @property
    def failure(self) -> Path:
        return self.artifacts / "failure.json"

    def run(self) -> int:
        return corpus.main(self.args, dependencies=self.dependencies)


@pytest.fixture
def case(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> _Case:
    return _Case(tmp_path, monkeypatch)


def test_issue116_corpus_runner_success_is_atomic_and_imports_after_validation(case: _Case) -> None:
    assert case.run() == 0
    assert case.load_called
    assert case.completed.is_file()
    assert not case.failure.exists()
    assert not case.completed.with_name("completed_build.json.tmp").exists()
    report = json.loads(case.completed.read_text(encoding="utf-8"))
    assert report["ok"] is True
    assert report["completed_build_anchor"] is True
    assert report["configuration"]["reducer_threads"] == 2
    assert report["inputs"]["reference_grid"]["stat_key_count"] == 25_921
    assert report["cache"]["source"] == "built"
    assert report["cache"]["wall_ms"] == 1000.0
    assert len(report["cache"]["files"]) == 3
    assert report["profile_events"]["event_counts"]["fg_response_cache/prebuild_song_done"] == 1
    assert report["memory"]["completed_build_anchor"] is True
    assert report["memory"]["process_at_completed_build_return"]["private"] == 802
    assert report["memory"]["process_post_verification"]["private"] == 803
    builder_return = case.call_log.index("builder_return")
    assert case.call_log[builder_return + 1] == "memory_info"
    assert case.call_log.index("capacity") < case.call_log.index("load_runtime")
    assert case.call_log.index("git:hash-object") < case.call_log.index("load_runtime")


def test_issue116_corpus_runner_accepts_registered_sibling_tool_without_importing_its_runtime(
    case: _Case,
) -> None:
    case.use_sibling_tool_worktree()
    assert case.run() == 0
    report = json.loads(case.completed.read_text(encoding="utf-8"))
    assert report["target"]["before"]["root"] == str(case.target.resolve())
    assert report["preflight_tool"]["before"]["root"] == str(case.runner_file.parents[2].resolve())
    assert case.load_called


def test_issue116_corpus_runner_rejects_tool_from_different_repository(case: _Case) -> None:
    foreign = case.base / "foreign"
    (foreign / "tools" / "bench").mkdir(parents=True)
    foreign_runner = foreign / "tools" / "bench" / "issue116_corpus_chart.py"
    foreign_runner.write_text("# foreign runner\n", encoding="utf-8")
    _git(foreign, "init", "-q")
    _git(foreign, "config", "user.email", "tests@example.invalid")
    _git(foreign, "config", "user.name", "Issue 116 Tests")
    _git(foreign, "add", ".")
    _git(foreign, "commit", "-q", "-m", "foreign")
    foreign_head = _git(foreign, "rev-parse", "HEAD")
    case.runner_file = foreign_runner
    case.payload["preflight_tool"] = {"root": str(foreign.resolve()), "git_head": foreign_head}
    case.payload["paths"]["preflight_tool_root"] = str(foreign.resolve())
    case.write_manifest()
    case.dependencies = case._dependencies()
    assert case.run() == 1
    assert not case.completed.exists()
    assert case.failure.is_file()
    assert not case.load_called


def test_issue116_corpus_runner_rejects_unregistered_sibling_tool(case: _Case) -> None:
    case.use_sibling_tool_worktree()
    original = case.dependencies.run_git

    def omit_sibling(root: Path, args) -> str:
        if root != case.target.resolve() and tuple(args) == ("worktree", "list", "--porcelain"):
            return f"worktree {case.target.resolve()}\nHEAD {case.head}\nbranch refs/heads/main"
        return original(root, args)

    case.dependencies = replace(case.dependencies, run_git=omit_sibling)
    assert case.run() == 1
    assert not case.completed.exists()
    assert case.failure.is_file()
    assert not case.load_called


def test_issue116_corpus_runner_rejects_forged_git_top_level(case: _Case) -> None:
    original = case.dependencies.run_git
    forged = case.base / "forged"
    forged.mkdir()

    def forge_top(root: Path, args) -> str:
        if tuple(args) == ("rev-parse", "--path-format=absolute", "--show-toplevel"):
            return str(forged)
        return original(root, args)

    case.dependencies = replace(case.dependencies, run_git=forge_top)
    assert case.run() == 1
    assert not case.completed.exists()
    assert case.failure.is_file()
    assert not case.load_called


@pytest.mark.parametrize(
    "fault",
    (
        "isolation_env",
        "config_env",
        "pycache_path",
        "numba_path",
        "hash_randomization",
        "hash",
        "git",
        "capacity",
    ),
)
def test_issue116_corpus_runner_rejects_preimport_contamination_and_writes_no_completed_anchor(
    case: _Case,
    monkeypatch: pytest.MonkeyPatch,
    fault: str,
) -> None:
    if fault == "isolation_env":
        monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(case.base / "wrong"))
    elif fault == "config_env":
        monkeypatch.setenv("METAFINDER_CONFIG_PATH", str(case.config))
    elif fault == "pycache_path":
        outside = case.base / "outside-pycache"
        monkeypatch.setenv("PYTHONPYCACHEPREFIX", str(outside))
        monkeypatch.setattr(sys, "pycache_prefix", str(outside))
    elif fault == "numba_path":
        monkeypatch.setenv("NUMBA_CACHE_DIR", str(case.base / "outside-numba"))
    elif fault == "hash_randomization":
        case.dependencies = replace(case.dependencies, hash_randomization=1)
    elif fault == "hash":
        index = case.args.index("--expected-chart-sha256") + 1
        case.args[index] = "0" * 64
    elif fault == "git":
        (case.target / "untracked.txt").write_text("dirty", encoding="utf-8")
    elif fault == "capacity":
        case.mode = "capacity"
    assert case.run() == 1
    assert not case.completed.exists()
    assert case.failure.is_file()
    diagnostic = json.loads(case.failure.read_text(encoding="utf-8"))
    assert diagnostic["completed_build_anchor"] is False
    assert not case.load_called


@pytest.mark.parametrize(
    "fault",
    (
        "source",
        "extra_cache",
        "profile_missing",
        "profile_duplicate",
        "profile_source",
        "database",
        "timeline",
        "post_mutation",
        "config_resolution",
        "builder_exception",
    ),
)
def test_issue116_corpus_runner_rejects_build_and_postcondition_failures(
    case: _Case,
    fault: str,
) -> None:
    case.mode = fault
    assert case.run() == 1
    assert not case.completed.exists()
    assert case.failure.is_file()
    diagnostic = json.loads(case.failure.read_text(encoding="utf-8"))
    assert diagnostic["ok"] is False
    assert diagnostic["completed_build_anchor"] is False


def test_issue116_corpus_runner_rechecks_capacity_at_build_entry(case: _Case) -> None:
    case.mode = "capacity_fall"
    assert case.run() == 1
    assert case.load_called
    assert not case.build_called
    assert not case.completed.exists()
    assert json.loads(case.failure.read_text(encoding="utf-8"))["completed_build_anchor"] is False


def test_issue116_corpus_runner_rejects_nonliteral_or_aliasing_manifest(
    case: _Case,
) -> None:
    case.payload["paths"]["timeline_cache_dir"] = case.payload["paths"]["fg_response_cache_dir"]
    case.payload["environment"]["TIMELINE_FRONTIER_CACHE_DIR"] = case.payload["paths"][
        "fg_response_cache_dir"
    ]
    case.write_manifest()
    assert case.run() == 1
    assert not case.completed.exists()
    assert not case.failure.exists()  # no trusted artifact root exists until manifest validation passes
    assert not case.load_called


def test_issue116_corpus_runner_rejects_nonempty_cold_cache_before_context_is_trusted(
    case: _Case,
) -> None:
    (case.fg_cache / "contamination").write_text("warm", encoding="utf-8")
    assert case.run() == 1
    assert not case.completed.exists()
    assert not case.failure.exists()
    assert not case.load_called


def test_issue116_corpus_runner_rejects_git_environment_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GIT_DIR", "forbidden")
    with pytest.raises(ValueError, match="Git environment overrides"):
        corpus._git_environment()


def test_issue116_live_capacity_reader_rejects_non_windows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(corpus.platform, "system", lambda: "Linux")
    with pytest.raises(ValueError, match="requires Windows"):
        corpus._windows_capacity_snapshot()


def test_issue116_atomic_json_never_overwrites_existing_output(tmp_path: Path) -> None:
    output = tmp_path / "result.json"
    output.write_text("owner", encoding="utf-8")
    with pytest.raises(ValueError, match="already exists"):
        corpus._atomic_write_json(output, {"ok": True})
    assert output.read_text(encoding="utf-8") == "owner"
