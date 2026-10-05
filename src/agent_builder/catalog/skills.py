"""Skill discovery: one folder per skill, each with a SKILL.md whose first paragraph describes it."""
from pathlib import Path

from ..config import settings
from ..core.schemas import SkillEntry


def load_skills(skills_dir: Path = settings.skills_dir) -> list[SkillEntry]:
    entries = []
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        text = skill_md.read_text(encoding="utf-8")
        description = _first_paragraph(text)
        entries.append(SkillEntry(id=skill_md.parent.name, description=description, path=str(skill_md)))
    return entries


def _first_paragraph(markdown: str) -> str:
    body = [ln for ln in markdown.splitlines() if not ln.startswith("#")]
    para: list[str] = []
    for line in body:
        if line.strip():
            para.append(line.strip())
        elif para:
            break
    return " ".join(para)
