"""Pydantic models for the auth endpoint."""

from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
