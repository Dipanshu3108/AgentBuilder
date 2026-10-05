"""The tool builder: write code and tests, check and test them in the sandbox, fix failures,
and publish only after human approval."""
import asyncio
from collections.abc import Callable
from dataclasses import dataclass

from ...catalog.tools import load_tools
from ...core.schemas import (
    BuilderErrorResponse,
    BuildToolRequest,
    ErrorMessage,
    TestReport,
    ToolBuilderResponse,
    ToolDecision,
    ToolDoneResponse,
    ToolEntry,
    ToolRecord,
    ToolSpec,
)
from ...registry.base import Registry
from ..base import Builder, BuildValidationError
from .prompts import TOOL_SYSTEM_PROMPT, build_user_message
from .publish import publish_tool
from .sandbox import run_tests

MAX_FIX_ATTEMPTS = 3


@dataclass(frozen=True)
class ToolContext:
    existing: list[ToolEntry]
    reserved: set[str]  # names of tools this builder did not create (core tools)


def _failure_text(report: TestReport) -> str:
    if report.problems:
        return "Static checks failed:\n" + "\n".join(f"- {problem}" for problem in report.problems)
    return f"Tests failed:\n{report.output}"


class ToolBuilder(Builder[BuildToolRequest, ToolSpec, ToolDoneResponse, ToolContext]):
    decision_type = ToolDecision
    done_type = ToolDoneResponse

    def __init__(self) -> None:
        self.progress: Callable[[str], None] = lambda _message: None

    def model_ids(self, request: BuildToolRequest) -> dict[str, str]:
        return {"builder": request.builder_model_id}

    async def load_context(self, request: BuildToolRequest, registry: Registry) -> ToolContext:
        existing = await load_tools()
        generated = {record.spec.name for record in registry.list_tools()}
        return ToolContext(existing=existing, reserved={tool.id for tool in existing} - generated)

    def system_prompt(self, context: ToolContext) -> str:
        tools = "\n".join(f"- `{tool.id}`: {tool.description}" for tool in context.existing) or "(none)"
        return TOOL_SYSTEM_PROMPT.format(tools=tools)

    def user_message(self, request: BuildToolRequest) -> str:
        return build_user_message(request)

    def finalize(self, spec: ToolSpec, request: BuildToolRequest) -> ToolSpec:
        # The server adds the "Use when:" prefix itself; drop one the LLM repeated.
        use_when = spec.use_when.strip()
        if use_when.lower().startswith("use when"):
            use_when = use_when[len("use when"):].lstrip(" :")
        return spec.model_copy(update={"name": request.name, "use_when": use_when})

    def validate(self, spec: ToolSpec, context: ToolContext) -> None:
        if spec.name in context.reserved:
            raise BuildValidationError(f"'{spec.name}' is a core tool; choose another name")

    async def propose(self, request: BuildToolRequest, registry: Registry) -> ToolBuilderResponse:
        """Generate, then check and test; feed failures back to the LLM up to MAX_FIX_ATTEMPTS."""
        current = request
        failure = ""
        for attempt in range(MAX_FIX_ATTEMPTS + 1):
            self.progress("Writing code and tests..." if attempt == 0 else f"Fixing (attempt {attempt})...")
            response = await super().propose(current, registry)
            if not isinstance(response, ToolDoneResponse):
                return response
            self.progress("Running static checks and sandboxed tests...")
            report = await asyncio.to_thread(run_tests, response.message)
            if report.passed:
                return response.model_copy(update={"report": report})
            failure = _failure_text(report)
            self.progress(failure.splitlines()[0])
            current = current.model_copy(update={"previous": response.message, "failure": failure})
        return BuilderErrorResponse(
            message=ErrorMessage(error=f"still failing after {MAX_FIX_ATTEMPTS} fixes. {failure}")
        )

    def approve(
        self, request: BuildToolRequest, response: ToolDoneResponse, registry: Registry
    ) -> ToolRecord:
        if response.message.name != request.name:
            raise BuildValidationError("proposal name does not match request")
        if response.report is None or not response.report.passed:
            raise BuildValidationError("only a tool whose tests passed can be published")
        return publish_tool(response.message, response.report, request.description, registry)


TOOL_BUILDER = ToolBuilder()
