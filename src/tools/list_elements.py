"""Tool: list_elements - returns the router inventory from a JSON file."""

import json

from src.core.settings import get_settings
from src.data_models.devices import RouterDevice


def list_elements() -> list[RouterDevice]:
    """Return all network routers from the JSON inventory file."""
    settings = get_settings()
    raw_routers = json.loads(settings.routers_data_file.read_text(encoding="utf-8"))
    return [RouterDevice.model_validate(router) for router in raw_routers]


def find_router(router_id: str) -> RouterDevice:
    """Return a single router by ID.

    Raises:
        ValueError: If no router with this ID exists.
    """
    for router in list_elements():
        if router.id == router_id:
            return router
    raise ValueError(f"Unknown router id: {router_id}")
