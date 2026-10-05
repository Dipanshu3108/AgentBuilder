"""`agent-builder agent ...`: build, inspect, and run single agents."""
import asyncio

import typer

from ..builders.agent.builder import AGENT_BUILDER
from ..config import settings
from ..core.schemas import AgentRecord, BuildAgentRequest
from ..registry.factory import get_registry
from ..runtime.agent_runner import load_agent
from ..runtime.tracing import save_run, traced_step
from .ui import (
    InputData,
    InputFile,
    InputFromRun,
    InputText,
    Version,
    ask_user,
    build_and_approve,
    echo_model,
    echo_run,
    read_input,
)

app = typer.Typer(no_args_is_help=True, help="Build, inspect, and run single agents.")



def _summary(record: AgentRecord) -> str:
    return (
        f"{record.id:<32} {record.status:<9} "
        f"model={record.spec.model.id} tools={record.spec.tools} skills={record.spec.skills}"
    )


@app.command("build")
def build(
    name: str,
    description: str,
    agent_model: str = typer.Option(settings.default_agent_model, "--model", "--agent-model"),
    builder_model: str = typer.Option(settings.default_builder_model, "--builder-model"),
    approve: bool = typer.Option(False, "--approve", help="Approve the displayed proposal."),
):
    """Build a proposal, clarify when needed, and save only after approval."""
    build_and_approve(
        AGENT_BUILDER,
        lambda answers: BuildAgentRequest(
            name=name,
            description=description,
            builder_model_id=builder_model,
            agent_model_id=agent_model,
            clarification_answers=answers,
        ),
        get_registry(),
        "Approve and save this agent?",
        approve,
    )


@app.command("list")
def list_agents():
    """List stored agents, every version."""
    records = get_registry().list()
    if not records:
        typer.echo("No agents found.")
        return
    for record in records:
        typer.echo(_summary(record))


@app.command("versions")
def versions(name: str):
    """List every stored version of one agent."""
    records = [record for record in get_registry().list() if record.spec.name == name]
    if not records:
        raise typer.BadParameter(f"agent not found: {name}")
    for record in records:
        typer.echo(f"{_summary(record)} created={record.created_at:%Y-%m-%d %H:%M}")


@app.command("show")
def show(name: str, version: Version = None):
    """Print an agent's full record, including its system prompt."""
    record = get_registry().get(name, version)
    if record is None:
        raise typer.BadParameter(f"agent not found: {name}")
    echo_model(record)


@app.command("run")
def run(
    name: str,
    input_text: InputText = None,
    input_file: InputFile = None,
    input_from_run: InputFromRun = None,
    data: InputData = None,
    version: Version = None,
):
    """Run an approved agent, answer its questions if it is Pending, and save the run."""
    registry = get_registry()
    agent_input = read_input(registry, input_text, input_file, input_from_run, data)
    try:
        agent = load_agent(name, registry, version)
    except LookupError as exc:
        raise typer.BadParameter(str(exc)) from exc
    step = asyncio.run(traced_step(name, agent, agent_input, ask_user))
    echo_run(save_run(registry, "agent", name, agent_input, [step]))
