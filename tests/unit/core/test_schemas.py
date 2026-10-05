import pytest
from pydantic import ValidationError

from agent_builder.core.schemas import AgentInput


def test_runtime_input_rejects_unknown_fields():
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        AgentInput(message="hello", unexpected=True)
