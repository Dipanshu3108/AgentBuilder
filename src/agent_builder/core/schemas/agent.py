"""Agent builder input/output and the persisted agent record."""
from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from pydantic import Field

from .builder import BuilderErrorResponse, BuilderPendingResponse, SpecOrQuestions
from .common import StrictModel
from .models import ModelReference

NAME_PATTERN = r"^[a-z0-9]+(?:[-_][a-z0-9]+)*$"


class BuildAgentRequest(StrictModel):
    name: str = Field(pattern=NAME_PATTERN)
    description: str = Field(min_length=1)
    builder_model_id: str
    agent_model_id: str
    clarification_answers: dict[str, str] = Field(default_factory=dict)


class AgentSpec(StrictModel):
    """Approval-ready output produced by the builder and stored in the registry."""

    name: str = Field(description="Machine-friendly name: lowercase, hyphens or underscores.")
    display_name: str
    purpose: str = Field(description="One or two clear sentences describing what the agent does.")
    system_prompt: str = Field(
        description="Complete system prompt for the new agent: role, task, constraints, output format."
    )
    tools: list[str] = Field(default_factory=list, description="Tool ids chosen from the catalog.")
    skills: list[str] = Field(default_factory=list, description="Skill ids chosen from the catalog.")
    model: ModelReference
    rationale: str = Field(description="Why these tools and skills were chosen (for the reviewer).")
    # Contract used to connect agents. Defaults keep records saved before contracts existed valid.
    accepts: str = Field(
        default="",
        description="What the agent expects in input `message` and `data`, e.g. 'data.text: relation lines'.",
    )
    returns: str = Field(
        default="",
        description="What the agent puts in output `data` when Done, e.g. 'data: {node_count, edge_count}'.",
    )


class BuilderDecision(SpecOrQuestions):
    """Private structured LLM output, converted into the public response envelope."""

    spec: AgentSpec | None = None


class BuilderDoneResponse(StrictModel):
    status: Literal["Done"] = "Done"
    message: AgentSpec


BuilderResponse = BuilderDoneResponse | BuilderPendingResponse | BuilderErrorResponse


class AgentRecord(StrictModel):
    """AgentSpec plus bookkeeping. This is the row/document in the registry."""

    agent_id: str = Field(default_factory=lambda: str(uuid4()))
    spec: AgentSpec
    version: int = 1
    status: Literal["approved", "archived"] = "approved"
    raw_description: str = Field(description="What the user originally typed.")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def id(self) -> str:
        return f"{self.spec.name}@v{self.version}"
