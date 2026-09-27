"""Tool: send_command - simulates running a CLI command on a router."""

from src.data_models.devices import CommandRequest, CommandResult
from src.tools.list_elements import find_router

# Canned outputs for a few well-known commands, keyed by lowercased command text
_DUMMY_OUTPUTS = {
    "show version": "Dummy OS v1.2.3, uptime 42 days",
    "show interfaces": "GigabitEthernet0/1 is up, line protocol is up",
    "show running-config": "! Dummy running configuration\nhostname {hostname}",
}


def send_command(request: CommandRequest) -> CommandResult:
    """Simulate sending a CLI command to a router and return its output.

    Raises:
        ValueError: If the target router does not exist.
    """
    router = find_router(request.router_id)

    template = _DUMMY_OUTPUTS.get(request.command.lower().strip())
    output = (
        template.format(hostname=router.hostname)
        if template
        else f"% Simulated output for '{request.command}' on {router.hostname}"
    )

    return CommandResult(
        router_id=router.id,
        command=request.command,
        output=output,
        success=True,
    )
