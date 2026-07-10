from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from tools.bench import issue116_run_preflight as preflight
from tools.bench.issue116_run_preflight import (
    _prepare_issue116_run,
    _primary_worktree_from_porcelain,
    _resolve_issue116_run_paths,
    resolve_primary_worktree_root,
    resolve_production_fg_cache_dir,
)

ROOT = Path(__file__).resolve().parents[1]


def _safe_target(
    bench_root: Path,
    target: Path,
    tool: Path,
    primary: Path,
) -> preflight._SafeWorktreeTarget:
    return preflight._SafeWorktreeTarget(
        bench_root=bench_root.resolve(),
        target_root=target.resolve(),
        tool_root=tool.resolve(),
        common_dir=(primary / ".git").resolve(),
        primary_root=primary.resolve(),
    )


def test_issue116_preflight_parses_primary_worktree_before_linked_worktrees() -> None:
    output = """worktree C:/repo/primary
HEAD aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
branch refs/heads/main

worktree C:/mfbench/issue116-a0
HEAD bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
branch refs/heads/codex/issue-116-a0-investigation
"""
    assert _primary_worktree_from_porcelain(output) == Path("C:/repo/primary")


def test_issue116_preflight_uses_git_primary_worktree_for_production_cache() -> None:
    primary = resolve_primary_worktree_root(ROOT)
    production = resolve_production_fg_cache_dir(ROOT)
    assert production == (primary / "bin" / "fg_response_frontier_cache").resolve()
    if primary != ROOT.resolve():
        assert production != (ROOT / "bin" / "fg_response_frontier_cache").resolve()


def test_issue116_preflight_git_state_includes_every_untracked_file(tmp_path, monkeypatch) -> None:
    worktree = (tmp_path / "mfbench" / "issue116-main").resolve()
    calls = []

    def _fake_git_stdout(root, *args):
        calls.append((root, args))
        return "a" * 40 if args == ("rev-parse", "HEAD") else ""

    monkeypatch.setattr(preflight, "_git_stdout", _fake_git_stdout)

    assert preflight._git_state(worktree) == ("a" * 40, "")
    assert calls == [
        (worktree, ("rev-parse", "HEAD")),
        (worktree, ("status", "--porcelain", "--untracked-files=all")),
        (worktree, ("rev-parse", "HEAD")),
    ]


def test_issue116_preflight_git_state_rejects_head_change_during_status(
    tmp_path, monkeypatch
) -> None:
    worktree = (tmp_path / "mfbench" / "issue116-main").resolve()
    replies = iter(("a" * 40, "", "b" * 40))
    monkeypatch.setattr(preflight, "_git_stdout", lambda root, *args: next(replies))

    with pytest.raises(ValueError, match="HEAD changed while reading status"):
        preflight._git_state(worktree)


def test_issue116_fixed_bench_root_accepts_only_literal_normal_directory(tmp_path) -> None:
    bench_root = (tmp_path / "mfbench").resolve()
    bench_root.mkdir()

    assert preflight.FIXED_BENCH_ROOT == Path(r"C:\mfbench")
    assert preflight._validate_bench_root(bench_root) == bench_root


def test_issue116_fixed_bench_root_must_already_exist(tmp_path) -> None:
    with pytest.raises(ValueError, match="fixed benchmark root does not exist"):
        preflight._validate_bench_root(tmp_path / "missing-mfbench")


def test_issue116_fixed_bench_root_rejects_non_directory(tmp_path) -> None:
    not_directory = tmp_path / "mfbench-file"
    not_directory.write_text("not a directory", encoding="utf-8")

    with pytest.raises(ValueError, match="not a normal directory"):
        preflight._validate_bench_root(not_directory)


def test_issue116_fixed_bench_root_rejects_symlink(tmp_path, monkeypatch) -> None:
    real_root = tmp_path / "real-mfbench"
    bench_root = tmp_path / "mfbench-link"
    real_root.mkdir()
    try:
        bench_root.symlink_to(real_root, target_is_directory=True)
    except OSError:
        # Windows may deny symlink creation without Developer Mode. Exercise the same lstat branch.
        bench_root = real_root
        monkeypatch.setattr(preflight, "_path_is_symlink", lambda metadata: True)

    with pytest.raises(ValueError, match="must not be a symlink"):
        preflight._validate_bench_root(bench_root)


