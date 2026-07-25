# ECLIPSE Submission Bundle

Status: archived research snapshot. These artifacts do not describe the current
production architecture or supported benchmark surface.

Files:
- `eclipse_report.pdf` - research-style report
- `eclipse_report.tex` - report source
- `implementation_plan.md` - implementation plan with data structures and pseudocode
- `ga_fg_reduction_prototype.py` - deterministic self-contained prototype harness
- `prototype_results.json` - results produced by the prototype harness

Run the prototype:

```bash
python ga_fg_reduction_prototype.py --output_json prototype_results.json
```

Default settings use three fixed seeds and write a machine-readable JSON summary.

Important note:
- The prototype is a faithful mock-up for the assignment, not a repo-integrated Vulkan benchmark.
- The report clearly separates prompt facts, added assumptions, and deployment validation gates.
