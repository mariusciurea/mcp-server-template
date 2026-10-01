"""Shared fixtures: test settings, a controlled router inventory, an
authenticated TestClient and a minimal MCP JSON-RPC client."""

import json
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

# Must be set before importing src: settings are read (and cached) at import
# time. Real env vars take precedence over the local .env file.
os.environ["JWT_SECRET_KEY"] = "test-secret-key-that-is-at-least-32-bytes"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD"] = "test-password"
os.environ["RATE_LIMIT"] = "1000/minute"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from src.core.rate_limit import limiter  # noqa: E402
from src.core.security import create_access_token  # noqa: E402
from src.core.settings import get_settings  # noqa: E402
from src.service import app  # noqa: E402

TEST_ROUTERS: list[dict[str, str]] = [
    {
        "id": "rtr-a",
        "hostname": "test-core-1",
        "ip_address": "192.0.2.1",
        "vendor": "Cisco",
        "location": "Lab 1",
        "status": "online",
    },
    {
        "id": "rtr-b",
        "hostname": "test-edge-1",
        "ip_address": "192.0.2.2",
        "vendor": "Juniper",
        "location": "Lab 2",
        "status": "degraded",
    },
    {
        "id": "rtr-c",
        "hostname": "test-edge-2",
        "ip_address": "192.0.2.3",
        "vendor": "MikroTik",
        "location": "Lab 2",
        "status": "offline",
    },
]

MCP_PROTOCOL_VERSION = "2025-03-26"


@pytest.fixture(autouse=True)
def routers_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the inventory at a temp JSON file so tests don't depend on src/data."""
    path = tmp_path / "routers.json"
    path.write_text(json.dumps(TEST_ROUTERS), encoding="utf-8")
    monkeypatch.setattr(get_settings(), "routers_data_file", path)
    return path


@pytest.fixture(autouse=True)
def reset_rate_limiter() -> None:
    """Start every test with an empty rate-limit bucket."""
    limiter.reset()


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    # Session-scoped: fastapi-mcp starts its MCP session manager only once per
    # process, bound to the event loop of the first client that hits /mcp.
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(subject='admin')}"}


class McpClient:
    """Minimal MCP client speaking JSON-RPC over the Streamable HTTP transport."""

    def __init__(self, client: TestClient, headers: dict[str, str]) -> None:
        self._client = client
        self._headers = {
            **headers,
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }
        self._next_id = 0

    def initialize(self) -> dict[str, Any]:
        result = self.request(
            "initialize",
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "pytest", "version": "1.0"},
            },
        )
        self.notify("notifications/initialized")
        return result

    def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self._next_id += 1
        message: dict[str, Any] = {"jsonrpc": "2.0", "id": self._next_id, "method": method}
        if params is not None:
            message["params"] = params

        response = self._client.post("/mcp", headers=self._headers, json=message)
        assert response.status_code == 200, response.text

        session_id = response.headers.get("mcp-session-id")
        if session_id:
            self._headers["mcp-session-id"] = session_id

        body = response.json()
        assert "error" not in body, body
        return body["result"]

    def notify(self, method: str) -> None:
        self._client.post("/mcp", headers=self._headers, json={"jsonrpc": "2.0", "method": method})

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.request("tools/call", {"name": name, "arguments": arguments or {}})


def tool_payload(result: dict[str, Any]) -> Any:
    """Decode the JSON text content returned by a successful MCP tool call."""
    assert result["isError"] is False, result
    return json.loads(result["content"][0]["text"])


@pytest.fixture
def mcp_client(client: TestClient, auth_headers: dict[str, str]) -> McpClient:
    mcp = McpClient(client, auth_headers)
    mcp.initialize()
    return mcp


@pytest.fixture
def anonymous_mcp_client(client: TestClient) -> McpClient:
    mcp = McpClient(client, headers={})
    mcp.initialize()
    return mcp
