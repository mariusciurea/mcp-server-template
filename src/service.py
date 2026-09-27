"""Entrypoint: FastAPI app exposing router tools over MCP, with JWT auth
and rate limiting.

Run with: python -m src.service
Or:       uvicorn src.service:app --reload
"""

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_mcp import FastApiMCP
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from src.core.rate_limit import limiter
from src.core.security import authenticate_user, create_access_token, get_current_user
from src.core.settings import get_settings
from src.data_models.auth import Token
from src.data_models.devices import (
    CommandRequest,
    CommandResult,
    RouterDevice,
    RouterStatusReport,
)
from src.tools.list_elements import list_elements as list_elements_tool
from src.tools.router_status import get_router_status as get_router_status_tool
from src.tools.send_command import send_command as send_command_tool

settings = get_settings()

app = FastAPI(title=settings.app_name, description=settings.app_description)

# Rate limiting: reject clients that exceed settings.rate_limit
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


@app.post("/auth/token", response_model=Token, tags=["auth"])
@limiter.limit(settings.rate_limit)
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()) -> Token:
    """Exchange the admin username/password for a JWT access token."""
    if not authenticate_user(form_data.username, form_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    return Token(access_token=create_access_token(subject=form_data.username))


@app.get(
    "/tools/routers",
    response_model=list[RouterDevice],
    operation_id="list_elements",
    tags=["tools"],
)
@limiter.limit(settings.rate_limit)
def list_elements(request: Request, current_user: str = Depends(get_current_user)) -> list[RouterDevice]:
    """List all network routers in the inventory."""
    return list_elements_tool()


@app.post(
    "/tools/routers/command",
    response_model=CommandResult,
    operation_id="send_command",
    tags=["tools"],
)
@limiter.limit(settings.rate_limit)
def send_command(
    request: Request,
    command_request: CommandRequest,
    current_user: str = Depends(get_current_user),
) -> CommandResult:
    """Send a CLI command to a router and return the simulated output."""
    try:
        return send_command_tool(command_request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@app.get(
    "/tools/routers/{router_id}/status",
    response_model=RouterStatusReport,
    operation_id="get_router_status",
    tags=["tools"],
)
@limiter.limit(settings.rate_limit)
def get_router_status(
    request: Request,
    router_id: str,
    current_user: str = Depends(get_current_user),
) -> RouterStatusReport:
    """Get simulated live status metrics for one router."""
    try:
        return get_router_status_tool(router_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# Exposes only the 3 tool endpoints as MCP tools at /mcp (not /auth/token)
# using the Streamable HTTP transport ("type": "http" in MCP client configs).
# The Authorization header is forwarded automatically, so MCP clients
# authenticate with the same JWT used for the REST API.
mcp = FastApiMCP(
    app,
    name=settings.app_name,
    description=settings.app_description,
    include_operations=["list_elements", "send_command", "get_router_status"],
)
mcp.mount_http()


if __name__ == "__main__":
    uvicorn.run("src.service:app", host="0.0.0.0", port=8000, reload=True)
