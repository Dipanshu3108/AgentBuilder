"""Deterministic checks on a plan: graph shape, references, and how each step's agent resolves."""
import re

from ...core.schemas import NAME_PATTERN, OrchestratorSpec
from ..base import BuildValidationError


def validate_plan(spec: OrchestratorSpec, existing_agents: set[str]) -> None:
    problems = []
    ids = [step.id for step in spec.steps]
    duplicates = sorted({step_id for step_id in ids if ids.count(step_id) > 1})
    if duplicates:
        problems.append(f"duplicate step ids: {duplicates}")

    known = set(ids)
    for step in spec.steps:
        unknown = set(step.after) - known
        if unknown:
            problems.append(f"step '{step.id}' waits for unknown steps: {sorted(unknown)}")
        if step.id in step.after:
            problems.append(f"step '{step.id}' waits for itself")
        if step.agent not in existing_agents:
            if not step.new_agent_description.strip():
                problems.append(
                    f"step '{step.id}': agent '{step.agent}' does not exist and has no new_agent_description"
                )
            if not re.fullmatch(NAME_PATTERN, step.agent):
                problems.append(f"step '{step.id}': invalid new agent name '{step.agent}'")

    if not problems:
        if _has_cycle(spec):
            problems.append("steps form a cycle")
        terminals = terminal_steps(spec)
        if len(terminals) != 1:
            problems.append(
                f"plan must end in exactly one final step, found {sorted(terminals)}; "
                "add a step that combines them"
            )
    if problems:
        raise BuildValidationError("; ".join(problems))


def terminal_steps(spec: OrchestratorSpec) -> list[str]:
    """Steps no other step waits for."""
    waited_on = {dep for step in spec.steps for dep in step.after}
    return [step.id for step in spec.steps if step.id not in waited_on]


def _has_cycle(spec: OrchestratorSpec) -> bool:
    remaining = {step.id: set(step.after) for step in spec.steps}
    while remaining:
        ready = [step_id for step_id, deps in remaining.items() if not deps]
        if not ready:
            return True
        for step_id in ready:
            del remaining[step_id]
        for deps in remaining.values():
            deps.difference_update(ready)
    return False
