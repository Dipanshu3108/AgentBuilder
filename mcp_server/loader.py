"""Registers every tool the server exposes.

Core tools are hand-written and reviewed in git. Generated tools come from the tool builder:
their code lives in tools/generated/<name>/ and their records in the registry. A background
thread syncs them every few seconds: a tool is served only while its latest record is approved
and its tool.py hashes to the recorded code_sha256. Agents list tools when each run starts, so
additions and removals apply to the next run without a restart.
"""
import hashlib
import importlib.util
import logging
import threading
import time
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from tools.core.files import list_output_files, read_file, write_file
from tools.core.relations import parse_relations

CORE_TOOLS = (parse_relations, write_file, read_file, list_output_files)
GENERATED_DIR = Path(__file__).parent / "tools" / "generated"
SYNC_SECONDS = 5

log = logging.getLogger("mcp_server.loader")


def register_tools(server: FastMCP) -> None:
    for tool in CORE_TOOLS:
        server.tool()(tool)


def _load_function(name: str, version: int, path: Path):
    spec = importlib.util.spec_from_file_location(f"generated_{name}_v{version}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, name)


class GeneratedTools:
    """Keeps the server's generated tools in step with the registry."""

    def __init__(self, server: FastMCP):
        from agent_builder.registry.factory import get_registry

        self.server = server
        self.registry = get_registry()
        self.loaded: dict[str, str] = {}  # tool name → code hash currently served
        self.warned: set[str] = set()  # tool versions already reported as tampered

    def sync(self) -> None:
        wanted: dict[str, tuple] = {}
        latest_seen: set[str] = set()
        for record in self.registry.list_tools():  # newest version first per name
            name = record.spec.name
            if name in latest_seen:
                continue
            latest_seen.add(name)
            path = GENERATED_DIR / name / "tool.py"
            if record.status != "approved" or not path.exists():
                continue
            if hashlib.sha256(path.read_bytes()).hexdigest() != record.code_sha256:
                if record.id not in self.warned:
                    log.warning("skipping %s: tool.py does not match its approved hash", record.id)
                    self.warned.add(record.id)
                continue
            wanted[name] = (record, path)

        for name in set(self.loaded) - set(wanted):
            self.server.remove_tool(name)
            del self.loaded[name]
            log.info("removed generated tool %s", name)
        for name, (record, path) in wanted.items():
            if self.loaded.get(name) == record.code_sha256:
                continue
            try:
                function = _load_function(name, record.version, path)
            except Exception:
                log.exception("failed to load %s", record.id)
                continue
            if name in self.loaded:
                self.server.remove_tool(name)
            description = f"{record.spec.description} Use when: {record.spec.use_when}"
            self.server.add_tool(function, name=name, description=description)
            self.loaded[name] = record.code_sha256
            log.info("loaded generated tool %s", record.id)

    def start(self) -> None:
        self.sync()

        def loop() -> None:
            while True:
                time.sleep(SYNC_SECONDS)
                try:
                    self.sync()
                except Exception:
                    log.exception("generated tool sync failed")

        threading.Thread(target=loop, name="generated-tool-sync", daemon=True).start()
