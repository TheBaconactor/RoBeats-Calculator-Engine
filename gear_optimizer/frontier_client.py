from __future__ import annotations

import hashlib
import ipaddress
import json
import logging
import os
import re
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

import requests

from gear_optimizer.core.constants import PATHS
from gear_optimizer.core.parsing import env_flag, env_str
from gear_optimizer.frontier_auth import (
    frontier_credentials_configured,
    load_client_credentials,
    signed_request_headers,
)

logger = logging.getLogger(__name__)

_DEFAULT_SERVER = "https://api.robeatsmeta.net/metafinder/v1"
_REVISION_RE = re.compile(r"[0-9a-f]{64}\Z")
_DIGEST_RE = re.compile(r"[0-9a-f]{64}\Z")
_BUNDLE_RE = re.compile(r"[a-z0-9][a-z0-9.-]{0,80}\.tar\.gz\Z")
_DATA_SCOPES = frozenset({"data", "timeline", "fg"})
_SCOPES = frozenset({"code", *_DATA_SCOPES})
_MAX_MANIFEST_BYTES = 32 * 1024 * 1024
_MAX_BUNDLE_BYTES = 256 * 1024 * 1024
_MAX_TOTAL_BYTES = 64 * 1024 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class FrontierSyncResult:
    enabled: bool
    revision: str = ""
    code_revision: str = ""
    downloaded_bundles: int = 0
    downloaded_bytes: int = 0
    installed_files: int = 0
    removed_files: int = 0


def frontier_client_enabled() -> bool:
    return not env_flag("ROBEATSMETA_OPTIMIZER_SERVICE_MODE")


def _server_base_url() -> str:
    value = env_str("METAFINDER_FRONTIER_SERVER_URL", _DEFAULT_SERVER).rstrip("/")
    try:
        parsed = urlsplit(value)
        host = str(parsed.hostname or "").lower().rstrip(".")
        port = parsed.port
    except ValueError as exc:
        raise RuntimeError("invalid MetaFinder frontier server URL") from exc
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise RuntimeError("invalid MetaFinder frontier server URL")
    if parsed.path.rstrip("/") != "/metafinder/v1" or parsed.scheme not in {"http", "https"} or not host:
        raise RuntimeError("MetaFinder frontier server URL must end in /metafinder/v1")
    loopback = host == "localhost"
    if not loopback:
        try:
            loopback = ipaddress.ip_address(host).is_loopback
        except ValueError:
            loopback = False
    if parsed.scheme != "https" and not loopback:
        raise RuntimeError("MetaFinder frontier server must use HTTPS")
    authority = f"[{host}]" if ":" in host else host
    if port is not None:
        authority = f"{authority}:{port}"
    return f"{parsed.scheme}://{authority}/metafinder/v1"


def _state_path(filename: str) -> Path:
    return Path(PATHS.bin_path(filename))


def _load_state(filename: str) -> dict:
    try:
        payload = json.loads(_state_path(filename).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) and int(payload.get("schema", 0) or 0) == 1 else {}


def _write_state(filename: str, payload: dict) -> None:
    path = _state_path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _relative_path(value: object) -> str:
    text = str(value or "")
    path = PurePosixPath(text)
    if not text or text.startswith("/") or path.is_absolute() or ".." in path.parts or path.as_posix() != text:
        raise ValueError(f"invalid path in frontier manifest: {text!r}")
    return text


