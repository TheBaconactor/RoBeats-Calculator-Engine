# Contributing

Thank you for improving RoBeats Song Optimizer.

## Before you open a PR

1. Read [`AGENTS.md`](AGENTS.md) and any subtree-specific agent notes.
2. Fix the owning invariant — no song-specific exceptions or silent fallbacks in optimizer logic.
3. Keep Base and Force Great leaderboards separate (`songs.best_score` vs `songs.best_fg_score`).
4. Add the narrowest tests that prove the change; GPU or Vulkan-facing work needs matching coverage.
5. Run `python -m ruff check .` and the applicable pytest markers (`not gpu` at minimum).

Behavior or policy changes need an implementation record under `docs/Implementation Records/` and an entry in `docs/CODEX_WORKLOG.md`.

## What not to commit

- `evolution.db`, frontier credentials, client registries, or `.env` secrets
- Generated artifacts under `bin/` or `artifacts/`

## License

By contributing, you agree that your contributions are licensed under the [Apache License 2.0](LICENSE).
