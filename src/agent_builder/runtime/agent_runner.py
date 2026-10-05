"""Load approved agents and execute their LiteLLM/MCP tool loop."""
import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from litellm import aresponses
from mcp import ClientSession
from pydantic import ValidationError

from ..config import settings
from ..core.mcp_client import open_session
from ..core.schemas import AgentInput, AgentOutput, AgentRecord, ModelConfig
from ..registry.base import Registry
from ..registry.factory import get_registry
from .resolver import build_system_prompt

MAX_TOOL_ROUNDS = 8
MAX_PENDING_ANSWERS = 3

OUTPUT_RULES = """\
Finish with exactly one JSON object matching the output schema below, and nothing else:
- "Done": the task is complete. `message` is a short summary; structured results go in `data`.
- "Pending": you cannot continue without the user. `message` is one clear question. Answers to
  earlier questions arrive in the input's `context.answers`; never ask an answered question again.
- "Error": the task cannot be completed. `message` says why."""


def _error(message: str) -> AgentOutput:
    return AgentOutput(status="Error", message=message)


def _item_value(item: Any, key: str) -> Any:
    return item.get(key) if isinstance(item, dict) else getattr(item, key, None)


def _response_item_dict(item: Any) -> dict[str, Any]:
    if isinstance(item, dict):
        return item
    if hasattr(item, "model_dump"):
        return item.model_dump(mode="json", exclude_none=True)
    return {}


def _response_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str):
        return output_text

    parts = []
    for item in response.output:
        if _item_value(item, "type") != "message":
            continue
        for content in _item_value(item, "content") or []:
            if _item_value(content, "type") == "output_text":
                parts.append(_item_value(content, "text") or "")
    return "".join(parts)


def _tool_result_text(result: Any) -> str:
    parts = []
    for item in result.content:
        text = getattr(item, "text", None)
        parts.append(text if text is not None else item.model_dump_json())
    return "\n".join(parts)


async def _completion_loop(
    record: AgentRecord,
    model: ModelConfig,
    agent_input: AgentInput,
    session: ClientSession | None,
    tools: list[dict[str, Any]],
) -> AgentOutput:
    output_schema = json.dumps(AgentOutput.model_json_schema(), indent=2)
    instructions = f"{build_system_prompt(record.spec)}\n\n{OUTPUT_RULES}\n{output_schema}"
    input_items: list[dict[str, Any]] = [
        {"role": "user", "content": agent_input.model_dump_json()}
    ]

    for _ in range(MAX_TOOL_ROUNDS):
        kwargs = model.litellm_kwargs()
        if "max_tokens" in kwargs:
            kwargs["max_output_tokens"] = kwargs.pop("max_tokens")
        if tools:
            kwargs["tools"] = tools
        response = await aresponses(
            **kwargs,
            input=input_items,
            instructions=instructions,
            store=False,
        )
        tool_calls = [
            item for item in response.output
            if _item_value(item, "type") == "function_call"
        ]

        if not tool_calls:
            try:
                return AgentOutput.model_validate_json(_response_text(response))
            except (ValidationError, ValueError, TypeError) as exc:
                return _error(f"model returned invalid agent output: {exc}")

        if session is None:
            return _error("model requested a tool but no tool session is available")
        input_items.extend(_response_item_dict(item) for item in response.output)
        for call in tool_calls:
            arguments = _item_value(call, "arguments")
            if isinstance(arguments, str):
                arguments = json.loads(arguments)
            call_id = _item_value(call, "call_id")
            result = await session.call_tool(_item_value(call, "name"), arguments=arguments)
            input_items.append(
                {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": _tool_result_text(result),
                }
            )

    return _error("maximum tool-call rounds exceeded")


@dataclass(frozen=True)
class LoadedAgent:
    record: AgentRecord
    model: ModelConfig
    mcp_url: str = settings.mcp_server_url

    async def run(self, agent_input: AgentInput) -> AgentOutput:
        if not self.record.spec.tools:
            return await _completion_loop(self.record, self.model, agent_input, None, [])

        allowed = set(self.record.spec.tools)
        async with open_session(self.mcp_url) as session:
            discovered = await session.list_tools()
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description or "",
                        "parameters": tool.inputSchema,
                    },
                }
                for tool in discovered.tools
                if tool.name in allowed
            ]
            return await _completion_loop(self.record, self.model, agent_input, session, tools)


Ask = Callable[[str], str]


async def run_until_settled(
    agent: LoadedAgent, agent_input: AgentInput, ask: Ask, max_answers: int = MAX_PENDING_ANSWERS
) -> AgentOutput:
    """Run the agent; while it is Pending, ask the user and re-run with the answer in context."""
    answers = list(agent_input.context.get("answers", []))
    for _ in range(max_answers + 1):
        context = {**agent_input.context, "answers": answers} if answers else agent_input.context
        output = await agent.run(agent_input.model_copy(update={"context": context}))
        if output.status != "Pending":
            return output
        if len(answers) == max_answers:
            break
        answers.append({"question": output.message, "answer": ask(output.message)})
    return _error(f"agent still Pending after {max_answers} answers: {output.message}")


def load_agent(
    agent_name: str,
    registry: Registry | None = None,
    version: int | None = None,
) -> LoadedAgent:
    """Load an approved agent and its model configuration by name."""
    resolved_registry = registry or get_registry()
    record = resolved_registry.get(agent_name, version)
    if record is None or record.status != "approved":
        raise LookupError(f"approved agent not found: {agent_name}")
    model = resolved_registry.get_model(record.spec.model.id)
    if model is None:
        raise LookupError(f"model not found: {record.spec.model.id}")
    return LoadedAgent(record=record, model=model)


async def run_agent(
    agent_name: str,
    agent_input: AgentInput,
    registry: Registry | None = None,
    version: int | None = None,
) -> AgentOutput:
    return await load_agent(agent_name, registry, version).run(agent_input)
