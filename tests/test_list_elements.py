"""Tests for the list_elements tool (and its find_router helper)."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from src.core.settings import PROJECT_ROOT, get_settings
from src.data_models.devices import RouterDevice, RouterStatus
from src.tools.list_elements import find_router, list_elements
from tests.conftest import TEST_ROUTERS, McpClient, tool_payload

# --- tool function ---


def test_list_elements_returns_all_routers_in_file_order() -> None:
    routers = list_elements()

    assert all(isinstance(router, RouterDevice) for router in routers)
    assert [router.model_dump(mode="json") for router in routers] == TEST_ROUTERS


def test_list_elements_parses_status_enum() -> None:
    statuses = [router.status for router in list_elements()]

    assert statuses == [RouterStatus.ONLINE, RouterStatus.DEGRADED, RouterStatus.OFFLINE]


def test_list_elements_empty_inventory(routers_file: Path) -> None:
    routers_file.write_text("[]", encoding="utf-8")

    assert list_elements() == []


def test_list_elements_rejects_invalid_status(routers_file: Path) -> None:
    routers_file.write_text(json.dumps([{**TEST_ROUTERS[0], "status": "exploded"}]), encoding="utf-8")

    with pytest.raises(ValidationError):
        list_elements()


def test_list_elements_rejects_missing_field(routers_file: Path) -> None:
    incomplete = {key: value for key, value in TEST_ROUTERS[0].items() if key != "hostname"}
    routers_file.write_text(json.dumps([incomplete]), encoding="utf-8")

    with pytest.raises(ValidationError):
        list_elements()


def test_shipped_inventory_file_is_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "routers_data_file", PROJECT_ROOT / "data" / "routers.json")

    routers = list_elements()

    assert routers
    assert len({router.id for router in routers}) == len(routers), "router ids must be unique"


@pytest.mark.parametrize("router_data", TEST_ROUTERS, ids=lambda r: r["id"])
def test_find_router_returns_matching_router(router_data: dict[str, str]) -> None:
    router = find_router(router_data["id"])

    assert router.model_dump(mode="json") == router_data


def test_find_router_unknown_id_raises() -> None:
    with pytest.raises(ValueError, match="Unknown router id: rtr-missing"):
        find_router("rtr-missing")


# --- REST endpoint ---


def test_endpoint_returns_inventory(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/tools/routers", headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == TEST_ROUTERS


def test_endpoint_requires_token(client: TestClient) -> None:
    response = client.get("/tools/routers")

    assert response.status_code == 401


def test_endpoint_rejects_invalid_token(client: TestClient) -> None:
    response = client.get("/tools/routers", headers={"Authorization": "Bearer not-a-jwt"})

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or expired token"}


# --- MCP tool ---


def test_mcp_tool_returns_inventory(mcp_client: McpClient) -> None:
    result = mcp_client.call_tool("list_elements")

    assert tool_payload(result) == TEST_ROUTERS


def test_mcp_tool_without_token_is_error(anonymous_mcp_client: McpClient) -> None:
    result = anonymous_mcp_client.call_tool("list_elements")

    assert result["isError"] is True
    assert "401" in result["content"][0]["text"]
