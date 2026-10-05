"""Strict contracts shared by the builders, registry, and runtime."""
from .agent import (
    NAME_PATTERN,
    AgentRecord,
    AgentSpec,
    BuildAgentRequest,
    BuilderDecision,
    BuilderDoneResponse,
    BuilderResponse,
)
from .builder import (
    BuilderErrorResponse,
    BuilderPendingResponse,
    Clarification,
    PendingMessage,
    SpecOrQuestions,
)
from .catalog import AgentEntry, Catalog, SkillEntry, ToolEntry
from .common import AgentInput, AgentOutput, ErrorMessage, StrictModel
from .connector import Compatibility
from .models import ModelConfig, ModelReference
from .orchestrator import (
    BuildOrchestratorRequest,
    OrchestratorBuilderResponse,
    OrchestratorDecision,
    OrchestratorDoneResponse,
    OrchestratorRecord,
    OrchestratorSpec,
    Step,
)
from .run import RunTrace, StepTrace
from .tool import (
    TOOL_NAME_PATTERN,
    BuildToolRequest,
    Capability,
    TestReport,
    ToolBuilderResponse,
    ToolDecision,
    ToolDoneResponse,
    ToolRecord,
    ToolSpec,
)

__all__ = [
    "NAME_PATTERN",
    "TOOL_NAME_PATTERN",
    "AgentEntry",
    "AgentInput",
    "AgentOutput",
    "AgentRecord",
    "AgentSpec",
    "BuildAgentRequest",
    "BuildOrchestratorRequest",
    "BuildToolRequest",
    "BuilderDecision",
    "BuilderDoneResponse",
    "BuilderErrorResponse",
    "BuilderPendingResponse",
    "BuilderResponse",
    "Capability",
    "Catalog",
    "Clarification",
    "Compatibility",
    "ErrorMessage",
    "ModelConfig",
    "ModelReference",
    "OrchestratorBuilderResponse",
    "OrchestratorDecision",
    "OrchestratorDoneResponse",
    "OrchestratorRecord",
    "OrchestratorSpec",
    "PendingMessage",
    "RunTrace",
    "SkillEntry",
    "SpecOrQuestions",
    "Step",
    "StepTrace",
    "StrictModel",
    "TestReport",
    "ToolBuilderResponse",
    "ToolDecision",
    "ToolDoneResponse",
    "ToolEntry",
    "ToolRecord",
    "ToolSpec",
]
