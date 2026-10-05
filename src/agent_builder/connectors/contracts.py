"""Judge whether agent A's output can feed agent B's input, from their text contracts."""
from ..core.llm import structured_completion
from ..core.schemas import AgentSpec, Compatibility, ModelConfig

CHECK_SYSTEM_PROMPT = """\
You check whether AI agents can be chained: agent A runs first, and its Done output
(`message` text plus structured `data`) is passed unchanged as agent B's input (`message`, `data`).
When A is several agents run in parallel, B receives all their outputs at once: `data` is keyed
by step id, each key holding that step's `data`, and `message` lists each step's summary.
Judge only from the descriptions given, and judge B against everything it receives together.
Answer "compatible" if B can work from that input as is, "needs_mapping" if the needed
information is there but in a different shape or field name, and "incompatible" if B needs
information A does not produce."""


def _describe(label: str, spec: AgentSpec, contract_name: str, contract: str) -> str:
    return (
        f"{label}\nName: {spec.name}\nPurpose: {spec.purpose}\n"
        f"{contract_name}: {contract or '(not described)'}"
    )


async def check_compatibility(a: AgentSpec, b: AgentSpec, model: ModelConfig) -> Compatibility:
    user = (
        f"{_describe('Agent A', a, 'Returns', a.returns)}\n\n"
        f"{_describe('Agent B', b, 'Accepts', b.accepts)}"
    )
    return await structured_completion(model, CHECK_SYSTEM_PROMPT, user, Compatibility)


async def check_fan_in(
    upstream: dict[str, AgentSpec], b: AgentSpec, model: ModelConfig
) -> Compatibility:
    """Several parallel steps (keyed by step id) feeding one agent together."""
    parts = "\n\n".join(
        _describe(f"Step '{step_id}'", spec, f"Returns (arrives as data.{step_id})", spec.returns)
        for step_id, spec in upstream.items()
    )
    user = f"Agent A is these steps, run in parallel:\n\n{parts}\n\n{_describe('Agent B', b, 'Accepts', b.accepts)}"
    return await structured_completion(model, CHECK_SYSTEM_PROMPT, user, Compatibility)
