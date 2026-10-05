"""Live tool discovery from the running MCP server, so the catalog never drifts from it."""
from ..config import settings
from ..core.mcp_client import open_session
from ..core.schemas import ToolEntry


async def load_tools(mcp_url: str = settings.mcp_server_url) -> list[ToolEntry]:
    async with open_session(mcp_url) as session:
        result = await session.list_tools()
    entries = []
    for tool in result.tools:
        # Convention: a tool description may end with "Use when: ..." to give the builder a hint.
        desc, _, use_when = (tool.description or "").partition("Use when:")
        entries.append(ToolEntry(id=tool.name, description=desc.strip(), use_when=use_when.strip()))
    return entries