def test_issue116_fixed_bench_root_rejects_junction_or_reparse(tmp_path, monkeypatch) -> None:
    bench_root = (tmp_path / "mfbench").resolve()
    bench_root.mkdir()
    monkeypatch.setattr(
        preflight,
        "_path_file_attributes",
        lambda metadata: preflight.WINDOWS_REPARSE_ATTRIBUTE,
    )

    with pytest.raises(ValueError, match="junction or reparse point"):
        preflight._validate_bench_root(bench_root)


def test_issue116_fixed_bench_root_rejects_canonical_relocation(tmp_path, monkeypatch) -> None:
    bench_root = (tmp_path / "mfbench").resolve()
    relocated = (tmp_path / "relocated").resolve()
    bench_root.mkdir()
    relocated.mkdir()
    monkeypatch.setattr(preflight, "_canonical_path", lambda path: relocated)

    with pytest.raises(ValueError, match="canonical path differs"):
        preflight._validate_bench_root(bench_root)


@pytest.mark.parametrize(
    "variable",
    (
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_NAMESPACE",
        "GIT_CEILING_DIRECTORIES",
        "GIT_DISCOVERY_ACROSS_FILESYSTEM",
        "GIT_CONFIG_COUNT",
        "GIT_CONFIG_KEY_0",
        "GIT_CONFIG_PARAMETERS",
    ),
)
def test_issue116_git_commands_reject_identity_environment_before_subprocess(
    tmp_path, monkeypatch, variable
) -> None:
    subprocess_calls = []
    monkeypatch.setenv(variable, "unsafe")
    monkeypatch.setattr(
        preflight.subprocess,
        "run",
        lambda *args, **kwargs: subprocess_calls.append((args, kwargs)),
    )

    with pytest.raises(ValueError, match=variable):
        preflight._git_stdout(tmp_path, "status")
    assert subprocess_calls == []


def test_issue116_git_stdout_does_not_accept_caller_environment(tmp_path) -> None:
    with pytest.raises(TypeError):
        preflight._git_stdout(tmp_path, "status", env={})


def test_issue116_safe_resolver_owns_bench_and_production_roots(tmp_path, monkeypatch) -> None:
    bench_root = tmp_path / "mfbench"
    worktree = bench_root / "issue116-main"
    run_root = bench_root / "issue116-a0-run-safe"
    production = tmp_path / "primary" / "bin" / "fg_response_frontier_cache"
    primary = production.parent.parent.resolve()
    target_calls = []

    def _fake_safe_target(root):
        target_calls.append(root)
        return _safe_target(bench_root, worktree, worktree, primary)

    monkeypatch.setattr(preflight, "_resolve_safe_worktree_target", _fake_safe_target)

    paths = preflight.resolve_issue116_run_paths(
        run_root,
        artifacts_dir=run_root / "custom-artifacts",
    )

    assert target_calls == [None]
    assert paths.bench_root == bench_root.resolve()
    assert paths.worktree_root == worktree.resolve()
    assert paths.preflight_tool_root == worktree.resolve()
    assert paths.git_common_dir == (primary / ".git").resolve()
    assert paths.primary_worktree_root == primary
    assert paths.run_root == run_root.resolve()
    assert paths.production_fg_cache_dir == production.resolve()
    assert paths.artifacts_dir == (run_root / "custom-artifacts").resolve()
    with pytest.raises(TypeError):
        preflight.resolve_issue116_run_paths(run_root, bench_root=tmp_path)
    with pytest.raises(TypeError):
        preflight.resolve_issue116_run_paths(
            run_root,
            production_fg_cache_dir=run_root / "fake-production",
        )


