"""File tools, confined to the output directory."""
import os
from pathlib import Path

OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./outputs")).resolve()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _safe_path(filename: str) -> Path:
    path = (OUTPUT_DIR / Path(filename).name).resolve()
    if path.parent != OUTPUT_DIR:
        raise ValueError("Path escapes output dir")
    return path


def write_file(filename: str, content: str) -> str:
    """Save text content to a file in the output directory and return its path.
    Use when: the agent must deliver a file (HTML, Markdown, JSON, CSV)."""
    path = _safe_path(filename)
    path.write_text(content, encoding="utf-8")
    return str(path)


def read_file(filename: str) -> str:
    """Read a file from the output directory.
    Use when: the agent needs to inspect or revise something it wrote earlier."""
    return _safe_path(filename).read_text(encoding="utf-8")


def list_output_files() -> str:
    """List files currently in the output directory.
    Use when: the agent needs to know which deliverables already exist."""
    return "\n".join(sorted(path.name for path in OUTPUT_DIR.iterdir() if path.is_file())) or "(empty)"
