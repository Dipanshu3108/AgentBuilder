"""Non-secret local defaults. Model configuration is loaded from the database."""
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_url: str = "mongodb://localhost:27017/agents_db"
    mcp_server_url: str = "http://127.0.0.1:8000/mcp"
    skills_dir: Path = Path("./skills")
    output_dir: Path = Path("./outputs")
    # The MCP server's tool package: sdk.py helpers and generated/<tool>/ folders.
    mcp_tools_dir: Path = Path("./mcp_server/tools")
    # Model ids registered with `agent-builder models add`; CLI flags override them.
    default_builder_model: str = "agent_builder"
    default_agent_model: str = "sub_agent_model"


settings = Settings()