def test_issue116_safe_prepare_always_reads_its_worktree_git_state(tmp_path, monkeypatch) -> None:
    bench_root = tmp_path / "mfbench"
    bench_root.mkdir()
    worktree = bench_root / "issue116-main"
    run_root = bench_root / "issue116-a0-run-safe-prepare"
    production = tmp_path / "primary" / "bin" / "fg_response_frontier_cache"
    primary = production.parent.parent.resolve()
    monkeypatch.setattr(
        preflight,
        "_resolve_safe_worktree_target",
        lambda root: _safe_target(bench_root, worktree, worktree, primary),
    )
    paths = preflight.resolve_issue116_run_paths(run_root)
    git_calls = []

    def _fake_git_state(root):
        git_calls.append(root)
        return "a" * 40, ""

    monkeypatch.setattr(preflight, "_git_state", _fake_git_state)

    payload = preflight.prepare_issue116_run(paths)

    assert git_calls == [worktree.resolve(), worktree.resolve()]
    assert payload["git_head"] == "a" * 40
    assert payload["target_worktree"] == {
        "root": str(worktree.resolve()),
        "git_head": "a" * 40,
    }
    assert payload["preflight_tool"] == {
        "root": str(worktree.resolve()),
        "git_head": "a" * 40,
    }
    with pytest.raises(TypeError):
        preflight.prepare_issue116_run(paths, git_state=("b" * 40, ""))


def test_issue116_safe_prepare_rejects_forged_paths_before_git_or_creation(
    tmp_path, monkeypatch
) -> None:
    bench_root = tmp_path / "mfbench"
    bench_root.mkdir()
    worktree = (bench_root / "issue116-main").resolve()
    run_root = (bench_root / "issue116-forged-run").resolve()
    production = (
        tmp_path / "primary" / "bin" / "fg_response_frontier_cache"
    ).resolve()
    primary = production.parent.parent.resolve()
    def _fake_safe_target(root):
        target = worktree if root is None else Path(root).resolve()
        if target != worktree:
            raise ValueError("unregistered target")
        return _safe_target(bench_root, worktree, worktree, primary)

    monkeypatch.setattr(preflight, "_resolve_safe_worktree_target", _fake_safe_target)
    safe_paths = preflight.resolve_issue116_run_paths(run_root)
    git_calls = []
    monkeypatch.setattr(preflight, "_git_state", lambda root: git_calls.append(root))

    forged_paths = (
        replace(safe_paths, bench_root=(tmp_path / "alternate-bench").resolve()),
        replace(safe_paths, fg_response_cache_dir=production),
        replace(safe_paths, fg_response_cache_dir=(bench_root / "alternate-cache").resolve()),
        replace(safe_paths, worktree_root=(bench_root / "alternate-worktree").resolve()),
        replace(safe_paths, preflight_tool_root=(bench_root / "alternate-tool").resolve()),
        replace(safe_paths, git_common_dir=(tmp_path / "alternate-common").resolve()),
        replace(safe_paths, primary_worktree_root=(tmp_path / "alternate-primary").resolve()),
        replace(
            safe_paths,
            production_fg_cache_dir=(tmp_path / "alternate-production-cache").resolve(),
        ),
    )
    for forged in forged_paths:
        with pytest.raises(ValueError):
            preflight.prepare_issue116_run(forged)
        assert not run_root.exists()

    assert git_calls == []


def test_issue116_safe_target_accepts_registered_same_repo_sibling(
    tmp_path, monkeypatch
) -> None:
    bench_root = tmp_path / "mfbench"
    target = (bench_root / "issue116-parent").resolve()
    tool = (bench_root / "issue116-candidate").resolve()
    primary = (tmp_path / "primary").resolve()
    common = (primary / ".git").resolve()
    for directory in (target, tool, common):
        directory.mkdir(parents=True)
    registered = (primary, tool, target)
    contexts = {
        tool: preflight._GitWorktreeContext(tool, common, primary, registered),
        target: preflight._GitWorktreeContext(target, common, primary, registered),
    }
    monkeypatch.setattr(preflight, "REPO_ROOT", tool)
    monkeypatch.setattr(preflight, "_validated_fixed_bench_root", lambda: bench_root.resolve())
    monkeypatch.setattr(
        preflight,
        "_git_worktree_context",
        lambda root: contexts[Path(root).resolve()],
    )

    assert preflight._resolve_safe_worktree_target(target) == _safe_target(
        bench_root, target, tool, primary
    )


def test_issue116_safe_target_defaults_to_same_short_tool_worktree(
    tmp_path, monkeypatch
) -> None:
    bench_root = tmp_path / "mfbench"
    tool = (bench_root / "issue116-candidate").resolve()
    primary = (tmp_path / "primary").resolve()
    common = (primary / ".git").resolve()
    for directory in (tool, common):
        directory.mkdir(parents=True)
    context = preflight._GitWorktreeContext(tool, common, primary, (primary, tool))
    monkeypatch.setattr(preflight, "REPO_ROOT", tool)
    monkeypatch.setattr(preflight, "_validated_fixed_bench_root", lambda: bench_root.resolve())
    monkeypatch.setattr(preflight, "_git_worktree_context", lambda root: context)

    assert preflight._resolve_safe_worktree_target(None) == _safe_target(
        bench_root, tool, tool, primary
    )


