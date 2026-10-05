"""Result of checking whether one agent's output can feed another agent's input."""
from typing import Literal

from pydantic import Field

from .common import StrictModel


class Compatibility(StrictModel):
    verdict: Literal["compatible", "needs_mapping", "incompatible"] = Field(
        description="compatible: pass output straight through. needs_mapping: usable after "
        "reshaping or renaming fields. incompatible: B cannot work from A's output."
    )
    reason: str = Field(description="One or two sentences naming the fields that match or are missing.")
