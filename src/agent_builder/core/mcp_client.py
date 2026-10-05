"""One place that opens MCP sessions, shared by catalog discovery and the runtime."""
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from ..config import settings


@asynccontextmanager
async def open_session(mcp_url: str = settings.mcp_server_url) -> AsyncIterator[ClientSession]:
    async with (
        streamable_http_client(mcp_url) as (read, write, _),
        ClientSession(read, write) as session,
    ):
        await session.initialize()
        yield session
