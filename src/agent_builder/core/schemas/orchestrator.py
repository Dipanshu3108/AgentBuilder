"""Orchestrator builder input/output and the persisted orchestrator record.

An orchestrator is a fixed plan of steps. Each step calls one agent; `after` lists the steps it
waits for, so steps without a dependency between them run in parallel.
"""
from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from pydantic import Field

from .agent import NAME_PATTERN
from .builder import BuilderErrorResponse, BuilderPendingResponse, SpecOrQuestions
from .common import StrictModel


class Step(StrictModel):
    id: str = Field(pattern=NAME_PATTERN, description="Short unique step id, e.g. 'extract'.")
    instruction: str = Field(description="What this step must do within the overall task.")
    agent: str = Field(description="Name of an existing agent, or the name for a new agent.")
    new_agent_description: str = Field(
        default="",
        description="Only when `agent` does not exist yet: a full description to build it from.",
    )
    after: list[str] = Field(default_factory=list, description="Step ids this step waits for.")
    reason: str = Field(description="Why this agent fits this step (for the reviewer).")
    on_error: Literal["stop", "continue"] = Field(
        default="stop", description="stop: fail the run. continue: later steps run without it."
    )
    retries: int = Field(default=0, ge=0, le=3, description="Extra attempts after an Error.")
    version: int | None = Field(
        default=None, description="Pinned agent version. Set by the application at approval."
    )


class OrchestratorSpec(StrictModel):
    name: str
    display_name: str
    purpose: str = Field(description="One or two sentences describing the end-to-end task.")
    steps: list[Step] = Field(min_length=1)
    rationale: str = Field(description="Why the task was split this way (for the reviewer).")
    accepts: str = Field(default="", description="What the orchestrator needs in input message/data.")
    returns: str = Field(default="", description="What the final step puts in output data.")


class BuildOrchestratorRequest(StrictModel):
    name: str = Field(pattern=NAME_PATTERN)
    description: str = Field(min_length=1)
    builder_model_id: str
    agent_model_id: str = Field(description="Model for any new sub-agents the plan needs.")
    clarification_answers: dict[str, str] = Field(default_factory=dict)
    feedback: list[str] = Field(default_factory=list, description="Reviewer feedback, oldest first.")
    previous_plan: OrchestratorSpec | None = None


class OrchestratorDecision(SpecOrQuestions):
    spec: OrchestratorSpec | None = None


class OrchestratorDoneResponse(StrictModel):
    status: Literal["Done"] = "Done"
    message: OrchestratorSpec


OrchestratorBuilderResponse = (
    OrchestratorDoneResponse | BuilderPendingResponse | BuilderErrorResponse
)


class OrchestratorRecord(StrictModel):
    """A saved orchestrator. A draft holds an approved plan whose sub-agents may not exist yet."""

    orchestrator_id: str = Field(default_factory=lambda: str(uuid4()))
    spec: OrchestratorSpec
    version: int = 1
    status: Literal["draft", "approved", "archived"] = "draft"
    request: BuildOrchestratorRequest
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def id(self) -> str:
        return f"{self.spec.name}@v{self.version}"
