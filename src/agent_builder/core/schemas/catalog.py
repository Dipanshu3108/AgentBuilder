"""What a builder can choose from."""
from pydantic import Field

from .common import StrictModel


class ToolEntry(StrictModel):
    id: str = Field(description="Tool name as exposed by the MCP server, e.g. 'parse_relations'.")
    description: str
    use_when: str = Field(default="", description="One-line hint for the builder about when to pick it.")


class SkillEntry(StrictModel):
    id: str = Field(description="Skill folder name, e.g. 'html-visualization'.")
    description: str
    path: str = Field(description="Path to the SKILL.md file.")


class AgentEntry(StrictModel):
    """An approved agent as the orchestrator builder sees it."""

    name: str
    version: int
    purpose: str
    accepts: str
    returns: str

    def as_prompt_line(self) -> str:
        return (
            f"- `{self.name}` (v{self.version}): {self.purpose}\n"
            f"  accepts: {self.accepts or '(not described)'}\n"
            f"  returns: {self.returns or '(not described)'}"
        )


class Catalog(StrictModel):
    tools: list[ToolEntry]
    skills: list[SkillEntry]

    def as_prompt_block(self) -> str:
        lines = ["## Available tools"]
        for t in self.tools:
            hint = f" Use when: {t.use_when}" if t.use_when else ""
            lines.append(f"- `{t.id}`: {t.description}{hint}")
        lines.append("\n## Available skills")
        for s in self.skills:
            lines.append(f"- `{s.id}`: {s.description}")
        return "\n".join(lines)

    def tool_ids(self) -> set[str]:
        return {t.id for t in self.tools}

    def skill_ids(self) -> set[str]:
        return {s.id for s in self.skills}
