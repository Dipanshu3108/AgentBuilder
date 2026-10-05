"""Stage 1 of the orchestrator builder: end-to-end flow → steps → agent per step (or a gap)."""
from dataclasses import dataclass

from ...catalog.agents import load_agents
from ...catalog.loader import load_catalog
from ...core.schemas import (
    AgentEntry,
    BuildOrchestratorRequest,
    Catalog,
    OrchestratorDecision,
    OrchestratorDoneResponse,
    OrchestratorRecord,
    OrchestratorSpec,
)
from ...registry.base import Registry
from ..base import Builder
from .prompts import PLANNER_SYSTEM_PROMPT, build_user_message
from .validate import validate_plan


@dataclass(frozen=True)
class PlannerContext:
    agents: list[AgentEntry]
    catalog: Catalog


class OrchestratorPlanner(
    Builder[BuildOrchestratorRequest, OrchestratorSpec, OrchestratorDoneResponse, PlannerContext]
):
    decision_type = OrchestratorDecision
    done_type = OrchestratorDoneResponse

    def model_ids(self, request: BuildOrchestratorRequest) -> dict[str, str]:
        return {"builder": request.builder_model_id, "agent": request.agent_model_id}

    async def load_context(self, request: BuildOrchestratorRequest, registry: Registry) -> PlannerContext:
        return PlannerContext(agents=load_agents(registry), catalog=await load_catalog())

    def system_prompt(self, context: PlannerContext) -> str:
        agents = "\n".join(entry.as_prompt_line() for entry in context.agents) or "(none yet)"
        return PLANNER_SYSTEM_PROMPT.format(agents=agents, catalog=context.catalog.as_prompt_block())

    def user_message(self, request: BuildOrchestratorRequest) -> str:
        return build_user_message(request)

    def finalize(self, spec: OrchestratorSpec, request: BuildOrchestratorRequest) -> OrchestratorSpec:
        steps = [step.model_copy(update={"version": None}) for step in spec.steps]
        return spec.model_copy(update={"name": request.name, "steps": steps})

    def validate(self, spec: OrchestratorSpec, context: PlannerContext) -> None:
        validate_plan(spec, {entry.name for entry in context.agents})

    def approve(
        self, request: BuildOrchestratorRequest, response: OrchestratorDoneResponse, registry: Registry
    ) -> OrchestratorRecord:
        """Approving the plan saves a draft; sub-agents are built next, then the final approval."""
        draft = registry.get_orchestrator(request.name, status="draft")
        latest = registry.get_orchestrator(request.name, status=None)
        record = OrchestratorRecord(
            spec=response.message,
            version=draft.version if draft else (latest.version + 1 if latest else 1),
            status="draft",
            request=request.model_copy(update={"previous_plan": None}),
        )
        if latest is not None:
            record.orchestrator_id = latest.orchestrator_id
        return registry.save_orchestrator(record)


PLANNER = OrchestratorPlanner()
