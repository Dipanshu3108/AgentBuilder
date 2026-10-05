"""`agent-builder tool ...`: build, inspect, test, and switch generated MCP tools.

`tool build` writes code and tests, runs static checks and sandboxed tests (fixing failures up to
three times), shows you the code, and publishes only after you approve. Approval is never
automatic. A running MCP server picks the tool up within seconds; no restart is needed.
"""
import hashlib

import typer

from ..builders.tool.builder import TOOL_BUILDER
from ..builders.tool.publish import generated_dir
from ..builders.tool.sandbox import run_tests
from ..config import settings
from ..core.schemas import BuildToolRequest, TestReport, ToolDoneResponse, ToolSpec
from ..registry.factory import get_registry
from .ui import Version, echo_done, echo_model, review_with_feedback

app = typer.Typer(no_args_is_help=True, help="Build, inspect, test, and switch generated MCP tools.")


def _report_line(report: TestReport | None) -> str:
    if report is None:
        return "tests: not run"
    isolation = "" if report.isolated else " (WARNING: ran WITH network access; unshare unavailable)"
    return f"tests: {'passed' if report.passed else 'FAILED'}{isolation}"


def render_tool(spec: ToolSpec, report: TestReport | None) -> str:
    rule = "-" * 72
    capabilities = ", ".join(spec.capabilities) or "none (pure computation)"
    return "\n".join([
        f"Tool: {spec.name}",
        f"  {spec.description}",
        f"  Use when: {spec.use_when}",
        f"  Capabilities: {capabilities}",
        f"  Rationale: {spec.rationale}",
        f"  {_report_line(report)}",
        f"{rule}\ntool.py\n{rule}\n{spec.code.rstrip()}",
        f"{rule}\ntest_tool.py\n{rule}\n{spec.tests.rstrip()}",
        rule,
    ])


def _get(name: str, version: int | None = None):
    record = get_registry().get_tool(name, version)
    if record is None:
        raise typer.BadParameter(f"tool not found: {name}")
    return record


@app.command("build")
def build(
    name: str,
    description: str,
    builder_model: str = typer.Option(settings.default_builder_model, "--builder-model"),
):
    """Generate a tool, test it in the sandbox, and publish it after you review the code."""
    registry = get_registry()
    TOOL_BUILDER.progress = lambda message: typer.echo(message, err=True)
    reviewed = review_with_feedback(
        TOOL_BUILDER,
        lambda answers, feedback, previous: BuildToolRequest(
            name=name,
            description=description,
            builder_model_id=builder_model,
            clarification_answers=answers,
            feedback=feedback,
            previous=previous,
        ),
        registry,
        lambda response: typer.echo(render_tool(response.message, response.report)),
        "Publish this tool?",
        False,
    )
    if reviewed is None:
        return
    request, response = reviewed
    assert isinstance(response, ToolDoneResponse)
    record = TOOL_BUILDER.approve(request, response, registry)
    echo_done({"id": record.id, "path": str(generated_dir(name))})


@app.command("list")
def list_tools():
    """List generated tools, every version, newest first."""
    records = get_registry().list_tools()
    if not records:
        typer.echo("No generated tools found.")
        return
    for record in records:
        capabilities = ",".join(record.spec.capabilities) or "-"
        typer.echo(f"{record.id:<32} {record.status:<9} capabilities={capabilities}")


@app.command("show")
def show(name: str, version: Version = None):
    """Print a tool's code, tests, and last test report."""
    record = _get(name, version)
    typer.echo(f"{record.id} [{record.status}]")
    typer.echo(render_tool(record.spec, record.report))


@app.command("test")
def test(name: str):
    """Re-run checks and sandboxed tests on the latest version, and verify the installed file."""
    record = _get(name)
    path = generated_dir(name) / "tool.py"
    installed = path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == record.code_sha256
    typer.echo(f"installed file: {'matches approved code' if installed else 'MISSING OR MODIFIED'}")
    report = run_tests(record.spec)
    echo_model(report)
    if not report.passed or not installed:
        raise typer.Exit(code=1)


def _set_status(name: str, status: str) -> None:
    record = _get(name)
    get_registry().set_tool_status(name, record.version, status)
    echo_done({"id": record.id, "status": status})


@app.command("enable")
def enable(name: str):
    """Serve the latest version again (the running MCP server picks it up within seconds)."""
    _set_status(name, "approved")


@app.command("disable")
def disable(name: str):
    """Stop serving the tool (the running MCP server drops it within seconds)."""
    _set_status(name, "disabled")
