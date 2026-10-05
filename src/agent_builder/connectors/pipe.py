"""Ad-hoc chaining A → B → C without saving an orchestrator."""
from ..core.schemas import AgentInput, StepTrace
from ..runtime.agent_runner import Ask, LoadedAgent
from ..runtime.tracing import traced_step
from .mapping import next_input


async def run_pipe(agents: list[LoadedAgent], first_input: AgentInput, ask: Ask) -> list[StepTrace]:
    """Run agents in order, feeding each Done output forward. Stops at the first non-Done step."""
    # Later agents only see the previous output, so keep the original task in their context.
    context = {**first_input.context, "task": first_input.message}
    steps: list[StepTrace] = []
    current = first_input
    for agent in agents:
        step = await traced_step(agent.record.spec.name, agent, current, ask)
        steps.append(step)
        if step.output.status != "Done":
            break
        current = next_input(step.output, context)
    return steps
