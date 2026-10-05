"""Time each agent call as a StepTrace and save whole runs to the registry."""
from datetime import UTC, datetime
from typing import Literal

from ..core.schemas import AgentInput, AgentOutput, RunTrace, StepTrace
from ..registry.base import Registry
from .agent_runner import Ask, LoadedAgent, run_until_settled


async def traced_step(step: str, agent: LoadedAgent, agent_input: AgentInput, ask: Ask) -> StepTrace:
    started = datetime.now(UTC)
    output = await run_until_settled(agent, agent_input, ask)
    return StepTrace(
        step=step,
        agent=agent.record.id,
        input=agent_input,
        output=output,
        started_at=started,
        finished_at=datetime.now(UTC),
    )


def save_run(
    registry: Registry,
    kind: Literal["agent", "pipe", "orchestrator"],
    target: str,
    agent_input: AgentInput,
    steps: list[StepTrace],
    output: AgentOutput | None = None,
) -> RunTrace:
    """Save a finished run; its output defaults to the last step's output."""
    run = RunTrace(
        kind=kind,
        target=target,
        input=agent_input,
        output=output or steps[-1].output,
        steps=steps,
    )
    if steps:
        run.started_at = min(step.started_at for step in steps)
        run.finished_at = max(step.finished_at for step in steps)
    return registry.save_run(run)
