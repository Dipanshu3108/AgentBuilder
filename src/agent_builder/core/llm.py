"""LiteLLM calls shared by the builders."""
from typing import TypeVar

from litellm import acompletion
from pydantic import BaseModel

from .schemas import ModelConfig

T = TypeVar("T", bound=BaseModel)


async def structured_completion(
    model: ModelConfig, system: str, user: str, response_type: type[T]
) -> T:
    """One chat completion whose answer must validate as `response_type`."""
    response = await acompletion(
        **model.litellm_kwargs(),
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        response_format=response_type,
    )
    message = response.choices[0].message
    parsed = getattr(message, "parsed", None)
    if isinstance(parsed, response_type):
        return parsed
    if parsed is not None:
        return response_type.model_validate(parsed)
    return response_type.model_validate_json(message.content)