def test_issue116_safe_target_rejects_different_repository(tmp_path, monkeypatch) -> None:
    bench_root = tmp_path / "mfbench"
    target = (bench_root / "issue116-other-repo").resolve()
    tool = (bench_root / "issue116-candidate").resolve()
    primary = (tmp_path / "primary").resolve()
    other_primary = (tmp_path / "other-primary").resolve()
    common = (primary / ".git").resolve()
    other_common = (other_primary / ".git").resolve()
    for directory in (target, tool, common, other_common):
        directory.mkdir(parents=True)
    contexts = {
        tool: preflight._GitWorktreeContext(tool, common, primary, (primary, tool, target)),
        target: preflight._GitWorktreeContext(
            target,
            other_common,
            other_primary,
            (other_primary, target, tool),
        ),
    }
    monkeypatch.setattr(preflight, "REPO_ROOT", tool)
    monkeypatch.setattr(preflight, "_validated_fixed_bench_root", lambda: bench_root.resolve())
    monkeypatch.setattr(
        preflight,
        "_git_worktree_context",
        lambda root: contexts[Path(root).resolve()],
    )

    with pytest.raises(ValueError, match="share one Git common dir"):
        preflight._resolve_safe_worktree_target(target)


def test_issue116_safe_target_rejects_fake_git_directory(tmp_path, monkeypatch) -> None:
    bench_root = tmp_path / "mfbench"
    fake = (bench_root / "fake-worktree").resolve()
    tool = (bench_root / "issue116-candidate").resolve()
    primary = (tmp_path / "primary").resolve()
    common = (primary / ".git").resolve()
    for directory in (fake, tool, common):
        directory.mkdir(parents=True)

    def _fail_git(root, *args):
        resolved_root = Path(root).resolve()
        if resolved_root == fake:
            raise preflight.subprocess.CalledProcessError(128, ["git", *args])
        if args[-1] == "--show-toplevel":
            return str(tool)
        if args[-1] == "--git-common-dir":
            return str(common)
        if args == ("worktree", "list", "--porcelain"):
            return f"worktree {primary}\n\nworktree {tool}\n"
        raise AssertionError(args)

    monkeypatch.setattr(preflight, "REPO_ROOT", tool)
    monkeypatch.setattr(preflight, "_validated_fixed_bench_root", lambda: bench_root.resolve())
    monkeypatch.setattr(preflight, "_git_stdout", _fail_git)

    with pytest.raises(ValueError, match="not an existing Git worktree"):
        preflight._resolve_safe_worktree_target(fake)


def test_issue116_git_context_rejects_unregistered_worktree(tmp_path, monkeypatch) -> None:
    target = (tmp_path / "unregistered").resolve()
    primary = (tmp_path / "primary").resolve()
    target.mkdir()
    (primary / ".git").mkdir(parents=True)

    def _fake_git(root, *args):
        if args[-1] == "--show-toplevel":
            return str(target)
        if args[-1] == "--git-common-dir":
            return str(primary / ".git")
        if args == ("worktree", "list", "--porcelain"):
            return f"worktree {primary}\nHEAD {'a' * 40}\n"
        raise AssertionError(args)

    monkeypatch.setattr(preflight, "_git_stdout", _fake_git)

    with pytest.raises(ValueError, match="not a registered Git worktree"):
        preflight._git_worktree_context(target)


def test_issue116_safe_target_rejects_deep_target(tmp_path, monkeypatch) -> None:
    bench_root = tmp_path / "mfbench"
    tool = bench_root / "issue116-candidate"
    deep_target = bench_root / "nested" / "issue116-parent"
    deep_target.mkdir(parents=True)
    tool.mkdir()
    monkeypatch.setattr(preflight, "REPO_ROOT", tool)
    monkeypatch.setattr(preflight, "_validated_fixed_bench_root", lambda: bench_root.resolve())

    with pytest.raises(ValueError, match="target worktree must be a direct child"):
        preflight._resolve_safe_worktree_target(deep_target)


