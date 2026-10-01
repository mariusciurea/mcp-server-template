"""Tests for how the tools are exposed by the MCP server as a whole."""

from tests.conftest import McpClient


def test_server_exposes_exactly_the_three_tools(mcp_client: McpClient) -> None:
    tools = mcp_client.request("tools/list")["tools"]

    assert sorted(tool["name"] for tool in tools) == [
        "get_router_status",
        "list_elements",
        "send_command",
    ]


def test_login_endpoint_is_not_exposed_as_tool(mcp_client: McpClient) -> None:
    tool_names = {tool["name"] for tool in mcp_client.request("tools/list")["tools"]}

    assert not any("login" in name or "token" in name for name in tool_names)


def test_tool_input_schemas_declare_required_arguments(mcp_client: McpClient) -> None:
    schemas = {tool["name"]: tool["inputSchema"] for tool in mcp_client.request("tools/list")["tools"]}

    assert set(schemas["list_elements"].get("required", [])) == set()
    assert set(schemas["send_command"]["required"]) == {"router_id", "command"}
    assert set(schemas["get_router_status"]["required"]) == {"router_id"}
