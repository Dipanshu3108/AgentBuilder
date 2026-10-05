"""Turn the ids in a spec back into real things: a filtered MCP toolset and skill text."""
from pathlib import Path

from ..config import settings
from ..core.schemas import AgentSpec


def resolve_skills(spec: AgentSpec, skills_dir: Path = settings.skills_dir) -> str:
    """Skills are plain instructions; they get appended to the system prompt."""
    blocks = []
    for skill_id in spec.skills:
        path = skills_dir / skill_id / "SKILL.md"
        if path.exists():
            blocks.append(f"<skill name=\"{skill_id}\">\n{path.read_text(encoding='utf-8')}\n</skill>")
    return "\n\n".join(blocks)


def build_system_prompt(spec: AgentSpec) -> str:
    skills = resolve_skills(spec)
    if not skills:
        return spec.system_prompt
    return f"{spec.system_prompt}\n\n# Reference skills\n{skills}"
