## Summary

Describe the problem and the focused change that solves it.

## Linked issue

Link the approved issue for features, scoring-policy changes, schema changes, public API changes, or architectural work.

## Broken invariant

What rule was violated, and where did the state first become incorrect?

## Scope and risk

List affected correctness, GPU, persistence, security, API, data, or deployment boundaries.

## Validation

List the commands you ran and the relevant results.

- [ ] `python -m ruff check .`
- [ ] `python -m pytest -m "not gpu" tests/`
- [ ] GPU/Vulkan tests, if the change affects GPU execution, timing, caches, or reachability

## Checklist

- [ ] I fixed the owning layer rather than adding a symptom-level workaround.
- [ ] I added or updated regression coverage for a behavior change.
- [ ] I kept Base and Force Great leaderboards separate.
- [ ] I did not add secrets, credentials, generated databases, caches, logs, or artifacts.
- [ ] I did not include absolute workstation paths, personal identifiers, or private infrastructure details.
- [ ] I updated the owning maintained documentation when required.
- [ ] I disclosed material AI assistance and reviewed every submitted line.
- [ ] I understand that submitting a contribution does not grant merge, release, administration, deployment, or maintainer authority.
