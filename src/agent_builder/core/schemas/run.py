"""Saved runs: what went in and came out of each agent call, so outputs can feed later runs."""
from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from pydantic import Field

from .common import AgentInput, AgentOutput, StrictModel


def _now() -> datetime:
    return datetime.now(UTC)


class StepTrace(StrictModel):
    step: str = Field(description="Step id; the agent name for single runs and pipes.")
    agent: str = Field(description="Exact agent version, e.g. 'graph-visualizer@v1'.")
    input: AgentInput
    output: AgentOutput
    started_at: datetime
    finished_at: datetime


class RunTrace(StrictModel):
    run_id: str = Field(default_factory=lambda: uuid4().hex[:12])
    kind: Literal["agent", "pipe", "orchestrator"]
    target: str = Field(description="Agent name, 'a|b|c' for a pipe, or orchestrator name.")
    input: AgentInput
    output: AgentOutput
    steps: list[StepTrace]
    started_at: datetime = Field(default_factory=_now)
    finished_at: datetime = Field(default_factory=_now)
