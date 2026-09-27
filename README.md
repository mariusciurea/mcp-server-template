# MCP Router Template

A professional Python MCP server template built with **FastAPI** and
**fastapi-mcp**. It exposes 3 dummy tools for managing network routers,
protected with JWT authentication and rate limiting. There is no database —
the router inventory is read from a JSON file.

## Structure

```
src/
├── service.py            # entrypoint: FastAPI app + auth + rate limit + MCP mount
├── core/
│   ├── settings.py        # config (Pydantic Settings, loaded from .env)
│   ├── security.py        # JWT issuing/validation
│   └── rate_limit.py      # limiter (slowapi)
├── data_models/
│   ├── auth.py             # Token model
│   └── devices.py          # Pydantic models: RouterDevice, CommandRequest, ...
├── tools/
│   ├── list_elements.py    # tool: lists the routers
│   ├── send_command.py     # tool: simulates sending a CLI command
│   └── router_status.py    # tool: simulates live metrics for a router
└── data/
    └── routers.json        # dummy "database" of routers
```

## Install

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy .env.example .env        # then fill in JWT_SECRET_KEY and ADMIN_PASSWORD
```

## Run

```bash
python -m src.service
# or
uvicorn src.service:app --reload
```

The server starts on `http://127.0.0.1:8000`. Interactive API docs are at
`/docs`, and the MCP server is mounted at `/mcp` (Streamable HTTP transport).

## Authentication

There is no user database — just a single admin account defined in `.env`.

```bash
curl -X POST http://127.0.0.1:8000/auth/token \
  -d "username=admin&password=<password-from-.env>"
```

The response contains an `access_token` JWT, used as
`Authorization: Bearer <token>` for every tool call, both over REST and over
MCP (fastapi-mcp forwards the `Authorization` header through to the tools
automatically).

## Rate limiting

Every endpoint (including `/auth/token`) is limited according to
`RATE_LIMIT` in `.env` (default `10/minute`, per client IP). Exceeding the
limit returns `429`.

## Available tools

| Tool | Method | Description |
|---|---|---|
| `list_elements` | GET `/tools/routers` | Lists all routers in the inventory |
| `send_command` | POST `/tools/routers/command` | Simulates running a CLI command on a router |
| `get_router_status` | GET `/tools/routers/{router_id}/status` | Simulates live metrics (uptime, CPU, memory) |

These are plain FastAPI endpoints protected with `Depends(get_current_user)`.
`fastapi-mcp` exposes exactly these three as MCP tools (via
`include_operations` in `service.py`) — the `/auth/token` login endpoint is
deliberately excluded so it can never show up as a callable tool.

## Connecting an MCP client (e.g. Claude Code)

1. Get a token (see Authentication above).
2. Register the server, passing the token as a header:

```bash
claude mcp add --transport http router-tools http://127.0.0.1:8000/mcp \
  --header "Authorization: Bearer <token>"
```

The JWT expires after `JWT_EXPIRE_MINUTES` (default 30). When it does, get a
fresh token and re-run `claude mcp add` (or update the header in your MCP
client config).

## Dependency note

`requirements.txt` pins `mcp<2.0.0` because `fastapi-mcp` 0.4.0 is not yet
compatible with the `mcp` 2.x SDK (an internal constructor signature
changed). Re-check whether this pin is still needed when upgrading
`fastapi-mcp`.

## Configuration (`.env`)

See [.env.example](.env.example) for all available variables
(`JWT_SECRET_KEY`, `JWT_ALGORITHM`, `JWT_EXPIRE_MINUTES`, `ADMIN_USERNAME`,
`ADMIN_PASSWORD`, `RATE_LIMIT`).

## Extending

- Adding a new tool means: a function in `tools/`, a data model in
  `data_models/` (if needed), and an endpoint in `service.py` with an
  explicit `operation_id` added to `include_operations`.
- To connect to real routers (SSH/NETCONF), replace the dummy logic in
  `tools/send_command.py` without changing the rest of the app.
