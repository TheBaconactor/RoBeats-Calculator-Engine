# Documentation

This index separates maintained production references from analytical and
research material. A document listed under “Maintained references” is expected
to match the current `main` branch. Background papers describe the mathematics
or a historical line of investigation and are not runtime API contracts.

## Start here

- [Architecture](ARCHITECTURE.md) — runtime flow, subsystem boundaries, and
  correctness invariants.
- [Navigation](NAVIGATION.md) — current entry points and file-level ownership.
- [Data setup](../DATA.md) — bundled inputs, generated state, and database-path
  configuration.
- [Contributing](../CONTRIBUTING.md) — contribution workflow and validation
  expectations.

## Maintained references

- [Engineering principles](ENGINEERING_PRINCIPLES.md)
- [Database schema](DATABASE_SCHEMA.md)
- [Maintenance playbook](MAINTENANCE_PLAYBOOK.md)
- [Fever timeline math](FEVER_TIMELINE_MATH.md)
- [Formula reference](FORMULA_REFERENCE.md)
- [Exact timing-envelope frontier](TIMING_ENVELOPE_EXACT_FRONTIER.md)
- [On-demand Team Buff tier scoring](ON_DEMAND_TEAM_BUFF_TIER_SCORING.md)

## Analytical background

These documents define mathematical problems or preserve design analysis. They
may use simplified models and should not be treated as descriptions of the
current module layout.

- [Analytical HitSim problem](ANALYTICAL_HITSIM_PROBLEM.md)
- [Analytical HitSim solution notes](ANALYTICAL_HITSIM_SOLUTION.md)
- [Analytical Force Greats problem](ANALYTICAL_FG_PROBLEM.md)
- [Early-Great frontier problem](FG_EARLY_GREAT_FRONTIER_MATH_PROBLEM.md)
- [Context-aware skyline paper](CONTEXT_AWARE_SKYLINE_OPTIMIZATION_PAPER.tex)

## Research artifacts

The [research index](research/README.md) contains dated evidence bundles,
proposals, formal analyses, and generated reports. Each artifact carries its
own scope and date; none is a production contract unless a maintained reference
explicitly adopts it.

## Documentation policy

- Update the owning reference in the same pull request as a behavior, schema,
  environment-variable, or public-interface change.
- Prefer links to public package surfaces over private helper functions.
- Remove completed plans and obsolete worklogs instead of presenting them as
  current guidance; Git history remains the archive.
- Run `python -m pytest tests/test_repo_guardrails.py` before publishing a
  documentation-only change.