def _validated_manifest(payload: object) -> dict:
    if not isinstance(payload, dict) or int(payload.get("protocol", 0) or 0) != 2:
        raise ValueError("unsupported MetaFinder frontier manifest")
    revision = str(payload.get("revision") or "")
    code_revision = str(payload.get("code_revision") or "")
    bundles = payload.get("bundles")
    if (
        _REVISION_RE.fullmatch(revision) is None
        or re.fullmatch(r"[0-9a-f]{40,64}", code_revision) is None
        or not isinstance(bundles, list)
    ):
        raise ValueError("invalid MetaFinder frontier manifest")
    names: set[str] = set()
    manifest_files: set[str] = set()
    total_bytes = 0
    total_files = 0
    validated: list[dict] = []
    for raw_bundle in bundles:
        if not isinstance(raw_bundle, dict):
            raise ValueError("invalid bundle in MetaFinder frontier manifest")
        name = str(raw_bundle.get("name") or "")
        digest = str(raw_bundle.get("sha256") or "").lower()
        content_digest = str(raw_bundle.get("content_sha256") or "").lower()
        files = raw_bundle.get("files")
        try:
            size = int(raw_bundle.get("size", -1))
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid bundle size in MetaFinder frontier manifest") from exc
        if (
            _BUNDLE_RE.fullmatch(name) is None
            or name in names
            or _DIGEST_RE.fullmatch(digest) is None
            or _DIGEST_RE.fullmatch(content_digest) is None
            or size < 0
            or size > _MAX_BUNDLE_BYTES
            or not isinstance(files, list)
        ):
            raise ValueError("invalid bundle in MetaFinder frontier manifest")
        names.add(name)
        entries: list[dict] = []
        member_names: set[str] = set()
        bundle_scopes: set[str] = set()
        for raw_entry in files:
            if not isinstance(raw_entry, dict):
                raise ValueError("invalid file in MetaFinder frontier manifest")
            scope = str(raw_entry.get("scope") or "")
            relative = _relative_path(raw_entry.get("path"))
            file_digest = str(raw_entry.get("sha256") or "").lower()
            try:
                file_size = int(raw_entry.get("size", -1))
            except (TypeError, ValueError) as exc:
                raise ValueError("invalid file size in MetaFinder frontier manifest") from exc
            member_name = f"{scope}/{relative}"
            if (
                scope not in _SCOPES
                or _DIGEST_RE.fullmatch(file_digest) is None
                or file_size < 0
                or file_size > _MAX_TOTAL_BYTES
                or member_name in member_names
                or member_name in manifest_files
            ):
                raise ValueError("invalid file in MetaFinder frontier manifest")
            member_names.add(member_name)
            manifest_files.add(member_name)
            bundle_scopes.add(scope)
            entries.append({"scope": scope, "path": relative, "size": file_size, "sha256": file_digest})
            total_files += 1
            total_bytes += file_size
            if total_bytes > _MAX_TOTAL_BYTES or total_files > 100_000:
                raise ValueError("MetaFinder frontier manifest exceeds client safety limits")
        if len(bundle_scopes) != 1:
            raise ValueError("MetaFinder frontier bundles must contain exactly one scope")
        validated.append(
            {
                "name": name,
                "size": size,
                "sha256": digest,
                "content_sha256": content_digest,
                "files": entries,
            }
        )
    if "code" not in {entry["scope"] for bundle in validated for entry in bundle["files"]}:
        raise ValueError("MetaFinder frontier manifest has no client code")
    return {"protocol": 2, "revision": revision, "code_revision": code_revision, "bundles": validated}


def _scope_root(scope: str, code_root: Path | None = None) -> Path:
    if scope == "code":
        if code_root is None:
            raise ValueError("MetaFinder code destination was not provided")
        return code_root
    if scope == "data":
        return Path(PATHS.data_dir)
    if scope == "timeline":
        configured = env_str("TIMELINE_FRONTIER_CACHE_DIR", "")
        return Path(configured) if configured else Path(PATHS.bin_path("timeline_frontier_cache"))
    if scope == "fg":
        configured = env_str("FG_RESPONSE_FRONTIER_CACHE_DIR", "")
        return Path(configured) if configured else Path(PATHS.bin_path("fg_response_frontier_cache"))
    raise ValueError(f"unknown frontier scope: {scope}")


def _destination(scope: str, relative: str, code_root: Path | None = None) -> Path:
    root = _scope_root(scope, code_root).resolve()
    destination = root.joinpath(*PurePosixPath(_relative_path(relative)).parts).resolve()
    if destination != root and root not in destination.parents:
        raise ValueError("frontier manifest path escapes its destination")
    return destination


def _request(session: requests.Session, base_url: str, path: str, credentials, *, stream: bool) -> requests.Response:
    headers = signed_request_headers(credentials, method="GET", path=path)
    response = session.get(
        f"{base_url.removesuffix('/metafinder/v1')}{path}",
        headers=headers,
        stream=stream,
        allow_redirects=False,
        timeout=(15, 300),
    )
    if response.status_code != 200:
        response.close()
        raise RuntimeError(f"MetaFinder frontier server returned HTTP {response.status_code}")
    return response


