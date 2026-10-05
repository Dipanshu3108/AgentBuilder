"""Base model and the portable input/output envelopes every runnable shares.

Input and output mirror each other, so one agent's Done output can be passed straight in as the
next agent's input: `message` carries text, `data` carries structured values.
"""
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class ErrorMessage(StrictModel):
    error: str


class AgentInput(StrictModel):
    """Portable input envelope for user-to-agent and agent-to-agent calls."""

    message: str = Field(description="The task or text for the agent.")
    data: dict[str, Any] = Field(default_factory=dict, description="Structured input values.")
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Run metadata and `answers` to questions the agent asked while Pending.",
    )


class AgentOutput(StrictModel):
    status: Literal["Done", "Pending", "Error"]
    message: str = Field(
        description="Done: short result summary. Pending: one question for the user. Error: reason."
    )
    data: dict[str, Any] = Field(default_factory=dict, description="Structured results, if any.")
