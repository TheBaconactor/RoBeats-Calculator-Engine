from __future__ import annotations

import anyio

from tools._mcp_harness import server as harness


def _resource_surface() -> tuple[set[str], set[str]]:
    async def _inner() -> tuple[set[str], set[str]]:
        resources = await harness.HARNESS.list_resources()
        templates = await harness.HARNESS.list_resource_templates()
        return (
            {str(resource.uri) for resource in resources},
            {template.uriTemplate for template in templates},
        )

    return anyio.run(_inner)


def test_harness_manifest_points_to_registered_tools_and_resources() -> None:
    coverage = harness.repo_get_harness_coverage()["facts"]
    tool_names = {tool.name for tool in harness.HARNESS._tool_manager.list_tools()}
    resource_uris, template_uris = _resource_surface()

    assert "Prefer 1-2 MCP calls for common repo questions." in coverage["principles"]

    for subsystem in coverage["subsystems"]:
        for tool_name in subsystem["tool_names"]:
            assert tool_name in tool_names
        for uri in subsystem["resource_uris"]:
            assert uri in resource_uris or uri in template_uris


def test_effective_settings_surface_reports_curated_env_overrides(monkeypatch) -> None:
    monkeypatch.setenv("GA_SEED", "12345")
    monkeypatch.setenv("FG_SEARCH_RADIUS", "77")

    response = harness.repo_get_effective_settings("benchmark")
    facts = response["facts"]

    assert facts["env_overrides"]["GA_SEED"] == "12345"
    assert facts["env_overrides"]["FG_SEARCH_RADIUS"] == "77"
    assert facts["workflow_settings"]["ga_seed"] == "12345"
    assert response["suggested_next_tools"][0] == "verify.suggest_checks"


def test_find_harness_gaps_flags_config_semantics_review_trigger() -> None:
    response = harness.repo_find_harness_gaps(
        ["gear_optimizer/core/env_config.py"],
        include_git_status=False,
        max_results=5,
    )

    assert response["status"] == "warning"
    findings = response["facts"]["findings"]
    assert findings
    assert findings[0]["title"].startswith("Config or env semantics changed:")
    assert "1-2 MCP calls" in findings[0]["suggested_capability"]


def test_verify_matrix_uses_explicit_changed_paths() -> None:
    docs_only = harness.verify_get_matrix(["docs/README.md"])
    harness_only = harness.verify_get_matrix(["tools/mcp_server.py"])

    assert docs_only["facts"]["category"] == "docs-only"
    assert harness_only["facts"]["category"] == "mcp-harness"
    assert harness_only["facts"]["matrix"]["required"]
