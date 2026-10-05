"""`agent-builder runs ...`: inspect saved runs."""
import typer

from ..registry.factory import get_registry
from .ui import echo_model

app = typer.Typer(no_args_is_help=True, help="Inspect saved runs.")


@app.command("list")
def list_runs(
    target: str | None = typer.Option(None, "--target", help="Agent name, or 'a|b' for a pipe."),
    limit: int = typer.Option(20, "--limit"),
):
    """List recent runs, newest first."""
    runs = get_registry().list_runs(target, limit)
    if not runs:
        typer.echo("No runs found.")
        return
    for run in runs:
        typer.echo(
            f"{run.run_id}  {run.started_at:%Y-%m-%d %H:%M}  {run.kind:<12} {run.target:<32} "
            f"{run.output.status:<7} {run.output.message[:60]}"
        )


@app.command("show")
def show(run_id: str):
    """Print a run's full trace: every step's input and output."""
    run = get_registry().get_run(run_id)
    if run is None:
        raise typer.BadParameter(f"run not found: {run_id}")
    echo_model(run)
