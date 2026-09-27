"""Application configuration, loaded from environment variables / .env."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Typed settings for the MCP service. See .env.example for all keys."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "MCP Router Template"
    app_description: str = "Dummy MCP server for managing network routers"

    # JWT auth
    jwt_secret_key: str = Field(description="Secret key used to sign JWT access tokens")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30

    # Single dummy admin account used to issue tokens (no user database)
    admin_username: str = "admin"
    admin_password: str = Field(description="Password for the dummy admin user")

    # Rate limiting, e.g. "10/minute" (see slowapi rate string format)
    rate_limit: str = "10/minute"

    # Dummy "database": a JSON file with router inventory data
    routers_data_file: Path = PROJECT_ROOT / "data" / "routers.json"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance, built once per process."""
    return Settings()
