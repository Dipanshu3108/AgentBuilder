"""Tool builder input/output and the persisted tool record.

A generated tool is one Python module with one public function, plus a pytest module. What
the code may import is limited by the capabilities it declares (see builders/tool/checks.py).
"""
from datetime import UTC, datetime
from typing import Literal

from pydantic import Field

from .builder import BuilderErrorResponse, BuilderPendingResponse, SpecOrQuestions
from .common import StrictModel

TOOL_NAME_PATTERN = r"^[a-z][a-z0-9_]*$"

Capability = Literal["files", "http", "packages"]


class ToolSpec(StrictModel):
    name: str = Field(description="Python function name, snake_case, e.g. 'csv_to_json'.")
    description: str = Field(description="What the tool does, one or two sentences.")
    use_when: str = Field(description="One line telling the agent builder when to pick this tool.")
    capabilities: list[Capability] = Field(
        default_factory=list,
        description="files: read/write in the output dir via output_path. http: httpx requests. "
        "packages: imports beyond the standard-library allowlist. Empty for pure computation.",
    )
    code: str = Field(description="Complete source of tool.py: imports and the one public function.")
    tests: str = Field(description="Complete source of test_tool.py, using pytest.")
    rationale: str = Field(description="Design choices and why the capabilities are needed.")


class TestReport(StrictModel):
    __test__ = False  # not a pytest test class

    passed: bool
    problems: list[str] = Field(default_factory=list, description="Static check failures.")
    output: str = Field(default="", description="Tail of the pytest output.")
    isolated: bool = Field(description="Whether tests ran without network access.")


class BuildToolRequest(StrictModel):
    name: str = Field(pattern=TOOL_NAME_PATTERN)
    description: str = Field(min_length=1)
    builder_model_id: str
    clarification_answers: dict[str, str] = Field(default_factory=dict)
    feedback: list[str] = Field(default_factory=list, description="Reviewer feedback, oldest first.")
    previous: ToolSpec | None = Field(default=None, description="The attempt being revised or fixed.")
    failure: str = Field(default="", description="Why the previous attempt failed checks or tests.")


class ToolDecision(SpecOrQuestions):
    spec: ToolSpec | None = None


class ToolDoneResponse(StrictModel):
    status: Literal["Done"] = "Done"
    message: ToolSpec
    report: TestReport | None = None


ToolBuilderResponse = ToolDoneResponse | BuilderPendingResponse | BuilderErrorResponse


class ToolRecord(StrictModel):
    spec: ToolSpec
    version: int = 1
    status: Literal["approved", "disabled"] = "approved"
    code_sha256: str = Field(description="Hash of spec.code; the server refuses mismatching files.")
    report: TestReport
    raw_description: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def id(self) -> str:
        return f"{self.spec.name}@v{self.version}"
