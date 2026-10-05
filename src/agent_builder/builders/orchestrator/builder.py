"""Stages 2–3 of the orchestrator builder: fill gaps with new agents, then final approval.

Stage 1 (planning) lives in planner.py. The CLI drives the stages in order; each stage reads the
draft from the registry, so the flow can stop after any stage and resume later.
"""
import asyncio

from ...connectors.contracts import check_compatibility, check_fan_in
from ...core.schemas import (
    BuildAgentRequest,
    Compatibility,
    ModelConfig,
    OrchestratorRecord,
    OrchestratorSpec,
    Step,
)
from ...registry.base import Registry
from ..base import BuildValidationError
from .validate import validate_plan


def missing_agents(spec: OrchestratorSpec, registry: Registry) -> list[Step]:
    """One step per agent name that has no approved version yet."""
    missing: dict[str, Step] = {}
    for step in spec.steps:
        record = registry.get(step.agent)
        if (record is None or record.status != "approved") and step.agent not in missing:
            missing[step.agent] = step
    return list(missing.values())


def _input_shape(step: Step, spec: OrchestratorSpec, registry: Registry) -> str:
    """How the runtime will build this step's input (see connectors.mapping.step_input)."""

    def returns(step_id: str) -> str:
        upstream = next(s for s in spec.steps if s.id == step_id)
        record = registry.get(upstream.agent)
        described = record.spec.returns if record else ""
        return described or upstream.instruction

    if not step.after:
        return f"the workflow's own input: {spec.accepts or 'the task as message text'}"
    if len(step.after) == 1:
        dep = step.after[0]
        return f"step '{dep}' output passed through as message and data; it returns: {returns(dep)}"
    keys = "; ".join(f"data.{dep} = step '{dep}' data ({returns(dep)})" for dep in step.after)
    return (
        "the outputs of several parallel steps at once. `data` is keyed by step id: "
        f"{keys}. `message` lists each step's summary prefixed with [step id]. Use these exact "
        "field names in the contract"
    )


def gap_request(step: Step, draft: OrchestratorRecord, registry: Registry) -> BuildAgentRequest:
    """Agent-builder request for a missing agent, with its place in the workflow as context."""
    return BuildAgentRequest(
        name=step.agent,
        description=(
            f"{step.new_agent_description}\n\n"
            f"This agent runs as step '{step.id}' of the '{draft.spec.name}' workflow "
            f"({draft.spec.purpose}). Its step instruction: {step.instruction}\n"
            f"Its input will be {_input_shape(step, draft.spec, registry)}."
        ),
        builder_model_id=draft.request.builder_model_id,
        agent_model_id=draft.request.agent_model_id,
    )


async def check_links(
    spec: OrchestratorSpec, registry: Registry, model: ModelConfig
) -> list[tuple[str, str, Compatibility]]:
    """Contract check per step with dependencies; a fan-in step is checked against all its
    upstream steps together, since that is what it receives."""

    def agent_spec(step_id: str):
        return registry.get(next(s for s in spec.steps if s.id == step_id).agent).spec

    async def check(step: Step) -> tuple[str, str, Compatibility]:
        if len(step.after) == 1:
            result = await check_compatibility(agent_spec(step.after[0]), agent_spec(step.id), model)
        else:
            upstream = {dep: agent_spec(dep) for dep in step.after}
            result = await check_fan_in(upstream, agent_spec(step.id), model)
        return " + ".join(step.after), step.id, result

    return list(await asyncio.gather(*(check(step) for step in spec.steps if step.after)))


def approve_orchestrator(draft: OrchestratorRecord, registry: Registry) -> OrchestratorRecord:
    """Pin every step to its agent's latest approved version and save as approved."""
    missing = missing_agents(draft.spec, registry)
    if missing:
        raise BuildValidationError(f"agents not built yet: {sorted(step.agent for step in missing)}")
    validate_plan(draft.spec, {step.agent for step in draft.spec.steps})
    steps = [
        step.model_copy(update={"version": registry.get(step.agent).version, "new_agent_description": ""})
        for step in draft.spec.steps
    ]
    record = draft.model_copy(
        update={"spec": draft.spec.model_copy(update={"steps": steps}), "status": "approved"}
    )
    return registry.save_orchestrator(record)