def test_issue116_safe_target_rejects_deep_or_outside_tool(tmp_path, monkeypatch) -> None:
    bench_root = tmp_path / "mfbench"
    target = bench_root / "issue116-parent"
    target.mkdir(parents=True)
    monkeypatch.setattr(preflight, "_validated_fixed_bench_root", lambda: bench_root.resolve())

    invalid_tools = (
        bench_root / "nested" / "issue116-candidate",
        tmp_path / "outside-candidate",
    )
    for tool in invalid_tools:
        tool.mkdir(parents=True)
        monkeypatch.setattr(preflight, "REPO_ROOT", tool)
        with pytest.raises(ValueError, match="tool worktree must be a direct child"):
            preflight._resolve_safe_worktree_target(target)


def test_issue116_safe_prepare_pins_sibling_target_and_tool_heads(
    tmp_path, monkeypatch
) -> None:
    bench_root = tmp_path / "mfbench"
    bench_root.mkdir()
    target = (bench_root / "issue116-parent").resolve()
    tool = (bench_root / "issue116-candidate").resolve()
    primary = (tmp_path / "primary").resolve()
    common = (primary / ".git").resolve()
    run_root = (bench_root / "issue116-parent-run").resolve()
    safe_target = _safe_target(bench_root, target, tool, primary)
    monkeypatch.setattr(preflight, "_resolve_safe_worktree_target", lambda root: safe_target)
    paths = preflight.resolve_issue116_run_paths(run_root, worktree_root=target)
    git_calls = []

    def _fake_git_state(root):
        git_calls.append(root)
        if root == target:
            return "a" * 40, ""
        if root == tool:
            return "b" * 40, ""
        raise AssertionError(root)

    monkeypatch.setattr(preflight, "_git_state", _fake_git_state)

    payload = preflight.prepare_issue116_run(paths)

    assert git_calls == [target, tool, target, tool]
    assert payload["git_head"] == "a" * 40
    assert payload["target_worktree"] == {"root": str(target), "git_head": "a" * 40}
    assert payload["preflight_tool"] == {"root": str(tool), "git_head": "b" * 40}


@pytest.mark.parametrize(
    ("changed_root", "message"),
    (
        ("target", "target Git state changed"),
        ("tool", "preflight tool Git state changed"),
    ),
)
def test_issue116_safe_prepare_rejects_state_change_before_manifest_publication(
    tmp_path, monkeypatch, changed_root, message
) -> None:
    bench_root = tmp_path / "mfbench"
    bench_root.mkdir()
    target = (bench_root / "issue116-parent").resolve()
    tool = (bench_root / "issue116-candidate").resolve()
    primary = (tmp_path / "primary").resolve()
    run_root = (bench_root / f"issue116-race-{changed_root}").resolve()
    safe_target = _safe_target(bench_root, target, tool, primary)
    monkeypatch.setattr(preflight, "_resolve_safe_worktree_target", lambda root: safe_target)
    paths = preflight.resolve_issue116_run_paths(run_root, worktree_root=target)
    reads = {target: 0, tool: 0}

    def _racing_git_state(root):
        reads[root] += 1
        initial = "a" * 40 if root == target else "b" * 40
        if reads[root] == 2 and root == (target if changed_root == "target" else tool):
            return "c" * 40, ""
        return initial, ""

    monkeypatch.setattr(preflight, "_git_state", _racing_git_state)

    with pytest.raises(ValueError, match=message):
        preflight.prepare_issue116_run(paths)
    assert run_root.is_dir()
    assert not paths.preflight_manifest_path.exists()


def test_issue116_preflight_cli_accepts_safe_sibling_target() -> None:
    args = preflight._parser().parse_args(
        [
            "--run-root",
            r"C:\mfbench\issue116-parent-run",
            "--worktree-root",
            r"C:\mfbench\issue116-parent",
        ]
    )

    assert args.worktree_root == r"C:\mfbench\issue116-parent"


