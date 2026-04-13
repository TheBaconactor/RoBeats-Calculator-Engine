from __future__ import annotations

import json
import sys
from pathlib import Path

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


_REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_stdio_probe() -> dict[str, object]:
    async def _inner() -> dict[str, object]:
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "tools.mcp_server"],
            cwd=str(_REPO_ROOT),
        )
        async with stdio_client(params) as streams:
            read, write = streams
            async with ClientSession(read, write) as session:
                init = await session.initialize()
                tools = await session.list_tools()
                resources = await session.list_resources()
                templates = await session.list_resource_templates()
                context = await session.call_tool("repo.get_context", {})
                benchmark = await session.call_tool("repo.get_effective_settings", {"workflow": "benchmark"})
                resource = await session.read_resource("repo://context")
                return {
                    "server_name": init.serverInfo.name,
                    "tool_names": [tool.name for tool in tools.tools],
                    "resource_uris": [str(resource.uri) for resource in resources.resources],
                    "resource_templates": [template.uriTemplate for template in templates.resourceTemplates],
                    "context": context.structuredContent,
                    "benchmark": benchmark.structuredContent,
                    "resource_payload": json.loads(resource.contents[0].text),
                }

    return anyio.run(_inner)


def test_stdio_server_registers_expected_surfaces() -> None:
    probe = _run_stdio_probe()

    assert probe["server_name"] == "gear-optimizer-engineering-harness"
    assert "repo.get_context" in probe["tool_names"]
    assert "repo.find_harness_gaps" in probe["tool_names"]
    assert "verify.get_matrix" in probe["tool_names"]
    assert "repo://context" in probe["resource_uris"]
    assert "verify://matrix" in probe["resource_uris"]
    assert "config://effective/{workflow}" in probe["resource_templates"]
    assert "history://record/{slug}" in probe["resource_templates"]


def test_common_repo_questions_fit_in_two_stdio_calls() -> None:
    probe = _run_stdio_probe()
    context = probe["context"]
    benchmark = probe["benchmark"]
    resource_payload = probe["resource_payload"]

    assert context["status"] == "ok"
    assert context["facts"]["branch"]
    assert "repo.get_effective_settings" in context["suggested_next_tools"]
    assert benchmark["status"] == "ok"
    assert benchmark["facts"]["workflow"] == "benchmark"
    assert "workflow_settings" in benchmark["facts"]
    assert resource_payload["branch"] == context["facts"]["branch"]
