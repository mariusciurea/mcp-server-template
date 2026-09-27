"""Pydantic models for network routers and the dummy tool payloads."""

from enum import Enum

from pydantic import BaseModel, Field


class RouterStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"


class RouterDevice(BaseModel):
    id: str
    hostname: str
    ip_address: str
    vendor: str
    location: str
    status: RouterStatus


class CommandRequest(BaseModel):
    router_id: str = Field(description="ID of the target router")
    command: str = Field(min_length=1, description="CLI command to run")


class CommandResult(BaseModel):
    router_id: str
    command: str
    output: str
    success: bool


class RouterStatusReport(BaseModel):
    router_id: str
    status: RouterStatus
    uptime_seconds: int
    cpu_usage_percent: float
    memory_usage_percent: float