def test_issue116_preflight_derives_all_related_paths_under_one_run_root(tmp_path) -> None:
    bench_root = tmp_path / "mfbench"
    run_root = bench_root / "issue116-a0-run-001"
    production = tmp_path / "primary" / "bin" / "fg_response_frontier_cache"

    paths = _resolve_issue116_run_paths(
        run_root,
        worktree_root=bench_root / "issue116-main",
        bench_root=bench_root,
        production_fg_cache_dir=production,
    )

    assert paths.bench_root == bench_root.resolve()
    assert paths.worktree_root == (bench_root / "issue116-main").resolve()
    assert paths.run_root == run_root.resolve()
    assert paths.fg_response_cache_dir == (run_root / "fg_response_frontier_cache").resolve()
    assert paths.timeline_cache_dir == (run_root / "timeline_frontier_cache").resolve()
    assert paths.optimizer_bin_dir == (run_root / "optimizer_bin").resolve()
    assert paths.database_path == (run_root / "evolution.db").resolve()
    assert paths.profile_events_path == (run_root / "profile_events.jsonl").resolve()
    assert paths.artifacts_dir == (run_root / "artifacts").resolve()
    assert paths.preflight_manifest_path == (run_root / "preflight.json").resolve()
    assert paths.environment() == {
        "FG_RESPONSE_FRONTIER_CACHE_DIR": str(paths.fg_response_cache_dir),
        "TIMELINE_FRONTIER_CACHE_DIR": str(paths.timeline_cache_dir),
        "ROBEATSMETA_OPTIMIZER_BIN_DIR": str(paths.optimizer_bin_dir),
        "EVOLUTION_DB_PATH": str(paths.database_path),
        "METAFINDER_PROFILE_EVENTS_PATH": str(paths.profile_events_path),
    }


@pytest.mark.parametrize("suffix", ((), ("nested",)))
def test_issue116_preflight_rejects_production_fg_cache_and_descendants(
    tmp_path, suffix
) -> None:
    bench_root = tmp_path / "mfbench"
    run_root = bench_root / "issue116-a0-run-002"
    production = tmp_path / "primary" / "bin" / "fg_response_frontier_cache"
    candidate = production.joinpath(*suffix)

    with pytest.raises(ValueError, match="production cache"):
        _resolve_issue116_run_paths(
            run_root,
            worktree_root=bench_root / "issue116-main",
            bench_root=bench_root,
            production_fg_cache_dir=production,
            fg_response_cache_dir=candidate,
        )


@pytest.mark.parametrize(
    "override",
    (
        "fg_response_cache_dir",
        "timeline_cache_dir",
        "database_path",
        "profile_events_path",
        "artifacts_dir",
    ),
)
def test_issue116_preflight_rejects_any_related_path_outside_run_root(
    tmp_path, override
) -> None:
    bench_root = tmp_path / "mfbench"
    run_root = bench_root / "issue116-a0-run-003"
    production = tmp_path / "primary" / "bin" / "fg_response_frontier_cache"
    kwargs = {override: run_root / ".." / f"escaped-{override}"}

    with pytest.raises(ValueError, match="escapes its run root"):
        _resolve_issue116_run_paths(
            run_root,
            worktree_root=bench_root / "issue116-main",
            bench_root=bench_root,
            production_fg_cache_dir=production,
            **kwargs,
        )


def test_issue116_preflight_rejects_unnamed_or_external_run_root(tmp_path) -> None:
    bench_root = tmp_path / "mfbench"
    production = tmp_path / "primary" / "bin" / "fg_response_frontier_cache"
    invalid_roots = (
        bench_root,
        bench_root / "nested" / "issue116-a0",
        tmp_path / "elsewhere" / "issue116-a0",
    )
    for invalid_root in invalid_roots:
        with pytest.raises(ValueError, match="direct named child"):
            _resolve_issue116_run_paths(
                invalid_root,
                worktree_root=bench_root / "issue116-main",
                bench_root=bench_root,
                production_fg_cache_dir=production,
            )


def test_issue116_preflight_rejects_colliding_related_paths(tmp_path) -> None:
    bench_root = tmp_path / "mfbench"
    run_root = bench_root / "issue116-a0-run-004"
    production = tmp_path / "primary" / "bin" / "fg_response_frontier_cache"
    collision = run_root / "same"

    with pytest.raises(ValueError, match="paths overlap"):
        _resolve_issue116_run_paths(
            run_root,
            worktree_root=bench_root / "issue116-main",
            bench_root=bench_root,
            production_fg_cache_dir=production,
            database_path=collision,
            profile_events_path=collision,
        )


