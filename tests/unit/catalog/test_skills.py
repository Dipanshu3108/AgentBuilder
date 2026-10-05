from pathlib import Path

from agent_builder.catalog.skills import load_skills

ROOT = Path(__file__).resolve().parents[3]


def test_skills_load_from_disk():
    ids = {s.id for s in load_skills(ROOT / "skills")}
    assert {"html-visualization", "data-extraction", "report-writing"} <= ids
