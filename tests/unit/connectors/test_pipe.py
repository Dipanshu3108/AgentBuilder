import asyncio
from types import SimpleNamespace

from agent_builder.connectors.pipe import run_pipe
from agent_builder.core.schemas import AgentInput, AgentOutput


class ScriptedAgent:
    """Stands in for LoadedAgent: returns scripted outputs and records every input."""

    def __init__(self, name, outputs):
        self.record = SimpleNamespace(id=f"{name}@v1", spec=SimpleNamespace(name=name))
        self.outputs = iter(outputs)
        self.inputs = []

    async def run(self, agent_input):
        self.inputs.append(agent_input)
        return next(self.outputs)


def test_pipe_answers_pending_and_feeds_done_output_forward():
    extractor = ScriptedAgent(
        "extractor",
        [
            AgentOutput(status="Pending", message="Which year?"),
            AgentOutput(status="Done", message="Extracted", data={"rows": [1, 2]}),
        ],
    )
    writer = ScriptedAgent("writer", [AgentOutput(status="Done", message="Wrote report")])

    steps = asyncio.run(run_pipe([extractor, writer], AgentInput(message="Summarize sales"), lambda q: "2025"))

    assert [step.output.status for step in steps] == ["Done", "Done"]
    assert extractor.inputs[1].context["answers"] == [{"question": "Which year?", "answer": "2025"}]
    assert writer.inputs[0].message == "Extracted"
    assert writer.inputs[0].data == {"rows": [1, 2]}
    assert writer.inputs[0].context["task"] == "Summarize sales"
