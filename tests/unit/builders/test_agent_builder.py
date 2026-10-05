import asyncio

import pytest
from pydantic import ValidationError

from agent_builder.builders import base
from agent_builder.builders.agent import builder
from agent_builder.builders.agent.builder import approve_agent
from agent_builder.builders.agent.validate import SpecValidationError, validate_spec
from agent_builder.core.schemas import (
    AgentSpec,
    BuildAgentRequest,
    BuilderDecision,
    BuilderDoneResponse,
    Catalog,
    ModelReference,
    SkillEntry,
    ToolEntry,
)
from agent_builder.runtime.agent_runner import load_agent
from tests.fakes.registry import FakeRegistry


def _catalog() -> Catalog:
    return Catalog(
        tools=[ToolEntry(id="parse_relations", description="x"), ToolEntry(id="write_file", description="y")],
        skills=[SkillEntry(id="html-visualization", description="z", path="skills/html-visualization/SKILL.md")],
    )


def _spec(**overrides) -> AgentSpec:
    base = {
        "name": "html_visualizer",
        "display_name": "HTML visualizer",
        "purpose": "p",
        "system_prompt": "You are ...",
        "tools": ["parse_relations", "write_file"],
        "skills": ["html-visualization"],
        "model": ModelReference(id="agent-model"),
        "rationale": "r",
    }
    return AgentSpec(**{**base, **overrides})


def test_valid_spec_passes():
    validate_spec(_spec(), _catalog())


def test_unknown_tool_rejected():
    with pytest.raises(SpecValidationError, match="unknown tools"):
        validate_spec(_spec(tools=["shell_exec"]), _catalog())


def test_builder_decision_requires_exactly_one_outcome():
    with pytest.raises(ValidationError, match="either spec or clarification questions"):
        BuilderDecision()


def test_propose_enforces_requested_name_and_model(monkeypatch):
    async def fake_completion(model, system, user, response_type):
        assert model.id == "builder-model"
        return BuilderDecision(spec=_spec(name="llm_chosen", model=ModelReference(id="other")))

    async def fake_catalog():
        return _catalog()

    monkeypatch.setattr(base, "structured_completion", fake_completion)
    monkeypatch.setattr(builder, "load_catalog", fake_catalog)
    request = BuildAgentRequest(
        name="html_visualizer",
        description="Build an HTML graph",
        builder_model_id="builder-model",
        agent_model_id="agent-model",
    )

    response = asyncio.run(builder.build_agent(request, FakeRegistry()))

    assert isinstance(response, BuilderDoneResponse)
    assert response.message.name == "html_visualizer"
    assert response.message.model.id == "agent-model"


def test_approval_is_the_persistence_boundary():
    registry = FakeRegistry()
    request = BuildAgentRequest(
        name="html_visualizer",
        description="Build an HTML graph",
        builder_model_id="builder-model",
        agent_model_id="agent-model",
    )
    response = BuilderDoneResponse(message=_spec())

    assert registry.records == []
    saved = approve_agent(request, response, registry)

    assert registry.records == [saved]
    assert saved.status == "approved"
    assert load_agent("html_visualizer", registry).model.id == "agent-model"

    next_version = approve_agent(request, response, registry)
    assert next_version.agent_id == saved.agent_id
    assert next_version.id != saved.id
