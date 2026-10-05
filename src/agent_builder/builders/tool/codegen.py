"""Lay a generated tool out on disk: the same files in the sandbox and in the MCP server."""
import hashlib
from pathlib import Path

from ...core.schemas import ToolSpec


def code_hash(spec: ToolSpec) -> str:
    return hashlib.sha256(spec.code.encode("utf-8")).hexdigest()


def write_tool_files(spec: ToolSpec, directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "tool.py").write_text(spec.code, encoding="utf-8")
    (directory / "test_tool.py").write_text(spec.tests, encoding="utf-8")
