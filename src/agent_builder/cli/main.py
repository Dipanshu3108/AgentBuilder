"""CLI for registering models, building agents, orchestrators and tools, and running them."""
import asyncio

import typer

from ..catalog.loader import load_catalog
from ..registry.factory import get_registry
from ..runtime.orchestrator_runner import DEFAULT_MAX_PARALLEL
from . import agents, connect, models, orchestrators, runs, tools
from .ui import InputData, InputFile, InputFromRun, InputText, Version

app = typer.Typer(no_args_is_help=True, help=__doc__)
app.add_typer(models.app, name="models")
app.add_typer(agents.app, name="agent")
app.add_typer(orchestrators.app, name="orch")
app.add_typer(tools.app, name="tool")
app.add_typer(connect.app, name="connect")
app.add_typer(runs.app, name="runs")


@app.command()
def catalog():
    """Show the tools and skills the builders can choose from."""
    typer.echo(asyncio.run(load_catalog()).as_prompt_block())


@app.command("run")
def run(
    name: str,
    input_text: InputText = None,
    input_file: InputFile = None,
    input_from_run: InputFromRun = None,
    data: InputData = None,
    version: Version = None,
):
    """Run an agent or orchestrator by name (an agent wins if both exist)."""
    registry = get_registry()
    if registry.get(name) is None and registry.get_orchestrator(name) is not None:
        orchestrators.run(
            name, input_text, input_file, input_from_run, data, version, DEFAULT_MAX_PARALLEL
        )
    else:
        agents.run(name, input_text, input_file, input_from_run, data, version)


if __name__ == "__main__":
    app()
