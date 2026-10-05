"""Turn one agent's output into the next agent's input."""
from typing import Any

from ..core.schemas import AgentInput, AgentOutput


def next_input(output: AgentOutput, context: dict[str, Any] | None = None) -> AgentInput:
    """Pass-through: a Done output's message and data become the next input's message and data."""
    if output.status != "Done":
        raise ValueError(f"only a Done output can feed the next agent, got {output.status}")
    return AgentInput(message=output.message, data=output.data, context=context or {})


def step_input(
    step_id: str, instruction: str, task: AgentInput, upstream: dict[str, AgentOutput]
) -> AgentInput:
    """Input for an orchestrator step: its instruction plus the task (first steps), the single
    upstream output (pass-through), or every upstream output keyed by step id (fan-in)."""
    if not upstream:
        message, data = task.message, task.data
    elif len(upstream) == 1:
        (only,) = upstream.values()
        message, data = only.message, only.data
    else:
        message = "\n".join(f"[{sid}] {output.message}" for sid, output in upstream.items())
        data = {sid: output.data for sid, output in upstream.items()}
    return AgentInput(
        message=f"Your step: {instruction}\n\n{message}",
        data=data,
        context={**task.context, "task": task.message, "step": step_id},
    )
