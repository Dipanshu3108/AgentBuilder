"""`agent-builder connect ...`: check and try agent-to-agent chaining."""
import asyncio

import typer

from ..config import settings
from ..connectors.contracts import check_compatibility
from ..connectors.pipe import run_pipe
from ..registry.factory import get_registry
from ..runtime.agent_runner import load_agent
from ..runtime.tracing import save_run
from .ui import (
    InputData,
    InputFile,
    InputFromRun,
    InputText,
    ask_user,
    echo_model,
    echo_run,
    read_input,
)

app = typer.Typer(no_args_is_help=True, help="Check and try agent-to-agent chaining.")


@app.command("check")
def check(
    agent_a: str,
    agent_b: str,
    builder_model: str = typer.Option(settings.default_builder_model, "--builder-model"),
):
    """Judge whether AGENT_A's output can feed AGENT_B's input, from their contracts."""
    registry = get_registry()
    a, b = registry.get(agent_a), registry.get(agent_b)
    model = registry.get_model(builder_model)
    for value, label in ((a, agent_a), (b, agent_b)):
        if value is None:
            raise typer.BadParameter(f"agent not found: {label}")
    if model is None:
        raise typer.BadParameter(f"model not found: {builder_model}")
    echo_model(asyncio.run(check_compatibility(a.spec, b.spec, model)))


@app.command("pipe")
def pipe(
    agents: list[str],
    input_text: InputText = None,
    input_file: InputFile = None,
    input_from_run: InputFromRun = None,
    data: InputData = None,
):
    """Run AGENTS in order, each Done output becoming the next agent's input. Saves the run."""
    if len(agents) < 2:
        raise typer.BadParameter("a pipe needs at least two agents")
    registry = get_registry()
    agent_input = read_input(registry, input_text, input_file, input_from_run, data)
    try:
        loaded = [load_agent(name, registry) for name in agents]
    except LookupError as exc:
        raise typer.BadParameter(str(exc)) from exc
    steps = asyncio.run(run_pipe(loaded, agent_input, ask_user))
    for step in steps[:-1]:
        typer.echo(f"{step.agent}: {step.output.status} - {step.output.message}", err=True)
    echo_run(save_run(registry, "pipe", "|".join(agents), agent_input, steps))
