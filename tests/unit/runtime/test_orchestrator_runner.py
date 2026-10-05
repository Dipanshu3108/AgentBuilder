import asyncio
from types import SimpleNamespace

from agent_builder.core.schemas import (
    AgentInput,
    AgentOutput,
    BuildOrchestratorRequest,
    OrchestratorRecord,
    OrchestratorSpec,
    Step,
)
from agent_builder.runtime.orchestrator_runner import LoadedOrchestrator


class EchoAgent:
    """Stands in for LoadedAgent: Done, with data naming the step; records its input."""

    def __init__(self, name):
        self.record = SimpleNamespace(id=f"{name}@v1")
        self.name = name
        self.inputs = []

    async def run(self, agent_input):
        self.inputs.append(agent_input)
        await asyncio.sleep(0)
        return AgentOutput(status="Done", message=f"{self.name} done", data={"by": self.name})


def test_fan_out_then_fan_in_returns_final_step_output():
    steps = [
        Step(id="extract", instruction="extract", agent="x", reason="r"),
        Step(id="chart", instruction="chart", agent="x", after=["extract"], reason="r"),
        Step(id="summary", instruction="summarize", agent="x", after=["extract"], reason="r"),
        Step(id="assemble", instruction="assemble", agent="x", after=["chart", "summary"], reason="r"),
    ]
    spec = OrchestratorSpec(name="report", display_name="R", purpose="p", steps=steps, rationale="r")
    request = BuildOrchestratorRequest(name="report", description="d", builder_model_id="b", agent_model_id="a")
    agents = {step.id: EchoAgent(step.id) for step in steps}
    orchestrator = LoadedOrchestrator(OrchestratorRecord(spec=spec, request=request), agents)

    output, traces = asyncio.run(orchestrator.run(AgentInput(message="Q3 sales"), ask=lambda q: ""))

    assert output.data == {"by": "assemble"}
    assert len(traces) == 4
    assert agents["extract"].inputs[0].message.endswith("Q3 sales")
    assert agents["chart"].inputs[0].data == {"by": "extract"}
    assembled = agents["assemble"].inputs[0]
    assert assembled.data == {"chart": {"by": "chart"}, "summary": {"by": "summary"}}
    assert assembled.context == {"task": "Q3 sales", "step": "assemble"}