def test_issue116_preflight_rejects_nested_related_paths(tmp_path) -> None:
    bench_root = tmp_path / "mfbench"
    run_root = bench_root / "issue116-a0-run-005"
    production = tmp_path / "primary" / "bin" / "fg_response_frontier_cache"

    with pytest.raises(ValueError, match="paths overlap"):
        _resolve_issue116_run_paths(
            run_root,
            worktree_root=bench_root / "issue116-main",
            bench_root=bench_root,
            production_fg_cache_dir=production,
            database_path=run_root / "artifacts" / "nested.db",
        )


@pytest.mark.parametrize(
    "override",
    (
        "fg_response_cache_dir",
        "timeline_cache_dir",
        "database_path",
        "profile_events_path",
        "artifacts_dir",
    ),
)
@pytest.mark.parametrize("relation", ("equal", "nested", "contains"))
def test_issue116_preflight_reserves_manifest_against_every_custom_path(
    tmp_path, override, relation
) -> None:
    bench_root = tmp_path / "mfbench"
    run_root = bench_root / "issue116-a0-run-manifest"
    manifest = run_root / "preflight.json"
    production = tmp_path / "primary" / "bin" / "fg_response_frontier_cache"
    candidate = {
        "equal": manifest,
        "nested": manifest / "nested",
        "contains": run_root,
    }[relation]

    with pytest.raises(ValueError, match="paths overlap"):
        _resolve_issue116_run_paths(
            run_root,
            worktree_root=bench_root / "issue116-main",
            bench_root=bench_root,
            production_fg_cache_dir=production,
            **{override: candidate},
        )


def test_issue116_preflight_requires_separate_direct_bench_worktree(tmp_path) -> None:
    bench_root = tmp_path / "mfbench"
    run_root = bench_root / "issue116-a0-run-worktree"
    production = tmp_path / "primary" / "bin" / "fg_response_frontier_cache"
    invalid = (
        bench_root / "nested" / "issue116-main",
        tmp_path / "elsewhere" / "issue116-main",
    )
    for worktree_root in invalid:
        with pytest.raises(ValueError, match="target worktree must be a direct child"):
            _resolve_issue116_run_paths(
                run_root,
                worktree_root=worktree_root,
                bench_root=bench_root,
                production_fg_cache_dir=production,
            )
    with pytest.raises(ValueError, match="target worktree and run root must be distinct"):
        _resolve_issue116_run_paths(
            run_root,
            worktree_root=run_root,
            bench_root=bench_root,
            production_fg_cache_dir=production,
        )
    with pytest.raises(ValueError, match="tool worktree and run root must be distinct"):
        _resolve_issue116_run_paths(
            run_root,
            worktree_root=bench_root / "issue116-parent",
            preflight_tool_root=run_root,
            bench_root=bench_root,
            production_fg_cache_dir=production,
        )


def test_issue116_preflight_prepares_fresh_run_and_records_clean_head(tmp_path) -> None:
    bench_root = tmp_path / "mfbench"
    bench_root.mkdir()
    run_root = bench_root / "issue116-a0-run-006"
    production = tmp_path / "primary" / "bin" / "fg_response_frontier_cache"
    paths = _resolve_issue116_run_paths(
        run_root,
        worktree_root=bench_root / "issue116-main",
        bench_root=bench_root,
        production_fg_cache_dir=production,
    )
    head = "a" * 40

    payload = _prepare_issue116_run(
        paths,
        git_state=(head, ""),
        publication_state_reader=lambda root: (head, ""),
    )

    assert payload["git_head"] == head
    assert payload["paths"]["worktree_root"] == str(paths.worktree_root)
    assert payload["paths"]["run_root"] == str(run_root.resolve())
    assert payload["paths"]["artifacts_dir"] == str(paths.artifacts_dir)
    assert payload["paths"]["preflight_manifest_path"] == str(paths.preflight_manifest_path)
    assert payload["environment"] == paths.environment()
    assert paths.fg_response_cache_dir.is_dir()
    assert paths.timeline_cache_dir.is_dir()
    assert paths.optimizer_bin_dir.is_dir()
    assert paths.artifacts_dir.is_dir()
    assert json.loads(paths.preflight_manifest_path.read_text(encoding="utf-8")) == payload


