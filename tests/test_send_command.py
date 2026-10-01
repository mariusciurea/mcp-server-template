"""Tests for the send_command tool."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from src.data_models.devices import CommandRequest, CommandResult
from src.tools.send_command import send_command
from tests.conftest import McpClient, tool_payload

# --- tool function ---


@pytest.mark.parametrize(
    ("command", "expected_output"),
    [
        ("show version", "Dummy OS v1.2.3, uptime 42 days"),
        ("show interfaces", "GigabitEthernet0/1 is up, line protocol is up"),
        ("show running-config", "! Dummy running configuration\nhostname test-core-1"),
    ],
)
def test_known_command_returns_canned_output(command: str, expected_output: str) -> None:
    result = send_command(CommandRequest(router_id="rtr-a", command=command))

    assert result == CommandResult(
        router_id="rtr-a",
        command=command,
        output=expected_output,
        success=True,
    )


def test_running_config_uses_target_router_hostname() -> None:
    result = send_command(CommandRequest(router_id="rtr-b", command="show running-config"))

    assert result.output.endswith("hostname test-edge-1")


def test_known_command_matching_ignores_case_and_whitespace() -> None:
    result = send_command(CommandRequest(router_id="rtr-a", command="  SHOW Version  "))

    assert result.output == "Dummy OS v1.2.3, uptime 42 days"
    assert result.command == "  SHOW Version  ", "original command text is echoed back"


def test_unknown_command_returns_generic_simulated_output() -> None:
    result = send_command(CommandRequest(router_id="rtr-c", command="ping 8.8.8.8"))

    assert result.success is True
    assert result.output == "% Simulated output for 'ping 8.8.8.8' on test-edge-2"


def test_unknown_router_raises() -> None:
    with pytest.raises(ValueError, match="Unknown router id: rtr-missing"):
        send_command(CommandRequest(router_id="rtr-missing", command="show version"))


def test_empty_command_is_rejected_by_model() -> None:
    with pytest.raises(ValidationError):
        CommandRequest(router_id="rtr-a", command="")


# --- REST endpoint ---


def test_endpoint_runs_command(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(
        "/tools/routers/command",
        headers=auth_headers,
        json={"router_id": "rtr-a", "command": "show version"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "router_id": "rtr-a",
        "command": "show version",
        "output": "Dummy OS v1.2.3, uptime 42 days",
        "success": True,
    }


def test_endpoint_unknown_router_returns_404(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(
        "/tools/routers/command",
        headers=auth_headers,
        json={"router_id": "rtr-missing", "command": "show version"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Unknown router id: rtr-missing"}


@pytest.mark.parametrize(
    "payload",
    [
        {"router_id": "rtr-a", "command": ""},
        {"router_id": "rtr-a"},
        {"command": "show version"},
    ],
    ids=["empty-command", "missing-command", "missing-router-id"],
)
def test_endpoint_invalid_payload_returns_422(
    client: TestClient, auth_headers: dict[str, str], payload: dict[str, str]
) -> None:
    response = client.post("/tools/routers/command", headers=auth_headers, json=payload)

    assert response.status_code == 422


def test_endpoint_requires_token(client: TestClient) -> None:
    response = client.post(
        "/tools/routers/command",
        json={"router_id": "rtr-a", "command": "show version"},
    )

    assert response.status_code == 401


# --- MCP tool ---


def test_mcp_tool_runs_command(mcp_client: McpClient) -> None:
    result = mcp_client.call_tool("send_command", {"router_id": "rtr-b", "command": "show interfaces"})

    assert tool_payload(result) == {
        "router_id": "rtr-b",
        "command": "show interfaces",
        "output": "GigabitEthernet0/1 is up, line protocol is up",
        "success": True,
    }


def test_mcp_tool_unknown_router_is_error(mcp_client: McpClient) -> None:
    result = mcp_client.call_tool("send_command", {"router_id": "rtr-missing", "command": "show version"})

    assert result["isError"] is True
    assert "Unknown router id: rtr-missing" in result["content"][0]["text"]


def test_mcp_tool_without_token_is_error(anonymous_mcp_client: McpClient) -> None:
    result = anonymous_mcp_client.call_tool("send_command", {"router_id": "rtr-a", "command": "show version"})

    assert result["isError"] is True
    assert "401" in result["content"][0]["text"]
