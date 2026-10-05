"""Approved agents and their contracts: what the orchestrator builder can assign to steps."""
from ..core.schemas import AgentEntry
from ..registry.base import Registry


def load_agents(registry: Registry) -> list[AgentEntry]:
    """Latest approved version of every agent."""
    latest: dict[str, AgentEntry] = {}
    for record in registry.list():
        name = record.spec.name
        if record.status != "approved":
            continue
        if name not in latest or record.version > latest[name].version:
            latest[name] = AgentEntry(
                name=name,
                version=record.version,
                purpose=record.spec.purpose,
                accepts=record.spec.accepts,
                returns=record.spec.returns,
            )
    return sorted(latest.values(), key=lambda entry: entry.name)
