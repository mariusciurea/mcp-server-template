"""Tool: get_router_status - simulates live health metrics for a router."""

import random

from src.data_models.devices import RouterStatusReport
from src.tools.list_elements import find_router


def get_router_status(router_id: str) -> RouterStatusReport:
    """Return simulated live status metrics for a single router.

    Raises:
        ValueError: If the router does not exist.
    """
    router = find_router(router_id)

    return RouterStatusReport(
        router_id=router.id,
        status=router.status,
        uptime_seconds=random.randint(1_000, 5_000_000),
        cpu_usage_percent=round(random.uniform(1.0, 90.0), 1),
        memory_usage_percent=round(random.uniform(10.0, 80.0), 1),
    )
