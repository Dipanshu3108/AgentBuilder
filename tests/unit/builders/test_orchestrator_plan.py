import pytest

from agent_builder.builders.base import BuildValidationError
from agent_builder.builders.orchestrator.validate import validate_plan
from agent_builder.core.schemas import OrchestratorSpec, Step


def _plan(*steps: Step) -> OrchestratorSpec:
    return OrchestratorSpec(name="report", display_name="Report", purpose="p", steps=list(steps), rationale="r")


def _step(step_id: str, agent: str = "known", after=(), new: str = "") -> Step:
    return Step(id=step_id, instruction="do it", agent=agent, after=list(after), reason="r", new_agent_description=new)


def test_valid_plan_with_new_agent_passes():
    validate_plan(_plan(_step("a"), _step("b", "fresh-agent", ["a"], new="Writes the report")), {"known"})


@pytest.mark.parametrize(
    ("steps", "problem"),
    [
        ((_step("a", after=["b"]), _step("b", after=["a"])), "cycle"),
        ((_step("a"), _step("b")), "exactly one final step"),
        ((_step("a", "missing"),), "does not exist"),
    ],
)
def test_invalid_plans_rejected(steps, problem):
    with pytest.raises(BuildValidationError, match=problem):
        validate_plan(_plan(*steps), {"known"})
