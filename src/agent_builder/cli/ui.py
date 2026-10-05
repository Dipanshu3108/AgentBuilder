"""Terminal helpers shared by every CLI command: output, input, clarification, approval."""
import asyncio
import json
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import typer
from pydantic import BaseModel

from ..connectors.mapping import next_input
from ..core.schemas import AgentInput, BuilderPendingResponse

if TYPE_CHECKING:
    from ..builders.base import Builder
    from ..core.schemas import RunTrace
    from ..registry.base import Registry


def echo_done(message: dict[str, Any]) -> None:
    typer.echo(json.dumps({"status": "Done", "message": message}, indent=2))


def echo_model(model: BaseModel) -> None:
    typer.echo(model.model_dump_json(indent=2))


InputText = Annotated[str | None, typer.Option("--input", help="Input message text.")]
InputFile = Annotated[Path | None, typer.Option("--input-file", help="File whose text is the input message.")]
InputFromRun = Annotated[
    str | None, typer.Option("--input-from-run", help="Use a saved run's Done output as input.")
]
InputData = Annotated[str | None, typer.Option("--data", help="JSON object merged into input data.")]
Version = Annotated[int | None, typer.Option("--version", help="Exact version; latest if omitted.")]


def read_input(
    registry: "Registry",
    input_text: str | None,
    input_file: Path | None,
    from_run: str | None,
    data: str | None,
) -> AgentInput:
    """Build AgentInput from exactly one message source, plus optional --data JSON."""
    if sum(source is not None for source in (input_text, input_file, from_run)) != 1:
        raise typer.BadParameter("Provide exactly one of --input, --input-file, --input-from-run")
    if from_run is not None:
        run = registry.get_run(from_run)
        if run is None:
            raise typer.BadParameter(f"run not found: {from_run}")
        agent_input = next_input(run.output)
    else:
        text = input_text if input_text is not None else input_file.read_text(encoding="utf-8")
        agent_input = AgentInput(message=text)
    if data is not None:
        extra = json.loads(data)
        if not isinstance(extra, dict):
            raise typer.BadParameter("--data must be a JSON object")
        agent_input = agent_input.model_copy(update={"data": {**agent_input.data, **extra}})
    return agent_input


def ask_user(question: str) -> str:
    """Answer an agent's Pending question from the terminal."""
    return typer.prompt(f"[agent asks] {question}")


def echo_run(run: "RunTrace") -> None:
    """Print the run's final output; the run id goes to stderr so stdout stays pure JSON."""
    echo_model(run.output)
    typer.echo(f"run_id: {run.run_id}", err=True)


def clarify_until_settled(
    build: Callable[[dict[str, str]], BaseModel],
    show_done: Callable[[BaseModel], None] = echo_model,
    answers: dict[str, str] | None = None,
) -> BaseModel:
    """Call `build(answers)` and ask Pending questions until the builder returns Done or Error.

    Pass `answers` to keep earlier answers (it is updated in place); `show_done` renders Done.
    """
    answers = {} if answers is None else answers
    while True:
        response = build(answers)
        if not isinstance(response, BuilderPendingResponse):
            (show_done if response.status == "Done" else echo_model)(response)
            return response
        echo_model(response)
        for question in response.message.questions:
            answers[question.id] = typer.prompt(question.question)


def approved(prompt: str, auto_approve: bool) -> bool:
    return auto_approve or typer.confirm(prompt)


def review_with_feedback(
    builder: "Builder",
    make_request: Callable[[dict[str, str], list[str], Any], BaseModel],
    registry: "Registry",
    show_done: Callable[[BaseModel], None],
    approval_prompt: str,
    auto_approve: bool,
) -> tuple[BaseModel, BaseModel] | None:
    """Propose, show, then approve, quit, or revise with typed feedback until settled.

    `make_request(answers, feedback, previous)` builds each request; `previous` is the proposal
    the feedback refers to. Returns the approved (request, response), or None on quit.
    """
    feedback: list[str] = []
    answers: dict[str, str] = {}
    requests: list[BaseModel] = []
    previous: list[Any] = []

    def attempt(current: dict[str, str]) -> BaseModel:
        requests.append(make_request(dict(current), list(feedback), previous[-1] if previous else None))
        return asyncio.run(builder.propose(requests[-1], registry))

    while True:
        response = clarify_until_settled(attempt, show_done, answers)
        if not isinstance(response, builder.done_type):
            raise typer.Exit(code=1)
        reply = "y" if auto_approve else typer.prompt(
            f"{approval_prompt} [y]es, [q]uit, or type feedback", default="y"
        )
        if reply.strip().lower() in {"y", "yes"}:
            return requests[-1], response
        if reply.strip().lower() in {"q", "quit", "n", "no"}:
            return None
        feedback.append(reply.strip())
        previous.append(response.message)


def build_and_approve(
    builder: "Builder",
    make_request: Callable[[dict[str, str]], BaseModel],
    registry: "Registry",
    approval_prompt: str,
    auto_approve: bool,
) -> Any:
    """Shared `<noun> build` flow: clarify, show the proposal, save only after approval.

    Returns the saved record, or None when the reviewer declines.
    """
    requests: list[BaseModel] = []

    def attempt(answers: dict[str, str]) -> BaseModel:
        requests.append(make_request(answers))
        return asyncio.run(builder.propose(requests[-1], registry))

    response = clarify_until_settled(attempt)
    if not isinstance(response, builder.done_type):
        raise typer.Exit(code=1)
    if approved(approval_prompt, auto_approve):
        record = builder.approve(requests[-1], response, registry)
        echo_done({"id": record.id})
        return record
    return None
