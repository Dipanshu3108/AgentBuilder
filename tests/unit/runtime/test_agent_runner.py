import asyncio
import json
from types import SimpleNamespace

from agent_builder.core.schemas import AgentInput, ModelConfig
from agent_builder.runtime import agent_runner as runner


class FakeSession:
    async def call_tool(self, name, arguments):
        assert name == "parse_relations"
        assert arguments == {"text": "A -[links]-> B"}
        return SimpleNamespace(content=[SimpleNamespace(text='{"nodes": [], "edges": []}')])


def test_responses_tool_loop_preserves_default_reasoning_and_parses_output(monkeypatch):
    responses = iter(
        [
            SimpleNamespace(
                output=[
                    {"type": "reasoning", "id": "reason_1", "summary": []},
                    {
                        "type": "function_call",
                        "id": "call_item_1",
                        "call_id": "call_1",
                        "name": "parse_relations",
                        "arguments": '{"text":"A -[links]-> B"}',
                    },
                ],
                output_text="",
            ),
            SimpleNamespace(
                output=[],
                output_text=json.dumps(
                    {"status": "Done", "message": "Wrote graph", "data": {"path": "outputs/graph.html"}}
                ),
            ),
        ]
    )
    requests = []

    async def fake_aresponses(**kwargs):
        requests.append(kwargs)
        return next(responses)

    monkeypatch.setattr(runner, "aresponses", fake_aresponses)
    monkeypatch.setattr(runner, "build_system_prompt", lambda _: "Visualize the graph")
    record = SimpleNamespace(spec=SimpleNamespace())
    model = ModelConfig(
        id="agent-model",
        model="azure/agent",
        api_key="secret",
        api_base="https://example.openai.azure.com",
    )
    tools = [
        {
            "type": "function",
            "name": "parse_relations",
            "description": "Parse relationships",
            "parameters": {"type": "object"},
        }
    ]

    result = asyncio.run(
        runner._completion_loop(
            record,
            model,
            AgentInput(message="A -[links]-> B"),
            FakeSession(),
            tools,
        )
    )

    assert result.status == "Done"
    assert result.data == {"path": "outputs/graph.html"}
    assert "reasoning" not in requests[0]
    assert "reasoning_effort" not in requests[0]
    assert requests[0]["tools"] == tools
    assert {"type": "function_call_output", "call_id": "call_1", "output": '{"nodes": [], "edges": []}'} in requests[1]["input"]
    assert {"type": "reasoning", "id": "reason_1", "summary": []} in requests[1]["input"]