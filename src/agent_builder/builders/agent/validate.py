"""Deterministic checks on an agent spec that the LLM cannot be trusted to do itself."""
from ...core.schemas import AgentSpec, Catalog
from ..base import BuildValidationError

SpecValidationError = BuildValidationError


def validate_spec(spec: AgentSpec, catalog: Catalog) -> None:
    unknown_tools = set(spec.tools) - catalog.tool_ids()
    unknown_skills = set(spec.skills) - catalog.skill_ids()
    problems = []
    if unknown_tools:
        problems.append(f"unknown tools: {sorted(unknown_tools)}")
    if unknown_skills:
        problems.append(f"unknown skills: {sorted(unknown_skills)}")
    if not spec.system_prompt.strip():
        problems.append("empty system prompt")
    if problems:
        raise SpecValidationError("; ".join(problems))