def _download_manifest(session: requests.Session, base_url: str, credentials) -> dict:
    path = "/metafinder/v1/manifest"
    with _request(session, base_url, path, credentials, stream=True) as response:
        raw_length = response.headers.get("Content-Length", "")
        if raw_length.isdigit() and int(raw_length) > _MAX_MANIFEST_BYTES:
            raise RuntimeError("MetaFinder frontier manifest is too large")
        body = bytearray()
        for chunk in response.iter_content(64 * 1024):
            body.extend(chunk)
            if len(body) > _MAX_MANIFEST_BYTES:
                raise RuntimeError("MetaFinder frontier manifest is too large")
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("MetaFinder frontier server returned an invalid manifest") from exc
    return _validated_manifest(payload)


def fetch_frontier_manifest() -> dict:
    if not frontier_client_enabled():
        raise RuntimeError("frontier manifests are not fetched by the MetaFinder server process")
    credentials = load_client_credentials()
    with requests.Session() as session:
        return _download_manifest(session, _server_base_url(), credentials)


def _bundle_is_current(bundle: dict, previous: dict, code_root: Path | None = None) -> bool:
    if str(previous.get("sha256") or "") != str(bundle["sha256"]):
        return False
    previous_files = {
        (str(entry.get("scope") or ""), str(entry.get("path") or "")): entry
        for entry in previous.get("files", [])
        if isinstance(entry, dict)
    }
    for entry in bundle["files"]:
        recorded = previous_files.get((entry["scope"], entry["path"]))
        destination = _destination(entry["scope"], entry["path"], code_root)
        try:
            file_stat = destination.stat()
        except OSError:
            return False
        if (
            not isinstance(recorded, dict)
            or int(file_stat.st_size) != int(entry["size"])
            or int(recorded.get("local_mtime_ns", -1)) != int(file_stat.st_mtime_ns)
        ):
            return False
    return True


def _download_bundle(session: requests.Session, base_url: str, credentials, revision: str, bundle: dict) -> Path:
    temp_root = Path(PATHS.bin_path("frontier_downloads"))
    temp_root.mkdir(parents=True, exist_ok=True)
    path = f"/metafinder/v1/bundles/{revision}/{bundle['name']}"
    digest = hashlib.sha256()
    size = 0
    handle = tempfile.NamedTemporaryFile(prefix="frontier-", suffix=".tar.gz", dir=temp_root, delete=False)
    temporary = Path(handle.name)
    try:
        with handle, _request(session, base_url, path, credentials, stream=True) as response:
            if response.headers.get("X-Content-SHA256", "").lower() != bundle["sha256"]:
                raise RuntimeError("MetaFinder frontier bundle digest header mismatch")
            for chunk in response.iter_content(1024 * 1024):
                if not chunk:
                    continue
                size += len(chunk)
                if size > int(bundle["size"]) or size > _MAX_BUNDLE_BYTES:
                    raise RuntimeError("MetaFinder frontier bundle exceeded its declared size")
                digest.update(chunk)
                handle.write(chunk)
        if size != int(bundle["size"]) or digest.hexdigest() != bundle["sha256"]:
            raise RuntimeError("MetaFinder frontier bundle failed SHA-256 verification")
        return temporary
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _install_bundle(archive_path: Path, bundle: dict, code_root: Path | None = None) -> int:
    expected = {f"{entry['scope']}/{entry['path']}": entry for entry in bundle["files"]}
    seen: set[str] = set()
    installed = 0
    try:
        with tarfile.open(archive_path, "r:gz") as archive:
            for member in archive:
                entry = expected.get(member.name)
                if (
                    entry is None
                    or member.name in seen
                    or not member.isfile()
                    or int(member.size) != int(entry["size"])
                ):
                    raise RuntimeError("MetaFinder frontier bundle contains an unexpected file")
                source = archive.extractfile(member)
                if source is None:
                    raise RuntimeError("MetaFinder frontier bundle file body is missing")
                destination = _destination(entry["scope"], entry["path"], code_root)
                destination.parent.mkdir(parents=True, exist_ok=True)
                temporary = destination.with_name(f".{destination.name}.{os.getpid()}.tmp")
                digest = hashlib.sha256()
                written = 0
                try:
                    with source, temporary.open("wb") as output:
                        for chunk in iter(lambda: source.read(1024 * 1024), b""):
                            written += len(chunk)
                            digest.update(chunk)
                            output.write(chunk)
                    if written != int(entry["size"]) or digest.hexdigest() != entry["sha256"]:
                        raise RuntimeError("MetaFinder frontier file failed SHA-256 verification")
                    os.chmod(temporary, 0o755 if int(member.mode) & 0o111 else 0o644)
                    os.replace(temporary, destination)
                finally:
                    temporary.unlink(missing_ok=True)
                seen.add(member.name)
                installed += 1
        if seen != set(expected):
            raise RuntimeError("MetaFinder frontier bundle is incomplete")
        return installed
    finally:
        archive_path.unlink(missing_ok=True)


