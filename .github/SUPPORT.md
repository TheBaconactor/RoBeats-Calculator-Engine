# Support

## Getting help

- Reproducible bugs: use the GitHub bug-report form.
- Focused feature proposals: use the feature-request form.
- Setup and data-layout questions: read [`README.md`](../README.md), [`Data/README.md`](../Data/README.md), and [`docs/README.md`](../docs/README.md) first.
- Security vulnerabilities: follow [`SECURITY.md`](SECURITY.md); never post sensitive details publicly.

## Support boundaries

Maintainers cannot guarantee response times, individual loadout consulting, hardware troubleshooting for unsupported devices, recovery of private databases, or support for modified forks.

The official production path is GPU-first on Vulkan. CPU paths are reference and verification tools, not a supported production fallback.

When requesting help, provide the commit used, operating system, Python version, GPU and driver, configuration relevant to the failure, minimal reproduction steps, and sanitized logs. Remove credentials, absolute workstation paths, personal identifiers, private uploads, and infrastructure details.

## Troubleshooting

**Data files are not found.** Confirm that the local tree matches [`Data/README.md`](../Data/README.md), and run the optimizer again.

**Taichi cannot initialize Vulkan.** Update the graphics driver, then verify Taichi directly:

```bash
python -c "import taichi as ti; ti.init(arch=ti.vulkan); print('Vulkan ready')"
```

**The first run is slow.** Cold runs compile Numba and Taichi kernels and may build missing exact frontiers. Later runs reuse compatible caches under `bin/`.
