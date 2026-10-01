"""Tests for the get_router_status tool."""

import pytest
from fastapi.testclient import TestClient

from src.data_models.devices import RouterStatus, RouterStatusReport
from src.tools import router_status
from src.tools.router_status import get_router_status
from tests.conftest import TEST_ROUTERS, McpClient, tool_payload


@pytest.fixture
def fixed_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make the simulated metrics deterministic."""
    monkeypatch.setattr(router_status.random, "randint", lambda low, high: 123_456)
    monkeypatch.setattr(router_status.random, "uniform", lambda low, high: (low + high) / 2)


# --- tool function ---


@pytest.mark.parametrize("router_data", TEST_ROUTERS, ids=lambda r: r["id"])
def test_status_comes_from_inventory(router_data: dict[str, str]) -> None:
    report = get_router_status(router_data["id"])

    assert report.router_id == router_data["id"]
    assert report.status == RouterStatus(router_data["status"])


@pytest.mark.usefixtures("fixed_metrics")
def test_metrics_use_simulated_values() -> None:
    report = get_router_status("rtr-a")

    assert report == RouterStatusReport(
        router_id="rtr-a",
        status=RouterStatus.ONLINE,
        uptime_seconds=123_456,
        cpu_usage_percent=45.5,
        memory_usage_percent=45.0,
    )


def test_metrics_stay_within_simulated_ranges() -> None:
    for _ in range(200):
        report = get_router_status("rtr-a")

        assert 1_000 <= report.uptime_seconds <= 5_000_000
        assert 1.0 <= report.cpu_usage_percent <= 90.0
        assert 10.0 <= report.memory_usage_percent <= 80.0
        assert report.cpu_usage_percent == round(report.cpu_usage_percent, 1)
        assert report.memory_usage_percent == round(report.memory_usage_percent, 1)


def test_unknown_router_raises() -> None:
    with pytest.raises(ValueError, match="Unknown router id: rtr-missing"):
        get_router_status("rtr-missing")


# --- REST endpoint ---


@pytest.mark.usefixtures("fixed_metrics")
def test_endpoint_returns_status(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/tools/routers/rtr-b/status", headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == {
        "router_id": "rtr-b",
        "status": "degraded",
        "uptime_seconds": 123_456,
        "cpu_usage_percent": 45.5,
        "memory_usage_percent": 45.0,
    }


def test_endpoint_unknown_router_returns_404(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/tools/routers/rtr-missing/status", headers=auth_headers)

    assert response.status_code == 404
    assert response.json() == {"detail": "Unknown router id: rtr-missing"}


def test_endpoint_requires_token(client: TestClient) -> None:
    response = client.get("/tools/routers/rtr-a/status")

    assert response.status_code == 401


# --- MCP tool ---


@pytest.mark.usefixtures("fixed_metrics")
def test_mcp_tool_returns_status(mcp_client: McpClient) -> None:
    result = mcp_client.call_tool("get_router_status", {"router_id": "rtr-c"})

    assert tool_payload(result) == {
        "router_id": "rtr-c",
        "status": "offline",
        "uptime_seconds": 123_456,
        "cpu_usage_percent": 45.5,
        "memory_usage_percent": 45.0,
    }


def test_mcp_tool_unknown_router_is_error(mcp_client: McpClient) -> None:
    result = mcp_client.call_tool("get_router_status", {"router_id": "rtr-missing"})

    assert result["isError"] is True
    assert "Unknown router id: rtr-missing" in result["content"][0]["text"]


def test_mcp_tool_without_token_is_error(anonymous_mcp_client: McpClient) -> None:
    result = anonymous_mcp_client.call_tool("get_router_status", {"router_id": "rtr-a"})

    assert result["isError"] is True
    assert "401" in result["content"][0]["text"]
