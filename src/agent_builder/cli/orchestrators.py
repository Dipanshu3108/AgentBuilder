"""`agent-builder orch ...`: build, inspect, and run orchestrators.

`orch build` runs three stages, each needing approval:
  1. plan     the builder splits the task into steps; approve or type feedback to revise
  2. gaps     every missing sub-agent is built with the normal agent builder
  3. final    contract checks between linked steps, then approve to save
The draft is saved after stage 1, so `orch build NAME --resume` continues at stage 2.
"""
import asyncio

import typer

from ..builders.agent.builder import AGENT_BUILDER
from ..builders.orchestrator.builder import (
    approve_orchestrator,
    check_links,
    gap_request,
    missing_agents,
)
from ..builders.orchestrator.planner import PLANNER
from ..config import settings
from ..core.schemas import (
    BuildOrchestratorRequest,
    OrchestratorRecord,
    OrchestratorSpec,
)
from ..registry.base import Registry
from ..registry.factory import get_registry
from ..runtime.orchestrator_runner import DEFAULT_MAX_PARALLEL, load_orchestrator
from ..runtime.tracing import save_run
from .ui import (
    InputData,
    InputFile,
    InputFromRun,
    InputText,
    Version,
    approved,
    ask_user,
    build_and_approve,
    echo_done,
    echo_model,
    echo_run,
    read_input,
    review_with_feedback,
)

app = typer.Typer(no_args_is_help=True, help="Build, inspect, and run orchestrators.")


def render_plan(spec: OrchestratorSpec, registry: Registry) -> str:
    lines = [f"Plan: {spec.name} ({len(spec.steps)} steps) - {spec.purpose}"]
    for number, step in enumerate(spec.steps, start=1):
        record = registry.get(step.agent)
        if step.version is not None:
            agent = f"{step.agent}@v{step.version}"
        elif record is not None and record.status == "approved":
            agent = f"{step.agent}@v{record.version} [existing]"
        else:
            agent = f"{step.agent} [NEW]"
        after = f"  after: {', '.join(step.after)}" if step.after else ""
        lines.append(f"  {number}. {step.id:<16} -> {agent}{after}")
        lines.append(f"       {step.instruction}")
        if agent.endswith("[NEW]"):
            lines.append(f"       new agent: {step.new_agent_description}")
    return "\n".join(lines)


def _plan_stage(
    name: str, description: str, agent_model: str, builder_model: str, registry: Registry, auto: bool
) -> OrchestratorRecord | None:
    reviewed = review_with_feedback(
        PLANNER,
        lambda answers, feedback, previous: BuildOrchestratorRequest(
            name=name,
            description=description,
            builder_model_id=builder_model,
            agent_model_id=agent_model,
            clarification_answers=answers,
            feedback=feedback,
            previous_plan=previous,
        ),
        registry,
        lambda response: typer.echo(render_plan(response.message, registry)),
        "Approve plan?",
        auto,
    )
    if reviewed is None:
        return None
    draft = PLANNER.approve(*reviewed, registry)
    typer.echo(f"Plan approved; draft saved as {draft.id}.")
    return draft


def _gap_stage(draft: OrchestratorRecord, registry: Registry, auto: bool) -> bool:
    for step in missing_agents(draft.spec, registry):
        typer.echo(f"\nStep '{step.id}' needs a new agent '{step.agent}'. Building it now.")
        record = build_and_approve(
            AGENT_BUILDER,
            lambda answers, step=step: gap_request(step, draft, registry).model_copy(
                update={"clarification_answers": answers}
            ),
            registry,
            f"Approve and save agent '{step.agent}'?",
            auto,
        )
        if record is None:
            return False
    return True


def _final_stage(draft: OrchestratorRecord, registry: Registry, auto: bool) -> bool:
    model = registry.get_model(draft.request.builder_model_id)
    if model is not None and any(step.after for step in draft.spec.steps):
        typer.echo("\nContract checks between linked steps:")
        for upstream, downstream, result in asyncio.run(check_links(draft.spec, registry, model)):
            typer.echo(f"  {upstream} -> {downstream}: {result.verdict} - {result.reason}")
    typer.echo("\n" + render_plan(draft.spec, registry))
    if not approved("Approve and save this orchestrator?", auto):
        return False
    record = approve_orchestrator(draft, registry)
    echo_done({"id": record.id})
    return True


@app.command("build")
def build(
    name: str,
    description: str = typer.Argument(None, help="End-to-end task. Not needed with --resume."),
    agent_model: str = typer.Option(
        settings.default_agent_model, "--model", "--agent-model", help="Model for new sub-agents."
    ),
    builder_model: str = typer.Option(settings.default_builder_model, "--builder-model"),
    resume: bool = typer.Option(False, "--resume", help="Continue a saved draft at the gap stage."),
    approve: bool = typer.Option(False, "--approve", help="Approve every stage without asking."),
):
    """Plan an orchestrator, build its missing sub-agents, and save after approval."""
    registry = get_registry()
    if resume:
        draft = registry.get_orchestrator(name, status="draft")
        if draft is None:
            raise typer.BadParameter(f"no draft orchestrator named {name}")
    else:
        if not description:
            raise typer.BadParameter("DESCRIPTION is required unless --resume is given")
        draft = _plan_stage(name, description, agent_model, builder_model, registry, approve)
        if draft is None:
            return
    resume_hint = f"Draft kept. Continue with: agent-builder orch build {name} --resume"
    if not _gap_stage(draft, registry, approve) or not _final_stage(draft, registry, approve):
        typer.echo(resume_hint, err=True)
        raise typer.Exit(code=1)


@app.command("list")
def list_orchestrators():
    """List orchestrators, every version, including drafts."""
    records = get_registry().list_orchestrators()
    if not records:
        typer.echo("No orchestrators found.")
        return
    for record in records:
        agents = [step.agent for step in record.spec.steps]
        typer.echo(f"{record.id:<32} {record.status:<9} steps={len(agents)} agents={agents}")


@app.command("show")
def show(name: str, version: Version = None):
    """Print an orchestrator's full record (the latest version, draft or approved)."""
    record = get_registry().get_orchestrator(name, version, status=None)
    if record is None:
        raise typer.BadParameter(f"orchestrator not found: {name}")
    echo_model(record)


@app.command("plan")
def plan(name: str, version: Version = None):
    """Print an orchestrator's steps, agents, and dependencies."""
    registry = get_registry()
    record = registry.get_orchestrator(name, version, status=None)
    if record is None:
        raise typer.BadParameter(f"orchestrator not found: {name}")
    typer.echo(f"{record.id} [{record.status}]")
    typer.echo(render_plan(record.spec, registry))


@app.command("run")
def run(
    name: str,
    input_text: InputText = None,
    input_file: InputFile = None,
    input_from_run: InputFromRun = None,
    data: InputData = None,
    version: Version = None,
    max_parallel: int = typer.Option(DEFAULT_MAX_PARALLEL, "--max-parallel", min=1),
):
    """Run an approved orchestrator and save the run with every step's trace."""
    registry = get_registry()
    task = read_input(registry, input_text, input_file, input_from_run, data)
    try:
        orchestrator = load_orchestrator(name, registry, version)
    except LookupError as exc:
        raise typer.BadParameter(str(exc)) from exc
    output, steps = asyncio.run(orchestrator.run(task, ask_user, max_parallel))
    for step in steps:
        typer.echo(f"{step.step} ({step.agent}): {step.output.status} - {step.output.message}", err=True)
    echo_run(save_run(registry, "orchestrator", name, task, steps, output))
