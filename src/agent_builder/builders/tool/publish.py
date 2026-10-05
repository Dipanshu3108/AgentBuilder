"""Install an approved tool into the MCP server's generated/ folder and record it.

Files are written first, then the record. The server loads a tool only when the latest record is
approved and the file on disk hashes to the recorded `code_sha256`, so a half-finished publish or
a hand-edited file is never loaded.
"""
import json
from datetime import UTC, datetime

from ...config import settings
from ...core.schemas import TestReport, ToolRecord, ToolSpec
from ...registry.base import Registry
from .codegen import code_hash, write_tool_files


def generated_dir(name: str):
    return settings.mcp_tools_dir / "generated" / name


def publish_tool(spec: ToolSpec, report: TestReport, description: str, registry: Registry) -> ToolRecord:
    previous = registry.get_tool(spec.name)
    record = ToolRecord(
        spec=spec,
        version=previous.version + 1 if previous else 1,
        code_sha256=code_hash(spec),
        report=report,
        raw_description=description,
    )
    directory = generated_dir(spec.name)
    write_tool_files(spec, directory)
    manifest = {
        "name": spec.name,
        "version": record.version,
        "code_sha256": record.code_sha256,
        "capabilities": spec.capabilities,
        "approved_at": datetime.now(UTC).isoformat(),
    }
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return registry.save_tool(record)
