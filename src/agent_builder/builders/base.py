"""The loop every builder shares: resolve models, ask the LLM, clarify or propose, validate.

A builder subclass supplies only what differs: the context it chooses from, its prompts, its
decision schema, how the application overrides the proposal, its checks, and how an approved
proposal is persisted. `propose()` never writes anything; only `approve()` does.
"""
from abc import ABC, abstractmethod
from typing import Any, ClassVar, Generic, TypeVar

from pydantic import BaseModel

from ..core.llm import structured_completion
from ..core.schemas import (
    BuilderErrorResponse,
    BuilderPendingResponse,
    ErrorMessage,
    PendingMessage,
    SpecOrQuestions,
)
from ..registry.base import Registry

RequestT = TypeVar("RequestT", bound=BaseModel)
SpecT = TypeVar("SpecT", bound=BaseModel)
DoneT = TypeVar("DoneT", bound=BaseModel)
ContextT = TypeVar("ContextT")


class BuildValidationError(ValueError):
    pass


class Builder(ABC, Generic[RequestT, SpecT, DoneT, ContextT]):
    decision_type: ClassVar[type[SpecOrQuestions]]
    done_type: ClassVar[type[BaseModel]]

    @abstractmethod
    def model_ids(self, request: RequestT) -> dict[str, str]:
        """Model ids that must exist, keyed by role. The "builder" role makes the LLM call."""

    @abstractmethod
    async def load_context(self, request: RequestT, registry: Registry) -> ContextT:
        """Whatever the LLM chooses from (a catalog, a list of agents, ...)."""

    @abstractmethod
    def system_prompt(self, context: ContextT) -> str: ...

    @abstractmethod
    def user_message(self, request: RequestT) -> str: ...

    def finalize(self, spec: SpecT, request: RequestT) -> SpecT:
        """Override fields the LLM must not decide, such as the requested name."""
        return spec

    def validate(self, spec: SpecT, context: ContextT) -> None:
        """Deterministic checks; raise BuildValidationError on failure."""

    @abstractmethod
    def approve(self, request: RequestT, response: DoneT, registry: Registry) -> Any:
        """Persist a reviewed proposal and return the saved record."""

    async def propose(
        self, request: RequestT, registry: Registry
    ) -> DoneT | BuilderPendingResponse | BuilderErrorResponse:
        models = {}
        for role, model_id in self.model_ids(request).items():
            model = registry.get_model(model_id)
            if model is None:
                return BuilderErrorResponse(
                    message=ErrorMessage(error=f"unknown {role} model id: {model_id}")
                )
            models[role] = model

        try:
            context = await self.load_context(request, registry)
            decision = await structured_completion(
                models["builder"],
                self.system_prompt(context),
                self.user_message(request),
                self.decision_type,
            )
            if decision.questions:
                return BuilderPendingResponse(message=PendingMessage(questions=decision.questions))

            spec = getattr(decision, "spec", None)
            if spec is None:
                raise BuildValidationError("builder returned neither a spec nor questions")
            spec = self.finalize(spec, request)
            self.validate(spec, context)
            return self.done_type(message=spec)
        except Exception as exc:
            return BuilderErrorResponse(message=ErrorMessage(error=str(exc)))
