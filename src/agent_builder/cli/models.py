"""`agent-builder models ...`: database-backed model configurations."""
import typer

from ..core.schemas import ModelConfig
from ..registry.factory import get_registry
from .ui import echo_done

app = typer.Typer(no_args_is_help=True, help="Manage database-backed model configurations.")


@app.command("add")
def add_model(
    model_id: str = typer.Option(..., "--id"),
    model: str = typer.Option(..., help="LiteLLM name, for example azure/gpt-4o."),
    api_base: str = typer.Option(...),
    api_version: str | None = typer.Option(None),
    temperature: float = typer.Option(1.0),
    max_tokens: int | None = typer.Option(None),
):
    """Create or replace a model configuration in MongoDB."""
    api_key = typer.prompt("API key", hide_input=True)
    config = ModelConfig(
        id=model_id,
        model=model,
        api_key=api_key,
        api_base=api_base,
        api_version=api_version,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    get_registry().save_model(config)
    echo_done({"id": model_id})


@app.command("list")
def list_models():
    """List model IDs without exposing credentials."""
    echo_done({"models": [model.id for model in get_registry().list_models()]})
