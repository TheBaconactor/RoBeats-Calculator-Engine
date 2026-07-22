from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import tarfile
import threading
import time
from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import Callable, Iterable

from gear_optimizer.core.constants import PATHS
from gear_optimizer.core.parsing import env_int, env_str
from gear_optimizer.data.exported_game_data_sync import ExportedGameDataPaths, sync_exported_game_data

logger = logging.getLogger(__name__)

_PROTOCOL = 2
_REVISION_RE = re.compile(r"[0-9a-f]{64}\Z")
_BUNDLE_RE = re.compile(r"[a-z0-9][a-z0-9.-]{0,80}\.tar\.gz\Z")
_GIT_NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,127}\Z")


def publication_root() -> Path:
    configured = env_str("ROBEATSMETA_FRONTIER_PUBLICATION_DIR", "")
    return Path(configured).expanduser() if configured else Path(PATHS.bin_path("frontier_publications"))


def source_snapshot_root() -> Path:
    configured = env_str("ROBEATSMETA_FRONTIER_SOURCE_DIR", "")
    return Path(configured).expanduser() if configured else Path(PATHS.bin_path("frontier_server_sources"))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{time.time_ns()}.tmp")
    try:
        temporary.write_text(json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _safe_relative(path: Path, root: Path) -> str:
    relative = path.relative_to(root).as_posix()
    parsed = PurePosixPath(relative)
    if not relative or parsed.is_absolute() or ".." in parsed.parts:
        raise ValueError(f"unsafe publication path: {relative!r}")
    return relative


def _iter_scope_files(
    scope: str,
    root: Path,
    allowlist: set[str] | None = None,
) -> Iterable[tuple[str, Path]]:
    if not root.is_dir():
        raise FileNotFoundError(f"frontier publication source is missing: {root}")
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        if not path.is_file() or path.is_symlink():
            continue
        relative = _safe_relative(path, root)
        if scope == "code" and (relative == "config.ini" or relative.startswith("Data/")):
            continue
        if scope in {"timeline", "fg"} and path.suffix not in {".npz", ".npy"}:
            continue
        if allowlist is not None and relative not in allowlist:
            continue
        yield relative, path


def _bundle_name(scope: str, relative: str) -> str:
    if scope == "data":
        first = PurePosixPath(relative).parts[0] if PurePosixPath(relative).parts else "root"
        group = re.sub(r"[^a-z0-9]+", "-", first.lower()).strip("-") or "root"
        return f"data-{group}.tar.gz"
    if scope == "code":
        return f"code-{hashlib.sha256(relative.encode('utf-8')).hexdigest()[:1]}.tar.gz"
    prefix = Path(relative).name[:2].lower()
    if re.fullmatch(r"[0-9a-f]{2}", prefix) is None:
        prefix = hashlib.sha256(relative.encode("utf-8")).hexdigest()[:2]
    return f"{scope}-{prefix}.tar.gz"


def _previous_file_hashes(manifest: dict | None) -> dict[tuple[str, str, int, int], str]:
    hashes: dict[tuple[str, str, int, int], str] = {}
    if not isinstance(manifest, dict):
        return hashes
    for bundle in manifest.get("bundles", []):
        if not isinstance(bundle, dict):
            continue
        for entry in bundle.get("files", []):
            if not isinstance(entry, dict):
                continue
            try:
                key = (
                    str(entry["scope"]),
                    str(entry["path"]),
                    int(entry["size"]),
                    int(entry.get("source_mtime_ns", -1)),
                )
                digest = str(entry["sha256"])
            except (KeyError, TypeError, ValueError):
                continue
            if re.fullmatch(r"[0-9a-f]{64}", digest):
                hashes[key] = digest
    return hashes


def _read_manifest(path: Path) -> dict | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _write_bundle(path: Path, files: list[tuple[dict, Path]]) -> None:
    with tarfile.open(path, "w:gz", compresslevel=6) as archive:
        for entry, source in files:
            info = archive.gettarinfo(str(source), arcname=f"{entry['scope']}/{entry['path']}")
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            info.mtime = 0
            with source.open("rb") as handle:
                archive.addfile(info, handle)


def build_publication(
    *,
    code_root: str | Path,
    data_root: str | Path,
    data_revision: str,
    code_revision: str,
    timeline_cache_root: str | Path,
    fg_cache_root: str | Path,
    root: str | Path | None = None,
    cache_allowlist: dict[str, set[str]] | None = None,
) -> Path:
    publications = Path(root) if root is not None else publication_root()
    publications.mkdir(parents=True, exist_ok=True)
    current_payload = _read_manifest(publications / "current.json") or {}
    previous_revision = str(current_payload.get("revision") or "")
    previous_root = publications / previous_revision if _REVISION_RE.fullmatch(previous_revision) else None
    previous_manifest = _read_manifest(previous_root / "manifest.json") if previous_root is not None else None
    prior_hashes = _previous_file_hashes(previous_manifest)

    sources = {
        "code": Path(code_root),
        "data": Path(data_root),
        "timeline": Path(timeline_cache_root),
        "fg": Path(fg_cache_root),
    }
    grouped: dict[str, list[tuple[dict, Path]]] = defaultdict(list)
    for scope, source_root in sources.items():
        allowed = (cache_allowlist or {}).get(scope) if scope in {"timeline", "fg"} else None
        for relative, source in _iter_scope_files(scope, source_root, allowed):
            file_stat = source.stat()
            size = int(file_stat.st_size)
            mtime_ns = int(file_stat.st_mtime_ns)
            digest = prior_hashes.get((scope, relative, size, mtime_ns)) or _sha256_file(source)
            entry = {
                "scope": scope,
                "path": relative,
                "size": size,
                "sha256": digest,
                "source_mtime_ns": mtime_ns,
            }
            grouped[_bundle_name(scope, relative)].append((entry, source))

    bundle_specs: list[dict] = []
    for name, files in sorted(grouped.items()):
        content_entries = [
            {
                "scope": entry["scope"],
                "path": entry["path"],
                "size": entry["size"],
                "sha256": entry["sha256"],
            }
            for entry, _source in files
        ]
        content_digest = hashlib.sha256(
            json.dumps(content_entries, separators=(",", ":"), sort_keys=True).encode("utf-8")
        ).hexdigest()
        bundle_specs.append(
            {
                "name": name,
                "content_sha256": content_digest,
                "files": [entry for entry, _source in files],
                "_sources": files,
            }
        )
    revision = hashlib.sha256(
        json.dumps(
            {
                "protocol": _PROTOCOL,
                "data_revision": str(data_revision),
                "code_revision": str(code_revision),
                "bundles": [(item["name"], item["content_sha256"]) for item in bundle_specs],
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    final_root = publications / revision
    if final_root.is_dir():
        _atomic_json(publications / "current.json", {"schema": 1, "revision": revision})
        return final_root

    work = publications / f".{revision}.{os.getpid()}.{time.time_ns()}.tmp"
    bundles_root = work / "bundles"
    bundles_root.mkdir(parents=True)
    previous_by_content = {
        str(bundle.get("content_sha256")): str(bundle.get("name"))
        for bundle in (previous_manifest or {}).get("bundles", [])
        if isinstance(bundle, dict)
    }
    try:
        for bundle in bundle_specs:
            destination = bundles_root / str(bundle["name"])
            prior_name = previous_by_content.get(str(bundle["content_sha256"]))
            prior_path = previous_root / "bundles" / prior_name if previous_root is not None and prior_name else None
            if prior_path is not None and prior_path.is_file():
                os.link(prior_path, destination)
            else:
                _write_bundle(destination, bundle.pop("_sources"))
            bundle.pop("_sources", None)
            bundle["size"] = int(destination.stat().st_size)
            bundle["sha256"] = _sha256_file(destination)
        manifest = {
            "protocol": _PROTOCOL,
            "revision": revision,
            "data_revision": str(data_revision),
            "code_revision": str(code_revision),
            "generated_at": int(time.time()),
            "bundles": bundle_specs,
        }
        (work / "manifest.json").write_text(
            json.dumps(manifest, separators=(",", ":"), sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(work, final_root)
        _atomic_json(publications / "current.json", {"schema": 1, "revision": revision})
        return final_root
    finally:
        shutil.rmtree(work, ignore_errors=True)


class FrontierDistributionState:
    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root) if root is not None else publication_root()
        self._lock = threading.Lock()
        self._revision = ""
        self._manifest_cache: dict[str, tuple[bytes, dict[str, str]]] = {}
        self.reload()

    def _load_publication(self, revision: str) -> tuple[bytes, dict[str, str]] | None:
        try:
            body = (self.root / revision / "manifest.json").read_bytes()
            payload = json.loads(body)
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(payload, dict) or str(payload.get("revision") or "") != revision:
            return None
        bundles = {
            str(bundle.get("name")): str(bundle.get("sha256"))
            for bundle in payload.get("bundles", [])
            if isinstance(bundle, dict)
            and _BUNDLE_RE.fullmatch(str(bundle.get("name") or ""))
            and re.fullmatch(r"[0-9a-f]{64}", str(bundle.get("sha256") or ""))
        }
        return body, bundles

    def reload(self) -> None:
        current = _read_manifest(self.root / "current.json") or {}
        revision = str(current.get("revision") or "")
        loaded = self._load_publication(revision) if _REVISION_RE.fullmatch(revision) else None
        with self._lock:
            self._revision = revision if loaded is not None else ""
            if loaded is not None:
                self._manifest_cache[revision] = loaded

    def install(self, publication: Path) -> None:
        revision = publication.name
        if _REVISION_RE.fullmatch(revision) is None or publication.parent.resolve() != self.root.resolve():
            raise ValueError("invalid frontier publication")
        loaded = self._load_publication(revision)
        if loaded is None:
            raise ValueError("invalid frontier publication manifest")
        with self._lock:
            self._revision = revision
            self._manifest_cache[revision] = loaded

    def manifest_bytes(self) -> bytes | None:
        with self._lock:
            revision = self._revision
            cached = self._manifest_cache.get(revision)
        return cached[0] if cached is not None else None

    def bundle_info(self, revision: str, name: str) -> tuple[Path, str] | None:
        if _REVISION_RE.fullmatch(revision) is None or _BUNDLE_RE.fullmatch(name) is None:
            return None
        with self._lock:
            cached = self._manifest_cache.get(revision)
        if cached is None:
            loaded = self._load_publication(revision)
            if loaded is None:
                return None
            with self._lock:
                self._manifest_cache[revision] = loaded
            cached = loaded
        digest = cached[1].get(name)
        if digest is None:
            return None
        publication = self.root / revision
        path = publication / "bundles" / name
        return (path, digest) if path.is_file() else None


def _validated_git_name(value: str, *, label: str) -> str:
    cleaned = str(value or "").strip()
    if _GIT_NAME_RE.fullmatch(cleaned) is None or cleaned.startswith("-") or ".." in cleaned:
        raise ValueError(f"invalid frontier Git {label}")
    return cleaned


def _git(repo_root: Path, *args: str, timeout: int = 120) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=str(repo_root),
        check=True,
        capture_output=True,
        text=True,
        timeout=max(1, int(timeout)),
    )
    return result.stdout.strip()


def _install_server_checkout(repo_root: Path, commit: str) -> bool:
    current = _git(repo_root, "rev-parse", "--verify", "HEAD^{commit}")
    if current == commit:
        return False
    if _git(repo_root, "status", "--porcelain", "--untracked-files=no"):
        raise RuntimeError("refusing to update a MetaFinder server checkout with tracked local changes")
    ancestry = subprocess.run(
        ["git", "merge-base", "--is-ancestor", current, commit],
        cwd=str(repo_root),
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if ancestry.returncode != 0:
        raise RuntimeError("refusing a non-fast-forward MetaFinder server update")
    _git(repo_root, "merge", "--ff-only", commit, timeout=300)
    installed = _git(repo_root, "rev-parse", "--verify", "HEAD^{commit}")
    if installed != commit:
        raise RuntimeError("MetaFinder server update did not reach the fetched commit")
    return True


def _extract_repository_snapshot(repo_root: Path, commit: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    work = destination.with_name(f".{destination.name}.{os.getpid()}.{time.time_ns()}.tmp")
    archive_path = work.with_suffix(".tar")
    shutil.rmtree(work, ignore_errors=True)
    archive_path.unlink(missing_ok=True)
    try:
        with archive_path.open("xb") as output:
            subprocess.run(
                ["git", "archive", "--format=tar", commit],
                cwd=str(repo_root),
                check=True,
                stdout=output,
                timeout=300,
            )
        work.mkdir()
        with tarfile.open(archive_path, "r:") as archive:
            for member in archive:
                path = PurePosixPath(member.name)
                if path.is_absolute() or not path.parts or ".." in path.parts:
                    raise ValueError(f"unsafe path in Git archive: {member.name!r}")
                target = work.joinpath(*path.parts)
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                elif member.isfile():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    source = archive.extractfile(member)
                    if source is None:
                        raise ValueError(f"missing file body in Git Data archive: {member.name!r}")
                    with source, target.open("xb") as output:
                        shutil.copyfileobj(source, output, length=1024 * 1024)
                    os.chmod(target, int(member.mode) & 0o777)
                else:
                    raise ValueError(f"unsupported entry in Git archive: {member.name!r}")
        os.replace(work, destination)
    finally:
        archive_path.unlink(missing_ok=True)
        shutil.rmtree(work, ignore_errors=True)


class FrontierServerMaintainer:
    def __init__(
        self,
        *,
        repo_root: str | Path,
        timeline_cache_root: str | Path,
        fg_cache_root: str | Path,
        state: FrontierDistributionState,
        prebuild: Callable[[Path], dict[str, set[str]]],
        restart_requested: Callable[[str], None] | None = None,
        publication_ready: Callable[[Path], None] | None = None,
        prepare_code_update: Callable[[], None] | None = None,
        code_update_aborted: Callable[[], None] | None = None,
    ) -> None:
        self.repo_root = Path(repo_root)
        self.timeline_cache_root = Path(timeline_cache_root)
        self.fg_cache_root = Path(fg_cache_root)
        self.state = state
        self.prebuild = prebuild
        self.restart_requested = restart_requested
        self.publication_ready = publication_ready
        self.prepare_code_update = prepare_code_update
        self.code_update_aborted = code_update_aborted
        self.remote = _validated_git_name(env_str("ROBEATSMETA_FRONTIER_GIT_REMOTE", "origin"), label="remote")
        self.branch = _validated_git_name(env_str("ROBEATSMETA_FRONTIER_GIT_BRANCH", "main"), label="branch")
        self.poll_seconds = max(60, env_int("ROBEATSMETA_FRONTIER_GIT_POLL_SECONDS", 300))
        self.fetch_timeout = max(30, env_int("ROBEATSMETA_FRONTIER_GIT_TIMEOUT_SECONDS", 120))
        self._stop = threading.Event()
        self._runtime_commit = _git(self.repo_root, "rev-parse", "--verify", "HEAD^{commit}")
        self._last_commit = ""
        self._initialized = False

    def _remote_commit(self) -> tuple[str, str]:
        try:
            _git(
                self.repo_root,
                "fetch",
                "--quiet",
                self.remote,
                f"{self.branch}:refs/remotes/{self.remote}/{self.branch}",
                timeout=self.fetch_timeout,
            )
        except (OSError, subprocess.SubprocessError):
            logger.warning("frontier server Git fetch failed; using the last fetched trusted ref", exc_info=True)
        ref = f"refs/remotes/{self.remote}/{self.branch}"
        commit = _git(self.repo_root, "rev-parse", "--verify", f"{ref}^{{commit}}", timeout=self.fetch_timeout)
        data_revision = _git(self.repo_root, "rev-parse", "--verify", f"{commit}:Data", timeout=self.fetch_timeout)
        if re.fullmatch(r"[0-9a-f]{40,64}", commit) is None or re.fullmatch(r"[0-9a-f]{40,64}", data_revision) is None:
            raise RuntimeError("Git returned an invalid frontier Data revision")
        return commit, data_revision

    def run_once(self) -> bool:
        commit, data_revision = self._remote_commit()
        if commit != self._runtime_commit:
            if self.prepare_code_update is not None:
                self.prepare_code_update()
            try:
                checkout_updated = _install_server_checkout(self.repo_root, commit)
            except Exception:
                if self.code_update_aborted is not None:
                    self.code_update_aborted()
                raise
            if checkout_updated:
                logger.info("installed MetaFinder server code revision %s", commit)
            logger.info("restarting into MetaFinder server code revision %s before prebuild", commit)
            self._stop.set()
            if self.restart_requested is not None:
                self.restart_requested(commit)
            return False
        if self._initialized and commit == self._last_commit:
            return False
        snapshot = source_snapshot_root() / commit
        if not (snapshot / "Data").is_dir() or not (snapshot / "gear_optimizer").is_dir():
            if snapshot.exists():
                shutil.rmtree(snapshot)
            _extract_repository_snapshot(self.repo_root, commit, snapshot)
        data_root = snapshot / "Data"
        sync_exported_game_data(
            paths=ExportedGameDataPaths(
                exported_json=data_root / "exported_game_data.json",
                gears_csv=data_root / "Gear" / "Gears.csv",
                minis_csv=data_root / "Gear" / "Minis.csv",
                sync_state=source_snapshot_root() / ".sync" / f"{commit}.json",
            ),
            force=True,
        )
        cache_allowlist = self.prebuild(data_root)
        publication = build_publication(
            code_root=snapshot,
            data_root=data_root,
            data_revision=data_revision,
            code_revision=commit,
            timeline_cache_root=self.timeline_cache_root,
            fg_cache_root=self.fg_cache_root,
            root=self.state.root,
            cache_allowlist=cache_allowlist,
        )
        self.state.install(publication)
        if self.publication_ready is not None:
            self.publication_ready(data_root)
        self._last_commit = commit
        self._initialized = True
        logger.info("published MetaFinder code/Data/frontier revision %s", publication.name)
        return True

    def serve_forever(self) -> None:
        while not self._stop.is_set():
            try:
                self.run_once()
            except Exception:
                logger.exception("frontier server maintenance failed; the last complete publication remains active")
            self._stop.wait(self.poll_seconds)

    def stop(self) -> None:
        self._stop.set()
