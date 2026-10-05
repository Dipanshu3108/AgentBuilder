"""Run an approved orchestrator: each step starts when its `after` steps are done, so
independent steps run in parallel. The result is the final step's AgentOutput."""
import asyncio
from dataclasses import dataclass

from ..connectors.mapping import step_input
from ..core.schemas import AgentInput, AgentOutput, OrchestratorRecord, Step, StepTrace
from ..registry.base import Registry
from ..registry.factory import get_registry
from .agent_runner import Ask, LoadedAgent, load_agent
from .tracing import traced_step

DEFAULT_MAX_PARALLEL = 4


@dataclass(frozen=True)
class LoadedOrchestrator:
    record: OrchestratorRecord
    agents: dict[str, LoadedAgent]  # step id → pinned agent

    async def run(
        self, task: AgentInput, ask: Ask, max_parallel: int = DEFAULT_MAX_PARALLEL
    ) -> tuple[AgentOutput, list[StepTrace]]:
        steps = {step.id: step for step in self.record.spec.steps}
        outputs: dict[str, AgentOutput] = {}
        traces: list[StepTrace] = []
        limit = asyncio.Semaphore(max_parallel)

        async def run_step(step: Step) -> StepTrace:
            upstream = {dep: outputs[dep] for dep in step.after if outputs[dep].status == "Done"}
            agent_input = step_input(step.id, step.instruction, task, upstream)
            async with limit:
                for _ in range(step.retries + 1):
                    trace = await traced_step(step.id, self.agents[step.id], agent_input, ask)
                    traces.append(trace)
                    if trace.output.status == "Done":
                        break
            return trace

        running: dict[asyncio.Task, str] = {}
        while len(outputs) < len(steps):
            started = set(outputs) | set(running.values())
            for step_id, step in steps.items():
                if step_id not in started and all(dep in outputs for dep in step.after):
                    running[asyncio.create_task(run_step(step))] = step_id
            if not running:
                return _error("plan has a cycle; no step can start"), traces
            done, _ = await asyncio.wait(running, return_when=asyncio.FIRST_COMPLETED)
            for finished in done:
                step_id = running.pop(finished)
                outputs[step_id] = finished.result().output
                if outputs[step_id].status != "Done" and steps[step_id].on_error == "stop":
                    for other in running:
                        other.cancel()
                    return _error(f"step '{step_id}' failed: {outputs[step_id].message}"), traces

        (final,) = [sid for sid in steps if not any(sid in s.after for s in steps.values())]
        return outputs[final], traces


def _error(message: str) -> AgentOutput:
    return AgentOutput(status="Error", message=message)


def load_orchestrator(
    name: str, registry: Registry | None = None, version: int | None = None
) -> LoadedOrchestrator:
    """Load an approved orchestrator and every pinned sub-agent; fail before any work starts."""
    resolved = registry or get_registry()
    record = resolved.get_orchestrator(name, version)
    if record is None:
        raise LookupError(f"approved orchestrator not found: {name}")
    agents = {step.id: load_agent(step.agent, resolved, step.version) for step in record.spec.steps}
    return LoadedOrchestrator(record=record, agents=agents)