def _sync_scopes(
    *,
    scopes: frozenset[str],
    state_filename: str,
    code_root: Path | None = None,
    initial_managed_files: set[tuple[str, str]] | None = None,
) -> FrontierSyncResult:
    if not frontier_credentials_configured():
        logger.info("[FrontierSync] skipped; no frontier credential file configured")
        return FrontierSyncResult(enabled=False)
    credentials = load_client_credentials()
    base_url = _server_base_url()
    previous_state = _load_state(state_filename)
    previous_bundles = {
        str(bundle.get("name")): bundle
        for bundle in previous_state.get("bundles", [])
        if isinstance(bundle, dict)
    }
    downloaded_bundles = downloaded_bytes = installed_files = 0
    staged_code_bundles: list[tuple[Path, dict]] = []
    try:
        with requests.Session() as session:
            manifest = _download_manifest(session, base_url, credentials)
            selected_bundles = [
                bundle for bundle in manifest["bundles"] if bundle["files"][0]["scope"] in scopes
            ]
            if not selected_bundles:
                raise RuntimeError("MetaFinder frontier manifest omitted a required scope")
            for bundle in selected_bundles:
                previous = previous_bundles.get(bundle["name"], {})
                if _bundle_is_current(bundle, previous, code_root):
                    continue
                archive = _download_bundle(session, base_url, credentials, manifest["revision"], bundle)
                downloaded_bundles += 1
                downloaded_bytes += int(bundle["size"])
                if scopes == frozenset({"code"}):
                    staged_code_bundles.append((archive, bundle))
                else:
                    installed_files += _install_bundle(archive, bundle, code_root)
        for archive, bundle in staged_code_bundles:
            installed_files += _install_bundle(archive, bundle, code_root)
    finally:
        for archive, _bundle in staged_code_bundles:
            archive.unlink(missing_ok=True)

    current_files = {
        (entry["scope"], entry["path"])
        for bundle in selected_bundles
        for entry in bundle["files"]
    }
    previous_files = {
        (str(entry.get("scope") or ""), str(entry.get("path") or ""))
        for bundle in previous_state.get("bundles", [])
        if isinstance(bundle, dict)
        for entry in bundle.get("files", [])
        if isinstance(entry, dict)
    }
    previous_files.update(initial_managed_files or set())
    removed = 0
    for scope, relative in sorted(previous_files - current_files):
        if scope not in scopes:
            continue
        destination = _destination(scope, relative, code_root)
        if destination.is_file():
            destination.unlink()
            removed += 1
    state_manifest = {**manifest, "bundles": json.loads(json.dumps(selected_bundles))}
    for bundle in state_manifest["bundles"]:
        for entry in bundle["files"]:
            entry["local_mtime_ns"] = int(
                _destination(entry["scope"], entry["path"], code_root).stat().st_mtime_ns
            )
    _write_state(state_filename, {"schema": 1, **state_manifest})
    result = FrontierSyncResult(
        enabled=True,
        revision=manifest["revision"],
        code_revision=manifest["code_revision"],
        downloaded_bundles=downloaded_bundles,
        downloaded_bytes=downloaded_bytes,
        installed_files=installed_files,
        removed_files=removed,
    )
    logger.info(
        "[FrontierSync] revision=%s bundles=%s bytes=%s files=%s removed=%s",
        result.revision,
        result.downloaded_bundles,
        result.downloaded_bytes,
        result.installed_files,
        result.removed_files,
    )
    return result


def sync_code_from_server(
    repo_root: str | Path,
    *,
    initial_managed_files: set[tuple[str, str]] | None = None,
) -> FrontierSyncResult:
    if not frontier_client_enabled():
        return FrontierSyncResult(enabled=False)
    return _sync_scopes(
        scopes=frozenset({"code"}),
        state_filename="client_update_state.json",
        code_root=Path(repo_root),
        initial_managed_files=initial_managed_files,
    )


def sync_frontiers_from_server() -> FrontierSyncResult:
    if not frontier_client_enabled():
        return FrontierSyncResult(enabled=False)
    return _sync_scopes(scopes=_DATA_SCOPES, state_filename="frontier_sync_state.json")
