# Contributing

Thank you for improving RoBeats Calculator Engine.

## Before you start

- Search existing issues and pull requests before proposing duplicate work.
- For a bug, include a minimal reproduction, environment details, and a sanitized traceback or log excerpt.
- For a larger change, open an issue first so the approach and validation requirements can be discussed.
- Report suspected vulnerabilities through the private process in [`SECURITY.md`](SECURITY.md), not a public issue.
- Read [`GOVERNANCE.md`](GOVERNANCE.md). Contributions do not grant repository administration, merge, release, deployment, or maintainer rights.

Participation in this project is governed by the [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

## Development setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements-dev.txt
```

On Windows PowerShell, activate the environment with `.\.venv\Scripts\Activate.ps1`.

## Pull requests

1. Read [`AGENTS.md`](AGENTS.md) and any subtree-specific agent notes.
2. Open an issue before implementing a new feature, scoring-policy change, schema change, public API change, or architectural rewrite.
3. Fix the owning invariant—no song-specific exceptions or silent fallbacks in optimizer logic.
4. Keep Base and Force Great leaderboards separate (`songs.best_score` vs `songs.best_fg_score`).
5. Add the narrowest tests that prove the change; GPU or Vulkan-facing work needs matching coverage.
6. Keep the patch focused and update user-facing documentation when behavior changes.
7. Disclose material AI assistance in the pull-request description. AI-assisted work is held to the same authorship, testing, and review standards as any other contribution.
8. Run `python -m ruff check .` and the applicable pytest markers (`not gpu` at minimum).

Behavior or policy changes need an implementation record under `docs/Implementation Records/` and an entry in `docs/CODEX_WORKLOG.md`.

### Acceptance rules

- All changes arrive through a pull request. Direct pushes from external contributors are not accepted.
- A pull request requires approval from the applicable code owner. Approval is discretionary and may be withdrawn before merge.
- Maintainers may close changes that bypass the owning invariant, duplicate an existing path, weaken exactness, add unbounded operational risk, or exceed the project's scope.
- Scoring, timing, reachability, persistence, security, data publication, service, and release changes require explicit lead-maintainer approval.
- Do not bundle drive-by refactors, mass formatting, generated churn, dependency upgrades, or unrelated cleanup.
- Do not represent the project, promise releases, publish builds, contact users as a maintainer, or use project branding for an unofficial distribution without written maintainer authorization.
- Authorship remains with the contributor; merge authority and project direction remain with the maintainers defined in [`GOVERNANCE.md`](GOVERNANCE.md).

### Validation

```bash
python -m ruff check .
python -m pytest -m "not gpu" tests/
```

Changes to GPU execution, timing, cache behavior, or reachability also require:

```bash
python -m pytest -m gpu tests/
```

Include the commands you ran and their results in the pull-request description.

## What not to commit

- `evolution.db`, frontier credentials, client registries, or `.env` secrets
- Generated artifacts under `bin/` or `artifacts/`
- Local changes to `config.ini`, caches, logs, profiles, or private chart uploads
- Absolute workstation paths, usernames, private network addresses, raw production logs, or personal identifiers

## License

By contributing, you agree that your contributions are licensed under the [Apache License 2.0](LICENSE).
