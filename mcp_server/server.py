"""Minimal local MCP server. Run with:  python mcp_server/server.py

Every tool here executes on *your* machine. The LLM only decides to call them.
Convention: end a description with "Use when: ..." to give the agent builder a selection hint.
"""
import logging

from loader import GeneratedTools, register_tools
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("local-tools", host="127.0.0.1", port=8000)
register_tools(mcp)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    GeneratedTools(mcp).start()
    mcp.run(transport="streamable-http")