@pytest.mark.parametrize("status", (" M tracked.py", "?? untracked.py"))
def test_issue116_preflight_rejects_tracked_or_untracked_changes_before_creation(
    tmp_path, status
) -> None:
    bench_root = tmp_path / "mfbench"
    bench_root.mkdir()
    run_root = bench_root / "issue116-a0-run-007"
    production = tmp_path / "primary" / "bin" / "fg_response_frontier_cache"
    paths = _resolve_issue116_run_paths(
        run_root,
        worktree_root=bench_root / "issue116-main",
        bench_root=bench_root,
        production_fg_cache_dir=production,
    )

    with pytest.raises(ValueError, match="no tracked or untracked"):
        _prepare_issue116_run(
            paths,
            git_state=("b" * 40, status),
            publication_state_reader=lambda root: ("b" * 40, status),
        )
    assert not run_root.exists()


def test_issue116_prepare_revalidates_fixed_bench_before_creation(
    tmp_path, monkeypatch
) -> None:
    bench_root = tmp_path / "mfbench"
    bench_root.mkdir()
    run_root = bench_root / "issue116-bench-revalidation"
    production = tmp_path / "primary" / "bin" / "fg_response_frontier_cache"
    paths = _resolve_issue116_run_paths(
        run_root,
        worktree_root=bench_root / "issue116-main",
        bench_root=bench_root,
        production_fg_cache_dir=production,
    )
    monkeypatch.setattr(
        preflight,
        "_path_file_attributes",
        lambda metadata: preflight.WINDOWS_REPARSE_ATTRIBUTE,
    )

    with pytest.raises(ValueError, match="junction or reparse point"):
        _prepare_issue116_run(
            paths,
            git_state=("b" * 40, ""),
            publication_state_reader=lambda root: ("b" * 40, ""),
        )
    assert not run_root.exists()


def test_issue116_sibling_preflight_rejects_dirty_tool_before_creation(tmp_path) -> None:
    bench_root = tmp_path / "mfbench"
    bench_root.mkdir()
    run_root = bench_root / "issue116-sibling-dirty-tool"
    production = tmp_path / "primary" / "bin" / "fg_response_frontier_cache"
    paths = _resolve_issue116_run_paths(
        run_root,
        worktree_root=bench_root / "issue116-parent",
        preflight_tool_root=bench_root / "issue116-candidate",
        bench_root=bench_root,
        production_fg_cache_dir=production,
    )

    with pytest.raises(ValueError, match="preflight tool worktree requires no tracked or untracked"):
        _prepare_issue116_run(
            paths,
            git_state=("b" * 40, ""),
            preflight_tool_git_state=("c" * 40, "?? changed-tool.py"),
            publication_state_reader=lambda root: ("b" * 40, ""),
        )
    assert not run_root.exists()


def test_issue116_preflight_rejects_abbreviated_or_non_hex_head(tmp_path) -> None:
    bench_root = tmp_path / "mfbench"
    bench_root.mkdir()
    run_root = bench_root / "issue116-a0-run-head"
    production = tmp_path / "primary" / "bin" / "fg_response_frontier_cache"
    paths = _resolve_issue116_run_paths(
        run_root,
        worktree_root=bench_root / "issue116-main",
        bench_root=bench_root,
        production_fg_cache_dir=production,
    )
    for invalid_head in ("abc123", "d" * 41, "g" * 40):
        with pytest.raises(ValueError, match="full exact Git HEAD"):
            _prepare_issue116_run(
                paths,
                git_state=(invalid_head, ""),
                publication_state_reader=lambda root: (invalid_head, ""),
            )
    assert not run_root.exists()


def test_issue116_preflight_atomically_rejects_existing_run_root(tmp_path) -> None:
    bench_root = tmp_path / "mfbench"
    run_root = bench_root / "issue116-a0-run-008"
    run_root.mkdir(parents=True)
    marker = run_root / "owner.txt"
    marker.write_text("existing", encoding="utf-8")
    production = tmp_path / "primary" / "bin" / "fg_response_frontier_cache"
    paths = _resolve_issue116_run_paths(
        run_root,
        worktree_root=bench_root / "issue116-main",
        bench_root=bench_root,
        production_fg_cache_dir=production,
    )

    with pytest.raises(ValueError, match="already exists"):
        _prepare_issue116_run(
            paths,
            git_state=("c" * 40, ""),
            publication_state_reader=lambda root: ("c" * 40, ""),
        )
    assert marker.read_text(encoding="utf-8") == "existing"
    assert not (run_root / "preflight.json").exists()
