"""Model configuration stored in the database, and references to it."""
from typing import Any

from pydantic import Field, SecretStr

from .common import StrictModel


class ModelConfig(StrictModel):
    """LiteLLM configuration. Secrets live in the model collection, never in .env."""

    id: str
    model: str = Field(description="LiteLLM model name, e.g. 'azure/gpt-4o'.")
    api_key: SecretStr
    api_base: str
    api_version: str | None = None
    temperature: float = 1.0
    max_tokens: int | None = None

    def litellm_kwargs(self) -> dict[str, Any]:
        values: dict[str, Any] = {
            "model": self.model,
            "api_key": self.api_key.get_secret_value(),
            "api_base": self.api_base,
            "temperature": self.temperature,
        }
        if self.api_version is not None:
            values["api_version"] = self.api_version
        if self.max_tokens is not None:
            values["max_tokens"] = self.max_tokens
        return values


class ModelReference(StrictModel):
    id: str
