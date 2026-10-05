"""The agent builder: produce a proposal, then persist it only after approval."""
from uuid import uuid4

from ...catalog.loader import load_catalog
from ...core.schemas import (
    AgentRecord,
    AgentSpec,
    BuildAgentRequest,
    BuilderDecision,
    BuilderDoneResponse,
    BuilderResponse,
    Catalog,
    ModelReference,
)
from ...registry.base import Registry
from ..base import Builder
from .prompts import BUILDER_SYSTEM_PROMPT, build_user_message
from .validate import SpecValidationError, validate_spec


class AgentBuilder(Builder[BuildAgentRequest, AgentSpec, BuilderDoneResponse, Catalog]):
    decision_type = BuilderDecision
    done_type = BuilderDoneResponse

    def model_ids(self, request: BuildAgentRequest) -> dict[str, str]:
        return {"builder": request.builder_model_id, "agent": request.agent_model_id}

    async def load_context(self, request: BuildAgentRequest, registry: Registry) -> Catalog:
        return await load_catalog()

    def system_prompt(self, context: Catalog) -> str:
        return BUILDER_SYSTEM_PROMPT.format(catalog=context.as_prompt_block())

    def user_message(self, request: BuildAgentRequest) -> str:
        return build_user_message(request)

    def finalize(self, spec: AgentSpec, request: BuildAgentRequest) -> AgentSpec:
        return spec.model_copy(
            update={"name": request.name, "model": ModelReference(id=request.agent_model_id)}
        )

    def validate(self, spec: AgentSpec, context: Catalog) -> None:
        validate_spec(spec, context)

    def approve(
        self, request: BuildAgentRequest, response: BuilderDoneResponse, registry: Registry
    ) -> AgentRecord:
        """Persist an already reviewed proposal as a new approved version."""
        if response.message.name != request.name:
            raise SpecValidationError("proposal name does not match request")
        if response.message.model.id != request.agent_model_id:
            raise SpecValidationError("proposal model does not match request")
        if registry.get_model(request.agent_model_id) is None:
            raise SpecValidationError(f"unknown agent model id: {request.agent_model_id}")

        previous = registry.get(request.name)
        record = AgentRecord(
            agent_id=previous.agent_id if previous else str(uuid4()),
            spec=response.message,
            version=registry.next_version(request.name),
            raw_description=request.description,
        )
        return registry.save(record)


AGENT_BUILDER = AgentBuilder()


async def build_agent(request: BuildAgentRequest, registry: Registry) -> BuilderResponse:
    """Return a strict proposal envelope. This function never writes an agent record."""
    return await AGENT_BUILDER.propose(request, registry)


def approve_agent(
    request: BuildAgentRequest, response: BuilderDoneResponse, registry: Registry
) -> AgentRecord:
    return AGENT_BUILDER.approve(request, response, registry)
