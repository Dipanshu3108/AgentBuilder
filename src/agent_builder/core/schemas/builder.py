"""Builder envelopes shared by every builder (agent, orchestrator, tool)."""
from typing import Literal

from pydantic import Field, model_validator

from .common import ErrorMessage, StrictModel


class Clarification(StrictModel):
    id: str = Field(description="Stable machine-friendly key for the answer.")
    question: str


class SpecOrQuestions(StrictModel):
    """Base for a builder's private LLM output. Subclasses add `spec: <Spec> | None = None`."""

    questions: list[Clarification] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_spec_or_questions(self) -> "SpecOrQuestions":
        if (getattr(self, "spec", None) is None) == (not self.questions):
            raise ValueError("provide either spec or clarification questions")
        return self


class PendingMessage(StrictModel):
    questions: list[Clarification] = Field(min_length=1)


class BuilderPendingResponse(StrictModel):
    status: Literal["Pending"] = "Pending"
    message: PendingMessage


class BuilderErrorResponse(StrictModel):
    status: Literal["Error"] = "Error"
    message: ErrorMessage
